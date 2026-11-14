import math
import unittest

import numpy as np

from lab import sequential as seq


class BetTests(unittest.TestCase):
    def test_bet_is_positive_and_below_the_positivity_boundary(self):
        for t in (1, 2, 10, 100, 1000):
            lam = seq.hedged_bet(0.006, t, -0.03, 0.03, 0.05)
            self.assertGreater(lam, 0.0)
            self.assertLess(lam, 1.0 / 0.03)

    def test_bet_shrinks_with_the_sample_and_a_tighter_bound_permits_a_larger_bet(self):
        # a tighter bound raises the 1/|lo| cap, so it can never force a smaller lambda
        wide = seq.hedged_bet(0.006, 10, -0.10, 0.10, 0.05)
        tight = seq.hedged_bet(0.006, 10, -0.01, 0.01, 0.05)
        self.assertGreaterEqual(tight, wide)
        self.assertLess(seq.hedged_bet(0.006, 100, -0.03, 0.03, 0.05),
                        seq.hedged_bet(0.006, 1, -0.03, 0.03, 0.05))

    def test_the_e_value_is_invariant_to_the_return_scale(self):
        # lambda scales as 1/scale, so lambda * r is invariant and the capital path is identical
        rng = np.random.default_rng(3)
        r = rng.normal(0.0008, 0.006, 200)
        base = seq.e_process(r, -0.03, 0.03)["e_value"]
        scaled = seq.e_process(r * 10.0, -0.30, 0.30)["e_value"]
        self.assertAlmostEqual(base, scaled, places=6)


class EProcessTests(unittest.TestCase):
    def test_a_positive_constant_stream_rejects_and_a_negative_one_does_not(self):
        up = seq.e_process([0.01] * 50, -0.03, 0.03, alpha=0.05)
        self.assertTrue(up["reject"])
        self.assertLess(up["p_anytime"], 0.05)
        down = seq.e_process([-0.01] * 50, -0.03, 0.03, alpha=0.05)
        self.assertFalse(down["reject"])
        self.assertEqual(down["e_value"], 1.0)

    def test_the_running_max_is_the_e_value_and_never_falls_below_one(self):
        # K_t is a supermartingale, so the raw path may dip below 1; the running max is the e-value
        rng = np.random.default_rng(7)
        r = rng.normal(0.0005, 0.006, 200)
        out = seq.e_process(r, -0.03, 0.03)
        self.assertGreaterEqual(float(out["running_max"].min()), 1.0 - 1e-12)
        self.assertTrue((np.diff(out["running_max"]) >= -1e-12).all())   # nondecreasing
        self.assertAlmostEqual(out["e_value"], float(out["running_max"].max()), places=9)

    def test_nan_days_are_skipped_not_zero_filled(self):
        r = [0.002, float("nan"), 0.002, float("nan"), 0.002]
        out = seq.e_process(r, -0.03, 0.03)
        self.assertEqual(out["n_observed"], 3)
        self.assertEqual(out["n_skipped"], 2)
        only_observed = seq.e_process([0.002, 0.002, 0.002], -0.03, 0.03)
        self.assertAlmostEqual(out["e_value"], only_observed["e_value"], places=12)

    def test_empty_and_all_nan_series_are_inconclusive_not_rejections(self):
        for r in ([], [float("nan")] * 5):
            out = seq.e_process(r, -0.03, 0.03)
            self.assertFalse(out["reject"])
            self.assertEqual(out["e_value"], 1.0)
            self.assertEqual(out["p_anytime"], 1.0)

    def test_an_out_of_bounds_observation_is_an_error_not_a_silent_clip(self):
        with self.assertRaises(ValueError):
            seq.e_process([0.0, 0.05], -0.03, 0.03)

    def test_bad_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            seq.e_process([0.0], 0.01, 0.02)          # does not straddle zero
        with self.assertRaises(ValueError):
            seq.e_process([0.0], -0.03, 0.03, alpha=0.0)
        with self.assertRaises(ValueError):
            seq.e_process([0.0], -0.03, 0.03, alpha=1.0)

    def test_the_rejection_threshold_is_one_over_alpha(self):
        out = seq.e_process([0.01] * 50, -0.03, 0.03, alpha=0.10)
        self.assertAlmostEqual(out["threshold"], 10.0, places=12)
        self.assertEqual(out["reject"], out["e_value"] >= 10.0)


