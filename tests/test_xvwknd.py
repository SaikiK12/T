"""Tests for R466 xvwknd_v1 (scripts/xvwknd_rule.py, scripts/run_xvwknd.py) on synthetic worlds only."""
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
import run_xvwknd as runner  # noqa: E402
import xvwknd_rule as rule  # noqa: E402
import xyzwknd_rule as base  # noqa: E402

H = base.HOUR_MS


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


def world(tmp, close_gap, seed, n=12):
    """Both venues follow one true price; on each weekend each venue adds its own drift from Friday 20:00 New York.
    close_gap=True removes the drifts at Sunday 20:00 (both venues back on the external price); False keeps them."""
    rng = np.random.default_rng(seed)
    lane, xyz, lt = Path(tmp) / "lane", Path(tmp) / "xyz", Path(tmp) / "lt"
    for d in (xyz, lt):
        (d / "klines_1h").mkdir(parents=True)
        (d / "funding").mkdir(parents=True)
        (d / "manifest.json").write_text(json.dumps({"files": {}}))
    lane.mkdir()
    coins = [f"S{i}" for i in range(n)]
    with open(lane / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, runner.COLS, lineterminator="\n")
        w.writeheader()
        for i, c in enumerate(coins):
            w.writerow({"coin": c, "lt_market_id": i, "etf": 0, "growth": "enabled", "ipo_424b4": ""})
    t = np.arange(utc("2026-04-17 00:00"), utc("2026-11-10 00:00"), H, dtype=np.int64)
    weekends = [w for span in runner.SPANS.values() for w in base.fridays(*span)]
    for c in coins:
        true = np.cumsum(rng.normal(0, 0.002, len(t)))
        dx, dl = np.zeros(len(t)), np.zeros(len(t))
        for wk in weekends:
            i_r = np.searchsorted(t, wk["R"])
            i_back = np.searchsorted(t, wk["E"] + H) if close_gap else np.searchsorted(t, wk["X2"] + 48 * H)
            dx[i_r:i_back] += rng.normal(0, 0.006)
            dl[i_r:i_back] += rng.normal(0, 0.006)
        ones = np.ones(len(t))
        pd.DataFrame({"t": t, "T": t + H - 1, "o": 0.0, "h": 0.0, "l": 0.0, "c": 100 * np.exp(true + dx),
                      "v": ones, "n": ones}).to_parquet(xyz / "klines_1h" / f"{c}.parquet", index=False)
        pd.DataFrame({"time": t + H, "rate": np.zeros(len(t)), "premium": 0.0}).to_parquet(
            xyz / "funding" / f"{c}.parquet", index=False)
        pd.DataFrame({"t": t, "close": 100 * np.exp(true + dl), "volume": ones}).to_parquet(
            lt / "klines_1h" / f"{c}.parquet", index=False)
        pd.DataFrame({"t": t + H, "rate": np.zeros(len(t))}).to_parquet(lt / "funding" / f"{c}.parquet", index=False)
    return lane, xyz, lt


