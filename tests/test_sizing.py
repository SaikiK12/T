import unittest

import numpy as np
import pandas as pd

from lab import sizing


class SizingTests(unittest.TestCase):
    def test_lagged_volatility_does_not_use_today_or_future(self):
        x = np.array([1.0, 1.0, 1.0, 3.0, 3.0])
        a = sizing.lagged_ewma_vol(x, halflife=2, min_periods=2)
        b = sizing.lagged_ewma_vol(np.r_[x[:3], 300.0, 300.0], halflife=2, min_periods=2)
        np.testing.assert_array_equal(a[:4], b[:4])
        self.assertTrue(np.isnan(a[0]))

    def test_volatility_matches_ewma_reference_and_resets_after_missing_outcome(self):
        r = np.array([0.01, -0.02, 0.03, -0.01, np.nan, 0.02, -0.01, 0.04])
        got = sizing.lagged_ewma_vol(r, halflife=2, min_periods=2)
        ref = pd.Series(r[:4]).ewm(halflife=2, adjust=False, min_periods=2).std(bias=True).shift(1)
        np.testing.assert_allclose(got[:4], ref.values, equal_nan=True)
        self.assertTrue(np.isfinite(got[4]))       # decision precedes the missing outcome
        self.assertTrue(np.isnan(got[5:7]).all())  # the outage is known on the next decision
        self.assertTrue(np.isfinite(got[7]))

    def test_unavailable_risk_never_implicitly_gives_full_size(self):
        for returns in (np.zeros(8), np.full(8, np.nan)):
            np.testing.assert_array_equal(sizing.volatility_multiplier(returns, 0.01, min_periods=2), 0.0)
        r = [0.01, -0.01, 0.02, np.nan, 0.01, 0.02, 0.03]
        m = sizing.volatility_multiplier(r, 0.01, min_periods=2, unknown=0.0)
        self.assertGreater(m[2], 0)
        self.assertEqual(m[4], 0)
        np.testing.assert_array_equal(sizing.volatility_multiplier(r, 0, min_periods=2, initial=1), 0.0)

    def test_explicit_warmup_size_cannot_extend_forever_without_a_risk_estimate(self):
        for r in (np.zeros(8), np.full(8, np.nan)):
            got = sizing.volatility_multiplier(r, 0.01, min_periods=2, initial=1, unknown=0)
            np.testing.assert_array_equal(got, [1, 1, 0, 0, 0, 0, 0, 0])

    def test_lower_bound_requires_hurdle_clearance_and_caps(self):
        m = sizing.lower_bound_multiplier([0.01, 0.02, np.nan], [0.001] * 3, 0.005, [0.01] * 3,
                                          z=1.0, cap=0.5)
        np.testing.assert_allclose(m, [0.4, 0.5, 0.0])

    def test_positive_floor_cannot_create_confidence_from_negative_or_invalid_edge(self):
        for se, hurdle in ((1, 0), (-1, 0), (0, -1)):
            self.assertEqual(sizing.lower_bound_multiplier(0, se, hurdle, 1, z=1, floor=0.25), 0)

    def test_nonfinite_parameters_and_positions_are_rejected(self):
        for bad in (np.nan, np.inf, -np.inf):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    sizing.volatility_multiplier([0.01, -0.01], bad)
                with self.assertRaises(ValueError):
                    sizing.lower_bound_multiplier(0.01, 0.001, 0, 0.01, z=bad)
                with self.assertRaises(ValueError):
                    sizing.apply_multiplier([[1.0]], [1], max_gross=bad)
                with self.assertRaises(ValueError):
                    sizing.turnover([[bad]])
        with self.assertRaises(ValueError):
            sizing.lagged_ewma_vol(np.ones((3, 2)))

    def test_position_caps_and_matched_constant_are_explicit(self):
        p = np.array([[1.0, -0.5], [1.0, -0.5]])
        q = sizing.apply_multiplier(p, [1.0, 2.0], max_symbol=0.75, max_gross=1.0)
        np.testing.assert_allclose(q, [[0.6, -0.4], [0.5, -0.5]])
        self.assertAlmostEqual(sizing.matched_constant_multiplier(p, [1.0, 2.0]), 1.5)
        np.testing.assert_allclose(sizing.turnover(q), [1.0, 0.2])

    def test_matching_applies_identical_caps_to_constant_and_dynamic_books(self):
        p = np.array([[2.0, -1.0], [0.2, -0.1], [0.5, -1.0]])
        m = np.array([2.0, 0.25, 1.5])
        kwargs = dict(max_symbol=0.75, max_gross=1.0)
        constant = sizing.matched_constant_multiplier(p, m, **kwargs)
        candidate = sizing.apply_multiplier(p, m, **kwargs)
        control = sizing.apply_multiplier(p, np.full(3, constant), **kwargs)
        self.assertAlmostEqual(np.abs(candidate).sum(axis=1).mean(), np.abs(control).sum(axis=1).mean())

    def test_gross_cap_applies_to_hedge_and_signal_together(self):
        complete_book = np.array([[1.0, -1.0]])
        q = sizing.apply_multiplier(complete_book, [2.0], max_gross=1.0)
        np.testing.assert_array_equal(q, [[0.5, -0.5]])


if __name__ == "__main__":
    unittest.main()
