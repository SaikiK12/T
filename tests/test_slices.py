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


class MissingObservationTests(unittest.TestCase):
    def setUp(self):
        self.P = np.zeros((24, 3))
        self.P[1:3, :2] = [0.5, -0.25]
        self.ret = np.zeros((24, 3))
        self.ret[1:3] = [[0.02, -0.04, 0.01], [-0.03, 0.02, -0.02]]
        self.elig = np.ones((24, 3), bool)
        self.cmat = np.tile([0.001, 0.002, 0.003], (24, 1))
        self.basket = np.zeros((24, 3), bool)
        self.basket[:, 2] = True

    def run_book(self, **kwargs):
        options = dict(basket=self.basket, missing="raise")
        options.update(kwargs)
        return slices.run(self.P, self.ret, self.elig, self.cmat, 0, 24, **options)

    def test_finite_book_matches_an_independent_cashflow_ledger_at_all_costs(self):
        for multiple in (1, 2, 3):
            with self.subTest(multiple=multiple):
                out = self.run_book(cmult=multiple)
                # Main: +0.5 coin A, -0.25 coin B. Hedge: -0.25 coin C.
                # Each main entry/exit costs 0.001; each hedge entry/exit costs 0.00075.
                np.testing.assert_allclose(out["gross"][1:4], [0.02, -0.02, 0])
                np.testing.assert_allclose(out["hedge"][1:4], [-0.0025, 0.005, 0])
                np.testing.assert_allclose(out["cost"][1:4], np.array([0.001, 0, 0.001]) * multiple)
                np.testing.assert_allclose(out["hedge_cost"][1:4],
                                           np.array([0.00075, 0, 0.00075]) * multiple)
                self.assertAlmostEqual(out["daily"][0], 0.0025 - 0.0035 * multiple)
                legacy = self.run_book(missing="legacy", cmult=multiple)
                for key in out:
                    np.testing.assert_allclose(out[key], legacy[key])

    def test_unknown_exposed_main_return_fails_for_both_sides(self):
        for column in (0, 1):
            for value in (np.nan, np.inf, -np.inf):
                with self.subTest(column=column, value=value):
                    self.ret[1, column] = value
                    with self.assertRaisesRegex(ValueError, "Exposed main return.*row 1"):
                        self.run_book(hedge=False)
                    self.ret[1, column] = [0.02, -0.04][column]

    def test_unknown_exposed_hedge_return_cannot_change_membership(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value):
                self.ret[1, 2] = value
                # A custom hedge and the full eligible basket both need this return.
                for basket in (self.basket, None):
                    with self.assertRaisesRegex(ValueError, "Exposed hedge return.*row 1"):
                        self.run_book(basket=basket)
                # The same observation is irrelevant when there is no hedge.
                self.assertTrue(np.isfinite(self.run_book(hedge=False)["daily"]).all())

    def test_legacy_default_keeps_historical_zero_fill_and_hedge_filter(self):
        self.ret[1, 0] = np.nan
        implicit = slices.run(self.P, self.ret, self.elig, self.cmat, 0, 24)
        explicit = slices.run(self.P, self.ret, self.elig, self.cmat, 0, 24, missing="legacy")
        self.assertAlmostEqual(implicit["gross"][1], 0.01)  # missing long contribution is zero
        self.assertAlmostEqual(implicit["hedge"][1], 0.00375)  # mean of the two remaining returns
        for key in implicit:
            np.testing.assert_array_equal(implicit[key], explicit[key])

    def test_unknown_unexposed_observations_are_irrelevant(self):
        self.ret[:] = np.nan
        self.P[:] = 0
        self.cmat[:] = np.nan
        self.basket[:] = False
        out = self.run_book()
        for values in out.values():
            np.testing.assert_array_equal(values, np.zeros_like(values))

    def test_known_zero_is_an_observation_and_terminal_missing_is_not(self):
        self.ret[1:3] = 0
        self.assertTrue(np.isfinite(self.run_book()["daily"]).all())
        self.P[-1, 0] = 0.5
        self.ret[-1, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "Exposed main return.*row 23"):
            self.run_book()

    def test_unknown_or_negative_cost_on_entry_and_exit_fails(self):
        for row in (1, 3):
            for value in (np.nan, np.inf, -np.inf, -0.001):
                with self.subTest(row=row, value=value):
                    self.cmat[row, 0] = value
                    with self.assertRaisesRegex(ValueError, f"Main trade cost.*row {row}"):
                        self.run_book()
                    self.cmat[row, 0] = 0.001

    def test_hedge_trade_cost_is_checked_only_when_size_changes(self):
        self.cmat[2, 2] = np.nan  # unchanged hedge, so no transaction fee is due
        self.assertEqual(self.run_book()["hedge_cost"][2], 0)
        for row in (1, 3):
            with self.subTest(row=row):
                self.cmat[row, 2] = np.nan
                with self.assertRaisesRegex(ValueError, f"Hedge trade cost.*row {row}"):
                    self.run_book()
                self.cmat[row, 2] = 0.003

    def test_empty_basket_cannot_hide_a_hedge_or_its_exit_fee(self):
        for row in (1, 2, 3):
            with self.subTest(row=row):
                self.basket[row] = False
                with self.assertRaisesRegex(ValueError, f"Empty required hedge basket at row {row}"):
                    self.run_book()
                self.basket[row, 2] = True

    def test_invalid_positions_multiplier_shapes_and_policy_fail(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(position=value):
                self.P[1, 0] = value
                with self.assertRaisesRegex(ValueError, "Positions must be finite"):
                    self.run_book()
        self.P[1, 0] = 0.5
        for value in (np.nan, np.inf, -1):
            with self.subTest(multiplier=value):
                with self.assertRaisesRegex(ValueError, "Cost multiplier"):
                    self.run_book(cmult=value)
        with self.assertRaisesRegex(ValueError, "shape"):
            slices.run(self.P[:-1], self.ret, self.elig, self.cmat, 0, 24, missing="raise")
        with self.assertRaisesRegex(ValueError, "boolean array matching"):
            self.run_book(basket=self.basket[:, :2])
        with self.assertRaisesRegex(ValueError, "boolean array matching"):
            self.run_book(basket=self.basket.astype(float))
        with self.assertRaisesRegex(ValueError, "Unknown missing-data policy"):
            self.run_book(missing="typo")

    def test_only_the_selected_interval_is_checked_and_reported(self):
        ret = np.full((48, 3), np.nan)
        costs = np.full((48, 3), np.nan)
        ret[12:36] = self.ret
        costs[12:36] = self.cmat
        elig = np.ones((48, 3), bool)
        actual = slices.run(self.P, ret, elig, costs, 12, 36, hedge=False, missing="raise")
        np.testing.assert_array_equal(actual["net"], self.run_book(hedge=False)["net"])
        ret[13, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "row 13, column 0"):
            slices.run(self.P, ret, elig, costs, 12, 36, hedge=False, missing="raise")

    def test_book_wrapper_passes_the_explicit_policy(self):
        indicator = self.P != 0
        self.ret[1, 0] = np.nan
        with self.assertRaisesRegex(ValueError, "Exposed main return"):
            slices.book(indicator, self.ret, self.elig, self.cmat, 2, 0.1, 0, 24,
                        hedge=False, missing="raise")


if __name__ == "__main__":
    unittest.main()
