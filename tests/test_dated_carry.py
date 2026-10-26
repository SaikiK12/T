from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
import unittest

from lab.dated_carry import rules,entry_plan,projected_result,local_pair_flags
from lab.executable_quotes import Receipt

UTC=1793000000*10**9;EXPIRY=1798185600*10**9


def inputs():
    meta={'result':{'instrument_name':'BTC-25DEC26','kind':'future','instrument_type':'reversed',
          'base_currency':'BTC','settlement_currency':'BTC','quote_currency':'USD','counter_currency':'USD',
          'settlement_period':'month','expiration_timestamp':EXPIRY//10**6,'is_active':True,
          'min_trade_amount':10,'contract_size':1,'tick_size':'0.5','taker_commission':'0.00035'}}
    spotmeta={'symbols':[{'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USDT','baseAssetPrecision':8,
              'status':'1','isSpotTradingAllowed':True,'tradeSideType':1,'orderTypes':['MARKET'],
              'baseSizePrecision':'0','quoteAmountPrecisionMarket':'1','maxQuoteAmountMarket':'1000000',
              'takerCommission':'0.0005'}]}
    spot={'lastUpdateId':123,'bids':[['9990','1']],'asks':[['10010','1']]}
    dated={'result':{'instrument_name':'BTC-25DEC26','timestamp':UTC//10**6,'state':'open',
                    'bids':[['10100',100],['10090',200]],'asks':[['10110',100],['10120',200]]}}
    r=Receipt(started_utc_ns=UTC-10**8,started_mono_ns=10**9,
              received_utc_ns=UTC+10**8,received_mono_ns=12*10**8)
    return meta,spotmeta,spot,dated,r


class DatedCarryTests(unittest.TestCase):
    def plan(self,profile='full'):
        m,sm,s,d,r=inputs();dr=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructedmetadata')
        return entry_plan(s,sm,r,d,dr,r,profile=profile)

    def test_minimum_is_increment_contract_size_is_not_step(self):
        m,sm,s,d,r=inputs();m['result']['min_trade_amount']=20
        dr=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructedmetadata')
        p=entry_plan(s,sm,r,d,dr,r)
        self.assertEqual(dr.contract.face_step_usd,20)
        self.assertEqual(dr.contract_size_usd,1)
        self.assertEqual(p['face_usd'],240)

    def test_active_is_not_open_and_perpetual_is_not_dated(self):
        m,sm,s,d,r=inputs();dr=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructedmetadata')
        d['result']['state']='locked'
        with self.assertRaisesRegex(ValueError,'dated_not_open'):entry_plan(s,sm,r,d,dr,r)
        m['result']['settlement_period']='perpetual'
        with self.assertRaises(ValueError):rules(m,'BTC-25DEC26','BTC',EXPIRY,'x')

    def test_linear_amount_units_cannot_enter_inverse_adapter(self):
        m,*_=inputs();m['result']['instrument_type']='linear'
        with self.assertRaises(ValueError):rules(m,'BTC-25DEC26','BTC',EXPIRY,'x')

    def test_top_depth_failure_keeps_same_face_target(self):
        p=self.plan();self.assertEqual(p['face_usd'],250)
        with self.assertRaisesRegex(ValueError,'insufficient'):self.plan('top_only')

    def test_fixed_inventory_and_all_cost_stress_without_funding(self):
        p=self.plan();nets=[]
        for k in (1,2,3):
            r=projected_result(p,cost_multiple=k,fee_control='public_standard',delivery_rate='0.00025',
                               delivery_price=10000,exit_ratio=1)
            self.assertEqual(r['total_initial_capital_usdt'],10000)
            self.assertTrue(r['coin_counted_once']);self.assertFalse(r['executable_admission'])
            self.assertIsNone(r['actual_net_usdt']);self.assertGreaterEqual(r['residual_unhedged_coin'],0)
            nets.append(r['conditional_net_usdt'])
        self.assertGreater(nets[0],nets[1]);self.assertGreater(nets[1],nets[2])

    def test_unknown_future_exit_keeps_net_unknown(self):
        r=projected_result(self.plan(),cost_multiple=2,fee_control='public_standard',delivery_rate='0.00025')
        self.assertIsNone(r['conditional_net_usdt']);self.assertIsNone(r['terminal'])

    def test_snapshot_order_and_first_seen_skew_not_repaired(self):
        m,sm,s,d,r=inputs();dr=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructedmetadata')
        s['bids']=[['10000','1'],['10001','1']]
        with self.assertRaises(ValueError):entry_plan(s,sm,r,d,dr,r)
        s=inputs()[2]
        r2=Receipt(started_utc_ns=UTC+2*10**9,started_mono_ns=31*10**8,
                   received_utc_ns=UTC+21*10**8,received_mono_ns=32*10**8)
        with self.assertRaisesRegex(ValueError,'skew'):entry_plan(s,sm,r,d,dr,r2)

    def test_between_request_clock_jump_and_common_deadline_age(self):
        _,_,_,_,r=inputs()
        r2=Receipt(started_utc_ns=UTC+100*10**9,received_utc_ns=UTC+1001*10**8,
                   started_mono_ns=15*10**8,received_mono_ns=16*10**8)
        self.assertIn('cross_receipt_clock_step_over_50ms',local_pair_flags(r,r2,r2.received_utc_ns))
        early=Receipt(started_utc_ns=UTC-18*10**8,received_utc_ns=UTC,
                      started_mono_ns=10**9,received_mono_ns=28*10**8)
        later=Receipt(started_utc_ns=UTC+4*10**8,received_utc_ns=UTC+5*10**8,
                      started_mono_ns=32*10**8,received_mono_ns=33*10**8)
        self.assertIn('spot:decision_request_age_over_2s',local_pair_flags(early,later,later.received_utc_ns))

    def test_negative_snapshot_and_face_step_are_rejected(self):
        m,sm,s,d,r=inputs();dr=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructedmetadata')
        s['lastUpdateId']=-1
        with self.assertRaises(ValueError):entry_plan(s,sm,r,d,dr,r)
        s=inputs()[2];d['result']['bids'][0][1]=105
        with self.assertRaisesRegex(ValueError,'increment'):entry_plan(s,sm,r,d,dr,r)

    def test_publication_age_is_at_common_decision_not_own_receipt(self):
        dated=Receipt(started_utc_ns=UTC+18*10**8,received_utc_ns=UTC+19*10**8,
                      started_mono_ns=18*10**8,received_mono_ns=19*10**8)
        spot=Receipt(started_utc_ns=UTC+27*10**8,received_utc_ns=UTC+28*10**8,
                     started_mono_ns=27*10**8,received_mono_ns=28*10**8)
        self.assertIn('dated_publication_age_over_2s',local_pair_flags(spot,dated,UTC))


if __name__=='__main__':unittest.main()
