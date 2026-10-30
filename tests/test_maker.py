import unittest

import numpy as np

from lab import engine, maker


def toy(T=48):
    close = np.full((T, 1), 100.0)
    low, high = close * 0.999, close * 1.001
    fund = np.full((T, 1), np.nan)
    vol = np.full((T, 1), 0.01)
    bins = np.zeros((1, T, 1), np.int8)
    elig = np.ones((T, 1), bool)
    cmat = np.full((T, 1), 6e-4)
    return bins, close, low, high, fund, vol, elig, cmat


def run(cells, arrays, **kw):
    bins, close, low, high, fund, vol, elig, cmat = arrays
    return maker.run_cells(bins, cells, close, low, high, fund, vol, elig, cmat, engine.eligible_index(elig), 0,
                           len(close), **kw)


class MakerTests(unittest.TestCase):
    def test_fill_needs_a_trade_through(self):
        a = toy()
        bins, close, low = a[0], a[1], a[2]
        bins[0, 5, 0] = 1
        low[6, 0] = 99.4                    # limit at 100 x (1 - 0.5 x 1%) = 99.5; traded through
        close[7, 0] = 100.5                 # exit at the close of bar 5 + 2
        o = run([[0, 1, 2, 1]], a, kappa=0.5)
        self.assertEqual((o["posts"].sum(), o["fills"].sum(), o["legs"].sum()), (1, 1, 1))
        self.assertAlmostEqual(o["gross"].sum(), 100.5 / 99.5 - 1)
        self.assertAlmostEqual(maker.net(o, fee=2e-4).sum(), 100.5 / 99.5 - 1 - 6e-4 - 2e-4)
        self.assertAlmostEqual(maker.net(o, fee=0, cmult=2).sum(), 100.5 / 99.5 - 1 - 12e-4)
        low[6, 0] = 99.49                   # touches but does not trade 2 bp through: no fill
        o = run([[0, 1, 2, 1]], a, kappa=0.5)
        self.assertEqual((o["posts"].sum(), o["fills"].sum()), (1, 0))

    def test_short_side_taker_baseline_and_funding(self):
        a = toy()
        bins, close, fund = a[0], a[1], a[4]
        bins[0, 10, 0] = 2
        close[14, 0] = 98.0
        fund[12, 0] = 0.001                  # settles while the short is open: the short receives it
        o = run([[0, 2, 4, -1]], a, kappa=-1)
        self.assertAlmostEqual(o["gross"].sum(), -(98.0 / 100.0 - 1) + 0.001)
        self.assertAlmostEqual(o["tcost"].sum(), 2 * 6e-4)
        self.assertEqual(o["legs"].sum(), 0)

    def test_maker_exit_and_episodes(self):
        a = toy()
        bins, low = a[0], a[2]
        bins[0, 5:8, 0] = 1                  # three hours in the bin: one episode
        low[6, 0] = 99.0
        o = run([[0, 1, 1, 1]], a, kappa=0.5, exit_mode=1)
        self.assertEqual(o["posts"].sum(), 1)
        # the exit limit at close[6] = 100 rests in bar 7, whose high 100.1 trades through: maker on both legs
        self.assertAlmostEqual(o["gross"].sum(), 100.0 / 99.5 - 1)
        self.assertEqual((o["legs"].sum(), o["tcost"].sum()), (2, 0))

    def test_unconditional_baseline_counts_every_eligible_hour(self):
        o = run([[-1, 0, 1, 1]], toy(), kappa=0.0)
        self.assertEqual(o["posts"].sum(), 47)          # the last hour has no bar to fill in
        self.assertEqual(o["fills"].sum(), 47)          # a low 0.1% under the close trades through a limit at the close

    def test_book_holds_one_position_per_symbol_and_cancels_conflicts(self):
        a = toy(T=96)
        bins, close, low, high, fund, vol, elig, cmat = a
        bins[0, 5, 0] = 1
        bins[0, 6, 0] = 2                    # a new episode while the first trade is still open: ignored
        low[6, 0] = 99.0
        cells = [[0, 1, 4, 1], [0, 2, 4, 1]]
        o = maker.book(bins, cells, close, low, high, fund, vol, elig, cmat, engine.eligible_index(elig), 0, 96,
                       kappa=0.5, slots=2)
        self.assertAlmostEqual(o["gross"].sum(), (100.0 / 99.5 - 1) / 2)
        bins2 = np.zeros((2, 96, 1), np.int8)
        bins2[0, 30, 0], bins2[1, 30, 0] = 1, 1
        o = maker.book(bins2, [[0, 1, 4, 1], [1, 1, 4, -1]], close, low, high, fund, vol, elig, cmat,
                       engine.eligible_index(elig), 0, 96, kappa=0.5)
        self.assertEqual(o["conflicts"], 1)
        self.assertEqual(o["gross"].sum(), 0)


if __name__ == "__main__":
    unittest.main()
