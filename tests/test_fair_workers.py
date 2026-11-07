import gzip
import json
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock
import urllib.error
from lab.fair_workers import CAP,FairWorker,endpoint,worker,NoRedirect


def fixture_worker(url,connection,max_jobs):
    connection.send(('ready',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
    for _ in range(max_jobs):
        cmd=connection.recv()
        if cmd is None:break
        connection.send(('network_start',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
        connection.send(('status',200));connection.send(('chunk',b'{"ok":true}'));connection.send(('done',None))
    connection.close()


def trickle_worker(url,connection,max_jobs):
    connection.send(('ready',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
    connection.recv();connection.send(('network_start',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
    connection.send(('status',200));connection.send(('chunk',b'{"partial":'))
    time.sleep(20)


def cap_worker(url,connection,max_jobs):
    connection.send(('ready',{'mono_ns':time.monotonic_ns(),'utc_ns':time.time_ns()}))
    connection.recv();connection.send(('status',200));connection.send(('chunk',b' '*CAP));connection.send(('done',None))
    time.sleep(20)


def ready_hang_worker(url,connection,max_jobs):time.sleep(20)


def production_fixture_worker(url,connection,max_jobs):
    calls=0
    class Response(io.BytesIO):
        status=200
    def open_request(req,timeout):
        nonlocal calls
        assert req.get_method()=='GET' and req.full_url==endpoint('BTC') and 0<timeout<=3
        calls+=1;return Response(json.dumps({'calls':calls}).encode())
    with mock.patch('lab.fair_workers.urllib.request.build_opener',return_value=mock.Mock(open=open_request)):
        worker(url,connection,max_jobs)


def production_backoff_worker(url,connection,max_jobs):
    def open_request(req,timeout):
        raise urllib.error.HTTPError(req.full_url,429,'fixture',{},io.BytesIO(b'{"stop":true}'))
    with mock.patch('lab.fair_workers.urllib.request.build_opener',return_value=mock.Mock(open=open_request)):
        worker(url,connection,max_jobs)


def slot(name):
    return {'body':name+'.json.gz','attempted':False,'bytes':0,'body_read_upper_bound':0,'read_window_end_mono_ns':time.monotonic_ns()+10**10}


class WorkerTests(unittest.TestCase):
    def worker(self,target=fixture_worker,max_jobs=6):
        w=FairWorker('BTC',target=target,max_jobs=max_jobs);self.addCleanup(w.close)
        self.assertTrue(w.wait_ready(time.monotonic()+3));return w

    def test_readiness_uses_no_commands_then_one_process_serves_finite_jobs(self):
        with tempfile.TemporaryDirectory() as d:
            w=self.worker(max_jobs=2);pid=w.process.pid
            self.assertEqual(w.status['network_commands'],0)
            records=[slot(str(i)) for i in range(3)]
            for r in records:w.request(r,Path(d))
            self.assertEqual(w.process.pid,pid);self.assertEqual([r['attempted'] for r in records],[True,True,False])
            self.assertEqual(w.status['network_commands'],2)
            for r in records[:2]:
                self.assertLessEqual(r['started_mono_ns'],r['worker_network_started_mono_ns'])
                self.assertLessEqual(r['worker_network_started_mono_ns'],r['received_mono_ns'])
                self.assertNotIn('worker_cleanup_finished_mono_ns',r)
                self.assertEqual(json.loads(gzip.decompress((Path(d)/r['body']).read_bytes())),{'ok':True})
            w.close();closed=w.status['closed_mono_ns'];w.close();self.assertEqual(w.status['closed_mono_ns'],closed)
            self.assertFalse(w.process.is_alive())

    def test_actual_worker_reuses_only_after_explicit_command_and_http_error_is_retained(self):
        with tempfile.TemporaryDirectory() as d:
            w=self.worker(production_fixture_worker,max_jobs=2)
            for i in (1,2):
                r=slot('actual'+str(i));w.request(r,Path(d));self.assertIsNone(r['error'])
                self.assertEqual(json.loads(gzip.decompress((Path(d)/r['body']).read_bytes())),{'calls':i})
            limited=self.worker(production_backoff_worker);r=slot('backoff');limited.request(r,Path(d))
            self.assertEqual(r['http_status'],429);self.assertIsNotNone(r['error']);self.assertEqual(r['bytes'],13)
            self.assertIsNone(NoRedirect().redirect_request(None,None,302,'fixture',{},'https://example.com'))

    def test_absolute_trickle_timeout_preserves_partial_and_no_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            w=self.worker(trickle_worker);pid=w.process.pid;r=slot('partial');begin=time.monotonic()
            w.request(r,Path(d),seconds=.1)
            self.assertLess(time.monotonic()-begin,1.0);self.assertIn('deadline',r['error'])
            self.assertEqual(r['body_read_upper_bound'],CAP)
            self.assertEqual(gzip.decompress((Path(d)/r['body']).read_bytes()),b'{"partial":')
            later=slot('later');w.request(later,Path(d));self.assertFalse(later['attempted'])
            self.assertEqual(w.process.pid,pid);self.assertEqual(w.status['network_commands'],1)

    def test_exact_cap_is_failed_not_complete_json_and_never_reads_cap_plus_one(self):
        with tempfile.TemporaryDirectory() as d:
            w=self.worker(cap_worker);r=slot('cap');w.request(r,Path(d))
            self.assertIn('truncated',r['error']);self.assertEqual(r['bytes'],CAP);self.assertEqual(r['body_read_upper_bound'],CAP)

    def test_expired_dispatch_and_bad_endpoint_or_limits_cannot_start_get(self):
        with tempfile.TemporaryDirectory() as d:
            w=self.worker();r=slot('expired');r['read_window_end_mono_ns']=0
            w.request(r,Path(d));self.assertFalse(r['attempted']);self.assertEqual(w.status['network_commands'],0)
            with self.assertRaises(ValueError):endpoint('../private')
            with self.assertRaises(ValueError):FairWorker('BTC',max_jobs=7)
            with self.assertRaises(ValueError):w.request(slot('bad'),Path(d),seconds=4)

    def test_readiness_timeout_terminates_owned_process_before_any_command(self):
        w=FairWorker('BTC',target=ready_hang_worker);self.addCleanup(w.close)
        self.assertFalse(w.wait_ready(time.monotonic()+.1));self.assertFalse(w.process.is_alive())
        self.assertEqual(w.status['network_commands'],0);self.assertIn('readiness',w.status['error'])
