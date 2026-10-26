import json
from pathlib import Path
import tempfile
import unittest

from lab.paper_admission import legacy_projection,REQUIRED
from scripts.paper_status import datasets


class PaperAdmissionTests(unittest.TestCase):
    def test_native_net_or_ontime_does_not_certify_complete_executable_money(self):
        row={'series':'old','kind':'ontime','net':.01,'net_2x':None,'net_3x':-.01,
             **{k:True for k in REQUIRED}}
        p=legacy_projection([row,{**row,'kind':'replay'}])[0]
        self.assertEqual(p['reported_rows'],2);self.assertEqual(p['native_missing_money_rows'],2)
        self.assertEqual(p['native_ontime_labels'],1)
        self.assertEqual(p['strict_executable_scored_days'],0)
        self.assertIsNone(p['strict_net_return']);self.assertFalse(p['activation_allowed'])
        self.assertEqual(row['net'],.01)

    def test_missing_or_unsafe_report_is_unavailable_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            p=datasets(d);self.assertEqual(p['paper_accounts'],[])
            self.assertIsNone(p['paper_controls'][0]['expected_net_lower_quote'])
            lane=Path(d)/'experiments/owner_acceptance_v1';lane.mkdir(parents=True)
            (lane/'results.json').write_text(json.dumps({'registry_id':'R320','activation_allowed':True}))
            self.assertEqual(datasets(d)['paper_controls'][0]['state'],'UNAVAILABLE')
