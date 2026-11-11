"""Tests for R465 ltwknd_v1 (scripts/run_ltwknd.py, scripts/fetch_lighter_wknd.py) on synthetic worlds only."""
import csv
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_ltwknd as runner  # noqa: E402
import xyzwknd_rule as rule  # noqa: E402

H = rule.HOUR_MS
COLS = ["coin", "market_id", "created_at", "status", "taker_fee", "maker_fee", "etf", "ipo_424b4"]


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


def world(tmp, overshoot, seed, n=14, thin=False):
    rng = np.random.default_rng(seed)
    lane, data = Path(tmp) / "lane", Path(tmp) / "data"
    (data / "klines_1h").mkdir(parents=True)
    (data / "funding").mkdir(parents=True)
    lane.mkdir()
    coins = [f"S{i}" for i in range(n)]
    with open(lane / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        for i, c in enumerate(coins):
            w.writerow({"coin": c, "market_id": i, "created_at": 0, "status": "active", "taker_fee": "0.0000",
                        "maker_fee": "0.0000", "etf": int(i >= n - 2), "ipo_424b4": ""})
    t = np.arange(utc("2026-02-13 00:00"), utc("2026-11-10 00:00"), H, dtype=np.int64)
    weekends = [w for span in runner.SPANS.values() for w in rule.fridays(*span)]
    for c in coins:
        logp = np.zeros(len(t))
        for wk in weekends:
            true, noise = rng.normal(0, 0.01), rng.normal(0, 0.01)
            i_e = np.searchsorted(t, wk["E"]) - 1
            i_x = np.searchsorted(t, wk["X1"]) - 1
            logp[i_e:] += true + overshoot * noise
            logp[i_x:] -= overshoot * noise
        vol = np.ones(len(t))
        if thin:
            vol[::2] = 0.0
        pd.DataFrame({"t": t, "close": 100 * np.exp(logp), "volume": vol}).to_parquet(
            data / "klines_1h" / f"{c}.parquet", index=False)
        pd.DataFrame({"t": t + H, "rate": np.zeros(len(t))}).to_parquet(data / "funding" / f"{c}.parquet",
                                                                        index=False)
    (data / "manifest.json").write_text(json.dumps({"files": {}}))
    return lane, data


class Constants(unittest.TestCase):
    def test_unit_and_spans(self):
        self.assertAlmostEqual(runner.UNIT_BP, 4.0)
        self.assertEqual(runner.DECISION, ("all", 50, "x1"))
        self.assertEqual(len(rule.fridays(*runner.SPANS["A"])), 18)
        self.assertEqual(len(rule.fridays(*runner.SPANS["B"])), 6)
        self.assertEqual(len(rule.fridays(*runner.SPANS["C"])), 8)      # Good Friday 2026-04-03 dropped

    def test_frozen_universe(self):
        u = runner.load_universe()
        self.assertEqual(len(u), 50)
        self.assertEqual({r["taker_fee"] for r in u}, {"0.0000"})


class Verdict(unittest.TestCase):
    base = {"n_a": 300, "wk_a": 18, "unit_a": 4.0, "p_a": 0.01, "mean_a": 20.0, "n_b": 80, "wk_b": 6,
            "unit_b": 4.0, "mean_b": 9.0, "n_c": 100, "wk_c": 8, "mean_c": 5.0}

    def test_states(self):
        self.assertEqual(runner.verdict(dict(self.base))[0], "PASS")
        self.assertEqual(runner.verdict(dict(self.base, mean_c=-5.0))[0], "PARTIAL")
        self.assertEqual(runner.verdict(dict(self.base, mean_c=-5.0, n_c=10))[0], "PASS")   # C too small
        self.assertEqual(runner.verdict(dict(self.base, mean_a=6.0))[0], "PARTIAL")
        self.assertEqual(runner.verdict(dict(self.base, p_a=0.2))[0], "NULL")
        self.assertEqual(runner.verdict(dict(self.base, mean_a=-20.0))[0], "NULL")            # follow is not a pass
        self.assertEqual(runner.verdict(dict(self.base, mean_b=-1.0))[0], "NULL")
        self.assertEqual(runner.verdict(dict(self.base, wk_a=9))[0], "INCONCLUSIVE")


class EndToEnd(unittest.TestCase):
    def test_planted_overshoot_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 1.0, 1)
            self.assertEqual(runner.run(lane=lane, data=data, check=False), "PASS")
            cells = pd.read_csv(lane / "results" / "cells.csv")
            self.assertEqual(len(cells), 32)
            d = cells[cells.decision].iloc[0]
            self.assertGreater(d.mean_a, 30)
            self.assertGreater(d.mean_c, 0)

    def test_no_overshoot_is_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 0.0, 2)
            self.assertIn(runner.run(lane=lane, data=data, check=False), ("NULL", "INCONCLUSIVE"))

    def test_zero_volume_candles_are_not_prices(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 1.0, 3, n=3, thin=True)
            per, skipped = runner.build(lane, data)
            k = pd.read_parquet(data / "klines_1h" / "S0.parquet")
            traded = k[k.volume > 0]
            tt, cc = traded.t.to_numpy("int64"), traded.close.to_numpy(float)
            weeks = {w["F"]: w for span in runner.SPANS.values() for w in rule.fridays(*span)}
            rows = per[per.coin == "S0"]
            self.assertGreater(len(rows), 0)
            for row in rows.itertuples():
                w = weeks[row.F]
                self.assertAlmostEqual(row.W, 1e4 * math.log(rule.price_at(tt, cc, w["E"]) /
                                                             rule.price_at(tt, cc, w["R"])))
            self.assertGreater(skipped["unpriced"], 0)          # W = 0 on the untraded hours

    def test_late_listing_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 1.0, 4, n=3)
            p = data / "klines_1h" / "S1.parquet"
            k = pd.read_parquet(p)
            k[k.t >= utc("2026-06-01 00:00")].to_parquet(p, index=False)
            per, skipped = runner.build(lane, data)
            self.assertGreater(skipped["not_listed"], 0)
            self.assertGreaterEqual(per[per.coin == "S1"].F.min(), "2026-06-12")


if __name__ == "__main__":
    unittest.main()
