import unittest

import numpy as np
import pandas as pd

from lab import factor_report as fr


class RankICTests(unittest.TestCase):
    def test_perfect_positive_and_negative_factors(self):
        f = np.tile(np.arange(10.0), (4, 1))
        fwd = f * 0.01 + np.arange(4.0)[:, None] * 1e-6
        ic, n = fr.rank_ic(f, fwd)
        np.testing.assert_allclose(ic, 1.0)
        np.testing.assert_array_equal(n, 10)
        ic, _ = fr.rank_ic(f, -fwd)
        np.testing.assert_allclose(ic, -1.0)

    def test_eligibility_and_missing_values_are_excluded_not_zeroed(self):
        f = np.array([[3.0, 1.0, 2.0, np.nan, 5.0]])
        fwd = np.array([[0.3, 0.1, 0.2, 9.9, np.nan]])
        elig = np.array([[True, True, True, True, True]])
        ic, n = fr.rank_ic(f, fwd, elig, min_obs=3)
        self.assertEqual(n[0], 3)
        self.assertAlmostEqual(ic[0], 1.0)
        elig[0, 0] = False
        ic, n = fr.rank_ic(f, fwd, elig, min_obs=3)
        self.assertTrue(np.isnan(ic[0]))
        self.assertEqual(n[0], 2)

    def test_constant_factor_gives_nan_not_a_crash(self):
        f = np.ones((3, 8))
        ic, n = fr.rank_ic(f, np.random.default_rng(0).normal(size=(3, 8)))
        self.assertTrue(np.isnan(ic).all())
        np.testing.assert_array_equal(n, 8)

    def test_min_obs_and_shape_validation(self):
        with self.assertRaises(ValueError):
            fr.rank_ic(np.ones((2, 3)), np.ones((2, 4)))
        with self.assertRaises(ValueError):
            fr.rank_ic(np.ones((2, 3)), np.ones((2, 3)), min_obs=1)


class DecayTests(unittest.TestCase):
    def test_h_day_target_is_the_window_sum_and_gaps_void_it(self):
        f = np.tile(np.arange(6.0), (6, 1))
        rng = np.random.default_rng(3)
        fwd = f * 0.01 + rng.normal(scale=1e-4, size=(6, 6))
        fwd[2, 0] = np.nan
        out = fr.ic_decay(f, fwd, horizons=(1, 3), lag=1)
        self.assertEqual(out[1]["days"], 6)
        # column 0 voided on windows covering row 2; other 5 columns keep every window
        self.assertEqual(out[3]["days"], 4)
        self.assertGreater(out[3]["mean_ic"], 0.99)

    def test_horizon_longer_than_panel_is_all_nan(self):
        f = np.ones((3, 6))
        out = fr.ic_decay(f, np.zeros((3, 6)), horizons=(5,))
        self.assertEqual(out[5]["days"], 0)


class QuantileTests(unittest.TestCase):
    def test_monotone_factor_gives_monotone_quantile_means(self):
        rng = np.random.default_rng(7)
        f = rng.normal(size=(30, 40))
        fwd = f * 0.02 + rng.normal(scale=0.001, size=(30, 40))
        means, counts = fr.quantile_returns(f, fwd, q=5)
        m = means.mean(axis=0)
        self.assertTrue((np.diff(m) > 0).all())
        np.testing.assert_array_equal(counts, 8)
        spread = fr.quantile_spread(means)
        self.assertGreater(spread["mean_spread"], 0)
        self.assertGreater(spread["nw_t"], 2)

    def test_sparse_days_are_nan_not_partial_books(self):
        f = np.array([[1.0, 2.0, np.nan, np.nan, np.nan]])
        means, counts = fr.quantile_returns(f, f * 0.01, q=5)
        self.assertTrue(np.isnan(means).all())
        np.testing.assert_array_equal(counts, 0)

    def test_ties_do_not_straddle_buckets_silently(self):
        f = np.zeros((1, 10))
        fwd = np.arange(10.0).reshape(1, 10)
        means, counts = fr.quantile_returns(f, fwd, q=5)
        np.testing.assert_array_equal(counts, 2)  # ordinal ranks split ties deterministically

    def test_indivisible_n_puts_remainder_in_the_lowest_buckets(self):
        rng = np.random.default_rng(42)
        f = rng.normal(size=(1, 23))
        fwd = rng.normal(size=(1, 23))
        _, counts = fr.quantile_returns(f, fwd, q=5)
        np.testing.assert_array_equal(counts[0], [5, 5, 4, 5, 4])

    def test_divisible_n_matches_pandas_qcut(self):
        rng = np.random.default_rng(5)
        f = rng.normal(size=(4, 25))
        fwd = rng.normal(scale=0.02, size=(4, 25))
        means, _ = fr.quantile_returns(f, fwd, q=5)
        for i in range(4):
            d = pd.DataFrame({"f": f[i], "r": fwd[i]})
            d["q"] = pd.qcut(d["f"].rank(method="first"), 5, labels=False)
            np.testing.assert_allclose(means[i], d.groupby("q")["r"].mean().to_numpy(), atol=1e-12)


