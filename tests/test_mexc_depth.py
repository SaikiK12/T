import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from lab import mexc
from scripts import record_mexc_depth as recorder


class MexcDepthTests(unittest.TestCase):
    @staticmethod
    def book(timestamp=1_800_000_000_000):
        return {
            "timestamp": timestamp,
            "asks": [[101.0, 1_000.0, 3], [102.0, 1_000.0, 2]],
            "bids": [[99.0, 1_000.0, 4], [98.0, 1_000.0, 1]],
        }

    @staticmethod
    def signal():
        return pd.DataFrame({"t": [1_792_418_400_000], "symbol": ["BTCUSDT"], "rank": [1.0]})

    @staticmethod
    def table(contract_size=1.0):
        return pd.DataFrame({
            "symbol": ["BTC_USDT"], "type": [1], "contract_size": [contract_size],
            "taker": [0.0002], "maker": [0.0001], "state": [1], "settle": ["USDT"],
        })

    def patches(self, depth, table=None):
        return mock.patch.multiple(
            recorder.mexc,
            get=mock.Mock(return_value=depth),
            contracts=mock.Mock(return_value=table if table is not None else self.table()),
        )

    def test_walk_formula_and_partial_fill_nan(self):
        levels = [[101.0, 10.0], [102.0, 10.0]]
        # First level fills 1,010 USDT; the next 990 USDT is at 2% from mid.
        expected = (1_010 * 0.01 + 990 * 0.02) / 2_000 * 1e4
        self.assertAlmostEqual(recorder.walk(levels, 1.0, 2_000.0, 100.0), expected)
        self.assertTrue(np.isnan(recorder.walk(levels, 3.0, 100_000.0, 100.0)))
        bids = [[99.0, 10.0], [98.0, 10.0]]
        self.assertTrue(np.isfinite(recorder.walk(bids, 1.0, 1_900.0, 100.0)))
        self.assertTrue(np.isfinite(recorder.walk(bids, 1.0, 1_900.0, 100.0, descending=True)))

    def test_malformed_levels_and_crossed_books_are_rejected(self):
        cases = [
            {"asks": [[101.0, -1.0]], "bids": [[99.0, 1.0]]},
            {"asks": [[101.0, np.nan]], "bids": [[99.0, 1.0]]},
            {"asks": [[0.0, 1.0]], "bids": [[-1.0, 1.0]]},
            {"asks": [[np.inf, 1.0]], "bids": [[99.0, 1.0]]},
            {"asks": [[102.0, 1.0], [101.0, 1.0]], "bids": [[99.0, 1.0]]},
            {"asks": [[101.0, 1.0]], "bids": [[98.0, 1.0], [99.0, 1.0]]},
            {"asks": [[99.0, 1.0]], "bids": [[99.0, 1.0]]},
        ]
        for bad in cases:
            with self.subTest(bad=bad), mock.patch.object(recorder.mexc, "get", return_value={**self.book(), **bad}):
                with self.assertRaises(ValueError):
                    recorder.snapshot("BTC_USDT", 1.0)
        with self.assertRaises(ValueError):
            recorder.snapshot("BTC_USDT", 0.0)

    def test_empty_source_and_empty_status_are_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            result = recorder.record(pd.DataFrame(), run_at="2026-10-19T15:45:00Z",
                                     depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["attempted"], 0)
            self.assertFalse(depth.exists())
            self.assertFalse(sidecar.exists())
            status_path = root / "status.json"
            out = recorder.status(depth_path=depth, status_path=status_path)
            self.assertEqual(out["coins"], 0)
            self.assertEqual(out["impact_denominators"]["10k"]["buy"]["observed"], 0)
            self.assertTrue(status_path.exists())

            with mock.patch.object(recorder.mexc, "contracts", return_value=pd.DataFrame()):
                result = recorder.record(self.signal(), run_at="2026-10-19T15:45:00Z",
                                         depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["attempted"], 0)
            self.assertFalse(sidecar.exists())

    def test_all_failed_runs_append_attempts_without_legacy_rows(self):
        sig = self.signal()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            with self.patches(self.book()), mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "require_unique_mapping") as guard, \
                    mock.patch.object(recorder.mexc, "get", side_effect=mexc.MexcError("unavailable")):
                result = recorder.record(sig, run_at="2026-10-19T15:45:00Z", max_retries=2, retry_delay=0,
                                         depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["failed"], 1)
            self.assertFalse(depth.exists())
            events = [json.loads(line) for line in sidecar.read_text().splitlines()]
            self.assertEqual([e["attempt"] for e in events], [1, 2])
            self.assertTrue(all(e["status"] == "failed" for e in events))
            guard.assert_called_once()
            out = recorder.status(depth_path=depth, status_path=root / "status.json", sidecar_path=sidecar)
            self.assertEqual(out["sidecar"]["attempts"], 2)
            self.assertEqual(out["sidecar"]["failed_unique_slot_contracts"], 1)
            self.assertEqual(out["sidecar"]["succeeded_unique_slot_contracts"], 0)
            self.assertEqual(out["sidecar"]["recoveries"], 0)

    def test_success_after_retry_and_same_slot_are_idempotent(self):
        sig = self.signal()
        response = self.book()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            api = mock.Mock(side_effect=[mexc.MexcError("temporary"), response])
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", api):
                result = recorder.record(sig, run_at="2026-10-19T15:45:00Z", max_retries=3, retry_delay=0,
                                         depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["recorded"], 1)
            self.assertEqual(api.call_count, 2)
            self.assertEqual(list(pd.read_csv(depth).columns), list(recorder.LEGACY_COLUMNS))
            before = depth.read_bytes()
            events = [json.loads(line) for line in sidecar.read_text().splitlines()]
            attempts = [e for e in events if e["event_type"] == "attempt"]
            rows = [e for e in events if e["event_type"] == "legacy_row"]
            self.assertEqual([e["attempt"] for e in attempts], [1, 2])
            self.assertEqual(attempts[-1]["status"], "success")
            self.assertEqual(attempts[-1]["contract_size"], 1.0)
            self.assertIn("receive_ms", attempts[-1])
            self.assertIn("age_ms", attempts[-1])
            self.assertIn("clock_skew_ms", attempts[-1])
            self.assertIn("fill_denominators", attempts[-1])
            self.assertIn("buy_1k", attempts[-1]["fill_denominators"])
            self.assertEqual(rows[-1]["status"], "written")
            self.assertTrue(rows[-1]["legacy_row_written"])

            # 15:55 is the same half-hour slot. It must not fetch or append.
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", side_effect=AssertionError("duplicate fetch")):
                again = recorder.record(sig, run_at="2026-10-19T15:55:00Z", max_retries=1, retry_delay=0,
                                        depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(again["skipped"], 1)
            self.assertEqual(depth.read_bytes(), before)
            self.assertEqual(len(sidecar.read_text().splitlines()), 3)
            out = recorder.status(depth_path=depth, status_path=root / "status.json", sidecar_path=sidecar)
            self.assertEqual(out["sidecar"]["attempts"], 2)
            self.assertEqual(out["sidecar"]["succeeded_unique_slot_contracts"], 1)
            self.assertEqual(out["sidecar"]["failed_unique_slot_contracts"], 1)
            self.assertEqual(out["sidecar"]["recoveries"], 1)
            self.assertEqual(out["sidecar"]["rows_written"], 1)

    def test_sidecar_records_local_receive_timing_and_frozen_metadata(self):
        sig = self.signal()
        exchange_ms = 1_800_000_000_100
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", return_value=self.book(exchange_ms)), \
                    mock.patch.object(recorder, "_local_ms", side_effect=[1_800_000_000_000, 1_800_000_000_250]):
                result = recorder.record(sig, run_at="2026-10-19T15:45:00Z", max_retries=1, retry_delay=0,
                                         workers=1, depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["recorded"], 1)
            events = [json.loads(line) for line in sidecar.read_text().splitlines()]
            attempt = next(e for e in events if e["event_type"] == "attempt")
            self.assertEqual(attempt["exchange_timestamp_ms"], exchange_ms)
            self.assertEqual(attempt["receive_ms"], 1_800_000_000_250)
            self.assertEqual(attempt["age_ms"], 150)
            self.assertAlmostEqual(attempt["clock_skew_ms"], -25.0)
            self.assertNotEqual(attempt["receipt_time"], attempt["receive_time"])
            self.assertEqual(attempt["contract_metadata"]["type"], 1)
            self.assertEqual(attempt["contract_metadata"]["state"], 1)
            self.assertEqual(attempt["contract_metadata"]["settle"], "USDT")
            self.assertEqual(attempt["contract_metadata"]["taker"], 0.0002)
            self.assertEqual(attempt["contract_metadata"]["maker"], 0.0001)

    def test_tradfi_failure_fails_closed_before_any_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            api = mock.Mock(side_effect=AssertionError("depth must not be requested"))
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", side_effect=RuntimeError("unavailable")), \
                    mock.patch.object(recorder.mexc, "get", api):
                result = recorder.record(self.signal(), run_at="2026-10-19T15:45:00Z",
                                         depth_path=depth, sidecar_path=sidecar)
            self.assertFalse(result["universe_resolved"])
            self.assertIn("unavailable", result["universe_error"])
            self.assertFalse(depth.exists())
            self.assertFalse(sidecar.exists())
            api.assert_not_called()

    def test_legacy_write_failure_is_a_false_row_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", return_value=self.book()), \
                    mock.patch.object(pd.DataFrame, "to_csv", side_effect=OSError("disk full")):
                result = recorder.record(self.signal(), run_at="2026-10-19T15:45:00Z", max_retries=1, retry_delay=0,
                                         workers=1, depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["recorded"], 0)
            self.assertEqual(result["write_failed"], 1)
            events = [json.loads(line) for line in sidecar.read_text().splitlines()]
            attempt = next(e for e in events if e["event_type"] == "attempt")
            row = next(e for e in events if e["event_type"] == "legacy_row")
            self.assertFalse(attempt["legacy_row_written"])
            self.assertEqual(row["status"], "write_failed")
            self.assertFalse(row["legacy_row_written"])

    def test_failed_slot_retry_continues_attempt_numbers(self):
        sig = self.signal()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", side_effect=mexc.MexcError("down")):
                recorder.record(sig, run_at="2026-10-19T15:45:00Z", max_retries=2, retry_delay=0,
                                depth_path=depth, sidecar_path=sidecar)
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", return_value=self.book()):
                result = recorder.record(sig, run_at="2026-10-19T15:49:00Z", max_retries=1, retry_delay=0,
                                         depth_path=depth, sidecar_path=sidecar)
            self.assertEqual(result["recorded"], 1)
            events = [json.loads(line) for line in sidecar.read_text().splitlines()]
            attempts = [e for e in events if e["event_type"] == "attempt"]
            self.assertEqual([e["attempt"] for e in attempts], [1, 2, 3])

    def test_status_reports_observed_and_undefined_impact_denominators(self):
        sig = self.signal()
        shallow = {"timestamp": 1_800_000_000_000,
                   "asks": [[101.0, 10.0]], "bids": [[99.0, 10.0]]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            sidecar = root / "attempts.jsonl"
            with mock.patch.object(recorder.mexc, "contracts", return_value=self.table()), \
                    mock.patch.object(recorder.live, "tradfi", return_value=set()), \
                    mock.patch.object(recorder.mexc, "get", return_value=shallow):
                recorder.record(sig, run_at="2026-10-19T15:45:00Z", max_retries=1, retry_delay=0,
                                depth_path=depth, sidecar_path=sidecar)
            out = recorder.status(depth_path=depth, status_path=root / "status.json")
            den = out["impact_denominators"]
            self.assertEqual(den["1k"]["buy"]["observed"], 1)
            self.assertEqual(den["1k"]["sell"]["undefined"], 1)
            self.assertEqual(den["10k"]["buy"]["undefined"], 1)
            self.assertEqual(den["50k"]["sell"]["undefined"], 1)
            self.assertEqual(out["impact_statistics"], den)
            self.assertIsNone(out["share_web_10k_above_assumed"])
            self.assertIsNone(out["share_api_10k_above_assumed"])
            self.assertEqual(out["coin_denominators"]["web_10k"]["observed"], 0)
            self.assertEqual(out["fee_coverage_10k"]["web"]["observed"], 1)
            self.assertEqual(out["fee_coverage_10k"]["api"]["observed"], 1)
            self.assertEqual(out["cost_coverage_10k"]["web"]["observed"], 0)
            coin = out["per_coin"][0]
            self.assertEqual(coin["impact_1k_observed"], 0)  # both-side impact is undefined
            self.assertEqual(coin["impact_1k_undefined"], 1)

    def test_status_shares_use_observed_coin_denominators(self):
        rows = []
        for symbol, rank, fee_taker, fee_maker, defined in (
                ("AUSDT", 1.0, 0.0002, 0.0001, True),
                ("BUSDT", 2.0, np.nan, np.nan, False)):
            row = {column: np.nan for column in recorder.LEGACY_COLUMNS}
            row.update({"run_at": "2026-10-19T15:45:00Z", "symbol": symbol, "contract": f"{symbol[:-4]}_USDT",
                        "signal_hour": 1_800_000_000_000, "rank": rank, "fee_taker": fee_taker,
                        "fee_maker": fee_maker, "half_spread_bp": 1.0, "bid_depth_05": 10.0,
                        "bid_reach_bp": 20.0, "ask_depth_05": 10.0, "ask_reach_bp": 20.0})
            if defined:
                for key in ("buy_1k", "sell_1k", "buy_10k", "sell_10k", "buy_50k", "sell_50k"):
                    row[key] = 1.0
            rows.append(row)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            depth = root / "depth.csv"
            pd.DataFrame(rows, columns=recorder.LEGACY_COLUMNS).to_csv(depth, index=False)
            out = recorder.status(depth_path=depth, status_path=root / "status.json",
                                  sidecar_path=root / "attempts.jsonl")
        self.assertEqual(out["coin_denominators"]["web_10k"], {"observed": 1, "undefined": 1, "total": 2})
        self.assertEqual(out["coin_denominators"]["api_10k"]["observed"], 1)
        self.assertEqual(out["share_web_10k_above_assumed"], 0.0)
        self.assertEqual(out["share_api_10k_above_assumed"], 1.0)
        self.assertEqual(out["fee_coverage"]["taker"], {"observed": 1, "undefined": 1, "total": 2})
        self.assertEqual(out["fee_coverage"]["maker"]["observed"], 1)


if __name__ == "__main__":
    unittest.main()
