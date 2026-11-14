import asyncio
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import tempfile
import unittest
import re

from lab.participant_capture import (SourceStop, STREAM, capture, choose_slot, classify, deny_ws_redirects,
                                     inherited_source_block, records, reserve)
from scripts.quant_runtime_v3 import combined_baseline, paper_already_attempted


def config():
    return dict(markets={"145": "WTI", "159": "BRENTOIL"}, slot_reserved_calls=8,
                slot_reserved_bytes=2097152, max_source_calls=32, max_source_bytes=8388608,
                metadata_response_cap=8192, slot_payload_cap=1556480, max_frames=10000,
                slots=[dict(id="day0", start="2026-11-07T20:00:00+00:00", end="2026-11-08T00:00:00+00:00",
                            duration_seconds=65),
                       dict(id="day1", start="2026-11-08T18:00:00+00:00", end="2026-11-08T23:00:00+00:00",
                            duration_seconds=180)])


NOW = datetime(2026, 11, 7, 21, tzinfo=timezone.utc)


def ticker(mid="145"):
    return dict(type="update/ticker", channel="ticker:" + mid,
                ticker=dict(last_updated_at=1794085200000000,
                            a=dict(price="80.1000", size="2.000"), b=dict(price="80.0900", size="3.000")))


def trade(mid="145"):
    return dict(type="update/trade", channel="trade:" + mid, trades=[dict(
        trade_id=1, market_id=int(mid), ask_account_id=1, bid_account_id=2,
        timestamp=1794085200000, transaction_time=1794085200000000,
        is_maker_ask=True, price="80.1000", size="0.100", taker_position_size_before="-1.200",
        maker_position_size_before="3.000", taker_entry_quote_before="96.000000", maker_entry_quote_before="240.000000")])


class FakeWS:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []

    async def send(self, text):
        self.sent.append(json.loads(text))

    async def recv(self):
        if not self.messages:
            raise asyncio.TimeoutError()
        item = self.messages.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item if isinstance(item, (str, bytes)) else json.dumps(item)


class FakeConnection:
    def __init__(self, ws, failure=None):
        self.ws, self.failure = ws, failure
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self

    async def __aenter__(self):
        if self.failure:
            raise self.failure
        return self.ws

    async def __aexit__(self, *args):
        return False


def metadata(url, cap):
    mid = url.rsplit("=", 1)[1]
    return 200, json.dumps(dict(code=200, order_book_details=[dict(
        market_id=int(mid), symbol={"145": "WTI", "159": "BRENTOIL"}[mid], status="active")])).encode(), "application/json"


class ParticipantStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "campaign"
        self.cfg = config()

    def test_window_boundaries_and_timezone_are_explicit(self):
        self.assertEqual(choose_slot(self.cfg, NOW)["id"], "day0")
        self.assertIsNone(choose_slot(self.cfg, datetime(2026, 11, 8, tzinfo=timezone.utc)))
        with self.assertRaises(ValueError):
            choose_slot(self.cfg, datetime(2026, 11, 7, 21))

    def test_full_reservation_and_unknown_crash_are_not_reset(self):
        target = reserve(self.folder, self.cfg, self.cfg["slots"][0], NOW)
        self.assertTrue(target.is_dir())
        self.assertEqual(records(self.folder)[0]["reserved_bytes"], 2097152)
        with self.assertRaises(SourceStop):
            reserve(self.folder, self.cfg, self.cfg["slots"][1], NOW)

    def test_missing_or_cut_journal_cannot_recreate_budget(self):
        self.folder.mkdir()
        (self.folder / "old.raw.gz").write_bytes(b"retained")
        with self.assertRaises(SourceStop):
            records(self.folder)
        (self.folder / "events.jsonl").write_bytes(b'{"event":"SLOT_STARTED"')
        with self.assertRaises(SourceStop):
            records(self.folder)

    def test_denied_host_is_inherited_without_reaching_a_client(self):
        raw = b'{"event":"BLOCK","key":"mainnet.zklighter.elliot.ai/api/v1/feed"}\n'
        self.assertTrue(inherited_source_block(raw))
        self.assertFalse(inherited_source_block(b'{"event":"BLOCK","key":"other.test"}\n'))
        with self.assertRaises(SourceStop):
            inherited_source_block(raw[:-1])

    def test_baseline_keeps_old_spend_and_rejects_prefix_corruption(self):
        a = b'{"event":"START","id":"0","reserved_bytes":20}\n'
        b = b'{"event":"START","id":"1","reserved_bytes":30}\n'
        c = b'{"event":"END","id":"1","charged_bytes":25}\n'
        self.assertEqual(combined_baseline(a, b + c, a, b), a + b + c)
        for legacy, priority in [(a + c, b), (a, b[:-1]), (a, a)]:
            with self.subTest(legacy=legacy, priority=priority), self.assertRaises(ValueError):
                combined_baseline(legacy, priority, a, b)

    def test_hour_boundary_uses_actual_task_start_and_keeps_old_fallback(self):
        r = dict(hour="20261107T19", tasks=[dict(id="R413", state="PROCESS_OK", started_utc="2026-11-07T20:00:01+00:00")])
        self.assertTrue(paper_already_attempted(r, "R413", "20261107T20"))
        self.assertFalse(paper_already_attempted(r, "R413", "20261107T19"))
        del r["tasks"][0]["started_utc"]
        self.assertTrue(paper_already_attempted(r, "R413", "20261107T19"))

    def test_schema_never_converts_source_prices_or_positions(self):
        row = trade()
        original = json.dumps(row)
        self.assertEqual(classify(row, self.cfg["markets"]), ("145", "update/trade", 1))
        self.assertEqual(json.dumps(row), original)
        row["trades"][0]["market_id"] = 999
        with self.assertRaises(SourceStop):
            classify(row, self.cfg["markets"])

    def test_workflow_keeps_one_writer_and_a_distinct_owner_command(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/quant-participant-runtime.yml"
        source = path.read_text()
        self.assertRegex(source, r"(?m)^concurrency:\n  group: quant-runtime-single-writer\n  cancel-in-progress: false\n")
        self.assertIn("github.event.comment.user.login == github.repository_owner", source)
        self.assertIn("'/quant-participant-migrate'", source)
        self.assertNotIn("'/quant-tick'", source)
        self.assertIn("active == 'R428' or (active == 'R422'", source)
        names = re.findall(r"(?m)^      - name: (.*)$", source)
        self.assertLess(names.index("Publish hour reservation before HTTP"), names.index("Run native capture and priority papers"))


class ParticipantCaptureTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "campaign"
        self.cfg = config()

    async def run_capture(self, connection, http=metadata, slot=None):
        return await capture(self.folder, self.cfg, slot or self.cfg["slots"][0],
                             http_get=http, connect=connection, clock=lambda: NOW)

    async def test_raw_first_seen_capture_counts_and_no_duplicate_slot(self):
        text = json.dumps(ticker(), separators=(",", ":"))
        ws = FakeWS([dict(type="connected"), text, trade(), ticker("159"), trade("159"), dict(type="ping")])
        connection = FakeConnection(ws)
        r = await self.run_capture(connection)
        self.assertEqual(r["state"], "PARTIAL_EARLY_TIMEOUT")
        self.assertEqual(r["source_calls"], 7)
        self.assertTrue(r["both_markets_have_live_ticker_and_trade"])
        self.assertEqual(connection.calls[0][0], (STREAM,))
        self.assertEqual(ws.sent[-1], {"type": "pong"})
        path = self.folder / "slots/day0/messages.jsonl.gz"
        frames = [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
        import base64, hashlib
        body = base64.b64decode(frames[1]["body_b64"])
        self.assertEqual(body, text.encode())
        self.assertEqual(hashlib.sha256(body).hexdigest(), frames[1]["sha256"])
        self.assertIsNone(r["pnl"])
        self.assertFalse(r["full_day"])
        again = await self.run_capture(connection)
        self.assertEqual(again["state"], "SLOT_ALREADY_ATTEMPTED")
        self.assertEqual(len(connection.calls), 1)

    async def test_http_denial_is_preserved_and_next_date_cannot_retry(self):
        connection = FakeConnection(FakeWS([]))
        r = await self.run_capture(connection, http=lambda u, c: (451, b"denied", "text/plain"))
        self.assertEqual(r["state"], "SOURCE_STOP")
        self.assertFalse(connection.calls)
        raw = self.folder / "slots/day0/145.metadata.gz"
        self.assertEqual(gzip.decompress(raw.read_bytes()), b"denied")
        with self.assertRaises(SourceStop):
            await self.run_capture(connection, slot=self.cfg["slots"][1])

    async def test_socket_failure_consumes_reservation_without_reconnect(self):
        connection = FakeConnection(FakeWS([]), failure=OSError("ordinary connection denied"))
        r = await self.run_capture(connection)
        self.assertEqual(r["state"], "SOURCE_STOP")
        self.assertEqual(r["reserved_bytes"], 2097152)
        self.assertEqual(len(connection.calls), 1)
        with self.assertRaises(SourceStop):
            await self.run_capture(connection)

    async def test_locked_websocket_client_cannot_follow_a_redirect(self):
        from websockets.asyncio.client import connect
        from websockets.datastructures import Headers
        from websockets.exceptions import InvalidStatus
        from websockets.http11 import Response
        connection = deny_ws_redirects(connect(STREAM))
        exc = InvalidStatus(Response(307, "Moved", Headers({"Location": "wss://other.test/stream"}), b"redirect"))
        self.assertIs(connection.process_redirect(exc), exc)
        self.assertEqual(connection.uri, STREAM)

    async def test_redirect_body_is_preserved_without_contacting_target(self):
        from websockets.datastructures import Headers
        from websockets.exceptions import InvalidStatus
        from websockets.http11 import Response
        exc = InvalidStatus(Response(307, "Moved", Headers({"Location": "wss://other.test/stream"}), b"redirect body"))
        class RedirectConnection(FakeConnection):
            def process_redirect(self, error):
                return "wss://other.test/stream"
            async def __aenter__(self):
                if self.process_redirect(exc) is exc:
                    raise exc
                raise AssertionError("target would have been contacted")
        connection = RedirectConnection(FakeWS([]))
        r = await self.run_capture(connection)
        self.assertEqual(r["state"], "SOURCE_STOP")
        self.assertEqual(r["handshake_error_status"], 307)
        self.assertEqual(gzip.decompress((self.folder / "slots/day0/handshake_error.body.gz").read_bytes()), b"redirect body")
        self.assertEqual(len(connection.calls), 1)

    async def test_bad_message_raw_is_retained_and_source_stops(self):
        connection = FakeConnection(FakeWS([b'<html>challenge</html>']))
        r = await self.run_capture(connection)
        self.assertEqual(r["state"], "SOURCE_STOP")
        self.assertEqual(r["frames"], 1)
        self.assertTrue((self.folder / "slots/day0/messages.jsonl.gz").is_file())
        self.assertTrue(any(x["event"] == "SOURCE_BLOCK" for x in records(self.folder)))

    async def test_budget_exhaustion_precedes_every_network_callback(self):
        self.cfg["max_source_bytes"] = 2097151
        connection = FakeConnection(FakeWS([]))
        calls = []
        with self.assertRaises(SourceStop):
            await self.run_capture(connection, http=lambda *a: calls.append(a))
        self.assertFalse(calls)
        self.assertFalse(connection.calls)

    async def test_wrong_absolute_window_precedes_all_network_and_reservations(self):
        connection = FakeConnection(FakeWS([]))
        calls = []
        with self.assertRaises(SourceStop):
            await self.run_capture(connection, http=lambda *a: calls.append(a), slot=self.cfg["slots"][1])
        self.assertFalse(calls)
        self.assertFalse(connection.calls)
        self.assertFalse(self.folder.exists())

    async def test_frame_limit_is_partial_not_a_profitable_or_full_day(self):
        self.cfg["max_frames"] = 1
        r = await self.run_capture(FakeConnection(FakeWS([ticker(), trade()])))
        self.assertEqual(r["state"], "PARTIAL_FRAME_LIMIT")
        self.assertFalse(r["both_markets_have_live_ticker_and_trade"])
        self.assertFalse(r["R367_usable_day"])
        self.assertFalse(r["reservation_refunded"])
