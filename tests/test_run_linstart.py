"""scripts/run_linstart.py (R485): short sign, D-7/D+14 indexing, cost scaling, week-cluster t, the null's
admissible days and seed reproducibility, gates and the INSUFFICIENT rule, funding window."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_linstart as rl  # noqa: E402

DAY = rl.DAY
D0 = rl.le.ms("2024-06-01")


def closes(n=60, start=D0 - 20 * DAY, f=lambda i: 100.0 + i):
    return pd.Series({start + i * DAY: f(i) for i in range(n)}, dtype=float)


class TestTrade(unittest.TestCase):
    def test_short_sign_and_indexing(self):
        c = closes()                                   # close on day start+i is 100+i
        g, early = rl.trade(c, D0)
        entry, exit_ = c[D0 - 7 * DAY], c[D0 + 14 * DAY]
        self.assertEqual((entry, exit_), (113.0, 134.0))
        self.assertAlmostEqual(g, -(134.0 / 113.0 - 1))
        self.assertLess(g, 0)                          # price up -> short loses
        self.assertFalse(early)
        down = closes(f=lambda i: 200.0 - i)
        self.assertGreater(rl.trade(down, D0)[0], 0)   # price down -> short gains

    def test_no_market_and_exit_early(self):
        c = closes()
        self.assertIsNone(rl.trade(c.drop(D0 - 7 * DAY), D0))
        g, early = rl.trade(c[c.index <= D0 + 5 * DAY], D0)
        self.assertTrue(early)
        self.assertAlmostEqual(g, -(c[D0 + 5 * DAY] / c[D0 - 7 * DAY] - 1))

    def test_closes_from_rows_keeps_confirmed_only(self):
        rows = [[str(D0), "1", "1", "1", "2.5", "0", "0", "0", "1"],
                [str(D0 + DAY), "1", "1", "1", "9", "0", "0", "0", "0"]]
        s = rl.closes_from_rows(rows)
        self.assertEqual(list(s.index), [D0])
        self.assertEqual(s[D0], 2.5)


class TestCostsAndStats(unittest.TestCase):
    def test_cost_scaling(self):
        g = np.array([0.01, -0.02])
        for m, bp in ((1, 20), (2, 40), (3, 60)):
            np.testing.assert_allclose(rl.net(g, m), g - bp / 1e4)

    def test_cluster_t_known_vector(self):
        x = np.array([1.0, 2.0, 3.0, 6.0])
        groups = [1, 1, 2, 2]
        # mean 3; cluster sums of (x - 3): -3, 3; se = sqrt(2/1 * 18) / 4 = 1.5; t = 2
        self.assertAlmostEqual(rl.cluster_t(x, groups), 2.0)

    def test_iso_week(self):
        self.assertEqual(list(rl.iso_week([rl.le.ms("2024-01-01"), rl.le.ms("2024-12-30")])), [202401, 202501])


class TestNull(unittest.TestCase):
    def test_admissible_days_exclude_events_and_unpriceable(self):
        c = closes(n=200, start=D0 - 100 * DAY)
        days = rl.admissible_days(c, [D0], D0 - 90 * DAY, D0 + 90 * DAY)
        self.assertTrue(len(days))
        self.assertTrue((np.abs(days - D0) > 30 * DAY).all())
        self.assertNotIn(D0 + 30 * DAY, set(days))
        self.assertIn(D0 + 31 * DAY, set(days))
        self.assertGreaterEqual(days.min(), c.index.min() + 7 * DAY)
        self.assertLessEqual(days.max(), c.index.max() - 14 * DAY)

    def test_null_reproducible_with_seed(self):
        cand = {"A": np.linspace(-0.1, 0.1, 50), "B": np.linspace(-0.05, 0.02, 30)}
        groups = {"A": 3, "B": 2}
        a = rl.null_means(cand, groups, 5, reps=50, seed=485)
        b = rl.null_means(cand, groups, 5, reps=50, seed=485)
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.array_equal(a, rl.null_means(cand, groups, 5, reps=50, seed=486)))
        rng = np.random.default_rng(485)                  # first replication by hand
        first = (cand["A"][rng.integers(0, 50, 3)].sum() + cand["B"][rng.integers(0, 30, 2)].sum()) / 5
        self.assertAlmostEqual(a[0], first)


class TestGatesAndVerdict(unittest.TestCase):
    def frame(self, x, insts):
        n = len(x)
        df = pd.DataFrame({"net1x": x, "inst_id": insts, "week": np.arange(n) // 2,
                           "day": [f"d{i:03d}" for i in range(n)]})
        df["net2x"] = df.net1x - 0.002
        return df

    def test_gates(self):
        x = np.r_[np.full(10, 0.05), np.full(10, 0.06)] + np.tile([0.001, -0.001], 10)
        g, d = rl.gates(self.frame(x, [f"S{i % 7}" for i in range(20)]), 0.01)
        self.assertTrue(all(g.values()))
        g, _ = rl.gates(self.frame(-x, [f"S{i % 7}" for i in range(20)]), 0.5)
        self.assertFalse(any(g.values()))

    def test_insufficient_below_20(self):
        ok = {k: True for k in ("G1", "G2", "G3", "G4", "G5")}
        self.assertEqual(rl.verdict(19, ok), "INSUFFICIENT")
        self.assertEqual(rl.verdict(20, ok), "CONFIRMS-ON-HISTORY")
        self.assertEqual(rl.verdict(20, {**ok, "G3": False}), "NULL")


class TestFunding(unittest.TestCase):
    def test_window_and_availability(self):
        hrs = 8 * 3600 * 1000
        f = pd.Series({D0 - 10 * DAY + i * hrs: 0.0001 for i in range(3 * 40)}, dtype=float)
        s = rl.funding_sum(f, D0)
        # (close of D-7, close of D+14] = (D-6 00:00, D+15 00:00]: 21 days x 3 settlements
        self.assertAlmostEqual(s, 63 * 0.0001)
        self.assertIsNone(rl.funding_sum(f[f.index > D0], D0))


if __name__ == "__main__":
    unittest.main()
