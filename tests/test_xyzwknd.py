"""Tests for R462 xyzwknd_v1 (scripts/xyzwknd_rule.py, scripts/run_xyzwknd.py) on synthetic worlds only."""
import csv
import json
import math
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import xyzwknd_rule as rule  # noqa: E402
import run_xyzwknd as runner  # noqa: E402

H = rule.HOUR_MS


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


class Calendar(unittest.TestCase):
    def test_summer_weekend_instants(self):
        w = rule.weekend(date(2026, 5, 8))
        self.assertEqual(w["R"], utc("2026-05-09 00:00"))      # Fri 20:00 EDT
        self.assertEqual(w["E"], utc("2026-05-10 23:00"))      # Sun 19:00 EDT
        self.assertEqual(w["X1"], utc("2026-05-11 02:00"))     # Sun 22:00 EDT
        self.assertEqual(w["X2"], utc("2026-05-11 14:00"))     # Mon 10:00 EDT

    def test_winter_weekend_instants(self):
        w = rule.weekend(date(2026, 11, 6))
        self.assertEqual(w["R"], utc("2026-11-07 01:00"))      # Fri 20:00 EST
        self.assertEqual(w["X2"], utc("2026-11-09 15:00"))     # Mon 10:00 EST

    def test_holiday_weekends_skipped(self):
        self.assertIsNone(rule.weekend(date(2026, 5, 22)))     # Memorial Day Monday
        self.assertIsNone(rule.weekend(date(2026, 6, 19)))     # Juneteenth Friday
        self.assertIsNone(rule.weekend(date(2026, 7, 3)))      # Independence Day observed
        self.assertIsNone(rule.weekend(date(2026, 9, 4)))      # Labor Day Monday
        self.assertIsNone(rule.weekend(date(2026, 11, 27)))    # early close
        self.assertIsNone(rule.weekend(date(2026, 5, 7)))      # a Thursday

    def test_sample_a_has_18_weekends(self):
        self.assertEqual(len(rule.fridays(*runner.A_SPAN)), 18)
        self.assertEqual(len(rule.fridays(*runner.B_SPAN)), 6)


class Prices(unittest.TestCase):
    def test_price_at_uses_last_closed_candle_within_3h(self):
        t = np.array([0, H, 2 * H], dtype=np.int64)
        c = np.array([10.0, 11.0, 12.0])
        self.assertEqual(rule.price_at(t, c, 3 * H), 12.0)     # candle [2h, 3h) closed at 3h
        self.assertEqual(rule.price_at(t, c, 2 * H + 1), 11.0)  # candle at 2h has not closed yet
        self.assertEqual(rule.price_at(t, c, 5 * H), 12.0)     # 3 h stale is still allowed
        self.assertTrue(math.isnan(rule.price_at(t, c, 6 * H)))

    def test_funding_window_is_open_closed(self):
        ft = np.array([H, 2 * H, 3 * H], dtype=np.int64)
        fr = np.array([1e-5, 2e-5, 4e-5])
        self.assertAlmostEqual(rule.funding_sum(ft, fr, H, 3 * H), 6e-5)

    def test_event_row_fade_short_after_rise(self):
        w = {"R": 10 * H, "E": 20 * H, "X1": 22 * H, "X2": 30 * H}
        t = np.arange(0, 40, dtype=np.int64) * H
        c = np.full(40, 100.0)
        c[19:] = 102.0           # price at E (close of the 19h candle) is 102
        c[21:] = 101.0           # price at X1 and X2 is 101
        ft = np.array([21 * H, 25 * H], dtype=np.int64)
        fr = np.array([1e-5, 1e-5])
        x = rule.event_row(t, c, ft, fr, w)
        self.assertEqual(x["s"], -1)
        self.assertAlmostEqual(x["W"], 1e4 * math.log(1.02))
        self.assertAlmostEqual(x["c_x1"], -1e4 * math.log(101 / 102))
        self.assertAlmostEqual(x["f_x1"], 0.1)                 # a short receives positive funding
        self.assertAlmostEqual(x["f_x2"], 0.2)
        self.assertAlmostEqual(x["g_x2"], x["c_x2"] + 0.2)

    def test_unit_cost(self):
        self.assertAlmostEqual(rule.unit_cost(True), 5.8)
        self.assertAlmostEqual(rule.unit_cost(False), 22.0)


