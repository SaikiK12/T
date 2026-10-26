import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from scripts import run_owner_acceptance as runner
from lab import prereg


class RiskRunnerTests(unittest.TestCase):
    def test_frozen_numeric_dependency_version_drift_is_refused_before_market_input(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);hashes=[]
            for name in ('data_inputs.json','fixtures.json','requirements.json','requirements_evidence.json','sources.json','benchmark_environment.json'):
                (lane/name).write_text('{}');hashes.append(prereg.sha256_file(lane/name))
            (lane/'code_inputs.json').write_text(json.dumps({'python_version':list(runner.sys.version_info[:3]),'packages':{'numpy':'unsupported-drift'},'sha256':{}}))
            hashes.append(prereg.sha256_file(lane/'code_inputs.json'))
            (lane/'PREREG.md').write_text('\n'.join(hashes));prereg.freeze(lane/'PREREG.md')
            with self.assertRaisesRegex(ValueError,'numeric package drift'):runner.verify(lane)

    def test_complete_finite_control_and_missing_day_keep_gap_without_model_selection(self):
        # Invented varying hourly path, zero market observations. Bootstrap is
        # tested in its own kernel tests; don't multiply it in workflow tests.
        start=pd.Timestamp('2025-11-01',tz='UTC');end=pd.Timestamp('2026-10-01',tz='UTC')
        t=np.arange(start.value//10**6-3_600_000,end.value//10**6,3_600_000,dtype=np.int64)
        f=pd.DataFrame({'t':t,'close':100*np.exp(np.cumsum(.001+np.sin(np.arange(len(t)))*.0001)),'vol':1.})
        settings={'start':start.isoformat(),'end':end.isoformat(),'validation_start':'2026-01-01T00:00:00Z'}
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'null_calibration',return_value=[]):
            p=Path(d);a=p/'complete';a.mkdir();r=runner.risk_forecasts(f,settings,a)
            self.assertEqual(r['common_scored_days'],273);self.assertEqual(r['state'],'COMPONENT_ASSESSED')
            self.assertFalse(r['winner_selected']);self.assertEqual(r['trial_count'],4)
            f.loc[f.t==pd.Timestamp('2026-02-01T12:00:00Z').value//10**6,'vol']=0
            b=p/'gap';b.mkdir();r=runner.risk_forecasts(f,settings,b)
            self.assertGreater(r['unscored_days'],0);self.assertEqual(r['intervals'],[])
            self.assertEqual(r['state'],'INCONCLUSIVE')
            records=[json.loads(x) for x in gzip.decompress((b/'risk_predictions.jsonl.gz').read_bytes()).splitlines()]
            self.assertEqual(len(records),273)
            self.assertIsNone(next(x for x in records if x['day']=='2026-02-01')['target_rv'])
