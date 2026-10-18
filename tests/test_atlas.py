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