class SizeAndPowerTests(unittest.TestCase):
    """The whole point of the monitor: valid at any stopping time, with usable power."""

    def test_size_is_at_most_alpha_under_a_zero_mean_stream(self):
        rng = np.random.default_rng(20261114)
        alpha, seeds, n = 0.05, 300, 365
        false = 0
        for _ in range(seeds):
            r = np.clip(rng.normal(0.0, 0.006, n), -0.03, 0.03)
            false += seq.e_process(r, -0.03, 0.03, alpha=alpha)["reject"]
        self.assertLessEqual(false / seeds, alpha)

    def test_a_negative_mean_never_rejects(self):
        rng = np.random.default_rng(11)
        false = 0
        for _ in range(150):
            r = np.clip(rng.normal(-0.0020, 0.006, 365), -0.03, 0.03)
            false += seq.e_process(r, -0.03, 0.03)["reject"]
        self.assertEqual(false, 0)

    def test_a_clear_positive_mean_is_detected_most_of_the_time(self):
        rng = np.random.default_rng(12)
        hits = 0
        for _ in range(200):
            r = np.clip(rng.normal(0.0015, 0.006, 365), -0.03, 0.03)
            hits += seq.e_process(r, -0.03, 0.03)["reject"]
        self.assertGreater(hits / 200, 0.9)

    def test_power_grows_with_the_sample(self):
        rng = np.random.default_rng(13)
        def detect(n, mu):
            return sum(seq.e_process(np.clip(rng.normal(mu, 0.006, n), -0.03, 0.03),
                                     -0.03, 0.03)["reject"] for _ in range(200)) / 200
        self.assertLess(detect(90, 0.0015), detect(365, 0.0015))

    def test_first_reject_index_is_the_first_breach_of_the_threshold(self):
        rng = np.random.default_rng(14)
        r = np.clip(rng.normal(0.0020, 0.006, 200), -0.03, 0.03)
        out = seq.e_process(r, -0.03, 0.03)
        if out["first_reject_index"] is not None:
            i = out["first_reject_index"]
            self.assertGreaterEqual(out["running_max"][i], out["threshold"])
            if i > 0:
                self.assertLess(out["running_max"][i - 1], out["threshold"])


class BlockAndMixtureTests(unittest.TestCase):
    def test_block_means_drops_a_trailing_partial_block(self):
        m, _, _ = seq.block_means([1.0, 2.0, 3.0, 4.0, 5.0], 2)
        self.assertEqual(list(m), [1.5, 3.5])           # the trailing 5.0 is dropped, never padded

    def test_block_means_of_empty_and_short_series(self):
        m, _, _ = seq.block_means([], 3)
        self.assertEqual(m.size, 0)
        m, _, _ = seq.block_means([1.0, 2.0], 3)
        self.assertEqual(m.size, 0)

    def test_mixture_process_is_a_supermartingale_and_rejects_a_positive_stream(self):
        out = seq.mixture_e_process([0.01] * 60, -0.03, 0.03)
        self.assertTrue(out["reject"])
        self.assertGreaterEqual(float(out["running_max"].min()), 1.0 - 1e-9)
        flat = seq.mixture_e_process([0.0] * 60, -0.03, 0.03)
        self.assertFalse(flat["reject"])

    def test_mixture_has_size_at_most_alpha_on_a_zero_mean_stream(self):
        rng = np.random.default_rng(21)
        false = 0
        for _ in range(200):
            r = np.clip(rng.normal(0.0, 0.006, 365), -0.03, 0.03)
            false += seq.mixture_e_process(r, -0.03, 0.03)["reject"]
        self.assertLessEqual(false / 200, 0.05)

    def test_block_mode_controls_size_where_the_raw_bet_inflates(self):
        # under strong autocorrelation the raw daily martingale is inexact; block means restore it
        rng = np.random.default_rng(22)
        phi, seeds, n = 0.7, 300, 365

        def size(mode, block=1):
            false = 0
            for _ in range(seeds):
                e = rng.normal(0.0, 0.01, n)
                r = np.empty(n)
                r[0] = e[0]
                for i in range(1, n):
                    r[i] = phi * r[i - 1] + e[i]
                r = np.clip(r, -0.30, 0.30)
                false += seq.lane_monitor(r, -0.30, 0.30, mode=mode, block=block)["reject"]
            return false / seeds
        self.assertLessEqual(size("block", 10), 0.05)
        self.assertGreater(size("bet"), 0.05)          # the raw mode is the one that fails here

    def test_lane_monitor_routes_every_mode_and_rejects_a_bad_mode(self):
        r = [0.01] * 200
        for mode in ("bet", "block", "mixture"):
            out = seq.lane_monitor(r, -0.03, 0.03, mode=mode, block=5)
            self.assertEqual(out["mode"], mode)
            self.assertTrue(out["reject"])
        self.assertEqual(seq.lane_monitor(r, -0.03, 0.03, mode="block", block=5)["n_blocks"], 40)
        with self.assertRaises(ValueError):
            seq.lane_monitor(r, -0.03, 0.03, mode="nope")


class MinDetectableMeanTests(unittest.TestCase):
    def test_mde_falls_with_more_days_and_lies_inside_the_bound(self):
        m = [seq.min_detectable_mean(n, -0.03, 0.03) for n in (60, 180, 365, 500)]
        self.assertTrue(all(m[i] > m[i + 1] for i in range(len(m) - 1)))
        self.assertTrue(all(0.0 < v < 0.03 for v in m))

    def test_mde_rejects_bad_parameters(self):
        with self.assertRaises(ValueError):
            seq.min_detectable_mean(0, -0.03, 0.03)
        with self.assertRaises(ValueError):
            seq.min_detectable_mean(100, -0.03, 0.03, power=1.0)


if __name__ == "__main__":
    unittest.main()
