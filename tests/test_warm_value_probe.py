import asyncio
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from lab.depth_replay import DepthReplay
from scripts import probe_warm_values as probe
from tests.test_funding_value_probe import make_fixture as previous_fixture
from tests.test_stream_quotes import ANCHOR,NS


def fixture(lane):
    with mock.patch.object(probe.cold,'seal'):
        previous_fixture(lane)
    out=lane/'evidence';r=next(x for x in json.loads((out/'fair_receipts.json').read_text())['records'] if x['symbol']=='BTC' and x['grid_second']==10)
    schedule=probe.Schedule(out,ANCHOR,{})
    for x in schedule.records:
        if x['symbol']=='BTC' and x['grid_second']==10:
            body=x['body'];profile=x['profile'];x.update(r);x.update(profile=profile,body=body)
            (out/body).write_bytes((out/r['body']).read_bytes())
            if profile=='REST_warm':
                x['parent_request_finished_mono_ns']=x.pop('worker_cleanup_finished_mono_ns')
                x.update(worker_network_started_mono_ns=x['started_mono_ns'],worker_network_started_utc_ns=0)
    # Entirely invented setup; seal only after all fixed inputs are assembled.
    workers={s:{'symbol':s,'url':probe.endpoint(s),'network_commands':1 if s=='BTC' else 0,'started_mono_ns':ANCHOR.mono_ns-2*NS,
                'worker_ready_clock':{'mono_ns':ANCHOR.mono_ns-NS},'ready_received_mono_ns':ANCHOR.mono_ns-NS,'closed_mono_ns':ANCHOR.mono_ns+65*NS} for s in probe.SYMBOLS}
    probe.write(out/'warm_workers.json',{'workers':workers});probe.write(out/'fair_receipts.json',{'records':schedule.records})
    probe.seal(lane)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        for module in (probe.depth,probe.depth.old):
            patch=mock.patch.object(module,'verify');patch.start();self.addCleanup(patch.stop)

    def test_216_rows_same_q_cost_source_roles_and_reproduction(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);fixture(lane);probe.report(lane)
            rows=[json.loads(x) for x in gzip.open(lane/'observations.jsonl.gz','rt')]
            self.assertEqual(len(rows),216)
            rr=[r for r in rows if r['symbol']=='BTC' and r['grid_second']==10 and r['access_delay_ms']==0]
            self.assertEqual([r['value_profile'] for r in rr],list(probe.PROFILES))
            self.assertTrue(all(r['quantity_base']==rr[0]['quantity_base'] and r['cost']==rr[0]['cost'] for r in rr))
            self.assertTrue(rr[0]['value_evidence']['flags'])
            self.assertFalse(rr[1]['value_evidence']['flags']);self.assertFalse(rr[2]['value_evidence']['flags'])
            self.assertTrue(all(not r['execution_ready'] and r['cash_ledger_status'].startswith('unscored:') for r in rows))
            probe.report(lane,out=lane/'reproduce')
            for name in ('results.json','observations.jsonl.gz'):
                self.assertEqual((lane/name).read_bytes(),(lane/'reproduce'/name).read_bytes())

    def test_no_cross_profile_failure_fallback_or_future_reply(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);fixture(lane)
            frames,mapping,anchor,connections=probe.depth.load_capture(lane);fairs=probe.read_fairs(lane,anchor)
            good=next(z for z in fairs if z[0]['profile']=='REST_warm')
            newer=({**good[0],'received_mono_ns':anchor.mono_ns+9_990_000_000,'body':'known-failure'},None)
            future=({**good[0],'received_mono_ns':anchor.mono_ns+11*NS,'body':'future'},good[1])
            replay=DepthReplay(frames,mapping['metadata'],{int(k):v for k,v in mapping['names'].items()},anchor,connections)
            rows=probe.rows_for(replay,[*fairs,newer,future])
            warm=next(r for r in rows if r['symbol']=='BTC' and r['grid_second']==10 and r['access_delay_ms']==0 and r['value_profile']=='REST_warm')
            cold=next(r for r in rows if r['symbol']=='BTC' and r['grid_second']==10 and r['access_delay_ms']==0 and r['value_profile']=='REST_cold')
            self.assertEqual(warm['rest_source_receipt'],'known-failure');self.assertIn('mexc:missing',warm['value_evidence']['flags'])
            self.assertFalse(cold['value_evidence']['flags'])

    def test_changed_warm_dispatch_clock_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);fixture(lane);p=lane/'evidence/fair_receipts.json';x=json.loads(p.read_text())
            r=next(r for r in x['records'] if r['attempted'] and r['profile']=='REST_warm')
            r['worker_network_started_mono_ns']=ANCHOR.mono_ns+66*NS;probe.write(p,x)
            with self.assertRaises(ValueError):probe.read_fairs(lane,ANCHOR)

    def test_worker_receipt_inventory_and_actual_close_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);fixture(lane);p=lane/'evidence/warm_workers.json';base=json.loads(p.read_text())
            for updates in ({'network_commands':2},{'closed_mono_ns':ANCHOR.mono_ns+9*NS},
                            {'worker_ready_clock':{'mono_ns':ANCHOR.mono_ns}}):
                changed=json.loads(json.dumps(base));changed['workers']['BTC'].update(updates);probe.write(p,changed)
                with self.assertRaises(ValueError):probe.read_fairs(lane,ANCHOR)

    def test_server_backoff_suppresses_all_future_fixed_slots(self):
        def attempt(r,out):
            r.update(attempted=True,http_status=429 if r['symbol']=='BTC' else 200,error='fixture');return r
        async def run(out):
            workers={s:mock.Mock(request=attempt) for s in probe.SYMBOLS}
            schedule=probe.Schedule(out,ANCHOR,workers)
            with mock.patch.object(probe.cold,'fair_request',side_effect=attempt),mock.patch.object(probe.time,'monotonic_ns',return_value=ANCHOR.mono_ns):
                with mock.patch.object(probe.asyncio,'sleep',new=mock.AsyncMock()):await schedule.run()
            return schedule.records
        with tempfile.TemporaryDirectory() as d:
            rows=asyncio.run(run(Path(d)));self.assertEqual(len(rows),72);self.assertEqual(sum(r['attempted'] for r in rows),12)
            self.assertTrue(all('backoff' in r['error'] for r in rows if not r['attempted']))

    def test_capture_refuses_existing_directory_and_metadata_backoff_avoids_workers(self):
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d);(lane/'evidence').mkdir()
            with mock.patch.object(probe,'verify'):
                with self.assertRaises(FileExistsError):probe.capture(lane)
        with tempfile.TemporaryDirectory() as d:
            lane=Path(d)
            class Backoff:
                def __init__(self,out):self.records=[];self.total=self.read_upper_bound=0
                def get(self,*a):self.records.append({'http_status':429});return None
            with mock.patch.object(probe,'verify'),mock.patch.object(probe.depth,'Metadata',Backoff),mock.patch.object(probe,'FairWorker') as make:
                probe.capture(lane);make.assert_not_called()
            self.assertEqual(json.loads((lane/'evidence/fair_receipts.json').read_text())['records'],[])
