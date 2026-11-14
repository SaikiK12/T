"""Tests for R464 xyzns_wknd_v1 (scripts/xyzns_rule.py, scripts/run_xyzns.py, scripts/fetch_xyz_ns.py) on synthetic
worlds only."""
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
import xyzns_rule as rule  # noqa: E402
import run_xyzns as runner  # noqa: E402
import fetch_xyz_ns as fetch  # noqa: E402

H = rule.HOUR_MS
COLS = ["coin", "spec", "cls", "close_et", "reopen_et", "growth", "fee_scale"]


def utc(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


class Calendar(unittest.TestCase):
    def test_commodity_weekend_summer(self):
        w = rule.instants(date(2026, 5, 8), "17:00", "18:00")
        self.assertEqual(w["R"], utc("2026-05-08 21:00"))      # Fri 17:00 EDT
        self.assertEqual(w["O"], utc("2026-05-10 22:00"))      # Sun 18:00 EDT
        self.assertEqual(w["E"], utc("2026-05-10 21:00"))      # Sun 17:00 EDT
        self.assertEqual(w["X1"], utc("2026-05-11 00:00"))     # Sun 20:00 EDT
        self.assertEqual(w["X2"], utc("2026-05-11 14:00"))     # Mon 10:00 EDT

    def test_fx_and_brent_winter(self):
        fx = rule.instants(date(2026, 11, 6), "17:00", "17:00")
        self.assertEqual(fx["R"], utc("2026-11-06 22:00"))     # Fri 17:00 EST
        self.assertEqual(fx["E"], utc("2026-11-08 21:00"))     # Sun 16:00 EST
        self.assertEqual(fx["X1"], utc("2026-11-09 00:00"))    # Sun 19:00 EST
        brent = rule.instants(date(2026, 11, 6), "18:00", "18:00")
        self.assertEqual(brent["R"], utc("2026-11-06 23:00"))  # Fri 18:00 EST

    def test_dst_end_weekend(self):
        # DST ends Sunday 2026-11-01 02:00; Friday 10-30 17:00 is EDT, Sunday 18:00 is EST
        w = rule.instants(date(2026, 10, 30), "17:00", "18:00")
        self.assertEqual(w["R"], utc("2026-10-30 21:00"))
        self.assertEqual(w["O"], utc("2026-11-01 23:00"))
        self.assertEqual(w["E"], utc("2026-11-01 22:00"))

    def test_holiday_weekends_skipped(self):
        for d in (date(2026, 5, 22), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 4)):
            self.assertIsNone(rule.instants(d, "17:00", "18:00"))

    def test_sample_sizes(self):
        a = [d for d in rule.friday_dates(*runner.A_SPAN) if rule.instants(d, "17:00", "18:00")]
        b = [d for d in rule.friday_dates(*runner.B_SPAN) if rule.instants(d, "17:00", "18:00")]
        self.assertEqual((len(a), len(b)), (18, 6))


class Universe(unittest.TestCase):
    def test_session_times(self):
        self.assertEqual(fetch.session_times("From Sunday 6:00 PM ET to Friday 5:00 PM ET"), ("17:00", "18:00"))
        self.assertEqual(fetch.session_times("From Sunday 6PM ET to Friday 6PM ET"), ("18:00", "18:00"))
        self.assertEqual(fetch.session_times("From Sunday 5PM ET to Friday 5PM ET"), ("17:00", "17:00"))
        with self.assertRaises(ValueError):
            fetch.session_times("24/5, from Sunday 8:05 PM ET to Friday 8:00 PM ET")

    def test_frozen_universe_shape(self):
        rows = runner.load_universe()
        self.assertEqual(len(rows), 14)
        self.assertEqual({r["cls"] for r in rows}, set(rule.CLASSES))
        self.assertEqual({r["coin"] for r in rows if r["growth"] != "enabled"}, {"GOLD"})


class Scoring(unittest.TestCase):
    def test_unit_cost(self):
        self.assertAlmostEqual(rule.unit_cost(True), 5.8)
        self.assertAlmostEqual(rule.unit_cost(False), 22.0)

    def test_verdict_states(self):
        base = {"n_a": 150, "wk_a": 18, "unit_a": 7.0, "n_b": 40, "wk_b": 6, "unit_b": 7.0}
        good = dict(base, mean_a=20.0, p_holm=0.01, mean_b=9.0)
        self.assertEqual(rule.verdict([good, good])[0], "PASS")
        part = dict(base, mean_a=9.0, p_holm=0.01, mean_b=1.0)
        self.assertEqual(rule.verdict([part, part])[0], "PARTIAL")
        null = dict(base, mean_a=20.0, p_holm=0.2, mean_b=9.0)
        self.assertEqual(rule.verdict([null, null])[0], "NULL")
        few = dict(good, n_a=59)
        self.assertEqual(rule.verdict([few, few])[0], "INCONCLUSIVE")
        thin_b = dict(good, n_b=19)
        self.assertEqual(rule.verdict([thin_b, thin_b])[0], "NULL")
        self.assertEqual(rule.verdict([few, good])[0], "PASS")


