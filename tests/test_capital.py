"""Synthetic account identities; these tests never load market outcomes."""
import unittest

import numpy as np

from lab.capital import segregated


class SegregatedCapitalTest(unittest.TestCase):
    def run_book(self, **overrides):
        args = dict(spot_net=[0.1, -0.1], spot_gross=[0.12, -0.09], spot_cost=[0.02, 0.01],
                    carry_gross=[0.1, 0.1], carry_funding=[0.04, 0.03], carry_cost=[0.01, 0.01])
        args.update(overrides)
        return segregated(**args)

    def assert_bookkeeping(self, book):
        np.testing.assert_allclose(book["equity"], 1 + np.cumsum(book["dollar_net"]), atol=1e-14)
        np.testing.assert_allclose(book["dollar_net"], book["dollar_gross"] - book["dollar_cost"], atol=1e-14)
        np.testing.assert_allclose(book["equity"], np.cumprod(1 + book["net"]), atol=1e-14)

    def test_spot_compounds_while_carry_keeps_initial_notional(self):
        book = self.run_book()
        np.testing.assert_allclose(book["spot_equity"], [1.1, 0.99])
        np.testing.assert_allclose(book["carry_equity"], [1.09, 1.18])
        np.testing.assert_allclose(book["equity"], [1.095, 1.085])
        np.testing.assert_allclose(book["dollar_net"], [0.095, -0.01])
        np.testing.assert_allclose(book["net"], [0.095, -0.01 / 1.095])
        # The second day's spot fee uses its OWN 1.1 NAV, not portfolio NAV.
        np.testing.assert_allclose(book["dollar_cost"], [0.015, 0.0105])
        np.testing.assert_allclose(book["dollar_gross"], [0.11, 0.0005])
        self.assert_bookkeeping(book)

    def test_funding_is_a_component_of_gross_not_an_extra_credit(self):
        first = self.run_book()
        changed_component = self.run_book(carry_funding=[-0.2, 0.4])
        np.testing.assert_allclose(first["dollar_funding"], [0.02, 0.015])
        np.testing.assert_allclose(changed_component["dollar_funding"], [-0.1, 0.2])
        np.testing.assert_array_equal(first["equity"], changed_component["equity"])
        np.testing.assert_array_equal(first["dollar_net"], changed_component["dollar_net"])

    def test_entry_fee_is_paid_once_on_initial_carry_capital(self):
        cost = np.array([0.01, 0.01])
        original = cost.copy()
        book = self.run_book(carry_cost=cost, carry_entry_cost=0.03)
        np.testing.assert_allclose(book["carry_equity"], [1.06, 1.15])
        np.testing.assert_allclose(book["dollar_cost"], [0.03, 0.0105])
        np.testing.assert_allclose(book["equity"], [1.08, 1.07])
        np.testing.assert_array_equal(cost, original)
        self.assert_bookkeeping(book)

    def test_unallocated_capital_stays_in_cash_without_rebalancing(self):
        book = self.run_book(spot_weight=0.2, carry_weight=0.3)
        np.testing.assert_allclose(book["equity"], [1.047, 1.052])
        np.testing.assert_allclose(book["equity"], 0.2 * book["spot_equity"] + 0.3 * book["carry_equity"] + 0.5)
        self.assert_bookkeeping(book)
        cash = self.run_book(spot_weight=0, carry_weight=0)
        np.testing.assert_array_equal(cash["equity"], [1, 1])
        for name in ("net", "dollar_net", "dollar_gross", "dollar_cost", "dollar_funding"):
            np.testing.assert_array_equal(cash[name], [0, 0])

    def test_carry_can_lose_more_than_initial_notional_after_profits(self):
        book = self.run_book(carry_gross=[1.5, -1.1], carry_cost=[0, 0], spot_weight=0, carry_weight=1)
        np.testing.assert_allclose(book["carry_equity"], [2.5, 1.4])
        np.testing.assert_allclose(book["net"], [1.5, -1.1 / 2.5])
        self.assert_bookkeeping(book)

    def test_no_cross_sleeve_rescue_or_reentry_after_bankruptcy(self):
        for weight in (0, 0.5):
            with self.subTest(carry_weight=weight), self.assertRaisesRegex(ValueError, "carry NAV"):
                self.run_book(carry_gross=[-1, 3], carry_cost=[0, 0],
                              spot_weight=0.5, carry_weight=weight,
                              spot_net=[1, 1], spot_gross=[1, 1], spot_cost=[0, 0])
        with self.assertRaisesRegex(ValueError, "carry NAV"):
            self.run_book(carry_entry_cost=1.2)
        with self.assertRaisesRegex(ValueError, "spot_net"):
            self.run_book(spot_net=[-1, 1], spot_gross=[-1, 1], spot_cost=[0, 0], spot_weight=0)

    def test_shape_and_finiteness_validation(self):
        for name in ("spot_net", "spot_gross", "spot_cost", "carry_gross", "carry_funding", "carry_cost"):
            for bad in ([], [0], [[0, 0]], 0, [0, np.nan], [0, np.inf], [0, 1j]):
                with self.subTest(name=name, bad=bad), self.assertRaises(ValueError):
                    self.run_book(**{name: bad})

    def test_weights_costs_and_spot_identity_validation(self):
        for kwargs in ({"spot_weight": -0.1}, {"carry_weight": -0.1},
                       {"spot_weight": 0.8, "carry_weight": 0.3},
                       {"spot_weight": np.nan}, {"carry_weight": [0.5]},
                       {"carry_entry_cost": -0.01}, {"carry_entry_cost": np.inf},
                       {"spot_cost": [-0.01, 0.01]}, {"carry_cost": [0.01, -0.01]},
                       {"spot_gross": [0.11, -0.09]}, {"spot_net": [-1.01, 0]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_book(**kwargs)
        # The declared tolerance is absolute; relative tolerance must not accept a large mismatch.
        with self.assertRaisesRegex(ValueError, "within 1e-9"):
            self.run_book(spot_net=[100, 0], spot_gross=[100.00001, 0], spot_cost=[0, 0])
        self.run_book(spot_gross=[0.12 + 0.5e-9, -0.09])

    def test_overflow_and_underflow_are_rejected_as_invalid_accounts(self):
        for kwargs in ({"spot_net": [1e308, 1e308], "spot_gross": [1e308, 1e308], "spot_cost": [0, 0]},
                       {"carry_gross": [1e308, 1e308], "carry_cost": [0, 0]}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_book(**kwargs)
        n = 2000
        with self.assertRaisesRegex(ValueError, "spot NAV"):
            segregated(np.full(n, -0.5), np.full(n, -0.5), np.zeros(n),
                       np.zeros(n), np.zeros(n), np.zeros(n))

    def test_single_day_zero_and_pure_sleeve_accounts(self):
        book = segregated([0], [0], [0], [0], [0], [0])
        self.assertEqual(set(book), {"equity", "net", "dollar_net", "dollar_gross", "dollar_funding",
                                     "dollar_cost", "spot_equity", "carry_equity"})
        self.assertTrue(all(value.shape == (1,) for value in book.values()))
        self.assert_bookkeeping(book)
        for sw, cw, source in ((1, 0, "spot_equity"), (0, 1, "carry_equity")):
            book = self.run_book(spot_weight=sw, carry_weight=cw)
            np.testing.assert_array_equal(book["equity"], book[source])
            self.assert_bookkeeping(book)


if __name__ == "__main__":
    unittest.main()
