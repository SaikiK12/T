import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_reserved_batch as rb

H = 3_600_000


class TomlTest(unittest.TestCase):
    def test_dump_round_trips_a_lane_spec(self):
        for lane in ("announce_v1", "fundext_v1", "squeeze_v1"):
            s = rb.lane_spec(lane)
            self.assertEqual(tomllib.loads(rb.dump_toml(s)), s)

    def test_event_spec_changes_only_the_window_keys(self):
        base = rb.lane_spec("fundext_v1")
        dry = rb.event_spec("fundext_v1", {"neg2"}, None, "/tmp/x")
        run = rb.event_spec("fundext_v1", {"neg2"}, rb.run_plan(), "/tmp/x", legs_dir="/tmp/legs")
        keys = {"kinds", "out", "start", "end", "filter", "events", "reserved_prereg"}
        for s in (dry, run):
            self.assertEqual({k: v for k, v in s.items() if k not in keys}, {k: v for k, v in base.items() if k not in keys})
        self.assertEqual((dry["start"], dry["end"], dry["filter"]), ("2021-01-01", "2026-09-30", {"window": "archive"}))
        self.assertNotIn("reserved_prereg", dry)
        self.assertEqual(run["filter"], {"window": "reserved_2020"})
        ann = rb.event_spec("announce_v1", {"prelist"}, rb.run_plan(), "/tmp/x", legs_dir="/tmp/legs")
        self.assertEqual((ann["filter"], ann["events"]), ({"window": "reserved_2020"}, rb.lane_spec("announce_v1")["events"]))
        reh = rb.event_spec("fundext_v1", {"neg2"}, rb.rehearsal_plan("/tmp/w"), "/tmp/x", legs_dir="/tmp/legs")
        self.assertEqual((reh["start"], reh["filter"]), ("2021-01-01", {"window": "rehearsal"}))
        self.assertEqual(run["events"], "/tmp/legs/fundext_legs.csv")
        self.assertLess(run["start"], "2021-01-01")
        self.assertTrue(run["reserved_prereg"].endswith("reserved_batch1/PREREG.md"))


class EventObsTest(unittest.TestCase):
    def legs(self):
        return pd.DataFrame({
            "kind": ["k", "k", "k", "other"], "ticker": ["A", "B", "C", "A"], "r0": [10, 10, 20, 10],
            "t0": [5, 4, 30, 1], "sg_24": [0.10, 0.02, np.nan, 9.0],
            "short_24_stop1000": [0.05, 0.02, -0.10, 9.0], "long_24_stop1000": [0.08, 0.01, -0.02, 9.0]})

    def test_one_observation_per_cluster_with_the_sign_and_cost(self):
        o = rb.event_obs(self.legs(), "k", "short", 24, 0, 0.004)
        self.assertEqual(o.r0.tolist(), [10])                      # the NaN leg drops; cluster 20 has no finite net
        self.assertAlmostEqual(o.net.iloc[0], (0.10 + 0.02) / 2 - 0.004)
        self.assertEqual(o.t0.iloc[0], 4)
        o = rb.event_obs(self.legs(), "k", "long", 24, 0, 0.004)
        self.assertAlmostEqual(o.net.iloc[0], -(0.10 + 0.02) / 2 - 0.004)

    def test_a_cover_reads_its_own_column_in_the_shorts_sign(self):
        o = rb.event_obs(self.legs(), "k", "long", 24, 1000, 0.0)
        self.assertEqual(o.r0.tolist(), [10, 20])
        self.assertAlmostEqual(o.net.iloc[1], 0.02)                # long = -(short-sign value)

    def test_leave_two_coins_out_drops_the_best_two(self):
        legs = pd.DataFrame({"kind": "k", "ticker": list("ABCDE"), "r0": range(5), "t0": range(5),
                             "sg_24": [0.5, 0.4, -0.1, 0.0, 0.1]})
        s = rb.event_stats(legs, "k", "short", 24, 0, [0.0, 0.01, 0.02])
        self.assertEqual(s["l2co_dropped"], ["A", "B"])
        self.assertAlmostEqual(s["l2co_mean_pct"], 0.0)
        self.assertAlmostEqual(s["mean_3x_pct"], s["mean_1x_pct"] - 2.0)


