"""Interval and cost-path parity on invented returns, exits and overlapping slices."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from lab import engine, evaluation, research, slices


def fixture():
    rng = np.random.default_rng(81)
    T, S = 144, 7
    bins = rng.integers(-1, 4, (2, T, S), dtype=np.int8)
    elig = rng.random((T, S)) > .25
    elig[60:65, :] = False
    ret = rng.normal(0, .01, (T, S)).astype(np.float32)
    ret[70, 2] = np.nan
    cmat = rng.uniform(.0001, .002, (T, S)).astype(np.float32)
    rules = [engine.Rule((0,), (0,), (1,), 1, side, hold) for side in (-1, 1) for hold in (1, 9)]
    return bins, ret, elig, cmat, rules


class EvaluationParity(unittest.TestCase):
    def test_full_series_costs_and_active_counts_match_dense_and_sparse_reference(self):
        bins, ret, elig, cmat, rules = fixture()
        index = engine.eligible_index(elig)
        for dense in (False, True):
            for cmult in (1., 2., 3.):
                with self.subTest(dense=dense, cmult=cmult):
                    old = engine.run_rules(bins, ret, elig, cmat, rules, 48, 96,
                                           cmult=cmult, dense=dense, index=index)
                    new = evaluation.rule_window(bins, ret, elig, cmat, rules, 48, 96,
                                                  cmult=cmult, dense=dense, index=index)
                    np.testing.assert_array_equal(new, old[:, 48:96])
                    self.assertEqual(new.nbytes * 3, old.nbytes)

    def test_daily_api_and_final_holdout_price_guard_match_existing_api(self):
        bins, ret, elig, cmat, rules = fixture()
        universe = SimpleNamespace(ret=ret, elig=elig, cmat=cmat, index=engine.eligible_index(elig),
                                   holdout_row=120, p=SimpleNamespace(T=len(ret)))
        reference = research.eval_rules(universe, bins, rules, 24, 96, batch=2)
        result = evaluation.rule_days(universe, bins, rules, 24, 96, batch=2)
        for left, right in zip(reference, result):
            np.testing.assert_array_equal(left, right)
        with patch.object(engine, "run_rules", side_effect=AssertionError("no execution")):
            with self.assertRaises(PermissionError):
                evaluation.rule_days(universe, bins, rules, 24, 120)

    def test_fixed_book_reuses_positions_but_keeps_exact_paid_cost_kernel(self):
        rng = np.random.default_rng(9)
        T, S = 80, 3
        parts = [(rng.random((T, S)) > .6, 1), (rng.random((T, S)) > .8, -1)]
        ret, elig, cmat = rng.normal(0, .01, (T, S)), np.ones((T, S), bool), np.full((T, S), .0008)
        result = evaluation.fixed_book_costs(parts, ret, elig, cmat, hold=5, unit=.1, t0=10, t1=70)
        for multiple, actual in result.items():
            positions = sum(slices.positions(ind, 5, 10, 70, .1, side) for ind, side in parts)
            expected = slices.run(positions, ret, elig, cmat, 10, 70, cmult=multiple, missing="raise")
            for name in expected:
                np.testing.assert_array_equal(actual[name], expected[name])
        ret[11, 0] = np.nan
        parts = [(np.ones((T, S), bool), 1)]
        with self.assertRaises(ValueError):
            evaluation.fixed_book_costs(parts, ret, elig, cmat, hold=5, unit=.1, t0=10, t1=70)
