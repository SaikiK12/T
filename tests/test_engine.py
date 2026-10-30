import unittest

import numpy as np

from lab import engine, stats
from lab.engine import Rule

T, S = 48, 3
C = 0.001


def toy(on_rows=range(5, 10), sym=0, ret=0.01, n_views=2):
    bins = np.zeros((n_views, T, S), np.int8)
    for r in on_rows:
        bins[0, r, sym] = 1
    rets = np.zeros((T, S), np.float32)
    rets[:, sym] = ret
    return bins, rets, np.ones((T, S), bool), np.full((T, S), C, np.float32)


def run(bins, rets, elig, cmat, rule, **kw):
    return engine.run_rules(bins, rets, elig, cmat, [rule], 0, T, **kw)[0]


def long_rule(**kw):
    base = dict(view=(0,), lo=(1,), hi=(1,), need=1, direction=1, hold=1)
    base.update(kw)
    return Rule(**base)


class PnlTests(unittest.TestCase):
    def test_entry_hold_exit_and_costs_by_hand(self):
        out = run(*toy(), long_rule())
        w = 1 / 10                                   # one position, ten slots
        self.assertAlmostEqual(float(out[5, 0]), w * 0.01 - w * C, places=7)   # first bar earns and pays entry cost
        for r in (6, 7, 8, 9):
            self.assertAlmostEqual(float(out[r, 0]), w * 0.01, places=7)
        self.assertAlmostEqual(float(out[10, 0]), -w * C, places=7)             # exit costs, earns nothing
        self.assertAlmostEqual(float(out[:, 0].sum()), 5 * w * 0.01 - 2 * w * C, places=6)
        self.assertAlmostEqual(float(out[:, 1].sum()), 2 * w * C, places=7)
        self.assertEqual(float(out[7, 2]), 1.0)
        self.assertEqual(float(out[11, 2]), 0.0)

    def test_short_earns_the_opposite_sign(self):
        out = run(*toy(ret=-0.01), long_rule(direction=-1))
        self.assertGreater(float(out[:, 0].sum()), 0.0)
        self.assertAlmostEqual(float(out[6, 0]), 0.1 * 0.01, places=7)

    def test_minimum_hold_keeps_the_position_after_the_signal_stops(self):
        out = run(*toy(on_rows=(5, 6)), long_rule(hold=4))
        self.assertEqual([float(out[r, 2]) for r in range(4, 11)], [0, 1, 1, 1, 1, 0, 0])   # rows 5..8

    def test_two_conditions_and_versus_or(self):
        bins, rets, elig, cm = toy(on_rows=range(5, 9), n_views=2)
        bins[1, 7:12, 0] = 1                          # second condition true on rows 7..11
        both = dict(view=(0, 1), lo=(1, 1), hi=(1, 1), direction=1, hold=1)
        and_ = run(bins, rets, elig, cm, Rule(need=2, **both))
        or_ = run(bins, rets, elig, cm, Rule(need=1, **both))
        self.assertEqual([int(and_[r, 2]) for r in range(4, 13)], [0, 0, 0, 1, 1, 0, 0, 0, 0])   # rows 7 and 8 only
        self.assertEqual([int(or_[r, 2]) for r in range(4, 13)], [0, 1, 1, 1, 1, 1, 1, 1, 0])    # rows 5..11

    def test_ineligible_symbol_cannot_enter_and_is_forced_out(self):
        bins, rets, elig, cm = toy()
        elig[7:, 0] = False
        out = run(bins, rets, elig, cm, long_rule())
        self.assertEqual([int(out[r, 2]) for r in range(5, 10)], [1, 1, 0, 0, 0])
        bins2, rets2, elig2, cm2 = toy()
        elig2[:, 0] = False
        self.assertEqual(float(run(bins2, rets2, elig2, cm2, long_rule())[:, 2].sum()), 0.0)

    def test_weights_shrink_when_more_positions_than_slots(self):
        bins = np.ones((1, T, 12), np.int8)
        rets = np.full((T, 12), 0.01, np.float32)
        out = engine.run_rules(bins, rets, np.ones((T, 12), bool), np.zeros((T, 12), np.float32),
                               [long_rule()], 0, T, slots=10)[0]
        self.assertAlmostEqual(float(out[3, 0]), 0.01, places=6)     # twelve positions at 1/12: gross exposure stays 1

    def test_cost_multiplier_scales_only_costs(self):
        base = engine.run_rules(*toy(), [long_rule()], 0, T, cmult=1.0)[0]
        triple = engine.run_rules(*toy(), [long_rule()], 0, T, cmult=3.0)[0]
        self.assertAlmostEqual(float(triple[:, 1].sum()), 3 * float(base[:, 1].sum()), places=7)
        self.assertAlmostEqual(float((base[:, 0] + base[:, 1]).sum()), float((triple[:, 0] + triple[:, 1]).sum()), places=6)


