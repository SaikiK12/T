import asyncio
import gzip
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from lab.depth_replay import DepthReplay
from lab.stream_quotes import FrameClock, NS, SYMBOLS
from scripts import probe_depth_quotes as probe
from tests.test_lighter_depth_state import message, snapshot
from tests.test_stream_quotes import ANCHOR, UTC, frame, metadata


def depth_frame(second=5, *, initial=True, data=None):
    p = snapshot() if initial else message()
    p["order_book"]["last_updated_at"] = UTC//1000+int(second*1e6)
    return {"venue":"lighter","number":int(second*1000)+1,"utc_ns":UTC+int(second*NS),
            "mono_ns":ANCHOR.mono_ns+int(second*NS),"raw":json.dumps(data if data is not None else p)}


def replay(frames):
    connections = {v:{"opened_mono_ns":0,"closed_mono_ns":100*NS} for v in ("mexc","lighter")}
    return DepthReplay(frames,metadata(),{1:"BTC"},ANCHOR,connections)


class DepthReplayTests(unittest.TestCase):
    def test_same_state_top_control_is_thin_without_changing_clocks_or_quantity(self):
        r = replay([frame("mexc",5),depth_frame()])
        full, books = r.observe("BTC",ANCHOR.mono_ns+5*NS)
        top, bbo = r.observe("BTC",ANCHOR.mono_ns+5*NS,full["quantity_base"],allow_new_quantity=False,profile="top_only")
        self.assertEqual(full["book_flags"],[])
        self.assertEqual(full["quantity_base"],"2.5")
        self.assertTrue(full["cost"]["displayed_fillable"])
        self.assertFalse(top["cost"]["displayed_fillable"])
        self.assertEqual(full["quantity_base"],top["quantity_base"])
        self.assertEqual(books[1].clock,bbo[1].clock)
        self.assertEqual(books[1].source_time_ns,bbo[1].source_time_ns)
        self.assertEqual(full["lighter_assembly"],top["lighter_assembly"])
        # Independent hand calculation: crossing 5+7.4; fee .5+.2, at q=2.5.
        for k, scenario in enumerate(full["cost"]["scenarios"],1):
            self.assertAlmostEqual(scenario["round_trip_cost_usd"],13.1*k)
        self.assertEqual(full["cost"]["capital_usd"],10000)
        self.assertFalse(full["execution_ready"])
        self.assertFalse(full["session_metadata"]["permission_certified"])

    def test_delayed_full_and_top_use_the_immediate_quantity(self):
        r = replay([frame("mexc",5),depth_frame(),frame("mexc",5.2,version=2,ask=103),depth_frame(5.2,initial=False)])
        a,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS)
        for profile in ("full","top_only"):
            b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+300_000_000,a["quantity_base"],allow_new_quantity=False,profile=profile)
            self.assertEqual(b["quantity_base"],a["quantity_base"])
            self.assertEqual(b["book_receive_times_ns"][0],ANCHOR.mono_ns+int(5.2*NS))
        with self.assertRaises(ValueError):r.advance(ANCHOR.mono_ns+5*NS)

    def test_no_future_quote_can_create_a_decision_or_delayed_quantity(self):
        r = replay([frame("mexc",5.2),depth_frame(5.2)])
        a,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS)
        b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+300_000_000,a["quantity_base"],allow_new_quantity=False)
        self.assertIsNone(a["quantity_base"])
        self.assertIsNone(b["cost"])
        self.assertIn("no_causal_decision_quantity",b["book_flags"])

    def test_nonce_gap_remains_poisoned_despite_pong_or_replacement(self):
        bad = message(begin=999,stamp=UTC//1000+5_100_000)
        r = replay([frame("mexc",5),depth_frame(),depth_frame(5.1,data=bad),
                    depth_frame(5.2,data={"type":"pong"}),depth_frame(5.3)])
        a,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS)
        self.assertTrue(probe.eligible(a))
        for profile in ("full","top_only"):
            b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+400_000_000,a["quantity_base"],allow_new_quantity=False,profile=profile)
            self.assertEqual(b["lighter_assembly"]["status"],"invalid")
            self.assertIsNone(b["cost"])

    def test_no_effect_update_does_not_freshen_an_old_liquidity_clock(self):
        r = replay([frame("mexc",6.2),depth_frame(),depth_frame(6.2,initial=False)])
        b,_ = r.observe("BTC",ANCHOR.mono_ns+int(6.2*NS))
        self.assertIn("lighter:receive_age_outside_0_1s",b["book_flags"])
        self.assertEqual(b["lighter_assembly"]["liquidity_receive_ns"],ANCHOR.mono_ns+5*NS)

    def test_latest_metadata_clock_step_blocks_even_unchanged_liquidity(self):
        f = depth_frame(5.1,initial=False); f["utc_ns"] += 100_000_000
        r = replay([frame("mexc",5),depth_frame(),f])
        b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+200_000_000)
        self.assertIn("lighter:state_local_UTC_step_over_50ms",b["book_flags"])
        self.assertIsNone(b["quantity_base"])

    def test_unattributed_corruption_and_transport_close_invalidate_depth(self):
        for bad in (depth_frame(5.1,data=[]),depth_frame(5.1,data={"type":"shutdown"})):
            r = replay([frame("mexc",5),depth_frame(),bad])
            b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+200_000_000)
            self.assertEqual(b["lighter_assembly"]["status"],"invalid")
        r = replay([frame("mexc",5),depth_frame()]);r.connections["lighter"]["closed_mono_ns"] = ANCHOR.mono_ns+5*NS+100_000_000
        b,_ = r.observe("BTC",ANCHOR.mono_ns+5*NS+200_000_000)
        self.assertIn("lighter:disconnected",b["book_flags"])
        self.assertEqual(b["lighter_assembly"]["reason"],"transport disconnected")

    def test_all_288_rows_and_missing_symbols_survive(self):
        rows = probe.fixed_rows(replay([frame("mexc",5),depth_frame()]))
        self.assertEqual(len(rows),288)
        self.assertEqual(len({(r['symbol'],r['grid_second'],r['access_delay_ms'],r['depth_profile']) for r in rows}),288)
        self.assertEqual(sum(probe.eligible(r) for r in rows),2)
        self.assertTrue(all(not r["execution_ready"] for r in rows))
        self.assertTrue(all(r["cost"] is None for r in rows if r["symbol"] != "BTC"))


class DepthTransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_boundary_precedes_slow_socket_cleanup(self):
        status={}
        class Socket:
            async def recv(self):raise OSError("fixture receive failure")
        class Connect:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*args):
                self_outer.assertIsNotNone(status["unusable_mono_ns"])
                await asyncio.sleep(.01)
                return False
        self_outer=self
        with tempfile.TemporaryDirectory() as d:
            anchor=FrameClock(time.time_ns(),time.monotonic_ns())
            await probe.stream("mexc",[],Path(d),anchor,status,connector=lambda *a,**kw:Connect())
            self.assertLess(status["unusable_mono_ns"],status["closed_mono_ns"])
        connections={v:{'opened_mono_ns':0,'closed_mono_ns':100*NS} for v in ('mexc','lighter')}
        connections['lighter']['unusable_mono_ns']=ANCHOR.mono_ns+5*NS+100_000_000
        r=DepthReplay([frame("mexc",5),depth_frame()],metadata(),{1:'BTC'},ANCHOR,connections)
        b,_=r.observe('BTC',ANCHOR.mono_ns+5*NS+200_000_000)
        self.assertIn('lighter:disconnected',b['book_flags'])

    async def test_no_receive_starts_when_ping_send_crosses_the_deadline(self):
        class Socket:
            async def send(self,x):pass
            async def recv(self):raise AssertionError("receive started past deadline")
        class Connect:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*args):return False
        ns=iter([10*NS,20*NS,76*NS,76*NS,77*NS])
        seconds=iter([0.,16.,76.])
        clock=SimpleNamespace(monotonic_ns=lambda:next(ns),monotonic=lambda:next(seconds))
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'time',clock):
            status={}
            await probe.stream('mexc',[],Path(d),FrameClock(UTC,10*NS),status,connector=lambda *a,**kw:Connect())
            self.assertEqual(status['reason'],'duration_complete')
            self.assertEqual(status['messages'],0)

    async def test_bounded_stream_retains_bad_raw_frames_without_reconnect(self):
        calls=[]
        class Socket:
            async def send(self,x):pass
            async def recv(self):return 'not-json'
        class Connect:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*args):return False
        def connector(url,**kw):
            calls.append(url)
            self.assertEqual(kw["max_size"],256*1024)
            self.assertIsNone(kw["compression"])
            self.assertEqual(kw["max_queue"],1)
            return Connect()
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"MAX_MESSAGES",2):
            status={};anchor=FrameClock(time.time_ns(),time.monotonic_ns())
            await probe.stream("lighter",[],Path(d),anchor,status,connector=connector)
            self.assertEqual(len(calls),1);self.assertEqual(status["messages"],2)
            self.assertEqual(status["reason"],"payload_or_message_cap")
            with gzip.open(Path(d)/"lighter.jsonl.gz","rt") as f:rows=[json.loads(x) for x in f]
            self.assertEqual([r['raw'] for r in rows],['not-json','not-json'])

    async def test_failed_handshake_and_frame_reservation_never_retry_or_overread(self):
        class Bad:
            async def __aenter__(self):raise OSError("fixture")
            async def __aexit__(self,*args):return False
        calls=[]
        def failed(*args,**kw):calls.append(1);return Bad()
        with tempfile.TemporaryDirectory() as d:
            status={};anchor=FrameClock(time.time_ns(),time.monotonic_ns())
            await probe.stream("mexc",[],Path(d),anchor,status,connector=failed)
            self.assertEqual(calls,[1]);self.assertIn("fixture",status["reason"])
        class Socket:
            async def recv(self):raise AssertionError("unbudgeted receive")
        class Good:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*args):return False
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"STREAM_BYTES",probe.FRAME_BYTES-1):
            status={};anchor=FrameClock(time.time_ns(),time.monotonic_ns())
            await probe.stream("mexc",[],Path(d),anchor,status,connector=lambda *a,**kw:Good())
            self.assertEqual(status["messages"],0);self.assertEqual(status["reason"],"payload_or_message_cap")


