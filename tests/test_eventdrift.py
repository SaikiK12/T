"""R368 eventdrift_v1: rule maths and the runner on a synthetic world (offline; says nothing about real data)."""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import eventdrift_rule as rule  # noqa: E402
import run_eventdrift as run  # noqa: E402

M = rule.MINUTE_MS
T0 = 1_780_000_000_000 - 1_780_000_000_000 % M      # a minute boundary
DAY = 1_440 * M


def make_bars(closes, start=T0):
    """Bars one minute apart whose open is the previous close."""
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    return pd.DataFrame({"t": start + np.arange(len(closes)) * M, "open": opens, "close": closes})


def world(n_events, drift_bp, noise_bp=8.0, seed=1):
    """One bar a minute for n_events days. At minute 870 of each day (14:30) a first-minute move of +-30 bp, then
    `drift_bp` more in the same direction spread over the next five minutes, plus noise everywhere."""
    rng = np.random.default_rng(seed)
    logp = np.zeros(n_events * 1440 + 20)
    step = rng.normal(0, noise_bp / 1e4, len(logp))
    events = []
    for d in range(n_events):
        i = d * 1440 + 870
        s = 1 if rng.random() < 0.5 else -1
        step[i] += s * 30 / 1e4
        step[i + 1:i + 6] += s * drift_bp / 1e4 / 5
        events.append(T0 + i * M)
    logp = 100 * np.exp(np.cumsum(step) - step[0])
    return make_bars(logp), events


