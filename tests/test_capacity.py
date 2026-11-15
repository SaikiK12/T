"""The capacity optimum must be a real maximum, and its invariant must hold numerically."""
import unittest

import numpy as np

from lab import capacity as cap


class FitTests(unittest.TestCase):
    def test_recovers_a_known_power_law(self):
        s = np.array([1000.0, 5000.0, 10000.0])
        a, beta = 0.4, 0.5
        y = a * s ** beta
        af, bf, r2 = cap.fit_cost_curve(s, y)
        self.assertAlmostEqual(af, a, places=9)
        self.assertAlmostEqual(bf, beta, places=9)
        self.assertAlmostEqual(r2, 1.0, places=9)

    def test_needs_two_positive_points(self):
        with self.assertRaises(ValueError):
            cap.fit_cost_curve([1000], [5.0])
        with self.assertRaises(ValueError):
            cap.fit_cost_curve([1000, 5000], [5.0, np.nan])


class OptimumTests(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.g = 0.438816, 0.4036, 0.0245

    def test_derivative_vanishes_at_the_optimum(self):
        n = cap.optimal_notional(self.g, self.a, self.b)
        h = n * 1e-5
        d = (cap.dollars_per_trade(n + h, self.g, self.a, self.b)
             - cap.dollars_per_trade(n - h, self.g, self.a, self.b)) / (2 * h)
        self.assertAlmostEqual(d, 0.0, places=6)

    def test_it_is_a_maximum_not_a_minimum(self):
        n = cap.optimal_notional(self.g, self.a, self.b)
        p = cap.dollars_per_trade(n, self.g, self.a, self.b)
        self.assertGreater(p, cap.dollars_per_trade(n * 0.5, self.g, self.a, self.b))
        self.assertGreater(p, cap.dollars_per_trade(n * 2.0, self.g, self.a, self.b))

    def test_cost_share_invariant_holds(self):
        n = cap.optimal_notional(self.g, self.a, self.b)
        share = cap.cost_bp(n, self.a, self.b) / 1e4 / self.g
        self.assertAlmostEqual(share, cap.cost_share_at_optimum(self.b), places=12)

    def test_invariant_is_independent_of_the_signal(self):
        for g in (0.001, 0.01, 0.05, 0.2):
            n = cap.optimal_notional(g, self.a, self.b)
            share = cap.cost_bp(n, self.a, self.b) / 1e4 / g
            self.assertAlmostEqual(share, 1 / (1 + self.b), places=12)

    def test_breakeven_is_above_the_optimum(self):
        n = cap.optimal_notional(self.g, self.a, self.b)
        be = cap.breakeven_notional(self.g, self.a, self.b)
        self.assertGreater(be, n)
        self.assertAlmostEqual(cap.dollars_per_trade(be, self.g, self.a, self.b), 0.0, places=6)

    def test_no_optimum_when_cost_does_not_rise_or_gross_is_negative(self):
        self.assertTrue(np.isnan(cap.optimal_notional(self.g, self.a, 0.0)))
        self.assertTrue(np.isnan(cap.optimal_notional(-0.01, self.a, self.b)))
        self.assertTrue(np.isnan(cap.optimal_notional(0.0, self.a, self.b)))


class ConstraintTests(unittest.TestCase):
    def test_depth_cap_binds_and_is_named(self):
        r = cap.constrained_notional(0.0245, 0.438816, 0.4036, depth_usd=7846)
        self.assertEqual(r["binding"], "depth")
        self.assertEqual(r["n"], 7846.0)
        self.assertGreater(r["raw_n"], r["n"])

    def test_fit_range_caps_an_extrapolated_optimum(self):
        r = cap.constrained_notional(0.0245, 0.438816, 0.4036, depth_usd=1e9)
        self.assertEqual(r["binding"], "fit_range")
        self.assertEqual(r["n"], 10_000.0)

    def test_capital_cap_can_bind(self):
        r = cap.constrained_notional(0.0245, 0.438816, 0.4036, depth_usd=1e9, capital_cap=2000)
        self.assertEqual(r["binding"], "capital")
        self.assertEqual(r["n"], 2000.0)

    def test_flat_cost_takes_the_largest_tradable_size(self):
        r = cap.constrained_notional(0.02, 5.0, 0.0, depth_usd=1e9)
        self.assertEqual(r["binding"], "no_optimum")
        self.assertEqual(r["n"], 10_000.0)


if __name__ == "__main__":
    unittest.main()