def fixture(lane):
    out=lane/"evidence";out.mkdir();probe.write(lane/"code_inputs.json",{})
    md=metadata();md['BTC']['lighter'].update(market_id=1,market_type='perp')
    probe.write(out/"metadata.json",{"metadata":md,"names":{"1":"BTC"}})
    probe.write(out/"anchor.json",vars(ANCHOR))
    receipts=[]
    for name,data in (("lighter_metadata",{"order_book_details":[md['BTC']['lighter']]}),
                      ("BTC_mexc_metadata",{"success":True,"data":md['BTC']['mexc']})):
        raw=json.dumps(data).encode();p=out/(name+".json.gz");p.write_bytes(gzip.compress(raw,mtime=0))
        import hashlib
        receipts.append({"name":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
            "body":p.name,"error":None,"started_mono_ns":1,"received_mono_ns":2,"body_read_upper_bound":len(raw)})
    probe.write(out/"receipts.json",{"requests":len(receipts),"response_bytes":sum(r['bytes'] for r in receipts),
        "response_body_read_upper_bound":sum(r['bytes'] for r in receipts),"duration_seconds":65,"records":receipts,"errors":[]})
    connections={}
    for venue,frames in (("mexc",[frame('mexc',5)]),("lighter",[depth_frame()])):
        for i,f in enumerate(frames,1):f['number']=i
        (out/(venue+".jsonl.gz")).write_bytes(gzip.compress(''.join(json.dumps(f)+'\n' for f in frames).encode(),mtime=0))
        connections[venue]={"handshake_attempts":1,"messages":len(frames),"payload_bytes":sum(len(f['raw'].encode()) for f in frames),
            "opened_mono_ns":ANCHOR.mono_ns,"unusable_mono_ns":ANCHOR.mono_ns+65*NS,"closed_mono_ns":ANCHOR.mono_ns+65*NS}
    probe.write(out/"connections.json",connections)
    probe.seal(lane)


