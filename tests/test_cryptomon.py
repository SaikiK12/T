"""R471 cryptomon_v1: events, statistics and verdict on a synthetic market (no market data)."""
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_cryptomon as cm  # noqa: E402

H = 3_600_000
HOLIDAY_MONDAYS = {date(2022, 1, 17), date(2025, 9, 1)}


def sessions(lo=date(2020, 6, 1), hi=date(2026, 11, 11)):
    d, out = lo, []
    while d <= hi:
        if d.weekday() < 5 and d not in HOLIDAY_MONDAYS:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def world(follow=0.0, seed=0, split_day=None):
    """BTC hourly random walk; every stock's gap carries 1.5 x W and its session move carries follow x W + noise."""
    rng = np.random.default_rng(seed)
    t0 = cm.ny_ms("2020-06-01", 0)
    t1 = cm.ny_ms("2026-11-12", 0)
    t = np.arange(t0 - t0 % H, t1, H)
    btc = pd.DataFrame({"t": t, "open": 30000 * np.exp(np.cumsum(rng.normal(0, 0.006, len(t))))})
    bo = dict(zip(btc["t"], btc["open"]))
    days = sessions()
    stocks = {}
    for tk in list(cm.DECIDE) + list(cm.REPORT):
        rows, close = [], 100.0
        for i, d in enumerate(days):
            p = days[i - 1] if i else None
            w = 0.0
            if p and (date.fromisoformat(d) - date.fromisoformat(p)).days >= 3:
                w = bo[cm.ny_ms(d, 9)] / bo[cm.ny_ms(p, 16)] - 1
            o = close * (1 + 1.5 * w + rng.normal(0, 0.003))
            if split_day and tk == "MSTR" and d == split_day:
                o *= 0.1
            c = o * (1 + (follow * w if tk != "QQQ" else 0.0) + rng.normal(0, 0.004))
            rows.append({"date": d, "open": o, "high": max(o, c), "low": min(o, c), "close": c, "adjclose": c,
                         "volume": 1e6})
            close = c
        stocks[tk] = pd.DataFrame(rows)
    return stocks, btc


class Events(unittest.TestCase):
    def test_ny_ms_handles_dst(self):
        self.assertEqual(cm.ny_ms("2026-01-05", 9), 1767621600000)   # 14:00 UTC in winter
        self.assertEqual(cm.ny_ms("2026-07-06", 9), 1783342800000)   # 13:00 UTC in summer

    def test_only_sessions_after_closures(self):
        ev = cm.events(*world())
        gaps = {(date.fromisoformat(s) - date.fromisoformat(p)).days for p, s in zip(ev["P"], ev["S"])}
        self.assertTrue(gaps <= {3, 4})
        self.assertIn("2022-01-18", set(ev["S"]))          # Tuesday after a Monday holiday
        self.assertGreaterEqual(ev[ev["ticker"] == "COIN"]["P"].min(), cm.DECIDE["COIN"])

    def test_split_guard_drops_the_break(self):
        ev = cm.events(*world(split_day="2024-08-12"))
        self.assertFalse(((ev["ticker"] == "MSTR") & (ev["S"] == "2024-08-12")).any())
        self.assertTrue(((ev["ticker"] == "COIN") & (ev["S"] == "2024-08-12")).any())


class Verdict(unittest.TestCase):
    def _run(self, follow):
        stocks, btc = world(follow=follow)
        ev = cm.events(stocks, btc)
        sess = cm.per_session(ev, list(cm.DECIDE))
        d = 1 if cm.sample_stats(sess, ev, cm.SPANS["A"], 0)["slope_D"]["slope"] > 0 else -1
        st = {k: cm.sample_stats(sess, ev, v, d) for k, v in cm.SPANS.items()}
        return cm.verdict(st["A"], st["B"]), st

    def test_planted_follow_passes(self):
        (state, _), st = self._run(0.3)
        self.assertEqual(state, "PASS")
        self.assertAlmostEqual(st["A"]["slope_D"]["slope"], 0.3, delta=0.05)
        self.assertAlmostEqual(st["A"]["slope_G"]["slope"], 1.5, delta=0.1)
        tr = st["A"]["trade"]
        self.assertAlmostEqual(tr["gross"]["mean_bp"] - tr["1x"]["mean_bp"], cm.UNIT_BP, places=6)

    def test_planted_fade_passes_on_the_fade_side(self):
        (state, text), st = self._run(-0.3)
        self.assertEqual(state, "PASS")
        self.assertIn("fade", text)
        self.assertGreater(st["B"]["trade"]["gross"]["mean_bp"], 0)

    def test_no_effect_is_null(self):
        (state, _), _ = self._run(0.0)
        self.assertEqual(state, "NULL")


class Run(unittest.TestCase):
    def test_run_writes_results(self):
        stocks, btc = world(follow=0.3)
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "yahoo").mkdir(parents=True)
            (data / "binance" / "klines_1h").mkdir(parents=True)
            for tk, df in stocks.items():
                df.to_parquet(data / "yahoo" / f"{tk}.parquet", index=False)
            btc.to_parquet(data / "binance" / "klines_1h" / "BTCUSDT.parquet", index=False)
            state = cm.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["state"], state)
            self.assertIn("QQQ", s["reported"])


if __name__ == "__main__":
    unittest.main()
