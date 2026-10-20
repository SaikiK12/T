"""Synthetic contracts only; no project outcome file is opened."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import run_optimizer as opt


class OptimizerTests(unittest.TestCase):
    def test_diagonal_covariance_has_known_analytic_solutions(self):
        cov = np.diag([1., 4., 9.])
        inverse_variance = np.array([36., 9., 4.])/49
        np.testing.assert_allclose(opt.minimum_variance(cov), inverse_variance)
        np.testing.assert_allclose(opt.hierarchical_risk(cov), inverse_variance)
        np.testing.assert_allclose(opt.equal_risk(cov), np.array([6., 3., 2.])/11, atol=1e-9)

    def test_minimum_variance_can_select_a_boundary_without_shorting(self):
        cov = np.array([[1., 1.5, 2.], [1.5, 4., 3.], [2., 3., 9.]])
        np.testing.assert_array_equal(opt.minimum_variance(cov), [1., 0., 0.])

    def test_equal_risk_solves_contributions_not_just_inverse_vol(self):
        cov = np.array([[1., 1.6, .3], [1.6, 4., .6], [.3, .6, 9.]])
        w = opt.equal_risk(cov)
        contributions = w*(cov @ w)
        np.testing.assert_allclose(contributions/contributions.sum(), np.ones(3)/3, atol=1e-10)
        self.assertGreater(np.max(np.abs(w-np.array([6, 3, 2])/11)), 1e-3)

    def test_hrp_nearest_pair_and_recursive_weights_match_a_hand_example(self):
        # Pair 0/1 has correlation .8; both outsider correlations are .1.
        cov = np.array([[1., 1.6, .3], [1.6, 4., .6], [.3, .6, 9.]])
        # Inverse-variance pair weights .8/.2 give pair variance 1.312.
        expected = np.array([.8*9, .2*9, 1.312])/(9+1.312)
        np.testing.assert_allclose(opt.hierarchical_risk(cov), expected)

    def test_methods_are_fully_invested_nonnegative_and_scale_invariant(self):
        rng = np.random.default_rng(67237)
        for _ in range(20):
            x = rng.normal(size=(3, 3))
            cov = x@x.T+np.eye(3)*.5
            for method in (opt.minimum_variance, opt.equal_risk, opt.hierarchical_risk):
                w = method(cov)
                self.assertTrue(np.isfinite(w).all())
                self.assertTrue((w >= 0).all())
                self.assertAlmostEqual(w.sum(), 1)
                np.testing.assert_allclose(method(cov*1e-7), w, atol=1e-9)

    def test_invalid_covariance_is_not_repaired_or_dropped(self):
        for cov in (np.ones((3, 3)), np.zeros((3, 3)), np.eye(2),
                    np.diag([1, -1, 1]), np.full((3, 3), np.nan),
                    np.array([[1, .2, 0], [.3, 1, 0], [0, 0, 1]])):
            for method in (opt.minimum_variance, opt.equal_risk, opt.hierarchical_risk):
                with self.subTest(cov=cov, method=method.__name__):
                    with self.assertRaises(opt.Error):
                        method(cov)

    def test_future_outcomes_cannot_change_weights_choice_or_scales(self):
        matrix = np.random.default_rng(4671).normal(.001, .01, (2099, 3))
        before = opt.fit(matrix)
        matrix[1095:] = np.random.default_rng(89).normal(100, 1000, (1004, 3))
        after = opt.fit(matrix)
        self.assertEqual(before['selected'], after['selected'])
        self.assertEqual(before['risk_scales'], after['risk_scales'])
        self.assertEqual(before['discovery_sharpes'], after['discovery_sharpes'])
        for name in opt.METHODS:
            np.testing.assert_array_equal(before['weights'][name], after['weights'][name])

    def test_all_cost_means_are_linear_in_fixed_sleeve_weights(self):
        summaries = {(name, 'validation', cm): {'mean_bp_day': 10*(j+1)-cm}
                     for j, name in enumerate(opt.source.SOURCES) for cm in (1, 2, 3)}
        for cm in (1, 2, 3):
            self.assertAlmostEqual(opt.stress_mean([.2, .3, .5], summaries, 'validation', cm, .5),
                                   .5*(23-cm))

    def test_each_registered_condition_can_block_a_pass(self):
        y = np.array([-.01, .01, -.005, .01]*50)
        x = y+.001
        boot = {'lower95': .0001, 'family_max_p': .01}
        good = opt.checks(x, y, 1., boot)
        self.assertTrue(all(good.values()))
        self.assertFalse(opt.checks(x, y, -1., boot)['validation_mean_2x_positive'])
        self.assertFalse(opt.checks(x, y, 1., {**boot, 'lower95': 0})['paired_mean_lower95_positive'])
        self.assertFalse(opt.checks(x, y, 1., {**boot, 'family_max_p': .051})[
                         'three_method_family_max_p_at_most_0_05'])
        self.assertFalse(opt.checks(y, y, 1., boot)['validation_sharpe_gain_at_least_0_15'])

    def test_verify_precedes_data_and_existing_results_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(opt, 'verify_registration', side_effect=opt.Error('tampered')):
                with mock.patch.object(opt.source, 'read_inputs') as read:
                    with self.assertRaisesRegex(opt.Error, 'tampered'):
                        opt.run(Path(directory)/'new')
                    read.assert_not_called()
            sentinel = Path(directory)/'result'
            sentinel.write_bytes(b'preserve me')
            with mock.patch.object(opt, 'verify_registration', return_value={}):
                with self.assertRaisesRegex(opt.Error, 'overwrite'):
                    opt.run(Path(directory))
            self.assertEqual(sentinel.read_bytes(), b'preserve me')

    def test_undefined_decision_metrics_are_inconclusive_not_null(self):
        path = np.linspace(-.01, .02, 50)
        boot = {'lower95': .001, 'family_max_p': .01}
        with self.assertRaisesRegex(opt.Error, 'Undefined required decision metric'):
            opt.checks(path, np.zeros(50), 1., boot)
        with self.assertRaisesRegex(opt.Error, 'Undefined required decision metric'):
            opt.checks(path, path, 1., {**boot, 'family_max_p': np.nan})


if __name__ == '__main__':
    unittest.main()
