import unittest

import numpy as np

from lab import sizing


class SizingTests(unittest.TestCase):
    def test_lagged_volatility_does_not_use_today_or_future(self):
        x = np.array([1.0, 1.0, 1.0, 3.0, 3.0])
        a = sizing.lagged_ewma_vol(x, halflife=2, min_periods=2)
        b = sizing.lagged_ewma_vol(np.r_[x[:3], 300.0, 300.0], halflife=2, min_periods=2)
        np.testing.assert_array_equal(a[:3], b[:3])
        self.assertTrue(np.isnan(a[0]))

    def test_lower_bound_requires_hurdle_clearance_and_caps(self):
        m = sizing.lower_bound_multiplier([0.01, 0.02, np.nan], [0.001] * 3, 0.005, [0.01] * 3,
                                          z=1.0, cap=0.5)
        np.testing.assert_allclose(m, [0.4, 0.5, 0.0])

    def test_position_caps_and_matched_constant_are_explicit(self):
        p = np.array([[1.0, -0.5], [1.0, -0.5]])
        q = sizing.apply_multiplier(p, [1.0, 2.0], max_symbol=0.75, max_gross=1.0)
        np.testing.assert_allclose(q, [[0.6, -0.4], [0.5, -0.5]])
        self.assertAlmostEqual(sizing.matched_constant_multiplier(p, [1.0, 2.0]), 1.5)
        np.testing.assert_allclose(sizing.turnover(q), [1.0, 0.2])


if __name__ == "__main__":
    unittest.main()
