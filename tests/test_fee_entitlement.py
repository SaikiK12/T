from decimal import Decimal as D
from fractions import Fraction as F
import unittest

from lab.fee_entitlement import fee_view,bind_opportunity_fee,rounded_cost_interval,membership,payoff_interval
from tests.test_opportunity_value import fixture,batch_case
from scripts.run_fee_entitlement import prepare_rows,evaluate,H,DAY,GRID0,D0
from scripts.check_fee_entitlement import exposure_max

ID='a'*64


def view(data=None,**changes):
    args=dict(instrument='ETH',source_identity=ID,origin='official_documentation_example',rate_unit='fraction',
        received_utc_ns=1000000000,asof_utc_ns=1000000000);args.update(changes)
    return fee_view({'success':True,'code':0,'data':data or {'symbol':'ETH','realTakerFee':'.0002','feeRateMode':'NORMAL'}},**args)


class FeeEvidenceTests(unittest.TestCase):
    def test_real_rate_is_not_discounted_twice(self):
        x=view({'symbol':'ETH','realTakerFee':'.0002','discountRate':'.5','deductRate':'.8',
                'joinDiscount':True,'enjoyDiscount':True,'feeRateMode':'NORMAL'})
        self.assertEqual(x['conditional_fraction_hypothesis_bp'],2)
        self.assertIsNone(x['opportunity_fee_bp']);self.assertFalse(x['owner_entitlement_verified'])

    def test_public_zero_cannot_promote_positive_native_opportunity(self):
        o=fixture();baseline=batch_case([o]);self.assertTrue(baseline['rows'][0]['conditional_batch_inclusion'])
        v=view({'symbol':'ETH','takerFeeRate':0},origin='public_contract_metadata')
        def change(inputs):
            patch=bind_opportunity_fee(inputs['market_reports'][o.opportunity_id],v)
            inputs['market_reports'][o.opportunity_id]=patch['market_report'];inputs['fees_bp'][o.opportunity_id]=patch['fee_bp']
            inputs['risk_inputs']['fee_inputs_known']=patch['risk_fee_inputs_known']
        after=batch_case([o],mutate=change)
        self.assertFalse(after['rows'][0]['conditional_batch_inclusion']);self.assertEqual(after['account_before'],after['account_after'])
        self.assertIn('cost:fee_unknown',after['rows'][0]['reasons'])

    def test_example_period_and_dynamic_tier_not_current_entitlement(self):
        x=view({'symbol':'ETH','realTakerFee':0,'feeRateMode':'TIERED','statisticType':'FIXED',
                'fixedStartTime':0,'fixedEndTime':1})
        self.assertIn('outside_published_fixed_period',x['flags']);self.assertIn('future_tier_leverage_quota_path_unverified',x['flags'])
        self.assertIsNone(x['actual_expected_net'])

    def test_nonfee_values_are_not_read_or_returned(self):
        class Forbidden:
            def __str__(self):raise AssertionError('nonfee value inspected')
        x=view({'symbol':'ETH','realTakerFee':0,'feeRateMode':'NORMAL','walletBalance':Forbidden(),'apiSecret':Forbidden()})
        self.assertNotIn('walletBalance',x);self.assertNotIn('apiSecret',x)

    def test_wrong_instrument_future_stale_unknown_units_and_exports_stay_unknown(self):
        self.assertIn('instrument_binding_missing_or_different',view({'symbol':'OTHER','realTakerFee':0})['flags'])
        self.assertIn('future_receipt',view(asof_utc_ns=0)['flags'])
        self.assertIn('receipt_older_than_1s',view(asof_utc_ns=3000000000)['flags'])
        self.assertIsNone(view(rate_unit='unknown')['conditional_fraction_hypothesis_bp'])
        self.assertFalse(view(origin='owner_redacted_export')['owner_entitlement_verified'])

    def test_rounded_floor_is_not_silently_a_point_estimate(self):
        self.assertEqual(rounded_cost_interval({'median_half_spread_bp':'.623','one_way_bp':1}),(F(1,10000),F(1,10000)))
        lo,hi=rounded_cost_interval({'median_half_spread_bp':1,'one_way_bp':1})
        self.assertEqual(lo,F(1,10000));self.assertEqual(hi,F('1.0005')/10000)
        lo,hi=rounded_cost_interval({'median_half_spread_bp':'5.195','one_way_bp':'5.195'})
        self.assertEqual(hi-lo,F('.001')/10000)
        with self.assertRaises(ValueError):rounded_cost_interval({'median_half_spread_bp':2,'one_way_bp':1})

    def test_ambiguous_threshold_preserves_active_and_inactive_completions(self):
        c=(F('.0001'),F('.0002'));self.assertEqual(membership(F('.0006'),c),'ambiguous')
        self.assertEqual(payoff_interval('.01',1,'ambiguous',c,8,3),(F(0),F('.0046')))
        self.assertEqual(payoff_interval('-.01',1,'ambiguous',c,8,3),(F('-.016'),F(0)))
        self.assertEqual(payoff_interval(None,1,'certain',c,8,3),(None,None))
        self.assertEqual(payoff_interval(None,1,'inactive',c,8,3),(F(0),F(0)))

    def test_exact_break_even_and_no_spread_double_charge(self):
        c=(F('.0001'),)*2
        self.assertEqual(payoff_interval('.002',1,'certain',c,8,1),(F('.0002'),)*2)
        self.assertEqual(payoff_interval('.002',1,'certain',c,8,2),(F('-.0016'),)*2)
        for bad in (True,1.0,'NaN'):
            with self.assertRaises(ValueError):view({'symbol':'ETH','realTakerFee':bad})

    def test_finite_invented_family_retains_ambiguous_selection_and_all_costs(self):
        t=D0*DAY
        def event(symbol,edge,g):return {'symbol':symbol,'t':str(t),'exit':str((t-GRID0)//H+1),'g':g,'E_sigma':edge,'sig':'1'}
        cost={'A':{'contract':'A_USDT','median_half_spread_bp':'.5','one_way_bp':1},
              'B':{'contract':'B_USD1','median_half_spread_bp':1,'one_way_bp':1}}
        rows,excluded=prepare_rows([event('B','.0004001','.005'),event('A','.01','.01')],cost)
        self.assertEqual([r['symbol'] for r in rows],['A','B']);self.assertEqual(rows[1]['PZ_status'],'ambiguous')
        config={'capital':'10000','entry_notional':'500','policies':['PZ','THROUGH','AWAY'],
            'cost_multiples':[1,2,3],'additional_fee_bp':[0,4,8],'cash_annual_scenarios':['0','.03']}
        cells,frontiers=evaluate(rows,config);self.assertEqual(len(cells),27);self.assertEqual(len(frontiers),9)
        cell=cells[0];self.assertEqual(cell['certain_count'],1);self.assertEqual(cell['ambiguous_count'],1)
        self.assertLess(cell['proxy_quote_total_lo'],cell['proxy_quote_total_hi'])
        self.assertIsNone(cell['actual_executable_expected_net']);self.assertIsNone(cell['exposure']['actual_account_nav'])
        self.assertEqual(exposure_max(rows,'PZ',0,F(500),False)[0],2)
        mutated=[event('B','.0004001','-100'),event('A','.01','-100')]
        self.assertEqual([r['PZ_status'] for r in prepare_rows(mutated,cost)[0]],[r['PZ_status'] for r in rows])

    def test_half_open_intervals_missing_payoffs_and_unsorted_source_rows(self):
        t=D0*DAY;cost={'A':{'contract':'A_USDT','median_half_spread_bp':'.5','one_way_bp':1}}
        def event(at,g):return {'symbol':'A','t':str(at),'exit':str((at-GRID0)//H+1),'g':g,'E_sigma':'.01','sig':'1'}
        rows,_=prepare_rows([event(t+2*H,''),event(t,'.01')],cost)
        self.assertEqual(exposure_max(rows,'THROUGH',8,F(500),False)[0],1)
        tied=[dict(r) for r in rows];tied[1]['entry_ms']=tied[0]['exit_ms']
        self.assertEqual(exposure_max(tied,'THROUGH',8,F(500),False)[0],1)
        with self.assertRaisesRegex(ValueError,'overlapping'):prepare_rows([event(t,'.01'),event(t+H,'.01')],cost)
        config={'capital':'10000','entry_notional':'500','policies':['PZ','THROUGH','AWAY'],
            'cost_multiples':[1,2,3],'additional_fee_bp':[0,4,8],'cash_annual_scenarios':['0','.03']}
        cells,_=evaluate(rows,config)
        self.assertTrue(all(c['proxy_quote_total_lo'] is None and c['missing_active_payoff_count']==1 for c in cells))