class DepthReportTests(unittest.TestCase):
    def test_sealed_fixture_report_reproduces_and_refuses_tampered_inputs_or_outputs(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe.old,"verify"),mock.patch.object(probe,"verify"):
            lane=Path(d);fixture(lane);probe.report(lane)
            a=(lane/'results.json').read_bytes();b=(lane/'observations.jsonl.gz').read_bytes()
            self.assertEqual(json.loads(a)['rows'],288)
            self.assertEqual(sum(x['valid_cost_grids'] for x in json.loads(a)['pairs']),2)
            probe.report(lane,out=lane/'repeat')
            self.assertEqual(a,(lane/'repeat/results.json').read_bytes())
            self.assertEqual(b,(lane/'repeat/observations.jsonl.gz').read_bytes())
            (lane/'results.json').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'overwrite'):probe.report(lane)
            (lane/'evidence/metadata.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'drift'):probe.report(lane,out=lane/'bad')

    def test_capture_and_input_identity_cannot_reset_a_failed_attempt(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe.old,"verify"),mock.patch.object(probe,"verify"):
            lane=Path(d);fixture(lane)
            with self.assertRaises(FileExistsError):probe.capture(lane)
            with self.assertRaisesRegex(ValueError,'already sealed'):probe.seal(lane)


def fixture_trickle_worker(url,pipe,limit,timeout):
    pipe.send(('status',200));pipe.send(('chunk',b'{"partial":'))
    time.sleep(5)


def fixture_cap_worker(url,pipe,limit,timeout):
    pipe.send(('status',200));pipe.send(('chunk',b'x'*limit));pipe.send(('done',None))


def fixture_complete_worker(url,pipe,limit,timeout):
    pipe.send(('status',200));pipe.send(('chunk',b'{}'));pipe.send(('done',None))


class AbsoluteMetadataTests(unittest.TestCase):
    def test_trickling_owned_worker_is_stopped_and_partial_receipt_survives(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'REST_BYTES',128):
            # Spawn must have time to deliver the first chunk on slower hosts;
            # the worker then outlives the deadline and must still be stopped.
            m=probe.Metadata(d,worker=fixture_trickle_worker,request_seconds=2)
            begin=time.monotonic();value=m.get('one','https://fixture.test/public')
            self.assertIsNone(value);self.assertLess(time.monotonic()-begin,3.5)
            self.assertEqual(len(m.records),1);self.assertIn('deadline',m.records[0]['error'])
            self.assertEqual(gzip.decompress((Path(d)/'one.json.gz').read_bytes()),b'{"partial":')
            self.assertEqual(m.read_upper_bound,128)
            self.assertEqual(m.total,len(b'{"partial":'))
            with self.assertRaises(probe.old.BudgetStop):m.get('uncertain-tail','https://fixture.test/public')

    def test_exact_byte_cap_and_seven_attempts_are_not_silently_renewed(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,'REST_BYTES',10):
            m=probe.Metadata(d,worker=fixture_cap_worker)
            self.assertIsNone(m.get('cap','https://fixture.test/public'))
            self.assertEqual(m.total,10)
            self.assertIn('truncated',m.records[0]['error'])
            with self.assertRaises(probe.old.BudgetStop):m.get('extra','https://fixture.test/public')
        with tempfile.TemporaryDirectory() as d:
            m=probe.Metadata(d,worker=fixture_complete_worker)
            for i in range(7):self.assertEqual(m.get(str(i),'https://fixture.test/public'),{})
            with self.assertRaises(probe.old.BudgetStop):m.get('eighth','https://fixture.test/public')
