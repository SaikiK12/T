"""Synthetic-only tests. Never load the project's spot cache or result arrays."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from scripts import run_mixed_signals as mixed


class MixedSignalTests(unittest.TestCase):
    def synthetic_prices(self, days=420):
        rng = np.random.default_rng(781254)
        increments = rng.normal(.0005, .015, (days, 6))
        increments[:, 0] = .0017
        return 100*np.exp(np.cumsum(increments, axis=0))

    def test_finite_grid_and_ids_have_exactly_thirty_six_members(self):
        self.assertEqual(len(mixed.GRID), 36)
        self.assertEqual(len(set(mixed.GRID)), 36)
        self.assertEqual(len({mixed.identity(config) for config in mixed.GRID}), 36)
        self.assertEqual(mixed.GRID[0], ('btc_ret28', .25, 'cash'))
        self.assertEqual(mixed.GRID[-1], ('btc_sma200', .75, 'reversal'))
        self.assertEqual(mixed.TREND_VARIANT, 'trend_plain')
        self.assertEqual(mixed.SEED, 20261020000+mixed.ROUND_ID)

    def test_regime_warmups_strict_ties_and_known_at_close(self):
        close = np.full((250, 6), 100.)
        for name, first in (('btc_ret28', 28), ('btc_ret56', 56), ('btc_sma200', 199)):
            bull, known = mixed.regime_state(close, name)
            self.assertFalse(bull.any())
            self.assertFalse(known[:first].any())
            self.assertTrue(known[first:].all())
            rising = close.copy()
            rising[:, 0] += np.arange(len(close))
            self.assertTrue(mixed.regime_state(rising, name)[0][first:].all())

    def test_bull_and_four_bear_templates_are_target_combinations(self):
        t = np.tile([.2, .1, 0, 0, 0, 0], (4, 1))
        m = np.tile([0, 1/3, 1/3, 1/3, 0, 0], (4, 1))
        r = np.tile([0, 0, 0, 1/3, 1/3, 1/3], (4, 1))
        components = {'trend': t, 'momentum28': m, 'reversal7': r}
        bull, known = np.array([True, False, True, False]), np.array([False, True, True, True])
        for p in mixed.PROPORTIONS:
            for bear, expected in (('cash', np.zeros(6)), ('trend', t[0]),
                                   ('half_trend_reversal', .5*t[0]+.5*r[0]), ('reversal', r[0])):
                with self.subTest(proportion=p, bear=bear):
                    out = mixed.mix_target(components, bull, known, p, bear)
                    np.testing.assert_array_equal(out[0], np.zeros(6))
                    np.testing.assert_allclose(out[2], p*t[2]+(1-p)*m[2])
                    np.testing.assert_allclose(out[[1, 3]], np.tile(expected, (2, 1)))
                    self.assertTrue((out >= 0).all())
                    self.assertTrue((out.sum(axis=1) <= 1+1e-12).all())

    def test_future_prices_cannot_change_past_components_or_mixed_targets(self):
        close = self.synthetic_prices()
        before_components, before = mixed.target_family(close)
        altered = close.copy()
        altered[350:] *= np.linspace(.25, 2, len(close)-350)[:, None]
        after_components, after = mixed.target_family(altered)
        for name in mixed.CONTROLS:
            np.testing.assert_array_equal(before_components[name][:350], after_components[name][:350])
        for left, right in zip(before, after):
            np.testing.assert_array_equal(left[:350], right[:350])
        np.testing.assert_array_equal(before_components['trend'],
                                     mixed.trend.trend_targets(close)['trend_plain'])

    def test_account_uses_a_full_bar_delay_and_charges_both_sides(self):
        close = np.full((4, 6), 100.)
        close[:, 0] = [100, 100, 110, 121]
        target = np.zeros_like(close)
        target[0, 0] = 1
        daily = np.ones(len(close), bool)
        for multiple in (1, 2, 3):
            cost = mixed.BASE_COST*multiple
            out = mixed.account(close, target, daily, 2, 4, multiple)
            self.assertAlmostEqual(out[0, 0], 1.1/(1+cost)-1, places=12)
            self.assertAlmostEqual(out[-1, 6], 1.1*(1-cost)/(1+cost), places=12)
            future = target.copy()
            future[1:, 0] = 1
            changed = mixed.account(close, future, daily, 2, 4, multiple)
            np.testing.assert_array_equal(out[0], changed[0])

    def test_flat_price_roundtrip_at_all_costs_matches_cash_arithmetic(self):
        close = np.full((8, 6), 100.)
        target = np.zeros_like(close)
        target[:, 0] = 1
        for multiple in (1, 2, 3):
            cost = mixed.BASE_COST*multiple
            out = mixed.account(close, target, np.ones(8, bool), 2, 8, multiple)
            self.assertAlmostEqual(out[-1, 6], (1-cost)/(1+cost), places=12)
            self.assertAlmostEqual(out[:, 3].sum(), 2*cost/(1+cost), places=12)
            self.assertAlmostEqual(out[-1, 7], out[-1, 6], places=12)

    def test_daily_rebalancing_uses_drifted_holdings(self):
        close = np.full((6, 6), 100.)
        close[:, 0] = [100, 100, 200, 100, 150, 120]
        target = np.zeros_like(close)
        target[:, :2] = .5
        daily = mixed.account(close, target, np.ones(6, bool), 2, 6, 1)
        hold_units = mixed.account(close, target, np.zeros(6, bool), 2, 6, 1)
        self.assertGreater(abs(daily[1, 8]-hold_units[1, 8]), 1e-6)
        self.assertGreater(daily[1, 3], 0)
        self.assertEqual(hold_units[1, 3], 0)

    def test_candidate_and_control_selection_use_their_separate_two_x_scores(self):
        close = np.full((30, 6), 100.)
        targets = [np.full_like(close, 0.) for _ in mixed.GRID]
        controls = {name: np.zeros_like(close) for name in mixed.CONTROLS}
        labels = {id(target): ('candidate', j) for j, target in enumerate(targets)}
        labels.update({id(target): ('control', j) for j, target in enumerate(controls.values())})

        def fake_account(close, target, schedule, start, end, multiple, scale=1.):
            kind, index = labels[id(target)]
            limit = 40 if kind == 'candidate' else 4
            mean = .001*((limit-index) if multiple == 1 else index)
            rows = np.zeros((end-start, 14))
            rows[:, 0] = mean+np.resize([-.01, .01], end-start)
            rows[:, 6] = np.cumprod(1+rows[:, 0])
            return rows

        daily = np.ones(30, bool)
        with mock.patch.object(mixed, 'account', side_effect=fake_account):
            choice = mixed.calibrate(close, targets, controls, daily,
                                     {name: daily for name in mixed.CONTROLS}, (2, 30))
        self.assertEqual(choice['selected_index'], 35)
        self.assertEqual(choice['control_index'], 3)

    def test_future_outcomes_cannot_change_discovery_choice_or_risk_scales(self):
        close = self.synthetic_prices()
        controls, targets = mixed.target_family(close)
        daily = np.ones(len(close), bool)
        schedules = {name: daily for name in mixed.CONTROLS}
        schedules['passive'] = np.arange(len(close)) % 30 == 0
        before = mixed.calibrate(close, targets, controls, daily, schedules, (220, 360))
        close[360:] *= 3
        controls, targets = mixed.target_family(close)
        after = mixed.calibrate(close, targets, controls, daily, schedules, (220, 360))
        self.assertEqual(before, after)

    def test_guard_failure_precedes_data_and_existing_outputs_stay_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'new'
            with mock.patch.object(mixed, 'verify_registration', side_effect=mixed.Error('digest')):
                with mock.patch.object(mixed.trend, 'load_prices') as reader:
                    with self.assertRaisesRegex(mixed.Error, 'digest'):
                        mixed.run(Path(directory), target)
                    reader.assert_not_called()
                    self.assertFalse(target.exists())
            sentinel = Path(directory)/'keep'
            sentinel.write_bytes(b'old')
            with self.assertRaisesRegex(mixed.Error, 'never overwrite'):
                mixed.run(Path(directory), Path(directory))
            self.assertEqual(sentinel.read_bytes(), b'old')

    def test_post_guard_data_failure_is_preserved_as_inconclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'fresh'
            with mock.patch.object(mixed, 'verify_registration', return_value={}):
                with mock.patch.object(mixed.trend, 'load_prices', side_effect=mixed.Error('gap')):
                    result = mixed.run(Path(directory), output)
            self.assertEqual(result['verdict'], 'INCONCLUSIVE')
            self.assertEqual(json.loads((output/'verdict.json').read_text())['reason'], 'gap')

    def test_deterministic_gzip_has_stable_bytes_and_preserves_daily_values(self):
        records = [{'date': 'synthetic', 'net': -.001, 'cost': .0036}]
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory)/'one.gz', Path(directory)/'two.gz'
            mixed.write_gzip_csv(first, records)
            mixed.write_gzip_csv(second, records)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertIn(b'-0.001', gzip.decompress(first.read_bytes()))
            with self.assertRaises(FileExistsError):
                mixed.write_gzip_csv(first, records)


if __name__ == '__main__':
    unittest.main()
