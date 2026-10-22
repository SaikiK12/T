"""Synthetic checks for R308's stress-conditioned reversal: no market data is read."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_nagel as m


def panel(days, rets, ranks=None, oi=None, fund=0.0):
    """A long panel: `rets` is days x perps (row D's return); closes compound from 100."""
    n_d, n_p = rets.shape
    close = 100 * np.cumprod(1 + rets, axis=0)
    rows = []
    for i, d in enumerate(days):
        for j in range(n_p):
            rows.append({"day": d, "perp": f"P{j:03d}", "close": close[i, j], "ret": rets[i, j], "fund": fund,
                         "oi_usd": 1e6 if oi is None else oi[i, j],
                         "rank_qvol30": float(j + 1) if ranks is None else ranks[i, j]})
    return pd.DataFrame(rows)


class StressTest(unittest.TestCase):
    def test_trigger_uses_only_past_rows_and_direction(self):
        x = pd.Series(np.r_[np.tile([1.0, 2.0], 100), 5.0, 1.5])
        t = m.trigger(x, "mvol")
        self.assertFalse(t.iloc[:179].any())                 # fewer than 180 previous rows
        self.assertTrue(t.iloc[200])
        self.assertFalse(t.iloc[201])
        o = m.trigger(-x, "oi")
        self.assertTrue(o.iloc[200])                         # a fall at or below the 10th percentile

    def test_measures_read_the_top_50(self):
        days = [f"2021-01-{d:02d}" for d in range(2, 5)]
        rets = np.full((3, 60), 0.01)
        rets[1, :50] = np.linspace(-0.1, 0.1, 50)
        rets[1, 50:] = 0.9                                  # outside the top 50: ignored
        w = m.wide(panel(days, rets))
        ms = m.measures(w)
        self.assertAlmostEqual(ms["mvol"].iloc[1], np.abs(np.linspace(-0.1, 0.1, 50)).mean(), places=6)
        self.assertAlmostEqual(ms["disp"].iloc[1], np.linspace(-0.1, 0.1, 50).std(ddof=1), places=6)


class BookTest(unittest.TestCase):
    def test_tiers(self):
        np.testing.assert_allclose(m.tier_cost([1, 20, 21, 50, 51, 100, 101, 400]),
                                   [6e-4, 6e-4, 8e-4, 8e-4, 12e-4, 12e-4, 20e-4, 20e-4])

    def test_reversal_legs_gross_and_cost(self):
        days = [f"2021-01-{d:02d}" for d in range(2, 5)]
        n = 30
        r0 = np.linspace(-0.15, 0.14, n)                     # row D's returns: P000 lowest
        r1 = np.zeros(n)
        r1[:6] = 0.02                                         # the 6 losers bounce
        r1[-6:] = -0.01                                       # the 6 winners give back
        rets = np.vstack([r0, r1, np.zeros(n)])
        w = m.wide(panel(days, rets, fund=0.0001))
        rows = m.rev_rows(w, 150, w["close"].index[:1])
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["n"], 30)
        self.assertAlmostEqual(r["long"], 0.02 - 0.0001, places=6)
        self.assertAlmostEqual(r["short"], -0.01 - 0.0001, places=6)
        self.assertAlmostEqual(r["gross"], 0.03, places=6)
        cl = 2 * 6e-4                                         # ranks 1-6
        ch = 2 * 8e-4                                         # ranks 25-30
        self.assertAlmostEqual(r["cost"], cl + ch, places=9)
        self.assertEqual(m.rev_rows(w, 20, w["close"].index[:1]), [])   # 20 names: a fifth is 4, below 5

    def test_trials_and_decision_skip_baselines(self):
        self.assertEqual(m.TRIALS, 8)
        rep = {(50, "all"): {"disc": {"1x": {"mean_bp": 9.0, "t": 5.0}}, "valid": {}},
               (50, "mvol"): {"disc": {"1x": {"mean_bp": 4.0, "t": 1.0}},
                              "valid": {"1x": {"t": 2.1, "mean_wo_best_bp": 1.0}, "2x": {"mean_bp": 2.0}}}}
        self.assertEqual(m.decide(rep), ((50, "mvol"), True, {"t_1x": True, "mean_2x": True, "wo_best": True}))


if __name__ == "__main__":
    unittest.main()