class ReservedGuardTest(unittest.TestCase):
    def test_mexc_panel_needs_a_frozen_prereg_with_the_token(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREG.md"
            p.write_text("# batch\nRESERVED-2020-READ\n")
            with self.assertRaises(Exception):                     # not frozen
                rb.mexc_panel(["X_USDT"], "2025-04-01", "2025-04-02", str(p))
            prereg.freeze(p)
            with self.assertRaises(PermissionError):               # frozen, but no MEXC token
                rb.mexc_panel(["X_USDT"], "2025-04-01", "2025-04-02", str(p))

    def test_mexc_panel_maps_mexc_columns(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "mexc_hist" / "klines_1h").mkdir(parents=True)
            (root / "mexc_hist" / "funding").mkdir(parents=True)
            t0 = 1_743_465_600_000                                   # 2025-04-01
            pd.DataFrame({"t": [t0, t0 + H], "open": 1.0, "high": 1.0, "low": 1.0, "close": [1.0, 2.0],
                          "vol": [5.0, 0.0], "amount": [10.0, 0.0]}).to_parquet(root / "mexc_hist/klines_1h/X_USDT.parquet")
            pd.DataFrame({"t": [t0 + H], "rate": [0.001], "cycle_h": 8}).to_parquet(root / "mexc_hist/funding/X_USDT.parquet")
            p = root / "PREREG.md"
            p.write_text("# batch\nRESERVED-MEXC-READ\n")
            prereg.freeze(p)
            with mock.patch.object(rb.data, "ROOT", root):
                pn = rb.mexc_panel(["X_USDT"], "2025-04-01", "2025-04-01", str(p))
            self.assertEqual(pn["close"][:2, 0].tolist(), [1.0, 2.0])
            self.assertEqual(pn["volume"][:2, 0].tolist(), [5.0, 0.0])
            self.assertAlmostEqual(float(pn["fund_event"][1, 0]), 0.001)
            self.assertTrue(np.isnan(pn["fund_event"][0, 0]))

    def test_unlock_2020_window_is_refused_without_the_frozen_batch_prereg(self):
        with mock.patch.object(rb, "PREREG", Path("/nonexistent/PREREG.md")):
            with self.assertRaises(Exception):
                rb.unlock_prices("binance_2020", ["BTCUSDT"], None, rb.run_plan())

    def test_the_run_plan_reads_2020_and_the_rehearsal_does_not(self):
        run, reh = rb.run_plan(), rb.rehearsal_plan("/tmp/w")
        for p in (run.events[0], run.legs[0], run.brute[0]):
            self.assertLess(p, "2021-01-01")
        for p in (reh.events[0], reh.legs[0], reh.brute[0]):
            self.assertGreaterEqual(p, "2021-01-01")
        self.assertEqual(run.prereg, rb.PREREG)

    def test_alpha_block_matches_the_candidates(self):
        a = rb.alpha_from_prereg("x\n" + rb.alpha_block())
        self.assertEqual(a, rb.ALPHA)


class UnlockStatsTest(unittest.TestCase):
    def test_week_clusters_costs_and_windows(self):
        day = pd.Timestamp("2025-01-06", tz="UTC").value // 10**6
        priced = pd.DataFrame({"day_ms": [day, day, day + 7 * 86_400_000, day + 14 * 86_400_000],
                               "perp": ["A", "B", "A", "C"], "gross": [0.05, 0.01, 0.03, np.nan],
                               "window": ["reserved_2020", "reserved_2020", "reserved_mexc", "post_archive"]})
        s = rb.unlock_stats(priced)
        self.assertEqual(s["n"], 3)                                 # the unpriced event is not counted
        self.assertEqual(s["clusters"], 2)
        self.assertAlmostEqual(s["mean_1x_pct"], (0.09 / 3 - 0.002) * 100)
        self.assertAlmostEqual(s["mean_3x_pct"], (0.09 / 3 - 0.006) * 100)
        self.assertEqual(s["l2co_dropped"], ["A", "B"])
        self.assertEqual(set(s["windows"]), {"reserved_2020", "reserved_mexc"})


class DecideTest(unittest.TestCase):
    def good(self, n, p, unit="pct"):
        return {"n": n, "p_one_sided": p, "t": 3.0, f"mean_2x_{unit}": 1.0, f"trimmed_mean_{unit}": 1.0,
                f"l2co_mean_{unit}": 1.0}

    def test_alpha_of_unreadable_candidates_moves_to_the_readable_ones(self):
        alpha = {"C14": 0.03, "C01": 0.01, "C09": 0.01}
        res = {"C14": self.good(300, 0.035, "bp"), "C01": self.good(50, 0.2), "C09": self.good(3, 0.0)}
        d = rb.decide(res, alpha)
        self.assertEqual(d["C09"]["verdict"], "UNREADABLE")             # 3 events < N_MIN
        self.assertAlmostEqual(d["C14"]["alpha"], 0.03 * 0.05 / 0.04)
        self.assertEqual(d["C14"]["verdict"], "PASS")                   # 0.035 <= 0.0375 after reallocation
        self.assertEqual(d["C01"]["verdict"], "FAIL")
        self.assertAlmostEqual(sum(x["alpha"] for x in d.values()), 0.05)

    def test_every_robustness_check_is_needed(self):
        alpha = {"C01": 0.05}
        for k in ("mean_2x_pct", "trimmed_mean_pct", "l2co_mean_pct"):
            r = self.good(50, 0.001)
            r[k] = -0.1
            self.assertEqual(rb.decide({"C01": r}, alpha)["C01"]["verdict"], "FAIL", k)
        self.assertEqual(rb.decide({"C01": self.good(50, 0.001)}, alpha)["C01"]["verdict"], "PASS")

    def test_daily_candidates_need_sixty_days(self):
        d = rb.decide({"C11b": self.good(59, 0.0, "bp")}, {"C11b": 0.05})
        self.assertEqual(d["C11b"]["verdict"], "UNREADABLE")

    def test_inputs_block_pins_each_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.csv"
            f.write_text("a\n")
            sha = __import__("hashlib").sha256(b"a\n").hexdigest()
            rb.inputs_ok(f"```inputs\n{f} {sha}  # a note\n```")
            for text in (f"```inputs\n{f} {'0' * 64}\n```", "```inputs\n```", "no block"):
                with self.assertRaises(SystemExit):
                    rb.inputs_ok(text)

    def test_run_refuses_before_the_date(self):
        with mock.patch.object(rb, "RUN_FROM", "2999-01-01"):
            with self.assertRaises(SystemExit):
                rb.run_batch()


if __name__ == "__main__":
    unittest.main()
