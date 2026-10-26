"""Complete invented four-stage protocol AND independent oracle before freeze."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from lab.level_probability import fit as prior_fit
import scripts.run_confidence as run
from scripts.check_confidence import audit


class ConfidencePipelineTests(unittest.TestCase):
    def test_all_stages_committed_boundaries_exports_account_dedup_and_oracle(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);lane=root/'experiments/confidence_v1';lane.mkdir(parents=True)
            config=dict(symbols=['BTC','ETH','SOL','WIF'],source_start='2025-01-01',source_end='2026-04-01',
                train_start='2025-01-05',train_end='2025-09-01',calibration_start='2025-09-01',calibration_end='2025-11-01',
                selection_start='2025-11-01',selection_end='2026-01-01',validation_start='2026-01-01',validation_end='2026-04-01',null_paths=2,limitations=['INVENTED fixture,notmarket evidence'])
            times=np.arange(run.ms(config['source_start']),run.ms(config['source_end']),run.HOUR)
            rng=np.random.default_rng(3319);records=[];sha={}
            for sym in config['symbols']:
                p=100*np.exp(np.cumsum(rng.normal(scale=.004,size=len(times))))
                o=np.r_[p[0],p[:-1]];hi=np.maximum(o,p)*np.exp(rng.uniform(0,.002,len(times)));lo=np.minimum(o,p)*np.exp(-rng.uniform(0,.002,len(times)))
                vol=np.exp(rng.normal(size=len(times)));amount=vol*p
                price=pd.DataFrame(dict(t=times,close=p,vol=vol,amount=amount));fund=pd.DataFrame(dict(t=times[::8],rate=.00003,cycle_h=8))
                for kind,frame in (('prices',price),('funding',fund)):
                    path=root/f'data/equations_v2/mexc/{kind}/{sym}_USDT.parquet';path.parent.mkdir(parents=True,exist_ok=True);frame.to_parquet(path,index=False);sha[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
                for start in range(0,len(times),2000):
                    stop=min(len(times),start+2000);first=int(times[start]//1000);last=int(times[stop-1]//1000)
                    raw=run.encode(dict(success=True,data=dict(time=(times[start:stop]//1000).tolist(),open=o[start:stop].tolist(),high=hi[start:stop].tolist(),low=lo[start:stop].tolist(),close=p[start:stop].tolist(),vol=vol[start:stop].tolist(),amount=amount[start:stop].tolist())))
                    packed=gzip.compress(raw,mtime=0);path=root/f'raw/{sym}-{start}.json.gz';path.parent.mkdir(exist_ok=True);path.write_bytes(packed)
                    records.append(dict(symbol=sym,path=str(path.relative_to(root)),url=f'https://contract.mexc.com/api/v1/contract/kline/{sym}_USDT?interval=Min60&start={first}&end={last}',gzip_sha256=hashlib.sha256(packed).hexdigest(),raw_sha256=hashlib.sha256(raw).hexdigest()))
                    sha[str(path.relative_to(root))]=hashlib.sha256(packed).hexdigest()
            data=dict(raw_records=records,sha256=sha,reference_training='reference-training.jsonl.gz',reference_later='reference-later.json.gz')
            (lane/'config.json').write_bytes(run.encode(config));(lane/'data_inputs.json').write_bytes(run.encode(data))
            with patch.object(run,'ROOT',root),patch.object(run,'LANE',lane),patch.object(run,'require_committed') as commits:
                # Old target/reference records for this invented fixture only.
                prior_rows={}
                for phase in ('train','calibration','selection','validation'):
                    prior_rows[phase]=run.observations(config,run.ms(config[phase+'_start']),run.ms(config[phase+'_end']))
                (root/data['reference_training']).write_bytes(gzip.compress(b''.join(run.encode(r) for r in prior_rows['train']),mtime=0))
                (root/data['reference_later']).write_bytes(run.packed(dict(calibration=prior_rows['calibration']+prior_rows['selection'],validation=prior_rows['validation'])))
                old=root/'experiments/level_probability_v1/model.json';old.parent.mkdir(parents=True);old.write_bytes(run.encode(prior_fit(prior_rows['train'])))
                for path in (root/data['reference_training'],root/data['reference_later'],old):data['sha256'][str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
                (lane/'data_inputs.json').write_bytes(run.encode(data));(lane/'code_inputs.json').write_bytes(run.encode({'sha256':{}}));(lane/'sources.json').write_text('{}')
                spec='\n'.join(hashlib.sha256((lane/n).read_bytes()).hexdigest() for n in ('config.json','data_inputs.json','code_inputs.json','sources.json'))
                (lane/'PREREG.md').write_text(spec);(lane/'PREREG.sha256').write_text(hashlib.sha256(spec.encode()).hexdigest()+'\n')
                results=[]
                for name,fn in (('training',run.train),('calibration',run.calibrate),('selection',run.choose),('results',run.evaluate)):
                    out=lane/name;out.mkdir();results.append(fn(out,config))
                self.assertGreater(commits.call_count,10)
            self.assertEqual(results[0]['stage'],'TRAINING_ONLY');self.assertEqual(results[1]['stage'],'CALIBRATION_ONLY')
            self.assertEqual(results[2]['stage'],'SELECTION_ONLY');self.assertIsNotNone(results[2]['winner'])
            result=json.loads((lane/'results/results.json').read_text());self.assertEqual(len(result['windows']['validation']['accounts']),39)
            self.assertEqual(result['registered_policy_variants'],14);self.assertIsNone(result['actual_executable_net'])
            checked=audit(lane/'results',root=root,lane=lane)
            self.assertEqual(checked['state'],'PASS');self.assertEqual(checked['checked_shared_accounts'],78)
            self.assertGreater(checked['checked_financial_events'],0);self.assertGreater(checked['checked_base_calibrated_probability_vectors'],0)
            # Mutating one delivered forecast must fail the independent audit.
            path=lane/'results/predictions.json.gz';payload=json.loads(gzip.decompress(path.read_bytes()))
            predictions=payload['validation']['predictions']['ridge_raw'];i=next(i for i,p in enumerate(predictions) if p is not None)
            predictions[i]=[1.,0.,0.];path.write_bytes(run.packed(payload))
            with self.assertRaisesRegex(ValueError,'independent numeric mismatch'):audit(lane/'results',root=root,lane=lane)


if __name__=='__main__':unittest.main()
