from dataclasses import replace
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from lab.spot_cash import SpotCashAccount, SpotEvent, SpotMark
from lab.stream_quotes import FrameClock, NS

ANCHOR = FrameClock(1_800_000_000*NS,100*NS)


def clock(seconds):
    return FrameClock(ANCHOR.utc_ns+seconds*NS,ANCHOR.mono_ns+seconds*NS)


def account(cash=1000, **kwargs):
    return SpotCashAccount('mexc-spot-model','USDT',cash,{'BTCUSDT':'BTC'},ANCHOR,**kwargs)


def fill(event_id='buy',q='1',price='100',fee='0',asset='USDT',second=1):
    return SpotEvent(event_id,'fill','BTCUSDT',clock(second).utc_ns,clock(second),'invented-fill',
                     quantity=q,price=price,fee_amount=fee,fee_asset=asset)


def mark(q='1',proceeds='100',fee='0',second=3,verified=True):
    return SpotMark('BTCUSDT',q,proceeds,fee,clock(second),clock(second).utc_ns,verified,True,'invented-mark')


class SpotCashTests(unittest.TestCase):
    def test_spot_principal_is_spent_and_inventory_not_reserved_again(self):
        a=account();a.post(fill(q='2.5',fee='1'),clock(1).mono_ns)
        self.assertEqual(a.cash,F(749));self.assertEqual(a.holdings['BTCUSDT'],F('2.5'))
        s=a.snapshot(clock(3).mono_ns,[mark('2.5','250','1')])
        self.assertEqual(F(s['nav']),998);self.assertEqual(F(s['net_pnl']),-2)
        self.assertTrue(s['spot_inventory_not_reserved_again'])

    def test_quote_fees_enter_cost_pool_and_are_not_subtracted_twice(self):
        a=account();a.post(fill(fee='10'),clock(1).mono_ns)
        a.post(fill('sell','-1','100','5',second=2),clock(2).mono_ns)
        s=a.snapshot(clock(3).mono_ns)
        self.assertEqual(F(s['cash']),985);self.assertEqual(F(s['net_pnl']),-15)
        self.assertEqual(a.realized,-15);self.assertEqual(a.cost_pool['BTCUSDT'],0)

    def test_base_buy_fee_reduces_hedgeable_quantity_and_preserves_principal(self):
        a=account();a.post(fill(fee='0.01',asset='BTC'),clock(1).mono_ns)
        self.assertEqual(a.cash,900);self.assertEqual(a.holdings['BTCUSDT'],F('0.99'))
        self.assertEqual(a.cost_pool['BTCUSDT'],100)
        s=a.snapshot(clock(3).mono_ns,[mark('0.99','99')])
        self.assertEqual(F(s['net_pnl']),-1)
        self.assertEqual(F(1)-a.holdings['BTCUSDT'],F('0.01'))  #Gross-sized perp hedge would be orphaned.
        a.post(fill('close','-0.99','100',second=4),clock(4).mono_ns)
        self.assertEqual(a.realized,-1);self.assertEqual(a.cash,999)

    def test_base_sell_fee_consumes_more_inventory_than_gross_sale(self):
        a=account();a.post(fill(),clock(1).mono_ns)
        a.post(fill('close','-0.99','100','0.01','BTC',2),clock(2).mono_ns)
        self.assertEqual(a.holdings['BTCUSDT'],0);self.assertEqual(a.realized,-1)
        self.assertEqual(a.cash,999)
        self.assertEqual(a.post(fill('short','-0.1',second=3),clock(3).mono_ns)['status'],'rejected')

    def test_missing_or_third_token_fee_withholds_nav_and_new_fills(self):
        for fee,asset in ((None,'USDT'),('0.01','MX'),('0',None)):
            a=account();a.post(fill(fee=fee,asset=asset),clock(1).mono_ns)
            self.assertIsNone(a.snapshot(clock(3).mono_ns,[mark()])['nav'])
            self.assertEqual(a.post(fill('again','0.1',second=3),clock(3).mono_ns)['status'],'rejected')
            self.assertFalse(a.snapshot(clock(3).mono_ns,[mark()])['model_new_buys_allowed'])

    def test_delayed_quote_fee_preserves_deficit_risk_across_deposit(self):
        a=account(100);a.post(fill(fee=None),clock(1).mono_ns)
        e=SpotEvent('fee','fee_resolution','BTCUSDT',clock(1).utc_ns,clock(2),'invented-receipt',
                    fee_amount='1',fee_asset='USDT',resolves='buy')
        self.assertEqual(a.post(e,clock(2).mono_ns)['status'],'applied')
        self.assertEqual(a.cash,-1);self.assertEqual(a.cost_pool['BTCUSDT'],101)
        deposit=SpotEvent('external','capital_change','__capital__',clock(3).utc_ns,clock(3),'invented-flow',amount='101')
        a.post(deposit,clock(3).mono_ns)
        s=a.snapshot(clock(3).mono_ns,[mark()])
        self.assertEqual(F(s['net_pnl']),-1);self.assertFalse(s['model_new_buys_allowed'])
        self.assertTrue(s['historical_risk_events'])

    def test_fee_resolution_cannot_relabel_known_asset_or_magnitude(self):
        for fee,asset,newfee,newasset in (('0.1',None,'0.2','USDT'),(None,'USDT','0.1','BTC'),('0.01','MX','0.01','USDT')):
            a=account();a.post(fill(fee=fee,asset=asset),clock(1).mono_ns)
            e=SpotEvent('fee','fee_resolution','BTCUSDT',clock(1).utc_ns,clock(2),'invented-receipt',
                        fee_amount=newfee,fee_asset=newasset,resolves='buy')
            self.assertEqual(a.post(e,clock(2).mono_ns)['status'],'rejected')
            self.assertIn('buy',a.pending)

    def test_borrow_missing_marks_and_uncertified_clock_fail_closed(self):
        a=account(10)
        self.assertEqual(a.post(fill(),clock(1).mono_ns)['status'],'rejected')
        self.assertEqual(a.post(fill('short','-1',second=2),clock(2).mono_ns)['status'],'rejected')
        a=account();a.post(fill(),clock(1).mono_ns)
        for marks in ([],[mark(verified=False)],[mark(fee=None)],[replace(mark(),inventory_consumed=D('0.9'))]):
            self.assertIsNone(a.snapshot(clock(3).mono_ns,marks)['nav'])

    def test_dedup_financial_revisions_and_durable_reopening(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary)/'spot.jsonl';a=account(journal_path=p);e=fill(fee='0.10')
            a.post(e,clock(1).mono_ns)
            duplicate=replace(e,clock=clock(2),fee_amount=D('0.1'))
            self.assertEqual(a.post(duplicate,clock(2).mono_ns)['status'],'duplicate')
            snapshot=a.snapshot(clock(3).mono_ns,[mark()])
            self.assertEqual(account(journal_path=p).snapshot(clock(3).mono_ns,[mark()]),snapshot)
            with self.assertRaises(ValueError):account(999,journal_path=p)
            revision=replace(e,quantity=D(2),clock=clock(3))
            self.assertEqual(a.post(revision,clock(3).mono_ns)['status'],'conflicting_revision')
            self.assertIsNone(a.snapshot(clock(3).mono_ns,[mark()])['nav'])

    def test_imports_require_explicit_simulation_and_exact_decimal_fields(self):
        e=fill();data=e.mapping();self.assertEqual(SpotEvent.from_mapping(data),e)
        data.pop('simulation_only')
        with self.assertRaises(ValueError):SpotEvent.from_mapping(data)
        with self.assertRaises(ValueError):fill(price=0.1)
        with self.assertRaises(ValueError):SpotEvent('fund','funding','BTCUSDT',clock(1).utc_ns,clock(1),'not-spot')


if __name__=='__main__':unittest.main()
