import unittest

import numpy as np

from lab.apsi import (
    apsi_index,
    basket_sigma24,
    ewma_covariance,
    fee_burden_ratio,
    snapshot_at,
)


class ApsiTests(unittest.TestCase):
    def test_covariance_is_symmetric_psd_and_positive_scale_equivariant(self):
        rng = np.random.default_rng(41023)
        returns = rng.normal(0.0, 0.01, (168, 5))
        cov = ewma_covariance(returns)
        self.assertTrue(np.allclose(cov, cov.T, atol=1e-15))
        self.assertGreaterEqual(float(np.linalg.eigvalsh(cov).min()), -1e-15)
        sigma = basket_sigma24(returns, np.full(5, 0.2))
        scaled = basket_sigma24(returns * 3.0, np.full(5, 0.2))
        self.assertAlmostEqual(scaled / sigma, 3.0, places=12)

    def test_perfectly_correlated_equal_weight_basket_keeps_single_asset_risk(self):
        base = np.tile(np.array([0.01, -0.006, 0.003, -0.002]), 42)
        one = basket_sigma24(base[:, None], [1.0])
        two = basket_sigma24(np.column_stack([base, base]), [0.5, 0.5])
        self.assertAlmostEqual(one, two, places=14)

    def test_recent_return_shock_has_more_weight_than_old_shock(self):
        recent = np.zeros((168, 1))
        old = np.zeros((168, 1))
        recent[-1, 0] = 0.1
        old[0, 0] = 0.1
        self.assertGreater(basket_sigma24(recent, [1.0]), basket_sigma24(old, [1.0]))

    def test_index_is_100_at_its_baseline_and_200_at_twice_baseline(self):
        baseline = np.linspace(0.01, 0.03, 30)
        median = float(np.median(baseline))
        self.assertAlmostEqual(apsi_index(median, baseline), 100.0)
        self.assertAlmostEqual(apsi_index(2 * median, baseline), 200.0)

    def test_snapshot_at_ignores_every_return_after_the_origin(self):
        rng = np.random.default_rng(923)
        returns = rng.normal(0.0, 0.01, (500, 3))
        baseline = np.full(30, 0.02)
        original = snapshot_at(returns, 400, [1 / 3] * 3, baseline)
        altered = returns.copy()
        altered[400:] = rng.normal(0.0, 2.0, altered[400:].shape)
        self.assertEqual(original, snapshot_at(altered, 400, [1 / 3] * 3, baseline))

    def test_round_trip_cost_share_scales_linearly_with_fee_multiple(self):
        # A 16 bp round trip consumes 4% of an estimated 4% one-day sigma move.
        self.assertAlmostEqual(fee_burden_ratio(0.0016, 0.04), 0.04)
        self.assertAlmostEqual(fee_burden_ratio(0.0016, 0.04, cost_multiple=3), 0.12)

    def test_rejects_incomplete_data_bad_weights_and_wrong_baseline_length(self):
        x = np.zeros((168, 2))
        x[5, 1] = np.nan
        with self.assertRaises(ValueError):
            ewma_covariance(x)
        with self.assertRaises(ValueError):
            basket_sigma24(np.zeros((168, 2)), [0.4, 0.4])
        with self.assertRaises(ValueError):
            apsi_index(0.02, np.full(29, 0.02))


if __name__ == "__main__":
    unittest.main()
