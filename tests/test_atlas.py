import unittest

import numpy as np
import pandas as pd

from lab import atlas, engine, sessions


def toy(T=24 * 300, S=40, V=6, effect=0.0003, seed=0):
    rng = np.random.default_rng(seed)
    bins = rng.integers(0, 5, (V, T, S)).astype(np.int8)
    bins[V - 1] = rng.integers(0, 3, T)[:, None]            # a view that depends on time only
    ret = (rng.standard_normal((T, S)) * 0.01).astype(np.float32)
    ret += effect * (bins[0] == 4)                           # planted: bin 4 of view 0 earns `effect` next bar
    elig = rng.random((T, S)) < 0.8
    cmat = np.full((T, S), 0.0006, np.float32)
    return bins, ret, elig, cmat


class ForwardTests(unittest.TestCase):
    def test_explicit_policy_rejects_interior_nonfinite_windows_and_recovers(self):
        for invalid in (np.nan, np.inf, -np.inf):
            for gap in range(3):
                with self.subTest(invalid=invalid, gap=gap):
                    ret = np.full((6, 2), 0.01, np.float64)
                    ret[gap, 0] = invalid
                    F, X = atlas.forward(ret, np.ones_like(ret, bool), 0, 6, horizons=(3,),
                                         missing="terminal_prefix")
                    self.assertTrue(np.isnan(F[0, 0, 0]))
                    self.assertTrue(np.isnan(X[0, 0, 0]))
                    invalid_windows = [start <= gap < start + 3 for start in range(4)]
                    np.testing.assert_array_equal(np.isnan(F[0, :4, 0]), invalid_windows)
                    np.testing.assert_array_equal(np.isnan(X[0, :4, 0]), invalid_windows)
                    self.assertAlmostEqual(float(F[0, 0, 1]), 0.03, places=7)
                    self.assertAlmostEqual(float(X[0, 0, 1]), 0.0, places=7)
                    np.testing.assert_allclose(F[0, 3], [0.03, 0.03])

    def test_horizon_longer_than_segment_has_no_complete_labels(self):
        ret = np.full((3, 2), 0.01)
        for policy in ("legacy", "terminal_prefix"):
            with self.subTest(policy=policy):
                F, X = atlas.forward(ret, np.ones_like(ret, bool), 0, 3, horizons=(6,), missing=policy)
                self.assertTrue(np.isnan(F).all())
                self.assertTrue(np.isnan(X).all())

    def test_nonpositive_horizon_is_rejected(self):
        ret = np.zeros((3, 1))
        for policy in ("legacy", "terminal_prefix"):
            for horizon in (0, -1):
                with self.subTest(horizon=horizon, policy=policy), self.assertRaises(ValueError):
                    atlas.forward(ret, np.ones_like(ret, bool), 0, 3, horizons=(horizon,), missing=policy)

    def test_default_preserves_legacy_interior_zero_and_terminal_prefix(self):
        ret = np.array([[.1], [np.nan], [.2], [.3], [np.nan]])
        elig = np.ones_like(ret, bool)
        default = atlas.forward(ret, elig, 0, 5, horizons=(2,))
        explicit = atlas.forward(ret, elig, 0, 5, horizons=(2,), missing="legacy")
        for a, b in zip(default, explicit):
            np.testing.assert_array_equal(a, b)
        np.testing.assert_allclose(default[0][0, :, 0], [.1, np.nan, .5, .3, np.nan])
        strict, _ = atlas.forward(ret, elig, 0, 5, horizons=(2,), missing="terminal_prefix")
        np.testing.assert_allclose(strict[0, :, 0], [np.nan, np.nan, .5, .3, np.nan])

    def test_terminal_loss_stays_in_the_target_and_eligible_benchmark(self):
        ret = np.column_stack(([.01, -.41, np.nan, np.nan, np.nan, np.nan],
                               np.full(6, .02), np.full(6, .04)))
        elig = np.ones_like(ret, bool)
        elig[0, 2] = False
        F, X = atlas.forward(ret, elig, 0, 6, horizons=(4,), missing="terminal_prefix")
        np.testing.assert_allclose(F[0, 0], [-.4, .08, .16], atol=1e-7)
        np.testing.assert_allclose(X[0, 0], [-.24, .24, .32], atol=1e-7)
        self.assertAlmostEqual(float(F[0, 1, 0]), -.41, places=7)
        self.assertTrue(np.isnan(F[0, 2:, 0]).all())

    def test_nan_at_window_end_is_interior_if_the_series_resumes_later(self):
        ret = np.array([[.1], [.2], [np.nan], [np.nan], [.3], [.1]])
        F, _ = atlas.forward(ret, np.ones_like(ret, bool), 0, 6, horizons=(3,), missing="terminal_prefix")
        self.assertTrue(np.isnan(F[0, 0, 0]))
        self.assertTrue(np.isnan(F[0, 1, 0]))

    def test_infinity_is_not_a_terminal_exit_observation(self):
        for invalid in (np.inf, -np.inf):
            ret = np.array([[.1], [invalid], [np.nan], [np.nan]])
            F, _ = atlas.forward(ret, np.ones_like(ret, bool), 0, 4, horizons=(3,), missing="terminal_prefix")
            self.assertTrue(np.isnan(F).all())

    def test_missing_start_and_all_missing_symbol_never_become_zero_labels(self):
        ret = np.column_stack(([np.nan, .1, .2, np.nan, np.nan], np.full(5, np.nan)))
        F, _ = atlas.forward(ret, np.ones_like(ret, bool), 0, 5, horizons=(3,), missing="terminal_prefix")
        self.assertTrue(np.isnan(F[0, 0]).all())
        self.assertAlmostEqual(float(F[0, 1, 0]), .3, places=7)
        self.assertTrue(np.isnan(F[0, :, 1]).all())

    def test_terminal_classification_cannot_read_beyond_the_selected_segment(self):
        ret = np.array([[.1], [.2], [np.nan], [np.nan], [.9]])
        first = atlas.forward(ret, np.ones_like(ret, bool), 0, 4, horizons=(3,), missing="terminal_prefix")
        ret[-1] = np.inf
        second = atlas.forward(ret, np.ones_like(ret, bool), 0, 4, horizons=(3,), missing="terminal_prefix")
        for a, b in zip(first, second):
            np.testing.assert_array_equal(a, b)
        np.testing.assert_allclose(first[0][0, :2, 0], [.3, .2])
        self.assertTrue(np.isnan(first[0][0, 2:, 0]).all())

    def test_unknown_missing_policy_is_rejected(self):
        ret = np.zeros((3, 1))
        with self.assertRaises(ValueError):
            atlas.forward(ret, np.ones_like(ret, bool), 0, 3, horizons=(1,), missing="silent_fill")

    def test_forward_uses_only_the_requested_segment(self):
        ret = np.array([[np.nan], [0.01], [0.02], [0.03], [np.inf]])
        F, _ = atlas.forward(ret, np.ones_like(ret, bool), 1, 4, horizons=(2,))
        np.testing.assert_allclose(F[0, :2, 0], [0.03, 0.05])
        self.assertTrue(np.isnan(F[0, 2, 0]))

    def test_forward_sums_next_bars_and_subtracts_the_eligible_mean(self):
        ret = np.array([[0.01, 0.0], [0.02, 0.02], [0.03, -0.01], [np.nan, 0.0]], np.float32)
        elig = np.ones((4, 2), bool)
        F, X = atlas.forward(ret, elig, 0, 4, horizons=(1, 2))
        np.testing.assert_allclose(F[1, 0], [0.03, 0.02])      # rows 0..1 for symbol 0 and 1
        np.testing.assert_allclose(F[1, 1], [0.05, 0.01])
        self.assertTrue(np.isnan(F[1, 3]).all())                 # the window would pass the end
        self.assertTrue(np.isnan(F[0, 3, 0]))                    # no return at the start
        np.testing.assert_allclose(X[1, 0], [0.005, -0.005], atol=1e-7)


