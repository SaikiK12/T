"""Synthetic checks for R305's audit helpers: no panel return is read."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_mlaudit as au


class AuditTest(unittest.TestCase):
    def test_trials_and_feature_sets(self):
        self.assertEqual(au.TRIALS, 7)
        self.assertNotIn("age", au.FITTED["gbm no-age"])
        self.assertEqual(len(au.FITTED["gbm no-age"]), 23)
        self.assertEqual(set(au.FITTED["gbm no-risk"]) | set(au.RISK), set(au.CLEAN))

    def test_score_signs(self):
        idx = pd.MultiIndex.from_product([[pd.Timestamp("2024-01-01")], ["A", "B"]])
        X = pd.DataFrame({"vol30": [-0.25, 0.25], "age": [0.25, -0.25]}, index=idx)
        s = au.score_pred(X, {"vol30": -1, "age": 1}, idx)
        self.assertEqual(list(s), [0.25, -0.25])          # calm and old ranks first

    def test_ols_alpha(self):
        rng = np.random.default_rng(0)
        x = rng.normal(0, 0.05, 400)
        a, b, t, n = au.ols_alpha(0.01 + 2.0 * x + rng.normal(0, 0.001, 400), x)
        self.assertAlmostEqual(a, 0.01, places=3)
        self.assertAlmostEqual(b, 2.0, places=1)
        self.assertGreater(t, 50)
        self.assertEqual(au.ols_alpha([1.0] * 5, [0.0] * 5)[0], None)

    def test_labels(self):
        def bk(v):
            return {"valid": {"1x": {"bp_day": v}}}
        beta = {"ew_universe": {"alpha_t": 3.0}, "btc": {"alpha_t": 2.5}}
        books = {"gbm no-age": bk(50), "gbm risk-only": bk(10), "composite": bk(5)}
        self.assertTrue(au.labels(books, beta)["unexplained"])
        books["composite"] = bk(45)
        lab = au.labels(books, {"ew_universe": {"alpha_t": 1.5}, "btc": {"alpha_t": 2.5}})
        self.assertTrue(lab["known_anomaly"] and lab["beta"])
        self.assertFalse(lab["unexplained"])

    def test_squeeze(self):
        d = pd.Timestamp("2024-02-01")
        ret = pd.DataFrame({"A": [1.5], "B": [-0.1], "C": [0.2]}, index=[d])
        rows = [{"t": d.value // 10**6, "w": {"A": -0.5, "B": -0.5, "C": 1.0}}]
        sq = au.squeeze(rows, ret, 7, "valid")
        self.assertEqual(sq["rebalances"], 1)
        self.assertEqual(sq["max_short_name_ret"], 1.5)
        self.assertEqual(sq["share_short_name_over_100pct"], 1.0)


if __name__ == "__main__":
    unittest.main()