class Rule(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(runner.DECISION, (25, "x2"))
        self.assertAlmostEqual(rule.unit_cost(True), 9.8)
        self.assertAlmostEqual(rule.unit_cost(False), 26.0)
        self.assertEqual(len(base.fridays(*runner.SPANS["A"])), 18)
        self.assertEqual(len(base.fridays(*runner.SPANS["B"])), 6)

    def test_frozen_universe(self):
        u = runner.load_universe()
        self.assertEqual(len(u), 50)
        self.assertEqual(sum(r["growth"] == "enabled" for r in u), 47)       # 3 standard-fee markets

    def test_fresh_price(self):
        t = np.array([0, H, 2 * H], dtype=np.int64)
        c = np.array([1.0, 2.0, 3.0])
        self.assertEqual(rule.fresh_price(t, c, np.array([1.0, 1.0, 1.0]), 2 * H), 2.0)
        self.assertTrue(math.isnan(rule.fresh_price(t, c, np.array([1.0, 0.0, 1.0]), 2 * H)))   # untraded hour
        self.assertTrue(math.isnan(rule.fresh_price(t[:1], c[:1], np.array([1.0]), 2 * H)))       # 2 h old

    def test_event_signs(self):
        w = base.weekend(date(2026, 6, 5))
        t = np.arange(w["E"] - 3 * H, w["X2"] + H, H, dtype=np.int64)
        px = np.where(t < w["E"], 100 * math.exp(0.005), 100.0)                     # xyz 50 bp dearer at E
        ones = np.ones(len(t))
        ft = t + H
        xyz_f = (ft, np.full(len(t), 1e-4))                                          # longs pay 1 bp an hour on xyz
        lt_f = (ft, np.zeros(len(t)))
        r = rule.event_row((t, px, ones), (t, np.full(len(t), 100.0), ones), xyz_f, lt_f, w)
        self.assertEqual(r["d"], 1)
        self.assertAlmostEqual(r["G"], 50.0, places=6)
        self.assertAlmostEqual(r["c_x2"], 50.0, places=6)
        hours = (w["X2"] - w["E"]) // H
        self.assertAlmostEqual(r["f_x2"], hours * 1.0, places=6)                    # the short xyz leg receives
        r2 = rule.event_row((t, np.full(len(t), 100.0), ones), (t, px, ones), lt_f, xyz_f, w)
        self.assertEqual(r2["d"], -1)
        self.assertAlmostEqual(r2["c_x2"], 50.0, places=6)
        self.assertAlmostEqual(r2["f_x2"], hours * 1.0, places=6)                   # the short Lighter leg receives


class Verdict(unittest.TestCase):
    base = {"n_a": 300, "wk_a": 18, "unit_a": 9.8, "p_a": 0.01, "mean_a": 30.0, "n_b": 80, "wk_b": 6,
            "unit_b": 9.8, "mean_b": 12.0}

    def test_states(self):
        self.assertEqual(runner.verdict(dict(self.base))[0], "PASS")
        self.assertEqual(runner.verdict(dict(self.base, mean_a=15.0))[0], "PARTIAL")
        self.assertEqual(runner.verdict(dict(self.base, mean_b=5.0))[0], "PARTIAL")
        self.assertEqual(runner.verdict(dict(self.base, mean_b=-1.0))[0], "NULL")
        self.assertEqual(runner.verdict(dict(self.base, p_a=0.2))[0], "NULL")
        self.assertEqual(runner.verdict(dict(self.base, mean_a=-30.0))[0], "NULL")
        self.assertEqual(runner.verdict(dict(self.base, wk_a=9))[0], "INCONCLUSIVE")


class EndToEnd(unittest.TestCase):
    def test_closing_gap_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, xyz, lt = world(tmp, True, 1)
            self.assertEqual(runner.run(lane=lane, xyz=xyz, lt=lt, check=False), "PASS")
            cells = pd.read_csv(lane / "results" / "cells.csv")
            self.assertEqual(len(cells), 10)
            self.assertGreater(cells[cells.decision].iloc[0].mean_a, 30)

    def test_persistent_gap_is_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, xyz, lt = world(tmp, False, 2)
            self.assertIn(runner.run(lane=lane, xyz=xyz, lt=lt, check=False), ("NULL", "INCONCLUSIVE"))

    def test_untraded_hour_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, xyz, lt = world(tmp, True, 3, n=2)
            p = lt / "klines_1h" / "S0.parquet"
            k = pd.read_parquet(p)
            k.loc[:, "volume"] = 0.0
            k.to_parquet(p, index=False)
            per, skipped = runner.build(lane, xyz, lt)
            self.assertFalse((per.coin == "S0").any())
            self.assertEqual(skipped["unpriced"], 24)


if __name__ == "__main__":
    unittest.main()