class Scoring(unittest.TestCase):
    def test_relative_demeans_by_weekend(self):
        per = pd.DataFrame({"F": ["f"] * 5, "coin": list("abcde"), "W": [10.0, 20, 30, 40, 50],
                            "s": [-1] * 5, "c_x2": [-1.0, -2, -3, -4, -5], "unit": [5.8] * 5})
        r = rule.relative(per, "x2")
        self.assertEqual(len(r), 4)                            # the median market has W_rel = 0
        row = r[r.coin == "e"].iloc[0]
        self.assertAlmostEqual(row.W, 20.0)
        self.assertAlmostEqual(row.g, -(5 - 3))                # move 5 vs median 3, faded
        self.assertAlmostEqual(row.unit, 11.6)

    def test_verdict_states(self):
        base = {"n_a": 300, "wk_a": 18, "unit_a": 5.8, "n_b": 80, "wk_b": 6, "unit_b": 5.8}
        good = dict(base, mean_a=20.0, p_holm=0.01, mean_b=9.0)
        self.assertEqual(rule.verdict([good, good])[0], "PASS")
        part = dict(base, mean_a=8.0, p_holm=0.01, mean_b=1.0)
        self.assertEqual(rule.verdict([part, part])[0], "PARTIAL")
        null = dict(base, mean_a=20.0, p_holm=0.2, mean_b=9.0)
        self.assertEqual(rule.verdict([null, null])[0], "NULL")
        few = dict(good, wk_a=5)
        self.assertEqual(rule.verdict([few, few])[0], "INCONCLUSIVE")
        flip = dict(good, mean_b=-9.0)
        self.assertEqual(rule.verdict([flip, flip])[0], "NULL")


class EndToEnd(unittest.TestCase):
    def test_planted_overshoot_is_found(self):
        """Weekend moves overshoot by 40% and revert at the Sunday reopen; the fade must come out positive."""
        rng = np.random.default_rng(1)
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = Path(tmp) / "lane", Path(tmp) / "data"
            (data / "klines_1h").mkdir(parents=True)
            (data / "funding").mkdir(parents=True)
            lane.mkdir()
            coins = [f"S{i}" for i in range(12)]
            with open(lane / "universe.csv", "w", newline="") as f:
                w = csv.DictWriter(f, ["coin", "us_ticker", "etf", "growth", "fee_scale", "cik", "ipo_424b4"],
                                   lineterminator="\n")
                w.writeheader()
                for i, c in enumerate(coins):
                    w.writerow({"coin": c, "us_ticker": c, "etf": int(i >= 10), "growth": "enabled",
                                "fee_scale": "1.0", "cik": "", "ipo_424b4": ""})
            t0, t1 = utc("2026-04-20 00:00"), utc("2026-11-10 00:00")
            t = np.arange(t0, t1, H, dtype=np.int64)
            weekends = rule.fridays(*runner.A_SPAN) + rule.fridays(*runner.B_SPAN)
            man = {"files": {}}
            for c in coins:
                logp = np.zeros(len(t))
                for wk in weekends:
                    true = rng.normal(0, 0.01)
                    noise = rng.normal(0, 0.01)
                    i_r = np.searchsorted(t, wk["R"]) - 1
                    i_e = np.searchsorted(t, wk["E"]) - 1
                    i_x = np.searchsorted(t, wk["X1"]) - 1
                    logp[i_r + 1:] += 0                      # flat to R
                    logp[i_e:] += true + noise               # weekend move with overshoot noise
                    logp[i_x:] -= noise                      # reverts once external prices return
                close = 100 * np.exp(logp)
                k = pd.DataFrame({"t": t, "c": close})
                fu = pd.DataFrame({"time": t + H, "rate": np.zeros(len(t))})
                k.to_parquet(data / "klines_1h" / f"{c}.parquet", index=False)
                fu.to_parquet(data / "funding" / f"{c}.parquet", index=False)
            (data / "manifest.json").write_text(json.dumps(man))
            state = runner.run(lane=lane, data=data, check=False)
            cells = pd.read_csv(lane / "results" / "cells.csv")
            d = cells[(cells.group == "all") & (cells.theta == 50) & (cells.exit == "x1")].iloc[0]
            self.assertGreater(d.mean_a, 30)
            self.assertLess(d.p_a, 0.01)
            self.assertEqual(state, "PASS")
            self.assertEqual(len(cells), 32)


if __name__ == "__main__":
    unittest.main()
