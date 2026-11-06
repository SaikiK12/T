import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import stats
from scripts import run_gexfilter as G


class GexFilter(unittest.TestCase):
    def test_nw_regression_matches_mean_t(self):
        rng = np.random.default_rng(1)
        y = rng.normal(0.1, 1, 400)
        b, t, _ = G.ols_nw(y, np.ones((400, 1)), lag=10)
        self.assertAlmostEqual(b[0], y.mean())
        self.assertAlmostEqual(t[0], stats.newey_west_t(y, 10)[2], places=6)

    def test_regression_recovers_slope(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=2000)
        y = 1 - 0.5 * x + rng.normal(scale=0.1, size=2000)
        b, t, r2 = G.ols_nw(y, np.column_stack([np.ones(2000), x]))
        self.assertAlmostEqual(b[1], -0.5, places=2)
        self.assertLess(t[1], -50)
        self.assertGreater(r2, 0.9)

    def test_rv_window_and_minimum_bars(self):
        idx = pd.date_range("2024-01-01", periods=48, freq="h", tz="UTC")
        r = pd.Series(0.01, index=idx)
        self.assertAlmostEqual(G.rv(r, idx[0], 24), np.sqrt(24) * 0.01)
        self.assertTrue(np.isnan(G.rv(r.iloc[:20], idx[0], 24)))

    def test_rank_uses_only_past_values(self):
        g = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=300, freq="D"), "price": 1.0, "dix": 0.4,
                          "gex": np.arange(300.0)})
        g2 = g.copy()
        g2.loc[299, "gex"] = -1e9                        # only the last day changes
        with tempfile.TemporaryDirectory() as tmp:
            vix = Path(tmp) / "vix.parquet"                 # synthetic: data/ is not in the checkout on CI
            pd.DataFrame({"day": g.date, "close": 20.0}).to_parquet(vix)
            p, p2 = Path(tmp) / "g1.csv", Path(tmp) / "g2.csv"
            g.to_csv(p, index=False)
            g2.to_csv(p2, index=False)
            a, b = G.gex_frame(p, vix), G.gex_frame(p2, vix)
        self.assertTrue(np.allclose(a["rank"].iloc[:-1].dropna(), b["rank"].iloc[:-1].dropna()))
        self.assertEqual(a["rank"].dropna().iloc[-1], 1.0)


if __name__ == "__main__":
    unittest.main()
