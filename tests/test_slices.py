import unittest

import numpy as np

from lab import slices


class SliceTests(unittest.TestCase):
    def test_slices_overlap_and_expire(self):
        ind = np.zeros((12, 1), bool)
        ind[5:7, 0] = True                              # two hours in the state, hold 3
        P = slices.positions(ind, 3, 0, 12, 0.1, -1)[:, 0]
        np.testing.assert_allclose(P[4:10], [0, -0.1, -0.2, -0.2, -0.1, 0])

    def test_book_pnl_costs_and_hedge(self):
        T, S = 24, 2
        ind = np.zeros((T, S), bool)
        ind[5, 0] = True
        ret = np.zeros((T, S))
        ret[6, 0] = -0.02                               # the shorted coin falls 2% in the next bar after row 6
        ret[6, 1] = 0.01
        elig = np.ones((T, S), bool)
        cmat = np.full((T, S), 6e-4)
        o = slices.book(ind, ret, elig, cmat, hold=3, unit=1.0, t0=0, t1=T, side=-1)
        self.assertAlmostEqual(o["gross"][6], 0.02)
        self.assertAlmostEqual(o["cost"].sum(), 2 * 6e-4)       # opened at 5, closed after row 7
        self.assertAlmostEqual(o["hedge"][6], 1.0 * (-0.02 + 0.01) / 2)
        self.assertAlmostEqual(o["hedge_cost"].sum(), 2 * 6e-4)
        self.assertAlmostEqual(o["daily"][0], 0.02 - 0.005 - 4 * 6e-4)

    def test_hedge_basket_can_be_one_coin(self):
        T, S = 24, 3
        ind = np.zeros((T, S), bool)
        ind[5, 0] = True
        ret = np.zeros((T, S))
        ret[6] = [-0.02, 0.01, 0.03]
        basket = np.zeros((T, S), bool)
        basket[:, 2] = True                             # hedge in column 2 only (BTC, say)
        o = slices.book(ind, ret, np.ones((T, S), bool), np.full((T, S), 6e-4), 3, 1.0, 0, T, basket=basket)
        self.assertAlmostEqual(o["hedge"][6], 0.03)

    def test_slices_start_at_t0(self):
        ind = np.ones((10, 1), bool)
        P = slices.positions(ind, 4, 5, 10, 1.0, 1)[:, 0]
        np.testing.assert_allclose(P, [1, 2, 3, 4, 4])


