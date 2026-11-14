import asyncio
from decimal import Decimal
import gzip
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from scripts import probe_stream_quotes as probe
from tests.test_stream_quotes import ANCHOR, NS, frame, metadata


class Response(io.BytesIO):
    status = 200


class MetadataBudgetTests(unittest.TestCase):
    def test_exact_response_cap_never_reads_one_extra_byte_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as d:
            network=probe.Metadata(d,opener=lambda *a,**kw:Response(b"x"*20))
            with mock.patch.object(probe,"REST_BYTES",10):
                self.assertIsNone(network.get("large","https://example.test/public"))
            self.assertEqual(network.total,10)
            self.assertTrue(network.records[0]["error"])
            self.assertEqual(gzip.decompress((Path(d)/"large.json.gz").read_bytes()),b"x"*10)

    def test_failed_attempts_consume_the_same_accumulated_request_budget(self):
        def fail(*a,**kw):raise TimeoutError("fixture")
        with tempfile.TemporaryDirectory() as d:
            network=probe.Metadata(d,opener=fail)
            for i in range(7):network.get(str(i),"https://example.test/public")
            with self.assertRaises(probe.BudgetStop):network.get("eighth","https://example.test/public")
            self.assertEqual(len(network.records),7)
            self.assertTrue(all(r["error"] for r in network.records))

    def test_expired_metadata_budget_never_calls_the_transport(self):
        with tempfile.TemporaryDirectory() as d:
            network=probe.Metadata(d,opener=lambda *a,**kw:self.fail("network used"))
            network.start=time.monotonic()-21
            with self.assertRaises(probe.BudgetStop):network.get("late","https://example.test/public")

    def test_frozen_capture_cannot_restart_or_reset_failed_evidence(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"verify"):
            lane=Path(d);(lane/"evidence").mkdir()
            with self.assertRaises(FileExistsError):probe.capture(lane)


class StreamBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_handshake_frame_cap_individual_clocks_and_no_reconnect(self):
        calls=[];sent=[]
        class Socket:
            async def send(self,x):sent.append(json.loads(x))
            async def recv(self):return '{"type":"pong"}'
        class Connector:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*exc):return False
        def connect(url,**kwargs):
            calls.append(url)
            self.assertEqual(kwargs["max_size"],probe.FRAME_BYTES)
            self.assertEqual(kwargs["max_queue"],1)
            self.assertIsNone(kwargs["compression"])
            return Connector()
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"MAX_MESSAGES",2):
            anchor=probe.FrameClock(time.time_ns(),time.monotonic_ns())
            status=await probe.stream("lighter",[{"type":"subscribe","channel":"ticker/1"}],Path(d),anchor,connector=connect)
            self.assertEqual(status["messages"],2)
            self.assertEqual(status["handshake_attempts"],1)
            self.assertEqual(status["reason"],"payload_or_message_cap")
            self.assertEqual(len(calls),1)
            self.assertEqual(sent,[{"type":"subscribe","channel":"ticker/1"}])
            with gzip.open(Path(d)/"lighter.jsonl.gz","rt") as f:rows=[json.loads(x) for x in f]
            self.assertEqual([r["number"] for r in rows],[1,2])
            self.assertLessEqual(rows[0]["mono_ns"],rows[1]["mono_ns"])
            self.assertEqual(status["payload_bytes"],sum(len(r["raw"].encode()) for r in rows))

    async def test_failed_handshake_is_retained_without_second_attempt(self):
        calls=[]
        class Bad:
            async def __aenter__(self):raise OSError("fixture refused")
            async def __aexit__(self,*a):return False
        def connect(*args,**kwargs):calls.append(1);return Bad()
        with tempfile.TemporaryDirectory() as d:
            anchor=probe.FrameClock(time.time_ns(),time.monotonic_ns())
            status=await probe.stream("mexc",[],Path(d),anchor,connector=connect)
            self.assertEqual(calls,[1])
            self.assertEqual(status["messages"],0)
            self.assertIn("refused",status["reason"])
            self.assertIsNone(status["opened_mono_ns"])

    async def test_full_frame_reservation_stops_before_overreading_byte_cap(self):
        class Socket:
            async def send(self,*a):pass
            async def recv(self):raise AssertionError("no capacity for a full frame")
        class Connect:
            async def __aenter__(self):return Socket()
            async def __aexit__(self,*a):return False
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"STREAM_BYTES",probe.FRAME_BYTES-1):
            anchor=probe.FrameClock(time.time_ns(),time.monotonic_ns())
            status=await probe.stream("mexc",[],Path(d),anchor,connector=lambda *a,**kw:Connect())
            self.assertEqual(status["reason"],"payload_or_message_cap")
            self.assertEqual(status["messages"],0)


