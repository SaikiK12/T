import unittest
from unittest.mock import patch
import numpy as np
from scripts.run_dependent_null import flags,summarize_cell,assess,base_intervals
from lab.dependent_null import METHODS


class NullRunnerTests(unittest.TestCase):
    def test_translation_detects_true_coordinate_and_retains_false_null_coordinates(self):
        r={'lower':[-.2,-.2,.01],'upper':[.2,.2,.3]}
        zero=flags(r,0);shift=flags(r,.5)
        self.assertFalse(zero['positive_detection']);self.assertTrue(shift['positive_detection'])
        self.assertTrue(zero['any_rejection']);self.assertTrue(shift['null_coordinate_exclusion'])
        self.assertEqual(r['lower'][0],-.2)
        self.assertIsNone(flags({'lower':None,'upper':None},.5))

    def test_unknown_replications_are_unscored_not_successes(self):
        p={'id':'gaussian_rho0.6','kind':'stationary','rho':.6,'tail':'gaussian'}
        r=summarize_cell(p,'calibrated_obm28',.5,[None,None],2)
        self.assertIsNone(r['power']);self.assertEqual(r['unscored_paths'],2)
        r=summarize_cell(p,'calibrated_obm28',0,[None,None],2)
        self.assertIsNone(r['family_false_exclusions'])

    def test_size_pass_cannot_hide_zero_power_or_authorize_market(self):
        rows=[];profiles=['gaussian_rho0.6']+[f'other{i}' for i in range(9)]
        for m in METHODS:
            for profile in profiles:
                rows.append({'method':m,'effect_shift':0,'profile':profile,'state':'COMPLETE',
                    'family_false_exclusion_fraction':0,'exact_binomial_interval':[0,.02]})
            rows.append({'method':m,'effect_shift':.5,'profile':'gaussian_rho0.6','state':'COMPLETE','power':0})
        r=assess(rows,profiles);self.assertTrue(all(x['state']=='NOT_ACCEPTED' for x in r))
        self.assertTrue(all(x['actual_order_allowed'] is False for x in r))
        for row in rows:
            if row['effect_shift']==.5:row['power']=.5
        r=assess(rows,profiles);self.assertEqual(sum(x['state']=='FINITE_SYNTHETIC_CANDIDATE' for x in r),2)
        self.assertTrue(all(x['market_validated'] is False for x in r))
        r=assess([x for x in rows if x['profile']!='other8'],profiles)
        self.assertTrue(all(x['state']=='NOT_ACCEPTED' for x in r))

    def test_failed_calibration_keeps_calibrated_methods_unknown(self):
        # Deterministic engineered path, not a production random calibration.
        x=np.column_stack([np.sin(np.arange(273)+j) for j in range(3)])
        with patch('scripts.run_dependent_null.block_intervals',return_value={'lower':[-1]*3,'upper':[1]*3}):
            r=base_intervals(x,{'state':'INCONCLUSIVE'},123)
        self.assertIsNone(r['calibrated_obm14']['lower']);self.assertIsNone(r['calibrated_obm28']['upper'])
