"""Offline R230 tests: causal ranks, exact costed accounts and family selection."""
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import run_weekly_rotation as r
from scripts import run_slow_trend as ref


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.close = np.full((20, 6), 100.)
        self.targets = np.zeros_like(self.close)
        self.targets[:, 0] = 1
        self.days = np.zeros(20, dtype=bool)

    def test_exact_grid_and_unique_identity(self):
        self.assertEqual(len(r.GRID), 96)
        self.assertEqual(len(set(map(r.identity, r.GRID))), 96)

    def test_stable_rank_and_directions(self):
        close = np.exp(np.arange(80)[:, None]*np.array([.001, .002, .003, .004, .005, .006]))
        mom = r.rank_targets(close, 7, 1, 2, False)
        rev = r.rank_targets(close, 7, -1, 2, False)
        np.testing.assert_array_equal(mom[-1], [0, 0, 0, 0, .5, .5])
        np.testing.assert_array_equal(rev[-1], [.5, .5, 0, 0, 0, 0])
        tie = r.rank_targets(np.ones((80, 6)), 7, 1, 2, False)
        np.testing.assert_array_equal(tie[-1], [.5, .5, 0, 0, 0, 0])

    def test_gate_and_warmup(self):
        close = np.exp(np.arange(80)[:, None]*np.full((1, 6), -.001))
        self.assertTrue(np.all(r.rank_targets(close, 7, 1, 1, True) == 0))
        ungated = r.rank_targets(close, 7, 1, 1, False)
        self.assertTrue(np.all(ungated[:7] == 0))
        self.assertTrue(np.all(ungated[7:].sum(axis=1) == 1))

    def test_rank_prefix_invariance(self):
        close = np.exp(np.random.default_rng(3).normal(0, .01, (100, 6)).cumsum(axis=0))
        for config in r.GRID:
            h, sign, k, gate, _ = config
            full = r.rank_targets(close, h, sign, k, gate)
            short = r.rank_targets(close[:80], h, sign, k, gate)
            np.testing.assert_array_equal(full[:80], short)

    def test_full_entry_final_exit_cost(self):
        rows = r.account(self.close, self.targets, self.days, 2, 10, .0012)
        self.assertAlmostEqual(rows[-1, 6], (1-.0012)/(1+.0012))
        np.testing.assert_allclose(rows[:, 0], rows[:, 1]-rows[:, 2], atol=1e-14)
        self.assertAlmostEqual(rows[0, 5], 1.)
        self.assertAlmostEqual(rows[-1, 7], rows[-1, 6])

    def test_partial_entry_cost(self):
        rows = r.account(self.close, self.targets, self.days, 2, 10, .0012, .5)
        self.assertAlmostEqual(rows[-1, 6], (1-.0006)/(1+.0006))
        self.assertAlmostEqual(rows[0, 5], .5)

    def test_one_full_bar_delay(self):
        a = self.targets.copy()
        b = self.targets.copy()
        a[1:] = 0
        b[2:] = 0
        left = r.account(self.close, a, self.days, 2, 3, 0)
        right = r.account(self.close, b, self.days, 2, 3, 0)
        np.testing.assert_array_equal(left, right)

    def test_fresh_split_initializes_before_regular_schedule(self):
        self.assertFalse(self.days[4])
        rows = r.account(self.close, self.targets, self.days, 4, 10, 0)
        self.assertEqual(rows[0, 5], 1.)

    def test_nonrebalance_days_keep_units(self):
        self.close[3:, 0] *= 2
        rows = r.account(self.close, self.targets*.5, self.days, 2, 10, 0)
        np.testing.assert_allclose(rows[:, 8:], np.broadcast_to(rows[0, 8:], (8, 6)))
        self.assertGreater(rows[2, 5], rows[0, 5])

    def test_full_daily_account_matches_frozen_reference(self):
        rng = np.random.default_rng(5)
        close = np.exp(rng.normal(0, .02, (25, 6)).cumsum(axis=0))
        targets = rng.uniform(size=(25, 6)); targets /= targets.sum(axis=1)[:, None]*1.1
        dates = ref.date_range('2022-01-01', '2022-01-26')
        for tier in (1, 2, 3):
            rows = r.account(close, targets, np.ones(25, bool), 2, 25, .0012*tier)
            oracle = ref.simulate(close, dates, 2, 25, .0012*tier, targets)
            np.testing.assert_allclose(rows[:, 0], [x['net'] for x in oracle], atol=2e-14)
            np.testing.assert_allclose(rows[:, 6], [x['nav'] for x in oracle], atol=2e-14)

    def test_partial_adjustment_uses_actual_drifted_weights(self):
        close = self.close.copy(); close[3:, 0] = 200
        days = self.days.copy(); days[4] = True
        rows = r.account(close, self.targets*.6, days, 2, 10, .0036, .5)
        units, cash = np.zeros(6), 1.
        for i in range(2, 5):
            prices = close[i-1]
            if i == 2 or days[i]:
                before = cash+units@prices
                weights = .5*(units*prices/before)+.5*self.targets[i-2]*.6
                units, cash, _, _ = ref.rebalance(units, cash, prices, weights, .0036)
            np.testing.assert_allclose(rows[i-2, 8:], units, atol=2e-14)

    def test_invalid_targets_fail(self):
        invalid = self.targets*2
        with self.assertRaises(ref.ContractError):
            r.account(self.close, invalid, self.days, 2, 10, .0012)

    def test_training_scales_never_leverage(self):
        self.assertEqual(r.risk_scales([-1, 1], [-2, 2]), (1., .5))
        self.assertEqual(r.risk_scales([-2, 2], [-1, 1]), (.5, 1.))

    def test_selection_uses_discovery_and_fixed_ties(self):
        self.assertEqual(r.select_candidate([{'sharpe': 1}, {'sharpe': 1}, {'sharpe': 0}]), 0)
        self.assertEqual(r.select_candidate([{'sharpe': 1}, {'sharpe': 2}]), 1)

    def test_bootstrap_duplicate_column_preserves_max_p(self):
        x = np.random.default_rng(4).normal(.001, .01, (80, 1))
        a, aa = r.bootstrap_family(x, 0, 10, 100)
        b, bb = r.bootstrap_family(np.tile(x, (1, 5)), 0, 10, 100)
        self.assertEqual(a['family_max_p'], b['family_max_p'])
        np.testing.assert_allclose(aa, bb, atol=1e-13)

    def test_bootstrap_recentered_maxima_ignore_mean_offsets(self):
        x = np.random.default_rng(4).normal(0, .01, (80, 4))
        _, a = r.bootstrap_family(x, 0, 10, 100)
        _, b = r.bootstrap_family(x+.001, 0, 10, 100)
        np.testing.assert_allclose(a, b, atol=1e-13)

    def test_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(ref.ContractError):
                r.fresh_output(Path(path))
            r.fresh_output(Path(path)/'new')

    def test_undefined_validation_metric_is_inconclusive_not_type_error(self):
        candidate = {'sharpe': None, 'max_drawdown': .1}
        passive = {'sharpe': 1., 'max_drawdown': .1}
        with self.assertRaises(ref.ContractError):
            r.decision_checks(candidate, passive, 1., {'lower95': .01, 'family_max_p': .01})


if __name__ == '__main__':
    unittest.main()
