import math
import unittest

import numpy as np
import pandas as pd

from lab.tearsheet import metrics, tearsheet


class TearsheetTest(unittest.TestCase):
    def setUp(self):
        days = pd.date_range("2026-01-30", periods=6, freq="D")
        self.r = pd.Series([0.10, -0.05, 0.02, -0.10, 0.03, 0.01], index=days)

    def test_hand_computed_metrics(self):
        m = metrics(self.r)
        r = self.r.values
        eq = np.cumprod(1 + r)
        self.assertEqual(m["days"], 6)
        self.assertAlmostEqual(m["total_return"], eq[-1] - 1)
        dd = eq / np.maximum.accumulate(eq) - 1
        self.assertAlmostEqual(m["max_drawdown"], dd.min())
        self.assertEqual(m["max_dd_days"], 5)                     # under water from day 2 to the end
        self.assertAlmostEqual(m["hit_rate"], 4 / 6)
        self.assertAlmostEqual(m["profit_factor"], 0.16 / 0.15)
        self.assertAlmostEqual(m["sharpe"], r.mean() / r.std(ddof=1) * math.sqrt(365))
        self.assertAlmostEqual(m["t"], r.mean() / (r.std(ddof=1) / math.sqrt(6)))
        self.assertEqual(m["losing_streak"], 1)
        self.assertAlmostEqual(m["worst_day"], -0.10)

    def test_deflation_is_harsher_with_more_trials(self):
        rng = np.random.default_rng(0)
        r = pd.Series(rng.normal(0.002, 0.01, 400))
        few, many = metrics(r, n_trials=10), metrics(r, n_trials=9_000_000)
        self.assertGreater(few["dsr"], many["dsr"])
        self.assertGreater(many["dsr_bar_sharpe"], few["dsr_bar_sharpe"])
        self.assertLessEqual(few["dsr"], few["psr"])

    def test_curve_and_months(self):
        t = tearsheet(self.r, window=3)
        self.assertEqual(len(t["curve"]), 6)
        self.assertAlmostEqual(t["curve"][-1]["equity"], float(np.prod(1 + self.r.values)))
        self.assertIsNone(t["curve"][0]["rolling_sharpe"])
        self.assertIsNotNone(t["curve"][2]["rolling_sharpe"])
        jan = [x for x in t["monthly"] if x["month"] == 1][0]
        self.assertAlmostEqual(jan["ret"], 1.10 * 0.95 - 1)
        self.assertEqual(len(t["monthly"]), 2)

    def test_autocorrelation_is_not_free_evidence(self):
        rng = np.random.default_rng(1)
        e = rng.normal(0, 0.01, 3000)
        ar = np.empty_like(e)
        ar[0] = e[0]
        for i in range(1, len(e)):
            ar[i] = 0.7 * ar[i - 1] + e[i]
        smooth = metrics(pd.Series(ar + 0.001))
        self.assertGreater(smooth["ac1"], 0.6)
        self.assertLess(smooth["sharpe_ac"], 0.6 * smooth["sharpe"])
        self.assertLess(smooth["t_nw"], 0.6 * smooth["t"])
        self.assertLess(smooth["n_eff"], 0.25 * 3000)
        iid = metrics(pd.Series(e + 0.001))
        self.assertAlmostEqual(iid["sharpe_ac"], iid["sharpe"], delta=0.25 * abs(iid["sharpe"]))
        self.assertAlmostEqual(iid["t_nw"], iid["t"], delta=0.2 * abs(iid["t"]))

    def test_short_or_empty_stream(self):
        self.assertEqual(metrics(pd.Series([0.01])), {"days": 1})
        self.assertEqual(tearsheet(pd.Series([], dtype=float))["curve"], [])


if __name__ == "__main__":
    unittest.main()
