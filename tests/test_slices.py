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


if __name__ == "__main__":
    unittest.main()
