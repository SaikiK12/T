import unittest

import numpy as np

from lab import engine, features, panel, research
from lab.engine import Rule
from tests.test_features import synthetic


def small_universe(T=24 * 300, S=14):
    p = synthetic(T=T, S=S)
    return research.make_universe(p, elig_top=8, col_top=12, window=24 * 10)


class UniverseTests(unittest.TestCase):
    def boundary_universe(self, holdout_close=100.0, days=3):
        t = panel.ms("2025-06-29") + np.arange(days * 24) * panel.HOUR
        close = np.full((len(t), 1), 100.0, np.float32)
        if len(t) > 48:
            close[48:] = holdout_close
        p = panel.Panel(t, ["SYNTHUSDT"], {"close": close})
        elig = np.ones_like(close, bool)
        return research.Universe(p, elig, np.zeros_like(close),
                                 engine.forward_returns(close, np.full_like(close, np.nan)),
                                 np.ones_like(close), None)

    def test_end_at_holdout_reads_its_first_close_and_requires_opt_in(self):
        rule = Rule(view=(0,), lo=(0,), hi=(0,), need=1, direction=1, hold=1)
        totals = []
        for price in (100.0, 200.0):
            u = self.boundary_universe(price)
            bins = np.zeros((1, u.p.T, 1), np.int8)
            self.assertEqual(u.holdout_row, 48)
            with self.assertRaises(PermissionError):
                research.eval_rules(u, bins, [rule], 0, 48, slots=1)
            result = research.eval_rules(u, bins, [rule], 0, 48, slots=1, allow_holdout=True)
            totals.append(float(result[0].sum()))
            before, _, _ = research.eval_rules(u, bins, [rule], 0, 24, slots=1)
            self.assertEqual(float(before.sum()), 0.0)
        self.assertAlmostEqual(totals[1] - totals[0], 1.0)

    def test_data_ending_before_holdout_does_not_trigger_boundary_guard(self):
        u = self.boundary_universe(days=2)
        bins = np.zeros((1, u.p.T, 1), np.int8)
        rule = Rule(view=(0,), lo=(0,), hi=(0,), need=1, direction=1, hold=1)
        result, _, _ = research.eval_rules(u, bins, [rule], 0, u.p.T, slots=1)
        self.assertEqual(result.shape, (1, 2))
        with self.assertRaises(PermissionError):
            research.eval_rules(u, bins, [rule], 0, u.p.T + 24, slots=1)

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


class ReservedWindowTests(unittest.TestCase):
    def test_reserved_window_needs_a_frozen_prereg_that_declares_it(self):
        import tempfile
        from pathlib import Path
        from lab import prereg
        panel.check_reserved(panel.START)  # the normal start needs nothing
        with self.assertRaises(PermissionError):
            panel.check_reserved("2020-01-01")
        with tempfile.TemporaryDirectory() as d:
            plain, declared = Path(d) / "a" / "PREREG.md", Path(d) / "b" / "PREREG.md"
            for f, text in ((plain, "no token"), (declared, f"reads {panel.RESERVED_TOKEN}")):
                f.parent.mkdir()
                f.write_text(text)
            with self.assertRaises(prereg.PreregError):
                panel.check_reserved("2020-01-01", declared)   # not frozen yet
            prereg.freeze(plain)
            prereg.freeze(declared)
            with self.assertRaises(PermissionError):
                panel.check_reserved("2020-01-01", plain)
            panel.check_reserved("2020-01-01", declared)
            with self.assertRaises(PermissionError):
                panel.load_panel(["BTCUSDT"], root=d, start="2020-06-01")
