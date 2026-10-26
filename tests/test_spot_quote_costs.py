from dataclasses import replace
from decimal import Decimal as D
import unittest
from lab.executable_quotes import Receipt,RestBook
from lab.microstructure import DepthLevel
from lab.spot_quote_costs import spot_rules,spot_book,illustrative_quantity,conditional_costs


def info(**kw):
    row=dict(symbol='BTCUSDT',baseAsset='BTC',quoteAsset='USDT',status='1',baseAssetPrecision=4,
             baseSizePrecision='0.3',quoteAmountPrecisionMarket='1',maxQuoteAmountMarket='100000',
             takerCommission='0.001',isSpotTradingAllowed=True,tradeSideType=1,orderTypes=['MARKET'])
    return {'symbols':[{**row,**kw}]}


def metadata(**kw):
    return {**dict(symbol='BTC_USDT',type=1,settleCoin='USDT',contractSize='0.001',volUnit=1,
                   minVol=1,maxVol=100000,apiAllowed=True,state=0,takerFeeRate='0.002'),**kw}


def books():
    receipt=Receipt(1_800_000_000_000_000_000,1_800_000_000_100_000_000,100_000_000_000,100_100_000_000)
    s=spot_book('BTCUSDT',{'lastUpdateId':1,'bids':[['99','1'],['98','1']],'asks':[['101','1'],['102','1']]},receipt)
    p=RestBook('mexc','BTC_USDT',receipt,(DepthLevel(101,1),DepthLevel(100,1)),
               (DepthLevel(103,1),DepthLevel(104,1)),None,'unverified',1)
    return s,p


class SpotQuoteCostTests(unittest.TestCase):
    def test_source_minimum_is_not_a_lot_increment(self):
        r=spot_rules('BTCUSDT',info());q,step=illustrative_quantity(r,metadata(),100)
        self.assertEqual(r.minimum_base,D('.3'));self.assertIsNone(r.lot_step_base)
        self.assertEqual(step,D('.001'));self.assertEqual(q,D('2.5'))
        self.assertNotEqual(q/r.minimum_base,(q/r.minimum_base).to_integral_value())
        self.assertIsNone(r.price_tick_quote)

    def test_spot_clock_absent_and_crossed_doc_example_rejected(self):
        s,p=books();self.assertIsNone(s.reported_timestamp_ms);self.assertEqual(s.version,1)
        with self.assertRaises(ValueError):spot_book('BTCUSDT',{'lastUpdateId':5,'bids':[['15','10']],'asks':[['14','1']]},s.receipt)

    def test_four_crossings_and_advertised_fee_cash_once(self):
        s,p=books();r=spot_rules('BTCUSDT',info())
        x=conditional_costs(s,p,r,metadata(),1,fee_control='advertised_quote_fee')
        self.assertEqual(D(x['crossing_quote']),4);self.assertEqual(D(x['commission_quote']),D('.608'))
        self.assertEqual([D(c['required_gross_quote_to_break_even']) for c in x['costs']],[D('4.608'),D('9.216'),D('13.824')])
        self.assertFalse(x['executable_pair_eligible']);self.assertIsNone(x['net_market_return'])

    def test_top_capacity_failure_never_shrinks_quantity(self):
        s,p=books();r=spot_rules('BTCUSDT',info())
        x=conditional_costs(s,p,r,metadata(),D('1.5'),profile='top_only')
        self.assertIsNone(x['costs']);self.assertIn('insufficient_shown_depth_fixed_quantity',x['conditional_calculation_reasons'])
        self.assertEqual(x['illustrative_base_quantity'],'1.5')
        self.assertIsNotNone(conditional_costs(s,p,r,metadata(),D('1.5'))['costs'])

    def test_minimum_amount_uses_both_actual_spot_fill_sides(self):
        s,p=books();r=spot_rules('BTCUSDT',info(quoteAmountPrecisionMarket='100'))
        x=conditional_costs(s,p,r,metadata(),1)
        self.assertIsNone(x['costs']);self.assertIn('spot_below_minimum_market_amount',x['conditional_calculation_reasons'])

    def test_missing_public_fee_is_not_zero_and_control_is_explicit(self):
        s,p=books();r=spot_rules('BTCUSDT',info(takerCommission=None))
        self.assertIsNone(conditional_costs(s,p,r,metadata(),1,fee_control='advertised_quote_fee')['costs'])
        x=conditional_costs(s,p,r,metadata(),1,fee_control='zero_charge')
        self.assertEqual(D(x['commission_quote']),0);self.assertFalse(x['executable_pair_eligible'])

    def test_public_permission_or_direction_flags_do_not_become_admission(self):
        s,p=books();r=spot_rules('BTCUSDT',info(status='2',isSpotTradingAllowed=False,tradeSideType=2))
        x=conditional_costs(s,p,r,metadata(apiAllowed=False),1)
        self.assertEqual(len(x['public_rule_flags']),4);self.assertFalse(x['executable_pair_eligible'])
        self.assertIsNone(x['costs'])

    def test_local_clock_skew_not_removed_by_unreported_source_clock(self):
        s,p=books();p=replace(p,receipt=Receipt(p.receipt.started_utc_ns,p.receipt.received_utc_ns+2_000_000_000,
                                             p.receipt.started_mono_ns,p.receipt.received_mono_ns+2_000_000_000))
        x=conditional_costs(s,p,spot_rules('BTCUSDT',info()),metadata(),1)
        self.assertIsNone(x['costs']);self.assertTrue(x['conditional_calculation_reasons'])

    def test_unknown_minimum_or_wrong_underlying_is_not_assumed(self):
        s,p=books();r=spot_rules('BTCUSDT',info(baseSizePrecision=None))
        self.assertIsNone(conditional_costs(s,p,r,metadata(),1)['costs'])
        with self.assertRaises(ValueError):illustrative_quantity(r,metadata(symbol='OTHER_USDT'),100)
        with self.assertRaises(ValueError):spot_rules('BTCUSDT',info(baseAsset='OTHER'))

    def test_precision_and_metadata_number_bounds(self):
        for changes in ({'baseAssetPrecision':True},{'takerCommission':'bad'},{'takerCommission':'-1'},
                        {'baseSizePrecision':'1e-1000000'},{'isSpotTradingAllowed':1},{'tradeSideType':'1'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):spot_rules('BTCUSDT',info(**changes))

    def test_direct_cost_call_cannot_bypass_lattice_or_payout_contract(self):
        s,p=books();r=spot_rules('BTCUSDT',info(baseSizePrecision='.001'))
        for q in (D('.5005'),D('.50001')):
            self.assertIsNone(conditional_costs(s,p,r,metadata(),q)['costs'])
        self.assertIsNone(conditional_costs(s,p,r,metadata(state=False),1)['costs'])
        with self.assertRaises(ValueError):conditional_costs(s,p,r,metadata(type=2),1)

    def test_rounded_quote_boundary_stays_unknown(self):
        s,p=books();r=spot_rules('BTCUSDT',info(quoteAmountPrecisionMarket='99'))
        x=conditional_costs(s,p,r,metadata(),1)
        self.assertIsNone(x['costs']);self.assertIn('spot_minimum_quote_rounding_boundary_unknown',x['conditional_calculation_reasons'])


if __name__=='__main__':unittest.main()