class BookTests(unittest.TestCase):
    def test_ls_weights_are_dollar_neutral_and_long_book_gross_one(self):
        f = np.tile(np.arange(10.0), (3, 1))
        w = fr.book_weights(f, q=5)
        np.testing.assert_allclose(w.sum(axis=1), 0.0)
        np.testing.assert_allclose(np.where(w > 0, w, 0).sum(axis=1), 1.0)
        np.testing.assert_allclose(-np.where(w < 0, w, 0).sum(axis=1), 1.0)
        wl = fr.book_weights(f, q=5, mode="long")
        np.testing.assert_allclose(wl.sum(axis=1), 1.0)
        self.assertTrue((wl >= 0).all())

    def test_turnover_counts_entry_and_full_replacement(self):
        w = np.zeros((3, 4))
        w[0, 0], w[0, 1] = 0.5, -0.5
        w[1, 2], w[1, 3] = 0.5, -0.5
        w[2] = w[1]
        np.testing.assert_allclose(fr.turnover(w), [0.5, 1.0, 0.0])

    def test_costs_charge_both_legs_and_scale_linearly(self):
        f = np.tile(np.arange(10.0), (5, 1))
        w = fr.book_weights(f, q=5)
        gross = fr.gross_book(w, f * 0.0)  # zero returns: net is pure cost
        net1 = fr.apply_costs(gross, w, 0.001)
        net3 = fr.apply_costs(gross, w, 0.003)
        np.testing.assert_allclose(net1, -fr.turnover(w) * 0.001)
        np.testing.assert_allclose(net3, 3 * net1)
        with self.assertRaises(ValueError):
            fr.apply_costs(gross, w, -0.1)

    def test_held_name_without_price_voids_the_day(self):
        w = np.array([[0.5, -0.5]])
        fwd = np.array([[0.01, np.nan]])
        self.assertTrue(np.isnan(fr.gross_book(w, fwd))[0])
        w0 = np.array([[0.0, 0.0]])
        self.assertEqual(fr.gross_book(w0, fwd)[0], 0.0)


class ReportTests(unittest.TestCase):
    def test_predictive_factor_report_is_positive_and_costs_hurt(self):
        rng = np.random.default_rng(11)
        f = rng.normal(size=(250, 30))
        fwd = f * 0.01 + rng.normal(scale=0.002, size=(250, 30))
        rep = fr.factor_report(f, fwd, cost_per_side=0.001, horizons=(1, 7), lag=5)
        self.assertGreater(rep["ic"]["mean_ic"], 0.5)
        self.assertGreater(rep["book"]["net"]["1"]["mean_bp_day"], 0)
        self.assertGreater(rep["book"]["net"]["1"]["mean_bp_day"],
                           rep["book"]["net"]["3"]["mean_bp_day"])
        self.assertEqual(rep["coverage"]["days_with_ic"], 250)
        self.assertIn(7, rep["ic_decay"])

    def test_noise_factor_report_is_near_zero_ic(self):
        rng = np.random.default_rng(12)
        f = rng.normal(size=(250, 30))
        fwd = rng.normal(scale=0.02, size=(250, 30))
        rep = fr.factor_report(f, fwd, horizons=(1,), lag=5)
        self.assertLess(abs(rep["ic"]["mean_ic"]), 0.1)


if __name__ == "__main__":
    unittest.main()
