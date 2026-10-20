"""Synthetic acquisition checks: no market endpoints or research caches are read."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts import fetch_mexc_history as fetch


class HistoryReceipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.end = fetch.START + 3 * fetch.mexc.HOUR
        self.rows = pd.DataFrame({"t": [fetch.START, self.end - fetch.mexc.HOUR], "close": [1., 2.]})
        self.actual_fetch_klines = fetch.mexc.fetch_klines
        self.bars = patch.object(fetch.mexc, "fetch_klines", return_value=self.rows).start()
        self.funding = patch.object(fetch.mexc, "funding_history", return_value=pd.DataFrame(columns=["t", "rate", "cycle_h"])).start()
        self.addCleanup(patch.stopall)

    def run_one(self, end=None):
        return fetch.one("TOY_USDT", self.end if end is None else end, self.out)[1]

    def test_closed_hour_bound_includes_last_complete_bar(self):
        h = fetch.mexc.HOUR
        for now in (12 * h, 12 * h + 34 * 60_000):
            self.assertEqual(fetch.closed_hour_end(now), 12 * h)
            self.assertEqual(fetch.closed_hour_end(now) - h, 11 * h)

    def test_roundtrip_receipt_empty_funding_and_same_request_resume(self):
        self.assertFalse(self.run_one().startswith("error"))
        p = self.out / "receipts/TOY_USDT.json"
        saved = json.loads(p.read_text())
        self.assertFalse(saved["coverage_certified"])
        self.assertEqual(saved["files"]["funding"]["rows"], 0)
        self.assertEqual(saved["files"]["klines_1h"]["max_t"], self.end - fetch.mexc.HOUR)
        self.bars.reset_mock()
        self.assertTrue(self.run_one().startswith("skip verified"))
        self.bars.assert_not_called()
        self.assertEqual(json.loads(p.read_text()), saved)

    def test_legacy_cache_rejected_without_read_write_or_fetch(self):
        p = self.out / "funding/TOY_USDT.parquet"
        p.parent.mkdir()
        p.write_bytes(b"historical bytes")
        self.assertIn("legacy/partial", self.run_one())
        self.assertEqual(p.read_bytes(), b"historical bytes")
        self.bars.assert_not_called()

    def test_later_requested_end_does_not_skip_stale_snapshot(self):
        self.run_one()
        self.bars.reset_mock()
        self.assertIn("cached request differs", self.run_one(self.end + fetch.mexc.HOUR))
        self.bars.assert_not_called()

    def test_changed_or_missing_bytes_rejected(self):
        self.run_one()
        p = self.out / "funding/TOY_USDT.parquet"
        p.write_bytes(b"changed")
        self.assertIn("cached bytes differ", self.run_one())
        p.unlink()  # temporary fixture only
        self.assertIn("cached bytes differ", self.run_one())

    def test_malformed_receipt_is_an_error_not_a_skip(self):
        p = self.out / "receipts/TOY_USDT.json"
        p.parent.mkdir()
        p.write_text("{")
        self.assertTrue(self.run_one().startswith("error"))
        self.bars.assert_not_called()

    def test_bad_timestamps_do_not_write_any_dataset(self):
        for times in ([fetch.START, fetch.START], [self.end], [fetch.START + 1, fetch.START], [None]):
            with self.subTest(times=times):
                self.bars.return_value = pd.DataFrame({"t": times})
                self.assertTrue(self.run_one().startswith("error"))
                self.assertFalse(list(self.out.rglob("*.parquet")))

    def test_failed_fetch_has_no_receipt(self):
        self.funding.side_effect = fetch.mexc.MexcError("synthetic outage")
        self.assertIn("synthetic outage", self.run_one())
        self.assertFalse(list(self.out.rglob("*.parquet")))
        self.assertFalse(list(self.out.rglob("*.json")))

    def test_interrupted_write_cannot_be_resumed_as_success(self):
        original = pd.DataFrame.to_parquet
        calls = 0

        def interrupted(frame, target, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                target.write(b"partial parquet bytes")
                raise OSError("synthetic disk failure")
            return original(frame, target, **kwargs)

        with patch.object(pd.DataFrame, "to_parquet", interrupted):
            self.assertIn("synthetic disk failure", self.run_one())
        before = {str(p): p.read_bytes() for p in self.out.rglob("*.parquet")}
        self.assertFalse(list(self.out.rglob("*.json")))
        self.assertIn("legacy/partial", self.run_one())
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.out.rglob("*.parquet")})

    def test_actual_kline_request_includes_last_closed_hour(self):
        h = fetch.mexc.HOUR
        end = fetch.closed_hour_end(fetch.START + 3 * h + 10_000)
        data = {"time": [(end - h) // 1000],
                **{k: [1.] for k in ("open", "high", "low", "close", "vol", "amount")}}
        # Use the real paging/filtering implementation beneath the mocked transport.
        with patch.object(fetch.mexc, "get", return_value=data) as get:
            result = self.actual_fetch_klines("TOY_USDT", fetch.START, end)
        self.assertEqual(result.t.tolist(), [end - h])
        self.assertEqual(get.call_args.args[1]["end"], (end - h) // 1000)

    def test_main_reports_per_symbol_failure_and_preserves_legacy_manifest(self):
        legacy = self.out / "manifest.json"
        legacy.write_bytes(b"old run provenance")
        table = pd.DataFrame({"symbol": ["TOY_USDT"], "type": [1]})
        with patch.object(fetch.mexc, "contracts", return_value=table), \
                patch.object(fetch, "one", return_value=("TOY_USDT", "error legacy cache")), \
                patch("sys.argv", ["fetch", "--out", str(self.out)]):
            self.assertEqual(fetch.main(), 1)
        self.assertEqual(legacy.read_bytes(), b"old run provenance")
        report = json.loads(next((self.out / "runs").glob("*/manifest.json")).read_text())
        self.assertEqual(report["errors"], ["TOY_USDT"])
        self.assertEqual(report["outcomes"]["TOY_USDT"], "error legacy cache")
        self.assertFalse(report["coverage_certified"])

    def test_invalid_end_rejected_before_network(self):
        for end in ("2026-10-20", "2099-01-01T00:00Z", "2025-04-01T01:01Z"):
            with self.subTest(end=end), patch.object(fetch.mexc, "contracts") as contracts, \
                    patch("sys.argv", ["fetch", "--end", end]), \
                    patch("sys.stderr"):
                with self.assertRaises(SystemExit) as raised:
                    fetch.main()
                self.assertEqual(raised.exception.code, 2)
                contracts.assert_not_called()

    def test_pinned_end_and_distinct_run_records(self):
        table = pd.DataFrame({"symbol": ["TOY_USDT"], "type": [1]})
        with patch.object(fetch.mexc, "contracts", return_value=table), \
                patch("sys.argv", ["fetch", "--out", str(self.out), "--end", "2025-04-01T03:00:00Z"]):
            self.assertEqual(fetch.main(), 0)
            self.assertEqual(fetch.main(), 0)
        reports = [json.loads(p.read_text()) for p in (self.out / "runs").glob("*/manifest.json")]
        self.assertEqual(len(reports), 2)
        self.assertTrue(all(r["end_exclusive"] == self.end for r in reports))
        self.assertEqual(self.bars.call_count, 2)  # contract and index once, no calls on resume


if __name__ == "__main__":
    unittest.main()