class StreamReportTests(unittest.TestCase):
    def test_causal_grid_reuses_decision_quantity_and_retains_all_failed_rows(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"verify"):
            lane=Path(d);out=lane/"evidence";out.mkdir()
            (lane/"code_inputs.json").write_text("{}")
            md=metadata();md["BTC"]["lighter"].update(market_id=1,market_type="perp")
            probe.write(out/"metadata.json",{"metadata":md,"names":{1:"BTC"}})
            probe.write(out/"anchor.json",vars(ANCHOR))
            network=probe.Metadata(out,opener=lambda *a,**kw:None)
            for name,payload in (("lighter_metadata",{"order_book_details":[md["BTC"]["lighter"]]}),
                                 ("BTC_mexc_metadata",{"data":md["BTC"]["mexc"]})):
                network.opener=lambda *a,_raw=json.dumps(payload).encode(),**kw:Response(_raw)
                network.get(name,"https://example.test/public")
            probe.write(out/"receipts.json",{"requests":2,"response_bytes":network.total,"duration_seconds":65,
                                             "errors":[],"records":network.records})
            connections={}
            for venue in ("mexc","lighter"):
                fs=[frame(venue,5),frame(venue,5.2,version=2,ask=103)]
                for i,event in enumerate(fs,1):event["number"]=i
                with gzip.open(out/(venue+".jsonl.gz"),"wt") as f:
                    for event in fs:f.write(json.dumps(event)+"\n")
                connections[venue]={"handshake_attempts":1,"opened_mono_ns":ANCHOR.mono_ns,
                                    "closed_mono_ns":ANCHOR.mono_ns+65*NS,
                                    "payload_bytes":sum(len(e["raw"].encode()) for e in fs),"messages":2}
            probe.write(out/"connections.json",connections)
            probe.seal(lane)
            with self.assertRaisesRegex(ValueError,"already sealed"):probe.seal(lane)
            summary=json.loads(probe.report(lane).read_text())
            with gzip.open(lane/"observations.jsonl.gz","rt") as f:rows=[json.loads(x) for x in f]
            self.assertEqual(len(rows),144)
            self.assertEqual(summary["predictive_trials"],0)
            first=[r for r in rows if r["symbol"]=="BTC" and r["grid_second"]==5]
            self.assertEqual([Decimal(r["quantity_base"]) for r in first],[Decimal("2.5")]*2)
            self.assertEqual(first[1]["entry_quote_cash_drift"],{"long_mexc_usd":5.,"long_lighter_usd":5.})
            self.assertTrue(all(r["cost"] is None for r in rows if r["symbol"]!="BTC"))
            self.assertTrue(all(not r["execution_ready"] for r in rows))
            self.assertEqual(sum(s["valid_cost_grids"] for s in summary["pairs"]),2)
            original=(lane/"observations.jsonl.gz").read_bytes()
            probe.report(lane)
            self.assertEqual(original,(lane/"observations.jsonl.gz").read_bytes())
            probe.write(out/"metadata.json",{})
            with self.assertRaisesRegex(ValueError,"drift"):probe.report(lane)

    def test_an_entire_failed_capture_still_has_144_inactive_observations(self):
        with tempfile.TemporaryDirectory() as d,mock.patch.object(probe,"verify"):
            lane=Path(d);(lane/"evidence").mkdir();(lane/"code_inputs.json").write_text("{}")
            probe.write(lane/"evidence/receipts.json",{"requests":0,"response_bytes":0,"duration_seconds":10,"errors":["blocked"]})
            probe.seal(lane)
            summary=json.loads(probe.report(lane).read_text())
            self.assertEqual(summary["rows"],144)
            self.assertEqual(sum(x["valid_cost_grids"] for x in summary["pairs"]),0)
            self.assertTrue(all(t["round_trip_cost_usd_range"] is None for p in summary["pairs"] for t in p["cost_tiers"]))


if __name__ == "__main__":
    unittest.main()
