from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from lab.acquisition_budget import BudgetError
from lab.paper_account import PaperAccount,PaperEvent,CloseMark
from lab.stream_quotes import FrameClock,NS
from scripts.check_paper_account import LinearOracle,close

UTC=1_790_000_000*NS
ANCHOR=FrameClock(UTC,10*NS)


def clock(s):return FrameClock(UTC+int(s*NS),ANCHOR.mono_ns+int(s*NS))


def event(i,kind='fill',second=1,**kw):
    fields=dict(event_id=str(i),kind=kind,venue='mexc',asset='USDT',symbol='BTC',
                occurred_ns=clock(second).utc_ns,clock=clock(second),source_identity='invented fixture',simulation_only=True)
    if kind=='fill':fields.update(quantity=1,price=100,fee=0)
    return PaperEvent(**{**fields,**kw})


class AccountTests(unittest.TestCase):
    def account(self,**kw):return PaperAccount({('mexc','USDT'):1000,('lighter','USDC'):1000},ANCHOR,**kw)

    def mx(self,a,second=10,marks=()):return a.snapshot(clock(second).mono_ns,marks)['accounts'][1]

    def test_partial_reversal_flat_cash_agrees_with_independent_decimal_oracle(self):
        a=self.account();o=LinearOracle('mexc','USDT',1000)
        for i,(q,p,f) in enumerate(((2,100,1),(2,110,'.5'),(-1,120,'.2'),(-5,90,'.3'),(2,80,'.1')),1):
            e=event(i,second=i,quantity=q,price=p,fee=f)
            self.assertEqual(a.post(e,clock(i).mono_ns)['status'],'applied');o.fill('BTC',q,p,f)
            close(self.mx(a,i)['known_cash_component'],o.cash,'independent cash')
        a.post(event('f','funding',6,amount=3),clock(6).mono_ns);o.funding_post(3,'USDT')
        for key,value in o.snapshot({}).items():close(self.mx(a,6)[key],value,key)
        self.assertEqual(self.mx(a,6)['cash'],'990.9')

    def test_opening_notional_reserves_capital_but_does_not_spend_it(self):
        a=self.account();a.post(event(1,quantity=2,fee=1),clock(1).mono_ns)
        x=self.mx(a,1);self.assertEqual(x['cash'],'999');self.assertEqual(x['locked_capital'],'200')
        self.assertEqual(x['available_capital'],'799');self.assertIsNone(x['nav'])

    def test_long_bid_short_ask_marks_and_future_exit_fee_are_separate(self):
        for q,exit_notional,pnl in ((2,198,-2),(-2,202,-2)):
            a=self.account();a.post(event(1,quantity=q,fee=1),clock(1).mono_ns)
            m=CloseMark('mexc','USDT','BTC',q,exit_notional,'.2',clock(2),clock(2).utc_ns,'fixture mark')
            x=self.mx(a,2,[m]);self.assertEqual(D(x['unrealized_liquidation_pnl']),D(pnl))
            self.assertEqual(D(x['nav']),D('996.8'));self.assertEqual(x['fees_paid'],'1')

    def test_stale_future_wrong_quantity_or_unknown_fee_marks_do_not_certify_nav(self):
        a=self.account();a.post(event(1),clock(1).mono_ns)
        good=CloseMark('mexc','USDT','BTC',1,99,1,clock(2),clock(2).utc_ns,'fixture')
        for m in (replace(good,clock=clock(3)),replace(good,clock=clock(0)),
                  replace(good,source_time_ns=clock(0).utc_ns-1),replace(good,position_quantity=2),
                  replace(good,estimated_exit_fee=None)):
            x=self.mx(a,2,[m]);self.assertIsNone(x['nav']);self.assertEqual(x['cash'],'1000')

    def test_unknown_fee_and_funding_resolve_only_by_new_receipt_without_rewriting(self):
        a=self.account();a.post(event('open',fee=None),clock(1).mono_ns)
        a.post(event('fund','funding',2,amount=None),clock(2).mono_ns)
        x=self.mx(a,2);self.assertIsNone(x['cash']);self.assertIsNone(x['realized_net_pnl'])
        self.assertEqual(x['known_cash_component'],'1000')
        a.post(event('fee','fee_resolution',3,amount=2,resolves='open'),clock(3).mono_ns)
        self.assertIsNone(self.mx(a,3)['cash'])
        e=event('resolve','funding_resolution',4,amount=3,resolves='fund')
        a.post(e,clock(4).mono_ns);self.assertEqual(self.mx(a,4)['cash'],'1001')
        self.assertEqual(a.post(e,clock(4).mono_ns)['status'],'duplicate')
        self.assertEqual(self.mx(a,4)['cash'],'1001');self.assertEqual(len(a.attempts),5)
        with self.assertRaises(ValueError):self.mx(a,2)

    def test_redelivery_changes_neither_cash_nor_original_economic_identity(self):
        a=self.account();e=event(1,fee=1);a.post(e,clock(1).mono_ns)
        later=replace(e,clock=clock(2),price=D('100.0'),quantity=D('1.0'))
        self.assertEqual(a.post(later,clock(2).mono_ns)['status'],'duplicate')
        self.assertEqual(self.mx(a,2)['cash'],'999');self.assertEqual(len(a.positions),1)

    def test_financial_revision_and_late_fill_taint_totals_instead_of_hiding_loss(self):
        for altered in (event(1,second=2,price=110),event('late',second=.5,price=80)):
            a=self.account();a.post(event(1),clock(1).mono_ns)
            a.post(altered,clock(2).mono_ns);x=self.mx(a,2)
            self.assertIsNone(x['cash']);self.assertIsNone(x['realized_net_pnl'])
            self.assertTrue(x['reconciliation_required']);self.assertEqual(x['known_cash_component'],'1000')

    def test_future_receipt_never_posts_or_taints_earlier_state(self):
        a=self.account();a.post(event(1),clock(1).mono_ns)
        bad=event(1,second=3,price=999)
        self.assertEqual(a.post(bad,clock(2).mono_ns)['status'],'rejected')
        self.assertEqual(self.mx(a,2)['cash'],'1000')
        with self.assertRaises(ValueError):event(9,occurred_ns=clock(2).utc_ns)

    def test_external_deposit_is_not_profit_and_collateral_never_crosses_venues(self):
        a=self.account();a.post(event('deposit','capital_change',1,amount=100),clock(1).mono_ns)
        x=self.mx(a,1);self.assertEqual(x['cash'],'1100');self.assertEqual(x['model_net_return'],'0')
        a.post(event('too big',second=2,quantity=20),clock(2).mono_ns)
        x=self.mx(a,2);self.assertIn('simulated_collateral_shortfall',x['reasons'])
        self.assertEqual(a.snapshot(clock(2).mono_ns)['accounts'][0]['cash'],'1000')
        self.assertEqual(a.post(event('wrong',asset='USDC',second=3),clock(3).mono_ns)['status'],'rejected')

    def test_execution_drag_is_diagnostic_not_an_additional_fee(self):
        a=self.account();a.post(event(1,price=101,fee=1,reference_mid=100),clock(1).mono_ns)
        a.post(event(2,second=2,quantity=-1,price=99,fee=1,reference_mid=100),clock(2).mono_ns)
        x=self.mx(a,2);self.assertEqual(x['realized_price_pnl'],'-2');self.assertEqual(x['cash'],'996')
        self.assertEqual(x['execution_drag_diagnostic_not_additive'],'2')

    def test_position_coverage_comes_from_accepted_fills_and_ends_at_observation(self):
        a=self.account();a.post(event(1,quantity=2),clock(1).mono_ns)
        a.post(event(2,second=2,quantity=-1),clock(2).mono_ns)
        spans=a.position_spans('mexc','USDT','BTC',clock(3))
        self.assertEqual([s.quantity for s in spans],[D(0),D(2),D(1)])
        self.assertEqual(spans[-1].end_ns,clock(3).utc_ns)
        a.post(event('late',second=.5),clock(4).mono_ns)
        self.assertIsNone(a.position_spans('mexc','USDT','BTC',clock(4)))

    def test_append_only_reopen_idempotence_baseline_and_corrupt_tail(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'account.jsonl';a=self.account(journal_path=path);e=event(1,fee=1)
            a.post(e,clock(1).mono_ns);prefix=path.read_bytes()
            b=self.account(journal_path=path)
            self.assertEqual(b.post(e,clock(2).mono_ns)['status'],'duplicate')
            self.assertTrue(path.read_bytes().startswith(prefix));self.assertEqual(self.mx(b,2)['cash'],'999')
            self.assertEqual(self.mx(a,2)['cash'],'999')
            with self.assertRaises(ValueError):PaperAccount({('mexc','USDT'):2000},ANCHOR,journal_path=path)
            with path.open('a') as f:f.write('partial')
            with self.assertRaises(BudgetError):self.account(journal_path=path)

    def test_schema_refuses_spot_cash_override_nonfinite_and_untyped_clocks(self):
        for change in ({'amount':100},{'quantity':True},{'fee':'NaN'},{'price':0},
                       {'simulation_only':False},{'clock':{'utc_ns':UTC,'mono_ns':0}}):
            with self.assertRaises(ValueError):event(1,**change)
        with self.assertRaises(ValueError):PaperEvent.from_mapping({**event(1).mapping(),'secret':'invented'})

