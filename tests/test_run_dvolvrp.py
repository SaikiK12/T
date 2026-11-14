import unittest

import numpy as np

from scripts import run_dvolvrp as r


class Days(unittest.TestCase):
    def test_rv_of_a_constant_hourly_move_and_skips(self):
        n_days = 40
        PH = 100.0 * np.exp(0.01 * (np.arange(n_days * 24 + 1) % 2))   # log returns alternate +1%, -1% hourly
        DV = {r.T0 + i * r.DAY: 50.0 for i in range(n_days)}
        f = r.days(PH, DV)
        self.assertEqual(len(f), n_days - 30 + 1)                          # days 0..10 have 30 days of path after them
        self.assertAlmostEqual(f.rv.iloc[0], 0.01 * np.sqrt(8760) * 100, places=6)
        PH[5] = np.nan
        self.assertNotIn(r.T0, set(r.days(PH, DV).d))

    def test_dvol_value_is_previous_bar_close(self):
        import pandas as pd, tempfile, os
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.parquet")
            pd.DataFrame({"t": [r.T0, r.T0 + r.HOUR], "open": 1.0, "high": 1.0, "low": 1.0,
                          "close": [40.0, 41.0]}).to_parquet(p)
            dv = r.dvol_at(p)
        self.assertEqual(dv[r.T0 + r.HOUR], 40.0)
        self.assertNotIn(r.T0, dv)


if __name__ == "__main__":
    unittest.main()