class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bins, cls.ret, cls.elig, cls.cmat = toy()
        T = cls.ret.shape[0]
        cls.index = engine.eligible_index(cls.elig)
        F, X = atlas.forward(cls.ret, cls.elig, 0, T, horizons=(1, 4, 24))
        group = np.broadcast_to((np.arange(T) // 24 % 2).astype(np.int8)[:, None], cls.ret.shape).copy()
        cls.acc = atlas.run(cls.bins, np.arange(6), F, X, cls.cmat, cls.index, group, 2, 0, T)
        eras = np.array([0, 100, 200, 300])
        to = atlas._time_only(cls.bins, np.arange(6, dtype=np.int64), *cls.index, 0, T, 7)
        cls.df = atlas.stats(cls.acc, [f"v{i}" for i in range(6)], (1, 4, 24), eras, ("even", "odd"), to)

    def test_planted_bin_is_found_at_the_right_horizon(self):
        d = self.df[(self.df.group == "all") & (self.df.measure == "excess")]
        hit = d[(d.view == 0) & (d.bin == 4) & (d.h == 1)].iloc[0]
        self.assertGreater(hit.t, 5)
        self.assertAlmostEqual(hit.mean_bp, 3 * 0.8, delta=0.8)   # 3 bp minus the share it lifts the mean
        self.assertEqual(hit.eras_same_sign, 3)
        self.assertGreater(hit.breadth, 0.7)
        self.assertAlmostEqual(hit.cost_rt_bp, 12, places=3)

    def test_noise_bins_look_like_noise(self):
        d = self.df[(self.df.group == "all") & (self.df.measure == "excess") & (self.df.view.isin([1, 2, 3, 4]))]
        t = d[d.h == 1].t.values
        self.assertLess(np.abs(t).max(), 4.0)
        self.assertLess(abs(np.std(t) - 1), 0.35)

    def test_time_only_views_are_flagged_and_have_no_excess(self):
        d = self.df[(self.df.view == 5) & (self.df.group == "all") & (self.df.measure == "excess")]
        self.assertTrue(d.time_only.all())
        self.assertFalse(self.df[self.df.view == 0].time_only.any())
        self.assertLess(d.mean_bp.abs().max(), 1e-3)

    def test_groups_add_up_to_all(self):
        c = self.df[(self.df.measure == "raw") & (self.df.h == 4)].pivot_table(index=["view", "bin"], columns="group", values="cells")
        np.testing.assert_allclose(c["even"] + c["odd"], c["all"])

    def test_placebo_fdr_threshold(self):
        rng = np.random.default_rng(1)
        real = np.concatenate([rng.standard_normal(1000), rng.normal(8, 1, 20)])
        nulls = [rng.standard_normal(1020) for _ in range(3)]
        tau = atlas.threshold(real, nulls, 0.1)
        self.assertTrue(3.0 <= tau <= 6.0)
        self.assertEqual(atlas.threshold(rng.standard_normal(1000), nulls, 0.1), np.inf)


class LiftTests(unittest.TestCase):
    def test_context_that_switches_an_edge_on_is_found(self):
        T, S = 24 * 300, 40
        rng = np.random.default_rng(5)
        bins = rng.integers(0, 5, (4, T, S)).astype(np.int8)
        ctx = rng.integers(0, 3, T).astype(np.int8)                        # a time-only context with 3 codes
        ret = (rng.standard_normal((T, S)) * 0.01).astype(np.float32)
        ret += 0.0006 * ((bins[0] == 4) & (ctx == 1)[:, None])              # the edge exists only in code 1
        elig = np.ones((T, S), bool)
        F, X = atlas.forward(ret, elig, 0, T, horizons=(1,))
        group = np.ascontiguousarray(np.broadcast_to(ctx[:, None], (T, S)))
        acc = atlas.run(bins, np.arange(4), F, X, np.full((T, S), 0.0006, np.float32), engine.eligible_index(elig),
                        group, 3, 0, T)
        df = atlas.lift_stats(acc, ["a", "b", "c", "d"], (1,), np.array([0, 100, 200, 300]), ("c0", "c1", "c2"))
        d = df[df.measure == "excess"].set_index(["view", "bin", "code"])
        on, off = d.loc[(0, 4, 1)], d.loc[(0, 4, 0)]
        self.assertGreater(on.lift_t, 5)
        self.assertAlmostEqual(on.lift_bp, 6 * 0.8, delta=1.5)                # inside minus outside, net of dilution
        self.assertTrue(on.amplifies)
        self.assertLess(off.lift_t, -2)                                      # outside code 1 the edge is weaker
        self.assertAlmostEqual(on.share, 1 / 3, delta=0.03)
        self.assertEqual(on.lift_eras_same_sign, 3)
        noise = df[(df.measure == "excess") & df.view.isin([1, 2, 3])].lift_t.values
        self.assertLess(np.abs(noise).max(), 4.0)
        self.assertLess(abs(np.std(noise) - 1), 0.35)


class GroupTests(unittest.TestCase):
    def test_sessions_follow_new_york(self):
        def g(stamp):
            t = np.array([pd.Timestamp(stamp, tz="UTC").value // 10**6 - sessions.HOUR])
            return atlas.SESSION_NAMES[atlas.session_groups(t)[0]]
        self.assertEqual(g("2024-07-01 03:00"), "asia")
        self.assertEqual(g("2024-07-01 09:00"), "europe")
        self.assertEqual(g("2024-07-01 13:00"), "us_open")       # 09:00 EDT
        self.assertEqual(g("2024-01-08 12:00"), "europe")        # 07:00 EST
        self.assertEqual(g("2024-01-08 13:00"), "us_open")       # 08:00 EST, the data-release hour
        self.assertEqual(g("2024-07-01 18:00"), "us_afternoon")
        self.assertEqual(g("2024-07-01 22:00"), "us_evening")
        self.assertEqual(g("2024-07-06 14:00"), "weekend")

    def test_tiers_and_regimes(self):
        np.testing.assert_array_equal(atlas.tier_groups(np.array([1, 10, 11, 25, 26, 50, 51])), [0, 0, 1, 1, 2, 2, -1])
        up = np.exp(np.linspace(0, 1, 24 * 400))
        g = atlas.regime_groups(up)
        self.assertTrue((g[:720] == -1).all())
        self.assertTrue(set(np.unique(g[800:])) <= {0, 1})


if __name__ == "__main__":
    unittest.main()
