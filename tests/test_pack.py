import unittest

import numpy as np

from lab import engine, pack


def toy(T=48, S=2):
    close = np.full((T, S), 100.0)
    low, high = close * 0.999, close * 1.001
    fund = np.full((T, S), np.nan)
    vol = np.full((T, S), 0.01)
    bins = np.zeros((1, T, S), np.int8)
    elig = np.ones((T, S), bool)
    cmat = np.full((T, S), 6e-4)
    return bins, close, low, high, fund, vol, elig, cmat


def run(cells, a, **kw):
    bins, close, low, high, fund, vol, elig, cmat = a
    return pack.run(bins, cells, close, low, high, fund, vol, elig, cmat, engine.eligible_index(elig), 0, len(close),
                    **kw)


class PackTests(unittest.TestCase):
    def test_maker_fill_marked_hourly_with_costs(self):
        a = toy(S=1)
        bins, close, low = a[0], a[1], a[2]
        bins[0, 5, 0] = 1
        low[6, 0] = 99.4                              # buy limit at 99.5 traded through in bar 6
        close[7, 0] = 100.5
        o = run([[0, 1, 2, 1]], a, kappa=0.5, fee=2e-4, slots=1)
        self.assertAlmostEqual(o["gross"][6], 100 / 99.5 - 1)
        self.assertAlmostEqual(o["gross"][7], 0.005)
        self.assertAlmostEqual(o["entry_cost"].sum(), 2e-4)
        self.assertAlmostEqual(o["exit_cost"][7], 6e-4)
        self.assertEqual(o["fills"].sum(), 1)
        self.assertEqual(o["n_open"][8], 0)
        self.assertAlmostEqual(o["daily"].sum(), 100 / 99.5 - 1 + 0.005 - 8e-4)

    def test_unfilled_order_frees_the_slot(self):
        a = toy(S=1)
        a[0][0, 5, 0] = 1
        o = run([[0, 1, 2, 1]], a, kappa=0.5, slots=1)
        self.assertEqual(o["n_open"][5], 1)            # the order holds the slot during bar 6
        self.assertEqual(o["n_open"][6], 0)
        self.assertEqual(o["gross"].sum(), 0)

    def test_taker_entry_hedge_and_funding(self):
        a = toy(S=2)                                   # column 1 plays BTC, the hedge
        bins, close, fund = a[0], a[1], a[4]
        bins[0, 10, 0] = 1
        close[11:, 0] = 102.0
        close[11:, 1] = 101.0
        fund[12, 0] = 0.001
        o = run([[0, 1, 4, 1]], a, kappa=-1, slots=1, hedge_col=1)
        self.assertAlmostEqual(o["gross"][11], 0.02)
        self.assertAlmostEqual(o["gross"][12], -0.001)  # the long pays funding
        self.assertAlmostEqual(o["hedge"][11], -0.01)   # short 1x BTC from the close of bar 10
        self.assertAlmostEqual(o["hedge_cost"].sum(), 2 * 6e-4)
        self.assertAlmostEqual(o["exposure"][10], 1.0)
        self.assertAlmostEqual(o["exposure"][14], 0.0)

    def test_universe_hedge_takes_the_basket_mean(self):
        a = toy(S=2)
        bins, close = a[0], a[1]
        bins[0, 10, 0] = 1
        close[11:, 0] = 98.0                           # the short's coin falls 2%, the other one rises 1%
        close[11:, 1] = 101.0
        o = run([[0, 1, 4, -1]], a, kappa=-1, slots=1, hedge_col=-2)
        self.assertAlmostEqual(o["gross"][11], 0.02)
        self.assertAlmostEqual(o["hedge"][11], (-0.02 + 0.01) / 2)   # long the basket of both eligible coins
        self.assertAlmostEqual(o["hedge_cost"].sum(), 2 * 6e-4)

    def test_priority_slots_and_gates(self):
        a = toy(S=2)
        bins = np.zeros((2, 48, 2), np.int8)
        bins[0, 5, 1] = 1
        bins[1, 5, 0] = 1
        a = (bins,) + a[1:]
        o = run([[1, 1, 2, -1], [0, 1, 2, 1]], a, kappa=-1, slots=1)
        self.assertEqual(o["exposure"][5], -1.0)         # the first cell wins the only slot
        ctx = np.zeros((1, 48, 2), np.int8)
        ctx[0, 5, 0] = 3
        o = run([[1, 1, 2, -1, 0, 3, -1], [0, 1, 2, 1, 0, 3, 1]], a, kappa=-1, slots=1, ctx=ctx)
        self.assertEqual(o["exposure"][5], 0.0)          # gate -1 blocks the short; code 3 is absent for column 1
        ctx[0, 5, 1] = 3
        o = run([[1, 1, 2, -1, 0, 3, -1], [0, 1, 2, 1, 0, 3, 1]], a, kappa=-1, slots=1, ctx=ctx)
        self.assertEqual(o["exposure"][5], 1.0)


if __name__ == "__main__":
    unittest.main()
