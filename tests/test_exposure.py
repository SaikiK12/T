import unittest

import numpy as np
import pandas as pd

from lab import exposure as ex


def chain():
    k = np.array([80, 90, 100, 110, 120.0])
    return pd.DataFrame({"f": 100.0, "strike": np.r_[k, k], "t": 30 / 365, "iv": 0.6,
                         "oi": [0, 50, 100, 400, 50, 50, 400, 100, 0, 0.0],
                         "call": [True] * 5 + [False] * 5})


class ExposureTest(unittest.TestCase):
    def test_greeks_match_finite_differences_of_delta(self):
        h = 1e-5
        for call in (True, False):
            d = lambda f=100.0, t=0.1, s=0.6: ex.greeks(f, 105, t, s, call).delta[0]
            g = ex.greeks(100.0, 105, 0.1, 0.6, call).iloc[0]
            self.assertAlmostEqual(g.gamma, (d(f=100 + h) - d(f=100 - h)) / (2 * h), places=6)
            self.assertAlmostEqual(g.vanna, (d(s=0.6 + h) - d(s=0.6 - h)) / (2 * h), places=5)
            self.assertAlmostEqual(g.charm, -(d(t=0.1 + h) - d(t=0.1 - h)) / (2 * h), places=5)

    def test_put_call_delta_parity_and_bad_rows(self):
        c = ex.greeks(100.0, [90, 110], 0.2, 0.5, True).delta
        p = ex.greeks(100.0, [90, 110], 0.2, 0.5, False).delta
        np.testing.assert_allclose(c - p, 1.0)
        self.assertTrue(ex.greeks([100, np.nan], 100, [0.0, 0.1], 0.5, True).isna().all().all())

    def test_exposures_follow_the_sign_convention_and_units(self):
        e = ex.exposures(chain())
        row = e[(e.strike == 110) & e.call].iloc[0]
        self.assertAlmostEqual(row.gex, row.gamma * 400 * 100 * 100 * 0.01)
        self.assertAlmostEqual(row.dex, row.delta * 400 * 100)
        self.assertTrue((e[~e.call & (e.oi > 0)].gex < 0).all())         # dealers short puts
        flipped = ex.exposures(chain(), sign_call=-1.0)
        self.assertTrue((flipped[flipped.call & (flipped.oi > 0)].gex < 0).all())

    def test_by_strike_walls_and_zero_gamma(self):
        s = ex.by_strike(ex.exposures(chain()))
        self.assertEqual(ex.walls(s), (110.0, 90.0))
        np.testing.assert_allclose(s.net_gex, s.call_gex + s.put_gex)
        grid = np.arange(70, 141, 1.0)
        prof = ex.gamma_profile(chain(), grid)
        z = ex.zero_gamma(prof, spot=100)
        self.assertTrue(90 < z < 110)                                       # puts below, calls above
        self.assertLess(prof.loc[85.0], 0)
        self.assertGreater(prof.loc[115.0], 0)
        self.assertTrue(np.isnan(ex.zero_gamma(pd.Series([1.0, 2.0], index=[1.0, 2.0]), 1.5)))


if __name__ == "__main__":
    unittest.main()