def world(tmp, overshoot, seed):
    """Synthetic universe of 14 markets. Each weekend move gets `overshoot` x a noise term that reverts at reopen."""
    rng = np.random.default_rng(seed)
    lane, data = Path(tmp) / "lane", Path(tmp) / "data"
    (data / "klines_1h").mkdir(parents=True)
    (data / "funding").mkdir(parents=True)
    lane.mkdir()
    spec = [("I0", "index", "17:00", "18:00"), ("I1", "index", "17:00", "18:00"),
            ("M0", "metal", "17:00", "18:00"), ("M1", "metal", "17:00", "18:00"), ("M2", "metal", "17:00", "18:00"),
            ("E0", "energy", "17:00", "18:00"), ("E1", "energy", "18:00", "18:00"),
            ("E2", "energy", "17:00", "18:00"), ("F0", "fx", "17:00", "17:00"), ("F1", "fx", "17:00", "17:00"),
            ("F2", "fx", "17:00", "17:00"), ("M3", "metal", "17:00", "18:00"), ("I2", "index", "17:00", "18:00"),
            ("E3", "energy", "17:00", "18:00")]
    with open(lane / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        for c, cls, cl, ro in spec:
            w.writerow({"coin": c, "spec": c, "cls": cls, "close_et": cl, "reopen_et": ro,
                        "growth": "enabled", "fee_scale": "1.0"})
    t = np.arange(utc("2026-04-20 00:00"), utc("2026-11-10 00:00"), H, dtype=np.int64)
    fridays = rule.friday_dates(*runner.A_SPAN) + rule.friday_dates(*runner.B_SPAN)
    for c, cls, cl, ro in spec:
        logp = np.zeros(len(t))
        for d in fridays:
            wk = rule.instants(d, cl, ro)
            if wk is None:
                continue
            true, noise = rng.normal(0, 0.006), rng.normal(0, 0.006)
            i_e = np.searchsorted(t, wk["E"]) - 1
            i_x = np.searchsorted(t, wk["X1"]) - 1
            logp[i_e:] += true + overshoot * noise
            logp[i_x:] -= overshoot * noise
        pd.DataFrame({"t": t, "c": 100 * np.exp(logp)}).to_parquet(data / "klines_1h" / f"{c}.parquet", index=False)
        pd.DataFrame({"time": t + H, "rate": np.zeros(len(t))}).to_parquet(data / "funding" / f"{c}.parquet",
                                                                           index=False)
    (data / "manifest.json").write_text(json.dumps({"files": {}}))
    return lane, data


class EndToEnd(unittest.TestCase):
    def test_planted_overshoot_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 1.0, 1)
            state = runner.run(lane=lane, data=data, check=False)
            cells = pd.read_csv(lane / "results" / "cells.csv")
            self.assertEqual(len(cells), 40)
            d = cells[(cells.group == "all") & (cells.theta == 50) & (cells.exit == "x1")].iloc[0]
            self.assertGreater(d.mean_a, 20)
            self.assertLess(d.p_a, 0.01)
            self.assertEqual(state, "PASS")
            ev = pd.read_csv(lane / "results" / "events.csv")
            self.assertEqual(set(ev.cls), set(rule.CLASSES))

    def test_no_overshoot_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 0.0, 2)
            state = runner.run(lane=lane, data=data, check=False)
            self.assertIn(state, ("NULL", "INCONCLUSIVE"))
            cells = pd.read_csv(lane / "results" / "cells.csv")
            d = cells[(cells.group == "all") & (cells.theta == 25) & (cells.exit == "x1")].iloc[0]
            self.assertTrue(abs(d.mean_a) < 1e-6 or math.isnan(d.mean_a))

    def test_late_listing_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane, data = world(tmp, 1.0, 3)
            p = data / "klines_1h" / "F2.parquet"
            k = pd.read_parquet(p)
            k[k.t >= utc("2026-09-01 00:00")].to_parquet(p, index=False)
            per, skipped = runner.build(lane, data)
            self.assertGreater(skipped["not_listed"], 0)
            first = per[per.coin == "F2"].F.min()
            self.assertGreaterEqual(first, "2026-09-11")
            self.assertEqual(skipped["holiday"], 14 * 4)


if __name__ == "__main__":
    unittest.main()
