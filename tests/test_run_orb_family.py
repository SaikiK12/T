"""Frozen-entry/provenance and parser checks on invented responses only."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from lab import prereg, registry
from scripts.run_orb_family import (digest, lane_lock, parse_bars, run, safe,
                                   summarize, verified_inputs)
from tests.test_orb_family import invented, session


class OrbRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lane = self.root / 'experiments/pilot'
        self.lane.mkdir(parents=True)
        self.folder = self.root / 'data/pilot'
        self.folder.mkdir(parents=True)
        self.s = session()
        self.write('experiments/pilot/calendar.json', dict(calendar=[self.s.day], sessions=[self.s.__dict__],
                                                         closed_days=[]))
        for kind in ('last', 'fair'):
            bars = invented(self.s)
            self.write(f'data/pilot/{self.s.day}_{kind}.json', dict(success=True, data={
                'time': [b.t // 1000 for b in bars],
                **{k: [getattr(b, field) for b in bars] for k, field in
                   [('open','open'),('high','high'),('low','low'),('close','close'),('vol','volume')]}}))
        self.write('data/pilot/contract.json', dict(success=True, data=dict(symbol='NAS100_USDT', type=2,
                   contractSize=1, volUnit=1, minVol=1, maxVol=10000, priceUnit=.01)))
        self.write('data/pilot/funding_0001.json', dict(success=True, data=dict(currentPage=1, totalPage=1,
            resultList=[dict(symbol='NAS100_USDT', settleTime=t, fundingRate=0.) for t in
                        [self.s.close_ms + 60_000 + 1, self.s.open_ms - 1]])))
        files = [dict(path=p.name, bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(self.folder.iterdir())]
        self.write('docs/provenance/pilot.json', dict(folder='data/pilot', symbol='NAS100_USDT', file_hashes=files))
        direct = ['lab/orb_family.py','scripts/run_orb_family.py','scripts/fetch_orb_pilot.py',
                  'experiments/pilot/calendar.json','docs/provenance/pilot.json']
        project = Path(__file__).resolve().parent.parent
        for name in direct[:3]:
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((project/name).read_bytes())
        self.write('experiments/pilot/inputs.json', dict(calendar=direct[3], data_manifest=direct[4],
                   code_and_policy={p:digest(self.root/p) for p in direct}))
        self.spec = self.lane/'PREREG.md'
        self.spec.write_text('# Invented test only\n- **Registry id:** R900\n- **Inputs manifest SHA-256:** '
                             + digest(self.lane/'inputs.json') + '\n')
        sha = prereg.freeze(self.spec)
        (self.root/'registry').mkdir()
        registry.append(self.root/'registry/rounds.csv', id='R900', date='2026-10-29', lane='pilot',
                        status='REGISTERED', verdict='PENDING', trials=12, prereg_sha=sha, path='experiments/pilot')

    def write(self, path, value):
        p=self.root/path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value)+'\n')

    def test_frozen_end_to_end_and_byte_identical_second_run(self):
        with redirect_stdout(StringIO()):
            a=run(self.root,self.lane,'one')
            b=run(self.root,self.lane,'two')
        self.assertEqual(a,b)
        self.assertEqual((self.lane/'runs/one/result.json').read_bytes(),
                         (self.lane/'runs/two/result.json').read_bytes())
        self.assertTrue(a['result']['complete'])
        self.assertEqual(len(a['summary']['accounts']),12)
        self.assertFalse(a['summary']['gate_eligible'])
        with self.assertRaises(ValueError):
            run(self.root,self.lane,'one')

    def test_unfrozen_spec_and_changed_input_binding_refused_before_data(self):
        (self.lane/'PREREG.sha256').unlink()
        with self.assertRaises(prereg.PreregError):
            verified_inputs(self.root,self.lane)

    def test_frozen_code_drift(self):
        (self.root/'lab/orb_family.py').write_text('changed')
        with self.assertRaisesRegex(ValueError,'frozen input drift'):
            verified_inputs(self.root,self.lane)

    def test_data_drift_extra_and_missing_file(self):
        p=self.folder/'contract.json'
        original=p.read_bytes()
        p.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError,'data byte drift'):
            verified_inputs(self.root,self.lane)
        p.write_bytes(original)
        q=self.folder/'extra'
        q.write_text('extra')
        with self.assertRaisesRegex(ValueError,'file set'):
            verified_inputs(self.root,self.lane)
        q.unlink()
        p.unlink()
        with self.assertRaisesRegex(ValueError,'file set'):
            verified_inputs(self.root,self.lane)

    def test_registry_trial_count_and_identity_required(self):
        p=self.root/'registry/rounds.csv'
        p.write_text(p.read_text().replace(',12,',',4,'))
        with self.assertRaisesRegex(ValueError,'trial count'):
            verified_inputs(self.root,self.lane)

    def test_existing_lock_is_not_removed(self):
        p=self.lane/'.orb_run.lock'
        p.write_text('other writer')
        with self.assertRaises(FileExistsError):
            with lane_lock(self.lane):pass
        self.assertEqual(p.read_text(),'other writer')

    def test_unsafe_paths_and_symlinks(self):
        for p in ('../other','/etc/passwd','folder\\file'):
            with self.assertRaises(ValueError):safe(self.root,p)
        p=self.root/'linked'
        p.symlink_to(self.folder,target_is_directory=True)
        with self.assertRaises(ValueError):safe(self.root,'linked/contract.json')

    def test_array_lengths_boolean_time_and_bad_order_refused(self):
        p=self.folder/f'{self.s.day}_last.json'
        original=json.loads(p.read_text())
        d=json.loads(p.read_text());d['data']['open'].pop()
        with self.assertRaises(ValueError):parse_bars(d)
        d=json.loads(p.read_text());d['data']['time'][0]=True
        with self.assertRaises(ValueError):parse_bars(d)
        d=json.loads(p.read_text());d['data']['time'][1]=d['data']['time'][0]
        with self.assertRaises(ValueError):parse_bars(d)
        self.assertEqual(len(parse_bars(original)),len(invented(self.s)))

    def test_unknown_result_has_no_selected_partial_calendar_comparison(self):
        result=dict(equity={f'{arm}_{scale}x':None for arm in ('parent','vwap','volume','joint') for scale in (1,2,3)},
                    days=[dict(accounts={f'{arm}_{scale}x':dict(status='missing',pnl=None) for arm in
                          ('parent','vwap','volume','joint') for scale in (1,2,3)})],
                    initial_equity_each=2000.,complete=False)
        summary=summarize(result)
        self.assertEqual(set(summary['paired_2x_dollars'].values()),{None})
        self.assertIsNone(summary['accounts']['parent_1x']['pnl'])


if __name__=='__main__':unittest.main()
