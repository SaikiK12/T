import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import quant_runtime_v4 as runtime


def ledger(number, size=90):
    return (json.dumps(dict(event='START',id=str(number),reserved_bytes=100))+'\n'
            +json.dumps(dict(event='END',id=str(number),charged_bytes=size))+'\n').encode()


class QuoteScopeRuntime(unittest.TestCase):
    def test_complete_inherited_prefix_and_all_late_appends_are_kept(self):
        inherited, previous = ledger(0), ledger(1)
        later = previous + ledger(2)
        self.assertEqual(runtime.combined_baseline(inherited,later,inherited,previous),inherited+later)

    def test_cut_divergent_duplicate_and_unknown_ledgers_never_migrate(self):
        old, current = ledger(0), ledger(1)
        bad = [current[:-1],ledger(0),current+b'{"event":"START","id":"2","reserved_bytes":999}\n']
        for raw in bad:
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                runtime.combined_baseline(old,raw,old,current)
        with self.assertRaises(ValueError):
            runtime.combined_baseline(old,ledger(3),old,ledger(3))

    def test_failed_predecessor_attempt_is_not_repeated_in_the_same_actual_hour(self):
        report={'hour':'20261108T13','tasks':[{'id':'R413','state':'FAILED',
                 'started_utc':'2026-11-08T14:00:02+00:00'}]}
        self.assertTrue(runtime.paper_already_attempted(report,'R413','20261108T14'))
        self.assertFalse(runtime.paper_already_attempted(report,'R413','20261108T13'))

    def test_source_parity_gate_requires_committed_primary_and_independent_proofs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);lane=root/'experiments/paper_quote_scope_v1';out=lane/'results';out.mkdir(parents=True)
            primary=out/'source_contract.json';marker=out/'source_contract.sha256';check=out/'independent_check.json'
            primary.write_text(json.dumps(dict(state='SOURCE_VIEW_PARITY_PASS',prereg_sha256='a'*64)))
            sha=hashlib.sha256(primary.read_bytes()).hexdigest()
            marker.write_text(sha+'  source_contract.json\n')
            check.write_text(json.dumps(dict(state='INDEPENDENT_IDENTITY_PASS',primary_report_sha256=sha)))
            with patch.object(runtime.subprocess,'check_output',side_effect=lambda cmd,cwd: (root/cmd[-1].split(':',1)[1]).read_bytes()):
                runtime.measurement_gate(root,'a'*64)
            with patch.object(runtime.subprocess,'check_output',return_value=b'uncommitted drift'),self.assertRaises(ValueError):
                runtime.measurement_gate(root,'a'*64)
            check.write_text(json.dumps(dict(state='INDEPENDENT_IDENTITY_PASS',primary_report_sha256='bad')))
            with self.assertRaises(ValueError):runtime.measurement_gate(root,'a'*64)

    def test_child_does_no_http_after_failed_predecessor_hour(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);old=root/runtime.OLD_OPS;old.mkdir(parents=True)
            stamp=runtime.datetime.now(runtime.timezone.utc).isoformat()
            (old/'latest.json').write_text(json.dumps({'tasks':[{'id':'R413','state':'FAILED','started_utc':stamp}]}))
            cfg={'tasks':[{'id':'R413','script':'scripts/forward_boroslock.py','policy':'aux','args':[]}]}
            with patch.object(runtime,'ROOT',root),patch.object(runtime,'NATIVE_CHILD') as child:
                runtime.child('scripts/forward_boroslock.py','aux',[],cfg)
            child.assert_not_called()

    def test_synthetic_migration_preserves_journals_and_prepares_one_committed_hour(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);root=tmp/'root';state=tmp/'state';lane=tmp/'lane'
            for p in (root,state,lane):p.mkdir()
            def git(folder,*args):
                return subprocess.check_output(['git',*args],cwd=folder,stderr=subprocess.DEVNULL)
            for p in (root,state):
                git(p,'init','-q');(p/'fixture').write_text('synthetic only\n');git(p,'add','fixture')
                git(p,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture')
            old=root/runtime.OLD_OPS;(old/'network/aux').mkdir(parents=True)
            old_base,old_current=ledger(0),ledger(1)
            (old/'aux_baseline.jsonl').write_bytes(old_base)
            (old/'network/aux/requests.jsonl').write_bytes(old_current)
            (old/'dispatch.jsonl').write_text('{"event":"FINISHED"}\n')
            for name,raw in [('inherited_aux_at_registration.jsonl',old_base),
                             ('previous_aux_at_registration.jsonl',old_current)]:
                (lane/name).write_bytes(raw)
            source=root/'data/recorders/participant_windows_v1/events.jsonl';source.parent.mkdir(parents=True)
            source.write_bytes(b'{"event":"SOURCE_BLOCK","reason":"synthetic prior denial"}\n')
            (lane/'r428_source_events_at_registration.jsonl').write_bytes(source.read_bytes())
            (lane/'acquisition_reservation.json').write_text('{"new_grant":false}')
            (state/'manifest.json').write_text(json.dumps(dict(schema=1,owner='github-actions',active_contract='R428',
                bootstrap=False,files={})))
            cfg=dict(state_prefixes=[runtime.OLD_OPS,runtime.OPS,'data/recorders/participant_windows_v1'],
                max_stored_bytes=1000000,health_lanes={},blocked={},start='2026-01-01',end='2099-01-01',
                policies={'aux':{'max_requests':4096,'max_body_bytes':16777216}},
                tasks=[dict(id='SYNTHETIC',script='unused.py',policy='aux',args=[],timeout=1)])
            names=['OPS','LANE','verify','run_child','fence','inventory','ROOT']
            before={k:getattr(runtime.base,k) for k in names}
            with patch.multiple(runtime.base,**before),patch.object(runtime,'ROOT',root),patch.object(runtime,'LANE',lane),\
                    patch.object(runtime,'verify',return_value=('a'*64,{})),\
                    patch.dict('os.environ',{'GITHUB_ACTIONS':'true'}):
                runtime.compose();runtime.base.ROOT=root
                r=runtime.migrate(cfg,state,'fixture')
                self.assertEqual(r['source_http_requests'],0)
                runtime.base.prepare(cfg,state,'fixture')
                git(state,'add','.')
                git(state,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','checkpoint')
                with patch.object(runtime.base,'run_child',return_value={'state':'PROCESS_OK','returncode':0}) as child:
                    runtime.base.execute(cfg,state,'fixture')
                child.assert_called_once()
            self.assertEqual((root/runtime.OPS/'aux_baseline.jsonl').read_bytes(),old_base+old_current)
            self.assertEqual((old/'network/aux/requests.jsonl').read_bytes(),old_current)
            self.assertEqual((lane/'r428_source_events_at_registration.jsonl').read_bytes(),source.read_bytes())
            self.assertEqual(json.loads((state/'manifest.json').read_text())['active_contract'],'R429')


if __name__=='__main__':unittest.main()