class RuleTests(unittest.TestCase):
    def test_event_row_uses_the_close_before_for_the_reaction_and_the_next_open_for_entry(self):
        closes = np.full(30, 100.0)
        closes[10] = 101.0                     # bar T-1 closes at 101 when T is bar 11
        closes[11:] = [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0,
                       115.0, 116.0, 117.0, 118.0, 119.0, 120.0]
        bars = make_bars(closes)
        row = rule.event_row(bars, T0 + 11 * M)
        self.assertTrue(row["usable"])
        self.assertAlmostEqual(row["r0"], 1e4 * math.log(102 / 101))
        # entry is the open of bar 12, which is the close of bar 11 = 102; h = 5 exits at the close of bar 16 = 107
        self.assertAlmostEqual(row["move5"], 1e4 * math.log(107 / 102))
        self.assertAlmostEqual(row["late5"], 1e4 * math.log(107 / 103))
        self.assertAlmostEqual(row["move1"], 1e4 * math.log(103 / 102))

    def test_a_missing_bar_makes_the_event_unusable_and_leaves_nothing_to_use(self):
        bars = make_bars(np.linspace(100, 101, 40))
        bars = bars[bars.t != T0 + 18 * M]
        row = rule.event_row(bars, T0 + 11 * M)
        self.assertFalse(row["usable"])
        self.assertTrue(math.isnan(row["r0"]) and math.isnan(row["move5"]))
        row = rule.event_row(make_bars(np.linspace(100, 101, 15)), T0 + 11 * M)     # the series ends too soon
        self.assertFalse(row["usable"])

    def test_sign_flip_p_is_exact_for_a_small_sample(self):
        rng = np.random.default_rng(0)
        self.assertAlmostEqual(rule.sign_flip_p([1.0, 1.0, 1.0], rng), 1 / 8)
        self.assertAlmostEqual(rule.sign_flip_p([1.0, -1.0], rng), 3 / 4)          # +-: 2 of 4 patterns tie or beat 0
        self.assertAlmostEqual(rule.sign_flip_p([2.0, 1.0, -1.0], rng), 3 / 8)     # sums 4, 2, 2 reach the observed 2
        self.assertTrue(math.isnan(rule.sign_flip_p([], rng)))

    def test_monte_carlo_p_agrees_with_the_exact_one_where_both_apply(self):
        x = np.random.default_rng(3).normal(0.4, 1.0, 14)
        exact = rule.sign_flip_p(x, np.random.default_rng(1), exact_max=18)
        mc = rule.sign_flip_p(x, np.random.default_rng(1), draws=100_000, exact_max=0)
        self.assertLess(abs(exact - mc), 0.01)

    def test_holm_matches_the_textbook_values(self):
        np.testing.assert_allclose(rule.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
        np.testing.assert_allclose(rule.holm([0.2]), [0.2])

    def test_subsets_split_on_the_sign_of_the_first_minute_and_drop_zero(self):
        r0 = np.array([-5.0, 0.0, 3.0, np.nan, -1.0])
        move = np.array([10.0, 7.0, 4.0, 2.0, np.nan])
        np.testing.assert_allclose(rule.continuation(r0, move, "neg"), [-10.0])      # -1 has no move: dropped
        np.testing.assert_allclose(rule.continuation(r0, move, "pos"), [4.0])
        np.testing.assert_allclose(rule.continuation(r0, move, "all"), [-10.0, 4.0])

    def test_verdict_needs_events_significance_and_cost(self):
        d = lambda n, mean, p: {"n": n, "mean": mean, "p_holm": p}                   # noqa: E731
        self.assertEqual(rule.verdict([d(9, 99, 0.001), d(3, 99, 0.001)])[0], "INCONCLUSIVE")
        self.assertEqual(rule.verdict([d(15, 30, 0.01), d(20, 1, 0.9)])[0], "PASS")
        self.assertEqual(rule.verdict([d(15, 18, 0.01), d(20, 1, 0.9)])[0], "PARTIAL")
        self.assertEqual(rule.verdict([d(15, 30, 0.2), d(20, 1, 0.9)])[0], "NULL")
        self.assertEqual(rule.verdict([d(15, 5, 0.01), d(20, 1, 0.9)])[0], "NULL")


class RunnerTests(unittest.TestCase):
    def lane(self, root, drift, seed, symbols=("CLUSDT", "NATGASUSDT")):
        lane, data = root / "lane", root / "klines_1m"
        lane.mkdir()
        data.mkdir()
        events, manifest = [], {}
        for sym, etype in zip(symbols, ("wpsr", "ngs")):
            bars, times = world(30, drift, seed=seed + (sym == "NATGASUSDT"))
            bars.to_parquet(data / f"{sym}.parquet", index=False)
            manifest[sym] = {"sha256": prereg.sha256_file(data / f"{sym}.parquet")}
            events += [(etype, pd.Timestamp(t, unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"), t) for t in times]
        (data / "manifest.json").write_text(json.dumps({"symbols": manifest, "sha256": "x" * 64}))
        pd.DataFrame(events, columns=["event", "release_utc", "release_ms"]).to_csv(lane / "events.csv", index=False)
        return lane, data

    def test_a_planted_drift_is_found_and_a_null_world_is_not(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = self.lane(Path(d), drift=60.0, seed=11)
            self.assertEqual(run.run(lane=lane, data=data, check=False), "PASS")
            cells = pd.read_csv(lane / "results" / "cells.csv")
            dec = cells[cells.decision]
            self.assertEqual(len(dec), 2)
            self.assertTrue((dec["mean"] > 40).all())
            self.assertTrue((dec.p_holm <= 0.05).all())
            self.assertEqual(len(cells), 26)
        verdicts = []
        for seed in range(20, 40, 4):
            with tempfile.TemporaryDirectory() as d:
                lane, data = self.lane(Path(d), drift=0.0, seed=seed)
                verdicts.append(run.run(lane=lane, data=data, check=False))
        self.assertNotIn("PASS", verdicts)
        self.assertNotIn("PARTIAL", verdicts)

    def test_a_drift_that_clears_one_cost_unit_but_not_two_is_partial(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = self.lane(Path(d), drift=18.0, seed=11)
            self.assertEqual(run.run(lane=lane, data=data, check=False), "PARTIAL")

    def test_plumbing_writes_coverage_only_and_no_return_columns(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = self.lane(Path(d), drift=0.0, seed=5)
            self.assertEqual(run.run(plumbing=True, lane=lane, data=data, check=False), "PLUMBING")
            cov = pd.read_csv(lane / "results" / "coverage.csv")
            self.assertEqual(list(cov.columns), ["event", "release_utc", "symbol", "bars", "needed", "usable"])
            self.assertEqual(len(cov), 60)
            self.assertTrue(cov.usable.all())
            self.assertFalse((lane / "results" / "cells.csv").exists())

    def test_the_frozen_input_check_refuses_a_changed_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.txt").write_text("one")
            good = prereg.sha256_file(root / "a.txt")
            spec = root / "PREREG.md"
            spec.write_text(f"```inputs\n{good}  a.txt\n```\n")
            self.assertEqual(run.frozen_inputs(spec, root), {"a.txt": good})
            (root / "a.txt").write_text("two")
            with self.assertRaises(prereg.PreregError):
                run.frozen_inputs(spec, root)

    def test_the_data_check_refuses_a_file_that_is_not_the_manifests(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = self.lane(Path(d), drift=0.0, seed=5)
            run.verify_data(data)
            bars = pd.read_parquet(data / "CLUSDT.parquet")
            bars.loc[0, "close"] += 1.0
            bars.to_parquet(data / "CLUSDT.parquet", index=False)
            with self.assertRaises(prereg.PreregError):
                run.verify_data(data)

    def test_the_real_calendar_is_sixty_releases_at_the_documented_instants(self):
        events = pd.read_csv(ROOT / "experiments" / "eventdrift_v1" / "events.csv")
        self.assertEqual(events.event.value_counts().to_dict(), {"wpsr": 30, "ngs": 30})
        hours = pd.to_datetime(events.release_utc).dt.strftime("%H:%M")
        self.assertEqual(set(hours), {"14:30", "16:00"})
        self.assertEqual(events.release_ms.diff().dropna().ge(0).all(), True)


if __name__ == "__main__":
    unittest.main()
