"""lab/stress.py on synthetic series: no market data is read."""
import unittest

import numpy as np
import pandas as pd

from lab import stress


class StressTest(unittest.TestCase):
    def setUp(self):
        days = pd.date_range("2025-09-01", "2025-10-31", freq="D")
        self.pnl = pd.Series(1.0, index=days)
        self.pnl.loc["2025-10-10"] = -30.0
        self.pnl.loc["2025-10-11"] = -10.0
        self.vol = pd.Series(0.02, index=days)
        self.vol.loc["2025-10-10"] = 0.15

    def test_episode_in_mean_days(self):
        r = stress.report(self.pnl)
        e = r["episodes"]["2025-10-10 liquidations"]
        self.assertEqual(e["days"], 2)
        self.assertAlmostEqual(e["sum"], -40.0)
        self.assertAlmostEqual(e["in_mean_days"], -40.0 / abs(r["mean"]))
        self.assertNotIn("LUNA", r["episodes"])                # no day of it in the series
        self.assertEqual(r["worst"][0], ("2025-10-10", -30.0))

    def test_volatility_tail(self):
        r = stress.report(self.pnl, self.vol, q=0.98)
        t = r["vol_top"]
        self.assertEqual(t["days"], 1)
        self.assertAlmostEqual(t["mean"], -30.0)
        self.assertLess(t["other_mean"], 1.0)                  # the other days include 2025-10-11

    def test_market_vol_uses_top_ranks_and_same_day_moves(self):
        panel = pd.DataFrame({
            "day": ["2025-10-10"] * 3 + ["2025-10-11"] * 3,
            "ret": [-0.10, 0.20, 0.90, 0.01, -0.03, np.nan],
            "rank_qvol30": [1, 2, 80, 1, 2, 3]})
        v = stress.market_vol(panel, top=50)
        self.assertAlmostEqual(v.loc["2025-10-10"], 0.15)      # rank 80 left out
        self.assertAlmostEqual(v.loc["2025-10-11"], 0.02)      # NaN left out

    def test_tz_aware_index_and_table(self):
        p = self.pnl.copy()
        p.index = p.index.tz_localize("UTC")
        r = stress.report(p, self.vol)
        self.assertIn("2025-10-10 liquidations", r["episodes"])
        self.assertIn("| All 61 days, mean |", stress.table(r))

    def test_no_episode_before_2021(self):
        self.assertTrue(all(a >= "2021-01-01" for a, _ in stress.EPISODES.values()))


if __name__ == "__main__":
    unittest.main()
