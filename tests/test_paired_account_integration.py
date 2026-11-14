import json
from pathlib import Path
import tempfile
import unittest
from scripts.run_paired_account import run_case,economic_rows

ROOT=Path(__file__).resolve().parents[1]


class PairedIntegrationTests(unittest.TestCase):
    def test_finite_paths_have_intended_states_and_unchanged_replay(self):
        c=json.loads((ROOT/'experiments/paired_execution_v1/fixtures.json').read_text())
        expected=('inactive','pending_orders','flat','exposed','exposed','exposed','hedged','unknown',
                  'unknown','unknown','hedged','exposed','unknown','unknown','unknown','exposed')
        with tempfile.TemporaryDirectory() as d:
            for case,state in zip(c['cases'],expected):
                for k in (1,2,3):
                    with self.subTest(case=case['name'],cost=k):
                        r=run_case(c,case,k,Path(d));self.assertEqual(r['snapshot']['pair']['state'],state)
                        self.assertTrue(r['journal_replay_identical'])
                        if state=='unknown':self.assertTrue(all(a['nav'] is None for a in r['snapshot']['accounts']))

    def test_reported_entry_basis_is_not_instantaneous_closed_perp_pnl(self):
        # Invented fixed sweeps with a large apparent cross-venue price gap.
        c={'displayed_fillable':True,'venue_margin_mid_notionals_usd':[100,110],
           'long_mexc_entry_cost_usd':1.1443,'long_lighter_entry_cost_usd':1.1437,
           'scenarios':[{'round_trip_cost_usd':k*2.288} for k in (1,2,3)]}
        size={'cost':c,'quantity_base':'1','observed_quantity':{'current_buy_sell_quote':[100.5,99.5,110.5,109.5]}}
        row={'sizes':[None,None,None,size],'symbol':'BTC','grid_second':10,'delay_ms':0,'readiness':{'state':'unknown'}}
        a,b=list(economic_rows([row]));self.assertGreater(float(a['scenarios'][0]['entry_basis_after_model_cost_quote']),0)
        for r in (a,b):
            for s in r['scenarios']:self.assertLess(float(s['instantaneous_paired_unwind_net_quote']),0)
            self.assertIsNone(r['actual_expected_funding']);self.assertFalse(r['execution_ready'])
        for one in a['scenarios'][0]['one_leg_failure_scenarios']:
            self.assertIsNone(one['probability']);self.assertFalse(one['future_exit_observed'])