class ExactAccountingTests(unittest.TestCase):
    def setup_book(self):
        p = np.zeros((24, 3))
        p[:, 0] = -1.0
        r = np.zeros_like(p)
        b = np.zeros_like(p, dtype=bool)
        b[:, 1] = True
        c = np.full_like(p, 0.01)
        return p, r, b, c

    def test_basket_switch_charges_constituent_turnover_and_counts_hedge_gross(self):
        p, r, b, c = self.setup_book()
        b[1:, 1], b[1:, 2] = False, True
        out = slices.run_exact(p, r, b, c, 0, 24)
        np.testing.assert_allclose(out["turnover"][:3], [2.0, 2.0, 0.0])
        self.assertAlmostEqual(out["daily"][0], -0.04)
        np.testing.assert_allclose(out["gross_exposure"], 2.0)
        np.testing.assert_allclose(out["net_exposure"], 0.0)
        np.testing.assert_allclose(out["hedge_gross_exposure"], 1.0)

    def test_costs_net_offsetting_legs_before_venue_orders(self):
        p, r, b, c = self.setup_book()
        b[:, 0] = True
        out = slices.run_exact(p, r, b, c, 0, 24)
        np.testing.assert_allclose(out["positions"][0], [-0.5, 0.5, 0.0])
        self.assertAlmostEqual(out["cost"].sum(), 0.01)
        np.testing.assert_allclose(out["leg_gross_exposure"], 2.0)
        np.testing.assert_allclose(out["gross_exposure"], 1.0)

    def test_missing_held_return_invalidates_day_without_reshuffling_hedge(self):
        p, r, b, c = self.setup_book()
        base = slices.run_exact(p, r, b, c, 0, 24)
        r[7, 1] = np.nan
        out = slices.run_exact(p, r, b, c, 0, 24)
        np.testing.assert_array_equal(out["positions"], base["positions"])
        self.assertFalse(out["valid"][7])
        self.assertFalse(out["daily_valid"][0])
        self.assertTrue(np.isnan(out["daily"][0]))
        self.assertEqual(out["missing_return_exposure"][7], 1.0)

    def test_missing_unheld_return_and_unused_cost_do_not_poison_pnl(self):
        p, r, b, c = self.setup_book()
        r[:, 2], c[:, 2] = np.nan, np.nan
        out = slices.run_exact(p, r, b, c, 0, 24)
        self.assertTrue(out["valid"].all())
        self.assertAlmostEqual(out["daily"][0], -0.02)

    def test_missing_execution_cost_and_missing_hedge_are_explicit(self):
        p, r, b, c = self.setup_book()
        c[0, 1] = np.nan
        out = slices.run_exact(p, r, b, c, 0, 24)
        self.assertFalse(out["valid"][0])
        self.assertTrue(np.isnan(out["daily"][0]))
        self.assertEqual(out["missing_cost_turnover"][0], 1.0)
        c[0, 1] = 0.01
        b[8] = False
        out = slices.run_exact(p, r, b, c, 0, 24)
        self.assertTrue(out["missing_hedge"][8])
        self.assertFalse(out["valid"][8])

    def test_exit_costs_are_explicit_and_apply_at_the_boundary(self):
        p, r, b, c = self.setup_book()
        with self.assertRaises(ValueError):
            slices.run_exact(p, r, b, c, 0, 24, liquidate=True)
        with self.assertRaises(ValueError):
            slices.run_exact(p, r, b, c, 0, 24, terminal_cmat=np.full(3, 0.02))
        out = slices.run_exact(p, r, b, c, 0, 24, liquidate=True, terminal_cmat=np.full(3, 0.02))
        self.assertAlmostEqual(out["terminal_cost"].sum(), 0.04)
        self.assertAlmostEqual(out["daily"][0], -0.06)
        self.assertAlmostEqual(out["turnover"].sum(), 4.0)
        np.testing.assert_array_equal(out["closing_positions"], 0.0)

    def test_unknown_basket_membership_cannot_become_a_phantom_hedge(self):
        p, r, b, c = self.setup_book()
        mask = b.astype(float)
        for invalid in (np.nan, np.inf, -1.0, 0.5):
            mask[3, 0] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    slices.run_exact(p, r, b, c, 0, 24, basket=mask)

    def test_daily_output_requires_a_calendar_aligned_window(self):
        p, r, b, c = self.setup_book()
        with self.assertRaisesRegex(ValueError, "UTC day"):
            slices.run_exact(p, r, b, c, 1, 25)

    def test_continuation_does_not_pay_a_second_entry(self):
        p, r, b, c = self.setup_book()
        out = slices.run_exact(p, r, b, c, 0, 24, initial_positions=[-1.0, 1.0, 0.0])
        self.assertEqual(out["cost"].sum(), 0.0)

    def test_cost_stress_uses_exact_scaled_position_changes(self):
        p, r, b, c = self.setup_book()
        p[1:, 0] = -0.5
        multiplier = np.r_[1.0, np.full(23, 2.0)]
        for cmult in (1.0, 2.0, 3.0):
            out = slices.run_exact(p * multiplier[:, None], r, b, c, 0, 24, cmult=cmult)
            # Base size halves while multiplier doubles: there is no rebalance.
            self.assertAlmostEqual(out["cost"].sum(), 0.02 * cmult)
            self.assertEqual(out["turnover"][1:].sum(), 0.0)


if __name__ == "__main__":
    unittest.main()
