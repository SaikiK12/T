"""R468 asiaclose_v1: rule instants, holidays, event rows and the runner on synthetic worlds (no market data)."""
import csv
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
import asiaclose_rule as rule  # noqa: E402
import run_asiaclose as runner  # noqa: E402

H = 3_600_000


def utc(y, m, d, h):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


class Instants(unittest.TestCase):
    def test_krx_weekday_night(self):
        o = rule.opening("KRX", date(2026, 6, 9))           # Tuesday
        self.assertEqual(o["kind"], "night")
        self.assertEqual(o["P"], "2026-06-08")
        self.assertEqual(o["R"], utc(2026, 6, 8, 6))
        self.assertEqual(o["E"], utc(2026, 6, 8, 23))        # 08:00 KST on D
        self.assertEqual(o["X1"], utc(2026, 6, 9, 1))
        self.assertEqual(o["X2"], utc(2026, 6, 9, 6))

    def test_monday_is_a_gap(self):
        o = rule.opening("TSE", date(2026, 6, 8))
        self.assertEqual((o["kind"], o["P"]), ("gap", "2026-06-05"))
        self.assertEqual(o["E"], utc(2026, 6, 7, 23))

    def test_krx_closures_missing_from_the_venue_table(self):
        self.assertIsNone(rule.opening("KRX", date(2026, 6, 3)))
        self.assertIsNone(rule.opening("KRX", date(2026, 7, 17)))
        o = rule.opening("KRX", date(2026, 6, 4))
        self.assertEqual((o["kind"], o["P"]), ("gap", "2026-06-02"))

    def test_hkex_entry_on_d(self):
        o = rule.opening("HKEX", date(2026, 7, 2))
        self.assertIsNone(rule.opening("HKEX", date(2026, 7, 1)))
        self.assertEqual((o["kind"], o["P"]), ("gap", "2026-06-30"))
        self.assertEqual((o["R"], o["E"], o["X1"]), (utc(2026, 6, 30, 7), utc(2026, 7, 2, 1), utc(2026, 7, 2, 3)))

    def test_half_day_never_serves_as_p(self):
        self.assertIsNone(rule.opening("HKEX", date(2026, 12, 28)))   # P would be the half day of 12-24

    def test_event_row_fade_and_funding(self):
        t = np.array([utc(2026, 6, 8, 5), utc(2026, 6, 8, 22), utc(2026, 6, 9, 0), utc(2026, 6, 9, 5)])
        c = np.array([100.0, 102.0, 101.0, 101.5])
        ft = np.array([utc(2026, 6, 9, 0), utc(2026, 6, 9, 1)])
        fr = np.array([0.0001, 0.0001])
        x = rule.event_row(t, c, ft, fr, rule.opening("KRX", date(2026, 6, 9)))
        self.assertAlmostEqual(x["W"], 1e4 * math.log(1.02))
        self.assertEqual(x["s"], -1)
        self.assertAlmostEqual(x["c_x1"], -1e4 * math.log(101 / 102))
        self.assertAlmostEqual(x["f_x1"], 2.0)                # the short receives two hours of 1 bp
        self.assertAlmostEqual(x["g_x1"], x["c_x1"] + 2.0)

    def test_unpriced_when_r_is_stale(self):
        t = np.array([utc(2026, 6, 8, 1), utc(2026, 6, 8, 22)])
        x = rule.event_row(t, np.array([100.0, 101.0]), np.array([]), np.array([]),
                           rule.opening("KRX", date(2026, 6, 9)))
        self.assertEqual(x["s"], 0)


def world(lane, data, rho, seed=1):
    """Four KRX markets (two per venue) whose closure move W is followed by rho * W at the open (rho < 0 overshoots)."""
    rng = np.random.default_rng(seed)
    rows = [{"venue": "xyz", "coin": "AAA", "exchange": "KRX", "local": "000001"},
            {"venue": "lighter", "coin": "BBB", "exchange": "KRX", "local": "000002"},
            {"venue": "xyz", "coin": "CCC", "exchange": "KRX", "local": "000003"},
            {"venue": "lighter", "coin": "DDD", "exchange": "KRX", "local": "000004"}]
    lane.mkdir(parents=True)
    with open(lane / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    t0, t1 = utc(2026, 4, 1, 0), utc(2026, 11, 11, 0)
    hours = np.arange(t0, t1, H)
    hour = (hours // H) % 24
    for u in rows:
        r = rng.normal(0, 0.002, len(hours))
        night = (hour >= 7) & (hour <= 22)
        r[night] += rng.normal(0, 0.004, night.sum())                  # the perp-only closure move
        lp = np.cumsum(r)
        for ix in np.where(hour == 0)[0]:                                # the open: rho times the night's move
            j = ix - 17
            if j >= 0:
                lp[ix:] += rho * (lp[ix - 1] - lp[j])
        k = pd.DataFrame({"t": hours, "close": 100 * np.exp(lp), "volume": 1.0})
        f = pd.DataFrame({"t": hours[1:], "rate": 0.0})
        for sub, df in (("klines_1h", k), ("funding", f)):
            p = data / u["venue"] / sub / f"{u['coin']}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)


class Runner(unittest.TestCase):
    def test_cell_count(self):
        self.assertEqual(len(runner.cells_spec()), 52)

    def test_overshoot_world_reads_fade(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            world(lane, data, rho=-0.5)
            state = runner.run(lane, data, check=False)
            s = pd.read_json(lane / "results" / "summary.json", typ="series")
            self.assertIn(state, ("PASS", "PARTIAL"))
            self.assertIn("side fade", s["text"])

    def test_underreaction_world_reads_follow(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            world(lane, data, rho=0.5, seed=2)
            state = runner.run(lane, data, check=False)
            s = pd.read_json(lane / "results" / "summary.json", typ="series")
            self.assertIn(state, ("PASS", "PARTIAL"))
            self.assertIn("side follow", s["text"])

    def test_null_world(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            world(lane, data, rho=0.0, seed=3)
            self.assertEqual(runner.run(lane, data, check=False), "NULL")

    def test_corporate_days_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            world(lane, data, rho=0.0, seed=4)
            u = pd.read_csv(lane / "universe.csv", dtype=str)
            u.loc[0, ["exchange", "local"]] = ["TSE", "285A"]
            u.to_csv(lane / "universe.csv", index=False)
            per, skipped = runner.build(lane, data)
            self.assertEqual(skipped["corporate"], 2)
            self.assertFalse(((per.coin == "AAA") & per.D.isin(["2026-09-28", "2026-09-29"])).any())

    def test_inconclusive_when_small(self):
        c = {"n_a": 10, "days_a": 5, "mean_a": 50.0, "p_a": 0.001, "unit_a": 4.0, "n_b": 60, "days_b": 20,
             "mean_b": 40.0, "unit_b": 4.0}
        self.assertEqual(runner.verdict(c)[0], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
