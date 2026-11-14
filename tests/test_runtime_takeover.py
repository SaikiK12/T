"""Takeover safety on synthetic sources, temporary state and mocked processes only."""
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib import error, request

from lab.runtime_transport import Budget, BoundedResponse, TransportStop, fence
from lab.runtime_takeover import admitted, restore, snapshot, health, run_child, single_writer
from scripts import quant_runtime


class FakeResponse(io.BytesIO):
    code = 200
    headers = {"Content-Type": "application/json"}


class TransportTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.policy = dict(prefixes=["https://public.example/data"], max_requests=4,
                           response_cap=32, max_body_bytes=200)

    def test_raw_body_is_unchanged_and_bytes_accumulate(self):
        raw = b'{"zero":"0","unknown":null}'
        with patch.object(request.OpenerDirector, "open", return_value=FakeResponse(raw)):
            with fence(self.root, self.policy):
                with request.build_opener().open('https://public.example/data') as r:
                    self.assertEqual(r.read(), raw)
        self.assertEqual(Budget(self.root, self.policy).usage(), (1, len(raw)))

    def test_auth_spoof_and_unregistered_host_stop_before_network(self):
        cases = [request.Request('https://public.example/data', headers={'Authorization':'synthetic'}),
                 request.Request('https://public.example/data', headers={'User-Agent':'Mozilla/5.0'}),
                 'https://fapi.binance.com/data', 'http://public.example/data']
        with patch.object(request.OpenerDirector, 'open', side_effect=AssertionError('network')):
            with fence(self.root, self.policy):
                for req in cases:
                    with self.assertRaises(TransportStop):request.build_opener().open(req)

    def test_denial_is_persistent_and_escapes_legacy_exception_retry(self):
        denied=error.HTTPError('https://public.example/data',403,'denied',{},io.BytesIO(b'blocked'))
        with patch.object(request.OpenerDirector,'open',side_effect=denied) as opened:
            with fence(self.root,self.policy):
                with self.assertRaises(TransportStop):request.build_opener().open('https://public.example/data')
            with fence(self.root,self.policy):
                with self.assertRaises(TransportStop):request.build_opener().open('https://public.example/data')
            self.assertEqual(opened.call_count,1)
        self.assertFalse(issubclass(TransportStop,Exception))

    def test_unfinished_reservation_survives_restart(self):
        b=Budget(self.root,self.policy);b.reserve('https://public.example/data')
        self.assertEqual(Budget(self.root,self.policy).usage(),(1,33))
        self.policy['max_body_bytes']=65
        with self.assertRaises(TransportStop):Budget(self.root,self.policy).reserve('https://public.example/data')

    def test_response_overflow_stops_and_never_returns_partial_as_complete(self):
        with patch.object(request.OpenerDirector,'open',return_value=FakeResponse(b'x'*100)):
            with fence(self.root,self.policy):
                with self.assertRaises(TransportStop):
                    with request.build_opener().open('https://public.example/data') as r:r.read()
        self.assertEqual(Budget(self.root,self.policy).usage(),(1,33))

    def test_html_is_not_accepted_as_data(self):
        r=FakeResponse(b'captcha');r.headers={'Content-Type':'text/html'}
        with patch.object(request.OpenerDirector,'open',return_value=r):
            with fence(self.root,self.policy):
                with self.assertRaises(TransportStop):request.build_opener().open('https://public.example/data')

    def test_redirect_never_sends_target_request(self):
        def original(opener,url,*args,**kwargs):
            return request.HTTPRedirectHandler().redirect_request(None,None,302,'',{},'https://other.example')
        with patch.object(request.OpenerDirector,'open',new=original):
            with fence(self.root,self.policy):
                with self.assertRaises(TransportStop):request.build_opener().open('https://public.example/data')
        self.assertEqual(Budget(self.root,self.policy).usage(),(1,33))

    def test_request_limit_is_campaign_wide(self):
        self.policy['max_requests']=1
        with patch.object(request.OpenerDirector,'open',return_value=FakeResponse(b'{}')):
            with fence(self.root,self.policy):
                with request.build_opener().open('https://public.example/data') as r:r.read()
        with self.assertRaises(TransportStop):Budget(self.root,self.policy).reserve('https://public.example/data')

    def test_context_restores_original_transport_after_failure(self):
        original=request.OpenerDirector.open
        with self.assertRaises(RuntimeError):
            with fence(self.root,self.policy):raise RuntimeError('synthetic')
        self.assertIs(request.OpenerDirector.open,original)

    def test_every_request_honors_campaign_window(self):
        self.policy.update(start='2000-01-01T00:00:00+00:00',end='2000-01-02T00:00:00+00:00')
        with self.assertRaises(TransportStop):Budget(self.root,self.policy).reserve('https://public.example/data')
        self.assertEqual(Budget(self.root,self.policy).usage(),(0,0))


class StateTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name)/'source';self.state=Path(t.name)/'canonical'
        self.root.mkdir();self.state.mkdir()
        self.config=dict(state_prefixes=['data/recorders/test','data/operations/test','experiments/test/journal'],max_stored_bytes=10000)
        (self.state/'manifest.json').write_text(json.dumps(dict(schema=1,owner='github-actions',bootstrap=True,files={})))

    def put(self,name,raw=b'synthetic\n'):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return p

    def test_missing_state_is_not_a_clean_reset(self):
        with self.assertRaises(FileNotFoundError):restore(self.root,self.state/'absent',self.config,{})

    def test_snapshot_restore_keeps_original_cache_mtime(self):
        p=self.put('experiments/test/journal/tbill.csv');os.utime(p,ns=(1000000000,1000000000))
        snapshot(self.root,self.state,self.config,report='synthetic')
        p.write_bytes(b'old\n');os.utime(p,None)
        # Use a prefix state fixture; divergence is deliberately rejected below.
        p.write_bytes(b'')
        restore(self.root,self.state,self.config,{})
        self.assertEqual(p.stat().st_mtime_ns,1000000000)
        self.assertEqual(p.read_bytes(),b'synthetic\n')

    def test_divergent_append_only_journal_cannot_be_truncated(self):
        p=self.put('experiments/test/journal/tickets.csv',b'head\nold\n')
        snapshot(self.root,self.state,self.config,report='x');p.write_bytes(b'head\nnew\n')
        with self.assertRaises(ValueError):restore(self.root,self.state,self.config,{})
        self.assertEqual(p.read_bytes(),b'head\nnew\n')

    def test_raw_capture_cannot_be_replaced(self):
        p=self.put('data/recorders/test/hour.body.gz',b'a')
        snapshot(self.root,self.state,self.config,report='x');p.write_bytes(b'b')
        with self.assertRaises(ValueError):restore(self.root,self.state,self.config,{})

    def test_traversal_and_source_code_paths_are_rejected(self):
        for name in ['../lab/x.py','/tmp/x','data/recorders/test/../../lab/x.py','lab/x.py','data\\recorders\\x']:
            self.assertFalse(admitted(name,self.config['state_prefixes']))

    def test_frozen_file_never_restored(self):
        p=self.put('experiments/test/journal/tickets.csv')
        snapshot(self.root,self.state,self.config,report='x')
        with self.assertRaises(ValueError):restore(self.root,self.state,self.config,{'experiments/test/journal/tickets.csv':'hash'})

    def test_hash_error_is_detected_before_any_file_copy(self):
        a=self.put('experiments/test/journal/a.csv',b'h\n')
        b=self.put('experiments/test/journal/b.csv',b'h\n')
        snapshot(self.root,self.state,self.config,report='x')
        a.write_bytes(b'');(self.state/'state/experiments/test/journal/b.csv').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):restore(self.root,self.state,self.config,{})
        self.assertEqual(a.read_bytes(),b'')

    def test_cut_journal_is_preserved_and_blocks_restore(self):
        self.put('experiments/test/journal/tickets.csv',b'a,b\n1,')
        snapshot(self.root,self.state,self.config,report='x')
        with self.assertRaises(ValueError):restore(self.root,self.state,self.config,{})

    def test_partial_source_file_is_retained_for_audit(self):
        self.put('data/recorders/test/hour.parquet.part',b'incomplete')
        m=snapshot(self.root,self.state,self.config,report='x')
        self.assertIn('data/recorders/test/hour.parquet.part',m['files'])

    def test_symlink_is_refused(self):
        p=self.root/'data';p.symlink_to(self.state,target_is_directory=True)
        with self.assertRaises(ValueError):snapshot(self.root,self.state,self.config,report='x')

    def test_health_uses_receipt_clock_and_does_not_claim_pnl(self):
        self.put('experiments/test/journal/status.json',b'{"updated":"2026-11-06T12:00Z"}')
        rows=health(self.root,{'R1':'test'},datetime(2026,11,7,tzinfo=timezone.utc))
        self.assertEqual(rows[0]['status'],'STALE_OR_CLOCK');self.assertNotIn('pnl',rows[0])

    def test_timeout_is_not_a_success(self):
        def timeout(*a,**kw):raise subprocess.TimeoutExpired('synthetic',1)
        out=run_child(self.root,'scripts/x.py',[],'synthetic',self.root/'log',1,timeout)
        self.assertEqual(out['state'],'FAILED_TIMEOUT')

    def test_child_preserves_native_option_arguments(self):
        calls=[]
        def invoke(args,**kwargs):calls.append(args);return subprocess.CompletedProcess(args,0)
        run_child(self.root,'scripts/x.py',['--execute'],'x',self.root/'log',1,invoke)
        self.assertEqual(calls[0][-2:],['--','--execute'])

    def test_default_plan_never_starts_a_task(self):
        with patch.object(quant_runtime,'execute',side_effect=AssertionError('writer')):
            with patch('sys.stdout',new=io.StringIO()):
                self.assertEqual(quant_runtime.main(['plan']),0)

    def test_native_option_reaches_child_parser_without_becoming_wrapper_option(self):
        with patch.object(quant_runtime,'child') as child:
            self.assertEqual(quant_runtime.main(['child','scripts/record_eea_pair.py','r419','--','--execute']),0)
        self.assertEqual(child.call_args.args[2],['--execute'])

    def test_child_cannot_bypass_central_writer(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}),patch.object(quant_runtime,'verify',side_effect=AssertionError('verify')):
            with self.assertRaises(ValueError):quant_runtime.child('scripts/x.py','x',[],{})

    def test_existing_forward_writer_blocks_before_restore(self):
        with single_writer(self.root),patch.object(quant_runtime,'ROOT',self.root), \
             patch.object(quant_runtime,'execute_locked',side_effect=AssertionError('restore')):
            with self.assertRaises(BlockingIOError):quant_runtime.execute({},self.state,'blocked')

    def test_crashed_hour_is_reserved_and_not_reexecuted(self):
        config=dict(self.config,state_prefixes=self.config['state_prefixes']+[quant_runtime.OPS],max_stored_bytes=200000,
                    start='2026-11-07T00:00:00+00:00',end='2026-11-19T00:00:00+00:00',
                    tasks=[dict(id='R419',script='scripts/x.py',args=[],policy='x',timeout=1)],blocked={},health_lanes={})
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):return cls(2026,11,7,4,30,tzinfo=timezone.utc)
        def git_result(args,**kwargs):
            if args[:2]==['git','show']:
                return (self.state/args[2].split(':',1)[1]).read_bytes()
            return 'synthetic\n'
        with patch.object(quant_runtime,'ROOT',self.root),patch.object(quant_runtime,'datetime',Clock), \
             patch.object(quant_runtime,'verify',return_value=('synthetic',{})), \
             patch.object(quant_runtime.subprocess,'check_output',side_effect=git_result), \
             patch.object(quant_runtime,'run_child',side_effect=RuntimeError('crash')) as writer:
            quant_runtime.prepare(config,self.state,'first')
            with self.assertRaises(RuntimeError):quant_runtime.execute(config,self.state,'first')
            result=quant_runtime.execute(config,self.state,'second')
        self.assertEqual(writer.call_count,1)
        self.assertEqual(result['state'],'HOUR_ALREADY_RESERVED')

    def test_unfinished_checkpoint_blocks_another_host_before_network(self):
        config=dict(self.config,state_prefixes=self.config['state_prefixes']+[quant_runtime.OPS],max_stored_bytes=200000,
                    start='2026-11-07T00:00:00+00:00',end='2026-11-19T00:00:00+00:00',
                    tasks=[],blocked={},health_lanes={})
        with patch.object(quant_runtime,'ROOT',self.root), \
             patch.object(quant_runtime,'verify',return_value=('synthetic',{})), \
             patch.object(quant_runtime.subprocess,'check_output',return_value='synthetic\n'):
            quant_runtime.prepare(config,self.state,'lost_host')
            with self.assertRaisesRegex(ValueError,'unfinished predecessor'):
                quant_runtime.prepare(config,self.state,'new_host')

    def test_uncommitted_checkpoint_cannot_dispatch(self):
        config=dict(self.config,state_prefixes=self.config['state_prefixes']+[quant_runtime.OPS],max_stored_bytes=200000,
                    start='2026-11-07T00:00:00+00:00',end='2026-11-19T00:00:00+00:00',
                    tasks=[],blocked={},health_lanes={})
        def fake_git(args,**kwargs):return b'not_the_reservation' if args[:2]==['git','show'] else 'synthetic\n'
        with patch.object(quant_runtime,'ROOT',self.root), \
             patch.object(quant_runtime,'verify',return_value=('synthetic',{})), \
             patch.object(quant_runtime.subprocess,'check_output',side_effect=fake_git):
            quant_runtime.prepare(config,self.state,'this_host')
            with self.assertRaisesRegex(ValueError,'committed and published'):
                quant_runtime.execute(config,self.state,'this_host')

    def test_old_frozen_workflow_can_be_retired_without_editing_it(self):
        p=self.state/'manifest.json';o=json.loads(p.read_text());o['active_contract']='a_future_registered_contract';p.write_text(json.dumps(o))
        with patch.object(quant_runtime,'execute',side_effect=AssertionError('writer')),patch('sys.stdout',new=io.StringIO()):
            self.assertEqual(quant_runtime.main(['run','--state-dir',str(self.state)]),0)


if __name__=='__main__':unittest.main()
