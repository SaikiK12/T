import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import probe_pair_quotes as probe


class Clock:
    def __init__(self):
        self.now = 0.

    def monotonic(self):
        return self.now

    def time_ns(self):
        return 10_000_000_000 + self.monotonic_ns()

    def monotonic_ns(self):
        return int(self.now * 1e9)

    def sleep(self, n):
        self.now += n


class Response(io.BytesIO):
    status = 200


class BoundedCaptureTests(unittest.TestCase):
    def test_first_seen_and_shared_rate_pacing_are_request_specific(self):
        clock = Clock()
        def get(req, timeout):
            self.assertTrue(req.full_url.startswith("https://"))
            self.assertLessEqual(timeout, 8.)
            clock.sleep(.2)
            return Response(b'{"code":200}')
        with tempfile.TemporaryDirectory() as d:
            c = probe.Capture(Path(d)/"evidence", opener=get, clock=clock)
            for i in range(2):
                c.get(str(i), "https://example.test/public", lighter=True)
            receipts = [r["receipt"] for r in c.records]
            self.assertEqual(c.total, 24)
            self.assertEqual(receipts[1]["started_mono_ns"], 1_100_000_000)
            self.assertNotEqual(receipts[0]["received_utc_ns"], receipts[1]["received_utc_ns"])
            c.save()
            with self.assertRaises(FileExistsError):
                probe.Capture(Path(d)/"evidence", opener=get, clock=clock)

    def test_failures_count_and_are_preserved_including_empty_response(self):
        def fail(*args, **kwargs):
            raise TimeoutError("fixture timeout")
        with tempfile.TemporaryDirectory() as d:
            c = probe.Capture(Path(d)/"evidence", opener=fail, clock=Clock())
            self.assertIsNone(c.get("failed", "https://example.test/public"))
            self.assertIn("timeout", c.records[0]["error"])
            self.assertEqual(gzip.decompress((c.out/"failed.json.gz").read_bytes()), b"")
            with mock.patch.object(probe, "MAX_REQUESTS", 1), self.assertRaises(probe.Stop):
                c.get("again", "https://example.test/public")
            self.assertEqual(len(c.records), 1)

    def test_exact_cap_truncation_blocks_parsing_and_never_reads_one_extra_byte(self):
        with tempfile.TemporaryDirectory() as d:
            c = probe.Capture(Path(d)/"evidence", opener=lambda *a, **kw: Response(b"x"*10), clock=Clock())
            with mock.patch.object(probe, "MAX_BYTES", 10):
                self.assertIsNone(c.get("big", "https://example.test/public"))
            self.assertEqual(c.total, 5)
            self.assertIn("cap", c.records[0]["error"])

    def test_duration_expiry_does_not_start_another_request(self):
        with tempfile.TemporaryDirectory() as d:
            clock = Clock()
            c = probe.Capture(Path(d)/"evidence", opener=lambda *a, **kw: self.fail("network used"), clock=clock)
            clock.sleep(probe.MAX_SECONDS)
            with self.assertRaises(probe.Stop):
                c.get("late", "https://example.test/public")
            self.assertEqual(c.records, [])

    def test_sealed_evidence_drift_and_missing_files_block_all_economics(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(probe, "verify_code"):
            lane = Path(d)
            (lane/"code_inputs.json").write_text("{}")
            (lane/"evidence").mkdir()
            (lane/"evidence/receipts.json").write_text("{}")
            probe.seal(lane)
            with self.assertRaisesRegex(ValueError, "already sealed"):
                probe.seal(lane)
            (lane/"evidence/receipts.json").write_text('{"changed":true}')
            with self.assertRaisesRegex(ValueError, "changed"):
                probe.report(lane)

    def test_full_offline_report_preserves_twelve_rows_cost_scenarios_and_unverified_sessions(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(probe, "verify_code"):
            lane = Path(d)
            (lane/"code_inputs.json").write_text("{}")
            c = probe.Capture(lane/"evidence", opener=lambda *a, **kw: None, clock=Clock())
            identities = []
            for market, symbol in enumerate(probe.SYMBOLS):
                mm = {"symbol": symbol+"_USDT", "contractSize": ".01", "volUnit": 1, "minVol": 1,
                      "maxVol": 100000, "type": 1, "settleCoin": "USDT", "state": 0,
                      "apiAllowed": True, "marketOrderMaxLevel": 20}
                lm = {"symbol": symbol, "market_id": market, "market_type": "perp", "status": "active",
                      "is_frozen": False, "index_price": "100", "supported_size_decimals": 2,
                      "min_base_amount": ".01", "min_quote_amount": "10"}
                payloads = [(symbol+"_mexc_meta", {"success": True, "data": mm}),
                            (symbol+"_lighter_meta", {"code": 200, "order_book_details": [lm]}),
                            (symbol+"_fair", {"success": True, "data": {"symbol": symbol+"_USDT", "fairPrice": 100, "timestamp": 10000}})]
                for i in (0, 1):
                    payloads.extend([(f"{symbol}_mexc_book_{i}", {"success": True, "data": {"bids": [[99, 1000, 1]], "asks": [[101, 1000, 1]]}}),
                                     (f"{symbol}_lighter_book_{i}", {"code": 200, "bids": [{"price": "99", "remaining_base_amount": "10"}],
                                                                  "asks": [{"price": "101", "remaining_base_amount": "10"}]})])
                for name, payload in payloads:
                    raw = json.dumps(payload).encode()
                    c.opener = lambda *a, _raw=raw, **kw: Response(_raw)
                    c.get(name, "https://example.test/public")
                identities.append({"symbol": symbol, "mexc": symbol+"_USDT", "market_id": market})
            c.save(complete=True)
            probe.write(c.out/"pairs.json", identities)
            probe.seal(lane)
            out = json.loads(probe.report(lane).read_text())
            self.assertEqual(len(out["observations"]), 12)
            self.assertEqual(out["predictive_trials"], 0)
            for row in out["observations"]:
                self.assertNotIn("error", row)
                self.assertTrue(row["first_seen_pair_ok"])
                self.assertFalse(row["execution_ready"])
                self.assertFalse(row["session_calendar_verified"])
                self.assertFalse(row["funding_notional_observation"]["settlement_notional_verified"])
                costs = row["conditional_cost"]
                self.assertEqual(costs["quantity_base"], 2.5)
                self.assertEqual([r["multiple"] for r in costs["scenarios"]], [1, 2, 3])
                self.assertAlmostEqual(costs["scenarios"][0]["round_trip_cost_usd"], 10.7)
            original = (lane/"results.json").read_bytes()
            probe.report(lane)
            self.assertEqual((lane/"results.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
