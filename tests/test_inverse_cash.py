from dataclasses import replace
from decimal import Decimal
from fractions import Fraction as F
import tempfile
from pathlib import Path
import unittest

from lab.inverse_cash import (InverseContract,InverseEvent,InverseCashAccount,
                              rational,terminal_conversion,walk)
from lab.stream_quotes import FrameClock

NS=10**9;UTC=1793000000*NS
ANCHOR=FrameClock(UTC,100*NS)


def event(name,kind,seconds,price,face=0,fee=F(0)):
    return InverseEvent(name,kind,'BTC-25DEC26',UTC+seconds*NS,
                        FrameClock(UTC+seconds*NS,ANCHOR.mono_ns+seconds*NS),
                        'constructed-hand-case',price,face,fee)


class InverseCashTests(unittest.TestCase):
    def make(self,coin=F(1),journal=None):
        c=InverseContract('BTC-25DEC26','BTC',10,10,UTC+10*NS,'constructed-contract')
        return InverseCashAccount(c,coin,ANCHOR,journal_path=journal)

    def test_short_reciprocal_not_linear_dollars(self):
        a=self.make(F(1,10))
        a.post(event('open','open',1,10000,-1000),101*NS)
        a.post(event('delivery','delivery',10,12000),110*NS)
        self.assertEqual(a.price_pnl,-F(1,60))
        self.assertEqual(a.coin,F(1,12))
        self.assertEqual(a.coin*12000,1000)
        self.assertIsNone(a.snapshot()['net_usdt'])

    def test_long_has_opposite_coin_pnl(self):
        a=self.make()
        a.post(event('open','open',1,10000,1000),101*NS)
        a.post(event('delivery','delivery',10,12000),110*NS)
        self.assertEqual(a.price_pnl,F(1,60))

    def test_split_fills_require_harmonic_entry_and_old_mark_collateral(self):
        a=self.make(F(3,20))
        self.assertEqual(a.post(event('one','open',1,10000,-1000),101*NS)['status'],'applied')
        self.assertEqual(a.post(event('two','open',2,20000,-1000),102*NS)['status'],'applied')
        self.assertEqual(a.entry_reciprocal,F(3,40000))
        a.post(event('final','delivery',10,5000),110*NS)
        self.assertEqual(a.coin,F(2,5))
        self.assertEqual(a.coin*5000,2000)

    def test_daily_pnl_telescopes_without_closing_or_delivery_charge(self):
        direct=self.make(F(1,10));daily=self.make(F(1,10))
        for a in (direct,daily):a.post(event('one','open',1,10000,-1000),101*NS)
        daily.post(event('day1','daily',3,20000),103*NS)
        self.assertEqual(daily.face,-1000)
        daily.post(event('day2','daily',7,5000),107*NS)
        for a in (direct,daily):a.post(event('final','delivery',10,12000,fee=F(1,48000)),110*NS)
        self.assertEqual(direct.snapshot(),daily.snapshot())
        with self.assertRaises(ValueError):event('fee','daily',3,20000,fee=F(1,100))

    def test_delivery_is_not_spot_sale_at_twap(self):
        neutral=terminal_conversion(1000,F(1,10),F(1,10),0,0,12000,1,0)
        adverse=terminal_conversion(1000,F(1,10),F(1,10),0,0,12000,F(99,100),0)
        self.assertEqual(neutral['usdt_proceeds'],1000)
        self.assertEqual(adverse['usdt_proceeds'],990)
        self.assertIsNone(terminal_conversion(1000,F(1,10),F(1,10),0,0,12000,None,0))
        self.assertIsNone(terminal_conversion(1000,F(1,10),F(1,10),0,0,None,1,0))

    def test_fees_reduce_coin_and_reserve_retains_price_delta(self):
        result=terminal_conversion(1000,F(1,10),F(1001,10000),F(1,20000),F(1,4000),20000,1,F(1,1000))
        self.assertEqual(result['residual_coin_delta'],F(1,20000))
        self.assertEqual(result['usdt_proceeds'],F(100075,100)*F(999,1000))

    def test_expiry_and_economic_time_guards(self):
        a=self.make()
        a.post(event('open','open',1,10000,-1000),101*NS)
        self.assertEqual(a.post(event('early','delivery',9,12000),109*NS)['status'],'rejected')
        self.assertEqual(a.post(event('late-day','daily',10,12000),110*NS)['status'],'rejected')
        self.assertEqual(a.post(event('late-open','open',10,12000,-10),110*NS)['status'],'rejected')
        a.post(event('final','delivery',10,12000),110*NS)
        self.assertEqual(a.post(event('again','daily',11,12000),111*NS)['status'],'rejected')

    def test_unknown_fee_preserved_and_blocks_additional_opening(self):
        a=self.make()
        r=a.post(event('one','open',1,10000,-1000,fee=None),101*NS)
        self.assertEqual(r['entry_collateral_assessment'],'unknown_fee')
        self.assertIsNone(a.snapshot()['coin_cash'])
        self.assertEqual(a.post(event('two','open',2,10000,-1000),102*NS)['status'],'rejected')
        a.post(event('final','delivery',10,12000),110*NS)
        self.assertIsNone(a.snapshot()['coin_cash'])

    def test_full_coin_collateral_and_minimum_not_borrowed(self):
        a=self.make(F(1,100))
        self.assertEqual(a.post(event('big','open',1,10000,-1000),101*NS)['status'],'rejected')
        self.assertEqual(a.post(event('grid','open',1,10000,-15),101*NS)['status'],'rejected')
        self.assertEqual(a.face,0)

    def test_first_seen_clock_and_revision_dedup(self):
        a=self.make();e=event('one','open',1,10000,-1000)
        self.assertEqual(a.post(e,100*NS)['status'],'rejected')
        self.assertEqual(a.post(e,101*NS)['status'],'applied')
        self.assertEqual(a.post(e,102*NS)['status'],'duplicate')
        self.assertEqual(a.post(replace(e,price_usd_per_coin=11000),102*NS)['status'],'conflicting_revision')
        self.assertIsNone(a.snapshot()['coin_cash'])

    def test_append_only_reopen_and_identity_change(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cash.jsonl';a=self.make(journal=path)
            a.post(event('one','open',1,10000,-1000),101*NS)
            a.post(event('day','daily',4,20000),104*NS)
            old=path.read_bytes();b=self.make(journal=path)
            self.assertEqual(a.snapshot(),b.snapshot());self.assertEqual(old,path.read_bytes())
            b.post(event('final','delivery',10,12000),110*NS)
            self.assertTrue(path.read_bytes().startswith(old))
            self.assertEqual(self.make(journal=path).coin,F(59,60))
            with self.assertRaises(ValueError):self.make(F(2),path)

    def test_invalid_journal_tail_is_not_repaired(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'cash.jsonl';self.make(journal=path)
            with path.open('a') as h:h.write('{')
            old=path.read_bytes()
            with self.assertRaises(ValueError):self.make(journal=path)
            self.assertEqual(old,path.read_bytes())

    def test_walk_face_is_not_base_and_depth_not_extrapolated(self):
        fills,a=walk([('10000','100'),('9000','100')],200,side='sell',unit='USD_face')
        self.assertEqual(a,F(19,900));self.assertEqual(sum(n for _,n in fills),200)
        with self.assertRaises(ValueError):walk([('10000','100')],200,side='sell',unit='USD_face')
        with self.assertRaises(ValueError):walk([('9000','100'),('10000','100')],50,side='sell',unit='USD_face')

    def test_public_numeric_extremes_and_boolean_rejected(self):
        for value in (True,False,1.1,'NaN','1e-100000000','1e100000000',Decimal('1e-100000000')):
            with self.subTest(value=str(value)):
                with self.assertRaises(ValueError):rational(value)


if __name__=='__main__':unittest.main()
