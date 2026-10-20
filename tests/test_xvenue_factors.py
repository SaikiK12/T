import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import xvenue_factors as xf

H, DAY, T0 = xf.H, xf.DAY, xf.T0


class XvenueFactorsTest(unittest.TestCase):
    def test_days_and_reserved_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "k.parquet"
            # a 2020 bar ending at day 0 (dropped), a bar ending exactly at day 1, one inside day 2, a zero-volume bar
            pd.DataFrame({"t": [T0 - H, T0 + 23 * H, T0 + DAY + 3 * H, T0 + 2 * DAY + 23 * H],
                          "close": [1.0, 2.0, 3.0, 4.0], "v": [5.0, 6.0, 7.0, 0.0]}).to_parquet(p)
            close, vol = xf.daily_bars(p, "v")
            self.assertTrue(np.isnan(close[0]))
            self.assertEqual(close[1], 2.0)
            self.assertTrue(np.isnan(close[2]))            # day 2's last bar is not the one ending at it
            self.assertTrue(np.isnan(close[3]))            # zero volume: not traded
            self.assertEqual((vol[0], vol[1], vol[2]), (0.0, 6.0, 7.0))
            f = Path(d) / "f.parquet"
            pd.DataFrame({"t": [T0, T0 + DAY + 2, T0 + DAY + H + 48], "rate": [0.5, 0.001, 0.002]}).to_parquet(f)
            fd, n, first = xf.daily_funding(f)
            self.assertEqual((fd[1], fd[2], first), (0.001, 0.002, 1))
            self.assertEqual(fd.sum(), 0.003)              # the settlement at the start instant is day 0: dropped

    def test_window_needs_history(self):
        f = np.zeros(xf.ND)
        n = np.zeros(xf.ND)
        f[4:10], n[4:10] = 0.001, 3
        w = xf.window(f, n, 4, 3)
        self.assertTrue(np.isnan(w[5]))                    # days 3..5 start before the history
        self.assertAlmostEqual(w[6], 0.003)
        self.assertTrue(np.isnan(w[12]))                   # no settlement in days 10..12

    def test_roll_sum(self):
        np.testing.assert_allclose(xf.roll_sum(np.array([1.0, 2, 3, 4]), 2), [np.nan, 3, 5, 7])


if __name__ == "__main__":
    unittest.main()
