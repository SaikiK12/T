"""Audit-only regression on complete invented long/short protocol exports.

Original failing frozen checker stays intact; no strategy/data/result repair.
"""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import scripts.run_level_probability as runner
import scripts.check_level_probability as original
import scripts.check_level_probability_v2 as corrected


class LevelOracleSignTests(unittest.TestCase):
    def test_full_oracle_on_constructed_both_direction_accounts(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);lane=root/'experiments/level_probability_v1';lane.mkdir(parents=True)
            config=dict(symbols=['BTC','ETH','SOL','WIF'],source_start='2025-04-20',source_end='2025-07-01',
                train_start='2025-05-01',train_end='2025-06-01',calibration_start='2025-06-01',
                calibration_end='2025-06-15',validation_start='2025-06-15',validation_end='2025-07-01',limitations=['constructed'])
            times=np.arange(runner.ms(config['source_start']),runner.ms(config['source_end']),runner.HOUR)
            for kind in ('prices','funding'):(root/'data/equations_v2/mexc'/kind).mkdir(parents=True)
            for sym in config['symbols']:
                i=np.arange(len(times));price=100*np.exp(.03*np.sin(i/16))
                pd.DataFrame(dict(t=times,close=price,vol=1.)).to_parquet(root/f'data/equations_v2/mexc/prices/{sym}_USDT.parquet',index=False)
                pd.DataFrame(dict(t=times[::8],rate=.0001,cycle_h=8)).to_parquet(root/f'data/equations_v2/mexc/funding/{sym}_USDT.parquet',index=False)
            for name,value in (('config.json',config),('data_inputs.json',{'sha256':{}}),
                               ('code_inputs.json',{'sha256':{}}),('sources.json',{})):
                (lane/name).write_bytes(runner.encode(value))
            spec='\n'.join(hashlib.sha256((lane/n).read_bytes()).hexdigest() for n in ('config.json','data_inputs.json','code_inputs.json','sources.json'))
            (lane/'PREREG.md').write_text(spec);(lane/'PREREG.sha256').write_text(hashlib.sha256(spec.encode()).hexdigest()+'\n')
            fitdir=lane/'fit';fitdir.mkdir();out=lane/'results';out.mkdir()
            with patch.object(runner,'ROOT',root),patch.object(runner,'LANE',lane),patch.object(runner,'require_committed'):
                runner.fit_stage(fitdir,config)
                for n in ('model.json','model.sha256','training.jsonl.gz'):(lane/n).write_bytes((fitdir/n).read_bytes())
                runner.evaluate_stage(out,config,lane/'model.json')
            with patch.object(original,'ROOT',root),patch.object(original,'LANE',lane):
                with self.assertRaisesRegex(ValueError,'fixed500 notional drift'):original.check(out)
            with patch.object(corrected,'ROOT',root),patch.object(corrected,'LANE',lane):
                audit=corrected.check_corrected_entry_sign(out)
            self.assertEqual(audit['state'],'PASS');self.assertEqual(audit['checked_shared_accounts'],36)
            self.assertGreater(audit['closed_positions'],0);self.assertEqual(audit['new_requests'],0)
            accounts=json.loads(gzip.decompress((out/'accounts.json.gz').read_bytes()))
            quantities=[float(e['quantity']) for a in accounts['validation'] for e in a['events'] if e['kind']=='fill']
            self.assertTrue(any(q>0 for q in quantities));self.assertTrue(any(q<0 for q in quantities))

    def test_only_unsigned_notional_guard_and_checker_name_change(self):
        old=Path(original.__file__).read_text();new=Path(corrected.__file__).read_text()
        prefix='\n'.join(new.splitlines()[:3])+'\n'
        expected=old.replace('if abs(q*p-F(500))>F(1,10**18):','if abs(abs(q*p)-F(500))>F(1,10**18):')
        expected=expected.replace('def check(directory):','def check_corrected_entry_sign(directory):',1)
        expected=expected.replace('json.dumps(check(a.directory),sort_keys=True)','json.dumps(check_corrected_entry_sign(a.directory),sort_keys=True)',1)
        self.assertEqual(new,prefix+expected)


if __name__=='__main__':unittest.main()