class NoLookAheadTests(unittest.TestCase):
    def test_future_returns_and_signals_cannot_change_the_past(self):
        rng = np.random.default_rng(0)
        bins = rng.integers(-1, 6, (3, T, S)).astype(np.int8)
        rets = rng.normal(0, 0.01, (T, S)).astype(np.float32)
        elig, cm = np.ones((T, S), bool), np.full((T, S), C, np.float32)
        rule = Rule(view=(0, 1, 2), lo=(2, 0, 1), hi=(4, 3, 5), need=2, direction=1, hold=2)
        base = run(bins, rets, elig, cm, rule)
        r2 = rets.copy()
        r2[20:] = rng.normal(0, 0.05, (T - 20, S))
        np.testing.assert_array_equal(base[:20], run(bins, r2, elig, cm, rule)[:20])
        b2 = bins.copy()
        b2[:, 25:] = rng.integers(-1, 6, (3, T - 25, S))
        np.testing.assert_array_equal(base[:25], run(b2, rets, elig, cm, rule)[:25])


class SparseKernelTests(unittest.TestCase):
    def test_sparse_kernel_matches_the_dense_reference(self):
        rng = np.random.default_rng(0)
        V, T, S = 5, 1500, 60
        bins = rng.integers(-1, 5, (V, T, S)).astype(np.int8)
        ret = (rng.standard_normal((T, S)) * 0.01).astype(np.float32)
        ret[rng.random((T, S)) < 0.01] = np.nan
        elig = rng.random((T, S)) < 0.2
        cmat = rng.uniform(0.0005, 0.002, (T, S)).astype(np.float32)
        rules = [Rule((0, 1), (0, 2), (1, 4), n, d, h) for n in (1, 2) for d in (1, -1) for h in (1, 4, 24)]
        a = engine.run_rules(bins, ret, elig, cmat, rules, 50, 1450, slots=7, dense=True)
        b = engine.run_rules(bins, ret, elig, cmat, rules, 50, 1450, slots=7)
        np.testing.assert_allclose(a, b, atol=1e-6)


class ReturnsAndStats(unittest.TestCase):
    def test_forward_returns_charge_funding_at_the_next_bar(self):
        close = np.array([[100.0], [101.0], [102.0], [103.0]], np.float32)
        ev = np.array([[np.nan], [np.nan], [0.001], [np.nan]], np.float32)   # settles on bar 2
        ret = engine.forward_returns(close, ev)
        self.assertAlmostEqual(float(ret[0, 0]), 0.01, places=6)
        self.assertAlmostEqual(float(ret[1, 0]), 102 / 101 - 1 - 0.001, places=6)   # a long held into bar 2 pays
        self.assertTrue(np.isnan(ret[3, 0]))

    def test_cost_matrix_tiers(self):
        rank = np.array([[1, 20, 21, 50, 51, 100, 101, np.nan]], np.float32)
        c = engine.cost_matrix(rank)[0]
        np.testing.assert_allclose(c, [6e-4, 6e-4, 8e-4, 8e-4, 12e-4, 12e-4, 20e-4, 20e-4], rtol=1e-6)

    def test_numba_newey_west_matches_the_reference(self):
        rng = np.random.default_rng(5)
        x = np.convolve(rng.normal(0.002, 0.01, 400), np.ones(3) / 3, mode="valid")
        for lag in (0, 2, 5):
            self.assertAlmostEqual(engine.nw_t(x, lag), stats.newey_west_t(x, lag)[2], places=9)

    def test_era_table_splits_days(self):
        out = np.zeros((2, 24 * 40, 3), np.float32)
        out[0, :, 0] = 0.001 / 24
        mean, tst = engine.era_table(out, 0, 24 * 40, edges=[10, 25])
        self.assertEqual(mean.shape, (2, 3))
        np.testing.assert_allclose(mean[0], 0.001, rtol=1e-5)
        self.assertEqual(float(mean[1].sum()), 0.0)


if __name__ == "__main__":
    unittest.main()
