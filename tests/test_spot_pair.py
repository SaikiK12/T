from dataclasses import replace
from fractions import Fraction as F
import unittest
from lab.paper_account import PaperAccount,PaperEvent,CloseMark
from lab.spot_pair import snapshot
from tests.test_spot_cash import ANCHOR,account,clock,fill,mark


class SpotPairTests(unittest.TestCase):
    def test_opening_basis_is_not_cash_profit_and_all_capital_counts(self):
        s=account(5000);p=PaperAccount({('mexc-perp-model','USDT'):5000},ANCHOR)
        s.post(fill(q='1',price='100',fee='1'),clock(1).mono_ns)
        p.post(PaperEvent('short','fill','mexc-perp-model','USDT','BTC_USDT',clock(1).utc_ns,clock(1),'invented',quantity=-1,price=102,fee=1),clock(1).mono_ns)
        m=CloseMark('mexc-perp-model','USDT','BTC_USDT',-1,102,1,clock(3),clock(3).utc_ns,'invented')
        r=snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns,spot_marks=[mark(fee='1')],perp_marks=[m])
        self.assertEqual(F(r['combined_net_pnl']),-4)
        self.assertEqual(F(r['return_on_total_capital']),F(-4,10000))
        self.assertEqual(F(r['spot']['cash']),4899);self.assertEqual(F(r['perp']['cash']),4999)
        self.assertEqual(F(r['perp']['locked_capital']),102);self.assertEqual(F(r['net_base_exposure']),0)

    def test_base_commission_detects_gross_hedge_orphan(self):
        s=account();p=PaperAccount({('p','USDT'):1000},ANCHOR)
        s.post(fill(fee='0.01',asset='BTC'),clock(1).mono_ns)
        p.post(PaperEvent('s','fill','p','USDT','BTC_USDT',clock(1).utc_ns,clock(1),'invented',quantity=-1,price=100,fee=0),clock(1).mono_ns)
        r=snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns)
        self.assertEqual(F(r['net_base_exposure']),F('-0.01'));self.assertIsNone(r['combined_nav'])

    def test_pending_fees_or_funding_withhold_total(self):
        s=account();p=PaperAccount({('p','USDT'):1000},ANCHOR)
        p.post(PaperEvent('fund','funding','p','USDT','BTC_USDT',clock(1).utc_ns,clock(1),'unknown',amount=None),clock(1).mono_ns)
        r=snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns)
        self.assertIsNone(r['combined_nav']);self.assertIsNone(r['net_base_exposure'])
        self.assertEqual(F(r['initial_total_segregated_capital']),2000)

    def test_no_fx_parity_anchor_or_hidden_position_guess(self):
        s=account();p=PaperAccount({('p','USDC'):1000},ANCHOR)
        with self.assertRaises(ValueError):snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns)
        p=PaperAccount({('p','USDT'):1000},replace(ANCHOR,mono_ns=1))
        with self.assertRaises(ValueError):snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns)
        p=PaperAccount({('p','USDT'):1000},ANCHOR)
        p.post(PaperEvent('s','fill','p','USDT','OTHER',clock(1).utc_ns,clock(1),'invented',quantity=1,price=100,fee=0),clock(1).mono_ns)
        with self.assertRaises(ValueError):snapshot(s,p,'BTCUSDT','BTC_USDT',clock(3).mono_ns)


if __name__=='__main__':unittest.main()
