import asyncio
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from lab.depth_replay import DepthReplay
from lab.funding_values import mexc_rest_fair
from scripts import probe_funding_values as probe
from tests.test_depth_quotes import depth_frame,fixture as old_fixture,fixture_cap_worker,fixture_trickle_worker
from tests.test_stream_quotes import ANCHOR,UTC,NS,frame,metadata


def make_fixture(lane):
    with mock.patch.object(probe.depth,'seal'):
        old_fixture(lane)
    out=lane/'evidence'
    fmx={'venue':'mexc','number':1,'utc_ns':UTC+7*NS,'mono_ns':ANCHOR.mono_ns+7*NS,
        'raw':json.dumps({'channel':'push.fair.price','symbol':'BTC_USDT','ts':(UTC+7*NS)//1_000_000,'data':{'price':102}})}
    flt={'venue':'lighter','number':2,'utc_ns':UTC+9_900_000_000,'mono_ns':ANCHOR.mono_ns+9_900_000_000,
        'raw':json.dumps({'type':'update/market_stats','channel':'market_stats:1','timestamp':(UTC+9_900_000_000)//1_000_000,
                         'market_stats':{'symbol':'BTC','market_id':1,'index_price':'103'}})}
    connections={}
    for venue,frames in [('mexc',[fmx,frame('mexc',9.8)]),('lighter',[depth_frame(9.8),flt])]:
        for i,f in enumerate(frames,1):f['number']=i
        (out/(venue+'.jsonl.gz')).write_bytes(gzip.compress(''.join(json.dumps(f)+'\n' for f in frames).encode(),mtime=0))
        connections[venue]={'handshake_attempts':1,'messages':len(frames),'payload_bytes':sum(len(f['raw'].encode()) for f in frames),
            'opened_mono_ns':ANCHOR.mono_ns,'unusable_mono_ns':ANCHOR.mono_ns+65*NS,'closed_mono_ns':ANCHOR.mono_ns+65*NS}
    probe.write(out/'connections.json',connections)
    schedule=probe.FairSchedule(out,ANCHOR)
    r=next(x for x in schedule.records if x['symbol']=='BTC' and x['grid_second']==10)
    payload={'success':True,'code':0,'data':{'symbol':'BTC_USDT','fairPrice':102,'timestamp':(UTC+9_850_000_000)//1_000_000}}
    raw=json.dumps(payload).encode();(out/r['body']).write_bytes(gzip.compress(raw,mtime=0))
    r.update(attempted=True,started_mono_ns=ANCHOR.mono_ns+9*NS,received_mono_ns=ANCHOR.mono_ns+9_950_000_000,
        received_utc_ns=UTC+9_950_000_000,worker_cleanup_finished_mono_ns=ANCHOR.mono_ns+9_960_000_000,
        bytes=len(raw),body_read_upper_bound=len(raw),sha256=hashlib.sha256(raw).hexdigest(),http_status=200,error=None)
    probe.write(out/'fair_receipts.json',{'records':schedule.records})
    probe.seal(lane)


class FairRequestTests(unittest.TestCase):
    def test_absolute_timeout_preserves_partial_and_reserves_uncertain_tail(self):
        with tempfile.TemporaryDirectory() as d:
            r={'attempted':False,'url':'https://fixture.test/public','body':'one.json.gz'}
            start=time.monotonic();probe.fair_request(r,Path(d),worker=fixture_trickle_worker,seconds=1.2)
            self.assertLess(time.monotonic()-start,2.5);self.assertTrue(r['attempted'])
            self.assertEqual(r['body_read_upper_bound'],4096);self.assertIn('deadline',r['error'])
            self.assertEqual(gzip.decompress((Path(d)/r['body']).read_bytes()),b'{"partial":')
            self.assertLessEqual(r['received_mono_ns'],r['worker_cleanup_finished_mono_ns'])

    def test_exact_cap_is_not_proof_of_complete_body_and_expired_start_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            r={'attempted':False,'url':'https://fixture.test/public','body':'cap.json.gz'}
            probe.fair_request(r,Path(d),worker=fixture_cap_worker)
            self.assertIn('truncated',r['error']);self.assertEqual(r['bytes'],4096)
            expired={'attempted':False,'read_window_end_mono_ns':0,'error':'pending'}
            probe.fair_request(expired,Path(d),worker=lambda *a:self.fail('late request'))
            self.assertFalse(expired['attempted']);self.assertEqual(expired['error'],'request_start_window_expired')


class FairScheduleTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_36_predeclared_slots_run_once_at_fixed_schedule_without_network(self):
        now=[ANCHOR.mono_ns];calls=[]
        async def sleep(delay):now[0]+=int(round(delay*NS))
        def request(r,out):
            self.assertEqual(now[0],r['scheduled_mono_ns'])
            calls.append((r['symbol'],r['grid_second']));r['attempted']=True
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'time',SimpleNamespace(monotonic_ns=lambda:now[0])),\
             mock.patch.object(probe.asyncio,'sleep',side_effect=sleep),mock.patch.object(probe,'fair_request',side_effect=request):
            schedule=probe.FairSchedule(Path(d),ANCHOR);await schedule.run()
        self.assertEqual(len(calls),36);self.assertEqual(len(set(calls)),36)

    async def test_known_backoff_stops_future_batches_without_resetting_slots(self):
        now=[ANCHOR.mono_ns];calls=[]
        async def sleep(delay):now[0]+=int(round(delay*NS))
        def request(r,out):r.update(attempted=True,http_status=429);calls.append(r['name'])
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'time',SimpleNamespace(monotonic_ns=lambda:now[0])),\
             mock.patch.object(probe.asyncio,'sleep',side_effect=sleep),mock.patch.object(probe,'fair_request',side_effect=request):
            schedule=probe.FairSchedule(Path(d),ANCHOR);await schedule.run()
        self.assertEqual(len(calls),6)
        self.assertEqual(sum(r['attempted'] for r in schedule.records),6)
        self.assertTrue(all('backoff' in r['error'] for r in schedule.records if not r['attempted']))


class ValueReportTests(unittest.TestCase):
    def test_full_sealed_fixture_retains144_rows_and_matched_book_costs_with_new_value_source(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe.depth,'verify'),mock.patch.object(probe.depth.old,'verify'):
            lane=Path(d);make_fixture(lane);probe.report(lane)
            j=json.loads((lane/'results.json').read_text())
            self.assertEqual(j['rows'],144);self.assertEqual(j['cash_confirmed'],0)
            self.assertEqual(sum(x['joint_publication_rows'] for x in j['pairs'] if x['profile']=='REST_system'),2)
            self.assertEqual(sum(x['joint_publication_rows'] for x in j['pairs'] if x['profile']=='WS_change'),0)
            rows=[json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')]
            chosen=[r for r in rows if r['symbol']=='BTC' and r['grid_second']==10]
            self.assertEqual({r['quantity_base'] for r in chosen},{'2.5'})
            self.assertTrue(all(not r['execution_ready'] and not r['value_evidence']['cash_certified'] for r in rows))
            for k in range(3):self.assertAlmostEqual(chosen[0]['cost']['scenarios'][k]['round_trip_cost_usd'],13.1*(k+1))
            rest=next(r for r in chosen if r['value_profile']=='REST_system')
            self.assertEqual(rest['value_evidence']['observations'][0]['clock_role'],'REST_system')
            self.assertIsNone(next(r for r in chosen if r['value_profile']=='WS_change')['value_evidence']['products'])

    def test_latest_failed_rest_response_poisons_without_selecting_an_older_good_value(self):
        connections={v:{'opened_mono_ns':0,'closed_mono_ns':100*NS} for v in ['mexc','lighter']}
        replay=DepthReplay([frame('mexc',9.8),depth_frame(9.8)],metadata(),{1:'BTC'},ANCHOR,connections)
        p=mexc_rest_fair({'success':True,'code':0,'data':{'symbol':'BTC_USDT','fairPrice':102,'timestamp':(UTC+9*NS)//1_000_000}},
            'BTC',type(ANCHOR)(UTC+9_500_000_000,ANCHOR.mono_ns+9_500_000_000),'old-good')
        fairs=[({'symbol':'BTC','received_mono_ns':ANCHOR.mono_ns+9_500_000_000,'body':'old-good'},p),
               ({'symbol':'BTC','received_mono_ns':ANCHOR.mono_ns+9_900_000_000,'body':'latest-failed'},None),
               ({'symbol':'BTC','received_mono_ns':ANCHOR.mono_ns+11*NS,'body':'future-good'},p)]
        rows=probe.rows_for(replay,fairs)
        row=next(r for r in rows if r['symbol']=='BTC' and r['grid_second']==10 and r['access_delay_ms']==0 and r['value_profile']=='REST_system')
        self.assertEqual(row['rest_source_receipt'],'latest-failed');self.assertIsNone(row['value_evidence']['products'])
        self.assertIn('mexc:missing',row['value_evidence']['flags'])

    def test_reproduction_is_byte_identical_and_sealed_or_output_drift_is_refused(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe.depth,'verify'),mock.patch.object(probe.depth.old,'verify'):
            lane=Path(d);make_fixture(lane);probe.report(lane);probe.report(lane,out=lane/'again')
            for name in ['results.json','observations.jsonl.gz']:
                self.assertEqual((lane/name).read_bytes(),(lane/'again'/name).read_bytes())
            (lane/'results.json').write_text('bad')
            with self.assertRaisesRegex(ValueError,'overwrite'):probe.report(lane)
            (lane/'evidence/fair_receipts.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'drift'):probe.report(lane,out=lane/'tampered')

    def test_capture_cannot_reset_or_recover_an_existing_failed_directory(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'verify'):
            lane=Path(d);(lane/'evidence').mkdir()
            with self.assertRaises(FileExistsError):probe.capture(lane)

    def test_metadata_backoff_does_not_start_more_requests_or_streams(self):
        class Limited:
            def __init__(self,out):self.records=[];self.total=self.read_upper_bound=0
            def get(self,name,url):self.records.append({'http_status':429});return None
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'verify'),\
             mock.patch.object(probe.depth,'Metadata',Limited),mock.patch.object(probe.depth,'stream') as stream,\
             mock.patch.object(probe.depth.old,'LT_LOCK',Path(d)/'api.lock'):
            lane=Path(d)/'lane';lane.mkdir();probe.capture(lane)
            r=json.loads((lane/'evidence/receipts.json').read_text())
            self.assertEqual(r['requests'],1);stream.assert_not_called()
            self.assertTrue(any('backoff' in e for e in r['errors']))
