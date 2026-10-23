"""Synthetic checks for the MEXC TradFi fetcher: no market endpoint is called."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts import fetch_mexc_tradfi as tf


def fake_get(calls):
    """A kline endpoint that serves one bar per step inside [start, end] (seconds), and records each request."""
    def get(path, params=None, **_):
        calls.append((path, dict(params)))
        step = tf.STEP[params["interval"]] // 1000
        t = list(range(params["start"], params["end"] + 1, step))
        out = {"time": t, "open": [1.0] * len(t), "high": [2.0] * len(t), "low": [0.5] * len(t),
               "close": [1.5] * len(t)}
        if not path.startswith("kline/index_price"):
            out |= {"vol": [3.0] * len(t), "amount": [4.0] * len(t)}
        return out
    return get


class BarsTest(unittest.TestCase):
    def test_pages_cover_the_range_once(self):
        calls = []
        start = 1_700_000_000_000 - 1_700_000_000_000 % tf.MINUTE
        end = start + (2 * tf.PAGE + 7) * tf.STEP["Min5"]
        with patch.object(tf.mexc, "get", side_effect=fake_get(calls)):
            df = tf.bars("NAS100_USDT", start, end, "Min5")
            idx = tf.bars("NAS100_USDT", start, start + 3 * tf.MINUTE, "Min1", "index_price")
        self.assertEqual(len(df), 2 * tf.PAGE + 7)
        self.assertEqual(df.t.iloc[0], start)
        self.assertEqual(df.t.iloc[-1], end - tf.STEP["Min5"])
        self.assertTrue(df.t.diff().dropna().eq(tf.STEP["Min5"]).all())
        self.assertEqual(len([c for c in calls if c[1]["interval"] == "Min5"]), 3)
        self.assertEqual(calls[-1][0], "kline/index_price/NAS100_USDT")
        self.assertEqual(len(idx), 3)
        self.assertTrue(idx.vol.isna().all())

    def test_tradfi_selection(self):
        table = pd.DataFrame({"symbol": ["BTC_USDT", "NAS100_USDT", "TESLA_USDT"], "type": [1, 2, 2]})
        self.assertEqual(tf.tradfi(table), ["NAS100_USDT", "TESLA_USDT"])
        self.assertTrue(set(tf.MINUTE_SYMBOLS) >= {"NAS100_USDT", "SPX500_USDT", "US30_USDT"})


class MinutesTest(unittest.TestCase):
    def test_writes_once_with_receipt_and_dated_1m_snapshot(self):
        calls = []
        end = pd.Timestamp("2026-10-22T12:00:00Z").value // 10**6
        with tempfile.TemporaryDirectory() as d, \
                patch.object(tf.hist, "START", end - 3 * 3_600_000), \
                patch.object(tf, "MIN1_DAYS", 1), \
                patch.object(tf.mexc, "get", side_effect=fake_get(calls)):
            sym, msg = tf.minutes("NAS100_USDT", end, d)
            self.assertFalse(msg.startswith("error"), msg)
            out = Path(d)
            k5 = pd.read_parquet(out / "klines_5m" / "NAS100_USDT.parquet")
            self.assertEqual(len(k5), 36)
            k1 = pd.read_parquet(out / "klines_1m" / "NAS100_USDT" / "2026-10-22.parquet")
            self.assertEqual(len(k1), 1440)
            rec = json.loads((out / "receipts_minutes" / "NAS100_USDT_2026-10-22.json").read_text())
            self.assertFalse(rec["coverage_certified"])
            self.assertEqual(rec["files"]["index_price_1m"]["rows"], 1440)
            n = len(calls)
            self.assertEqual(tf.minutes("NAS100_USDT", end, d)[1], "skip receipt exists")
            self.assertEqual(len(calls), n)
            # a later day adds a new 1-minute snapshot and leaves the 5-minute file alone
            later = end + 86_400_000
            sym, msg = tf.minutes("NAS100_USDT", later, d)
            self.assertFalse(msg.startswith("error"), msg)
            self.assertTrue((out / "klines_1m" / "NAS100_USDT" / "2026-10-23.parquet").exists())
            rec2 = json.loads((out / "receipts_minutes" / "NAS100_USDT_2026-10-23.json").read_text())
            self.assertIn("skipped", rec2["files"]["klines_5m"])
            self.assertEqual(len(pd.read_parquet(out / "klines_5m" / "NAS100_USDT.parquet")), 36)


if __name__ == "__main__":
    unittest.main()
