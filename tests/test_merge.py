import unittest

import numpy as np

from lab import atlas, engine, merge


class TradeTests(unittest.TestCase):
    def test_enter_hold_exit_and_costs_by_hand(self):
        T, S = 8, 1
        ret = np.full((T, S), 0.01, np.float32)
        elig = np.ones((T, S), bool)
        cmat = np.full((T, S), 0.001, np.float32)
        f = np.array([[0.0], [0.01], [0.01], [0.0], [0.0], [0.0], [0.0], [0.0]], np.float32)  # cost rt 0.002
        out = merge.trade(f, ret, elig, engine.eligible_index(elig), cmat, 0, T, k_in=1.0, k_out=0.0, slots=1,
                          min_hold=3, ls=False)
        held = out[:, 3] + out[:, 4]
        np.testing.assert_array_equal(held, [0, 1, 1, 1, 0, 0, 0, 0])   # enters at 1, kept 3 bars by min_hold
        self.assertAlmostEqual(out[1, 1], 0.001)                         # entry cost
        self.assertAlmostEqual(out[4, 1], 0.001)                         # exit cost
        self.assertAlmostEqual(out[:, 2].sum(), 0.03, places=6)
        self.assertAlmostEqual(out[:, 0].sum(), 0.028, places=6)

    def test_threshold_blocks_small_forecasts_and_short_side(self):
        T, S = 5, 2
        ret = np.tile(np.array([[0.01, -0.01]], np.float32), (T, 1))
        elig = np.ones((T, S), bool)
        cmat = np.full((T, S), 0.001, np.float32)
        f = np.tile(np.array([[0.001, -0.005]], np.float32), (T, 1))   # first below 1x cost, second above
        out = merge.trade(f, ret, elig, engine.eligible_index(elig), cmat, 0, T, k_in=1.0, slots=2, min_hold=1)
        self.assertTrue((out[:, 3] == 0).all() and (out[:, 4] == 1).all())
        self.assertGreater(out[:, 2].sum(), 0)                           # short a falling symbol earns


class ForecastTests(unittest.TestCase):
    def test_calibration_undoes_double_counting(self):
        rng = np.random.default_rng(0)
        T, S = 24 * 200, 30
        b = rng.integers(0, 4, (T, S)).astype(np.int8)
        bins = np.stack([b, b, rng.integers(0, 4, (T, S)).astype(np.int8)])   # view 1 duplicates view 0
        ret = (rng.standard_normal((T, S)) * 0.01 + 0.002 * (b == 3)).astype(np.float32)
        elig = np.ones((T, S), bool)
        index = engine.eligible_index(elig)
        tens = {"main": (bins, ["a", "b", "c"], np.zeros(3, bool))}
        F, X = atlas.forward(ret, elig, 0, T, (1,))
        tables = merge.cell_stats(tens, F, X, np.full((T, S), 0.0005, np.float32), index, 0, T, (1,))
        cells = merge.select(tables[(1, "excess")], 2, 3.0)
        self.assertEqual({(c[1], c[2]) for c in cells}, {(0, 3), (1, 3)})
        f = merge.forecast(tens, cells, [1, 2], index, 0, T, S)
        beta = merge.calibrate(f, X[0], elig)
        self.assertAlmostEqual(beta[0], 1.0, delta=0.15)
        self.assertAlmostEqual(beta[1], 0.5, delta=0.08)


class WalkForwardTests(unittest.TestCase):
    def run_toy(self, effect, seed):
        rng = np.random.default_rng(seed)
        T, S = 24 * 360, 30
        bins = rng.integers(0, 4, (3, T, S)).astype(np.int8)
        ret = (rng.standard_normal((T, S)) * 0.01).astype(np.float32)
        ret += effect * ((bins[0] == 3).astype(np.float32) - (bins[0] == 0))
        elig = np.ones((T, S), bool)
        cmat = np.full((T, S), 0.0002, np.float32)
        index = engine.eligible_index(elig)
        tens = {"main": (bins, ["a", "b", "c"], np.zeros(3, bool))}
        refits = list(range(24 * 120, T + 1, 24 * 30))
        fc, picks = merge.walk_forward(tens, ret, elig, cmat, index, refits, 100, 24, [4], [1, 3])
        f = fc[(4, "excess")][0]
        return merge.trade(f, ret, elig, index, cmat, refits[0], refits[-1], k_in=0.5, slots=10, min_hold=1), picks

    def test_planted_effect_is_traded_out_of_sample(self):
        out, picks = self.run_toy(0.002, 1)
        self.assertGreater(out[:, 0].sum(), 0.5)
        self.assertTrue(all(p[0][1] == 0 for p in picks[(4, "excess")]))

    def test_noise_loses_about_the_costs(self):
        out, _ = self.run_toy(0.0, 2)
        gross = out[:, 2].reshape(-1, 24).sum(1)
        self.assertLess(abs(gross.mean()) / (gross.std() / np.sqrt(len(gross))), 3.0)
        self.assertLessEqual(out[:, 0].sum(), out[:, 2].sum())


if __name__ == "__main__":
    unittest.main()


class EpisodeTests(unittest.TestCase):
    def test_a_persistent_condition_counts_once(self):
        T, S = 24 * 20, 2
        bins = np.ones((1, T, S), np.int8)
        bins[0, 100:130, 0] = 0                       # one 30-hour episode
        bins[0, 200:201, 1] = 0                       # one 1-hour episode
        bins[0, 300:302, 1] = 0                       # another, 2 hours
        ret = np.zeros((T, S), np.float32)
        elig = np.ones((T, S), bool)
        index = engine.eligible_index(elig)
        tens = {"main": (bins, ["v"], np.zeros(1, bool))}
        F, X = atlas.forward(ret, elig, 0, T, (1,))
        acc = atlas.run(bins, np.arange(1), F, X, np.zeros((T, S), np.float32), index, np.zeros((T, S), np.int8), 1,
                        0, T, elig=elig, episodes=True)
        self.assertEqual(int(acc["cnt"][0, 0].sum()), 3)          # bin 0: three entries
        self.assertEqual(int(acc["cnt"][1, 0].sum()), 5)          # bin 1: both start at t=0, then 1 + 2 re-entries

    def test_session_specific_means_are_traded(self):
        rng = np.random.default_rng(3)
        T, S = 24 * 360, 30
        bins = rng.integers(0, 4, (2, T, S)).astype(np.int8)
        session = (np.arange(T) % 24 >= 12).astype(np.int8)        # two "sessions" a day
        ret = (rng.standard_normal((T, S)) * 0.01).astype(np.float32)
        live = (bins[0] == 3) & (session[:, None] == 1)
        ret += 0.004 * live - 0.004 * ((bins[0] == 0) & (session[:, None] == 1))
        elig = np.ones((T, S), bool)
        cmat = np.full((T, S), 0.0002, np.float32)
        index = engine.eligible_index(elig)
        tens = {"main": (bins, ["a", "b"], np.zeros(2, bool))}
        refits = list(range(24 * 120, T + 1, 24 * 30))
        out = {}
        for name, kw in (("pooled", {}), ("session", {"session": session, "n_groups": 2})):
            fc, picks = merge.walk_forward_v2(tens, ret, elig, cmat, index, refits, 100, 24, [1], [2], min_episodes=20, **kw)
            o = merge.trade(fc[(1, "excess")][0], ret, elig, index, cmat, refits[0], refits[-1], k_in=1.0, slots=10,
                            min_hold=1)
            out[name] = o[:, 0].sum()
        self.assertGreater(out["session"], out["pooled"])
        self.assertGreater(out["session"], 0.5)
