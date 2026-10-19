import unittest

import numpy as np

from lab import engine, features, panel, research
from lab.engine import Rule
from tests.test_features import synthetic


def small_universe(T=24 * 300, S=14):
    p = synthetic(T=T, S=S)
    return research.make_universe(p, elig_top=8, col_top=12, window=24 * 10)


class UniverseTests(unittest.TestCase):
    def test_columns_and_eligibility_are_point_in_time(self):
        u = small_universe()
        self.assertEqual(u.elig.shape, u.p["close"].shape)
        self.assertTrue((~u.elig | ~np.isnan(u.p["close"])).all())               # never eligible without a price
        self.assertLessEqual(int(u.elig.sum(axis=1).max()), 8)
        self.assertTrue(np.isfinite(u.ret[: u.p.T - 1][u.elig[: u.p.T - 1]]).mean() > 0.95)

    def test_holdout_is_unreachable_by_default(self):
        u = small_universe()
        bins = np.zeros((1, u.p.T, u.p.S), np.int8)
        rule = Rule(view=(0,), lo=(0,), hi=(0,), need=1, direction=1, hold=1)
        # synthetic data starts 2021-01-01 and is shorter than the holdout, so move the holdout inside it for the check
        old = research.HOLDOUT
        research.HOLDOUT = "2021-06-01"
        try:
            with self.assertRaises(PermissionError):
                research.eval_rules(u, bins, [rule], 0, u.p.T)
            research.eval_rules(u, bins, [rule], 0, 24 * 100)                       # before the holdout: fine
            research.eval_rules(u, bins, [rule], 0, u.p.T, allow_holdout=True)      # explicit opt-in
        finally:
            research.HOLDOUT = old

    def test_exact_holdout_boundary_already_depends_on_its_first_bar(self):
        u = small_universe()
        bins = np.zeros((1, u.p.T, u.p.S), np.int8)
        rule = Rule(view=(0,), lo=(0,), hi=(0,), need=1, direction=1, hold=1)
        old = research.HOLDOUT
        research.HOLDOUT = "2021-06-01"
        try:
            boundary = u.holdout_row
            with self.assertRaises(PermissionError):
                research.eval_rules(u, bins, [rule], 0, boundary)
            research.eval_rules(u, bins, [rule], 0, boundary - 24)
            research.eval_rules(u, bins, [rule], 0, boundary, allow_holdout=True)
        finally:
            research.HOLDOUT = old

    def test_panel_ending_before_holdout_is_not_mistaken_for_a_boundary_bar(self):
        u = small_universe()
        bins = np.zeros((1, u.p.T, u.p.S), np.int8)
        rule = Rule(view=(0,), lo=(0,), hi=(0,), need=1, direction=1, hold=1)
        self.assertEqual(u.holdout_row, u.p.T)
        research.eval_rules(u, bins, [rule], 0, u.p.T)

    def test_daily_results_add_up_to_hourly(self):
        u = small_universe()
        specs = [s for s in features.default_specs() if s.family == "ret" and s.k == 1][:3]
        bins, _ = features.views(u.bank, specs, u.elig)
        rules = [Rule(view=(0,), lo=(5,), hi=(7,), need=1, direction=1, hold=3),
                 Rule(view=(1, 2), lo=(0, 0), hi=(2, 3), need=2, direction=-1, hold=1)]
        ret_d, cost_d, act_d = research.eval_rules(u, bins, rules, 0, 24 * 100, allow_holdout=True)
        hourly = engine.run_rules(bins, u.ret, u.elig, u.cmat, rules, 0, 24 * 100)
        np.testing.assert_allclose(ret_d.sum(axis=1), hourly[:, :, 0].sum(axis=1), rtol=1e-4, atol=1e-6)
        np.testing.assert_allclose(cost_d.sum(axis=1), hourly[:, :, 1].sum(axis=1), rtol=1e-4, atol=1e-7)
        self.assertEqual(ret_d.shape, (2, 100))
        self.assertGreater(float(act_d.max()), 0.0)


if __name__ == "__main__":
    unittest.main()
