import unittest

import numpy as np

from lab import xfund as v1
from lab import xfund_v2 as v2
from scripts import run_xfund_listing as r


def series(nd, first, rate, price=10.0):
    f = np.zeros(nd)
    n = np.zeros(nd, int)
    f[first:] = rate
    n[first:] = 1
    close = np.full(nd, price)
    return v2.Daily.build(close, np.ones(nd, bool), f, n)


class Listing(unittest.TestCase):
    def test_same_coin(self):
        self.assertTrue(r.same_coin(1.02, 1.0))
        self.assertTrue(r.same_coin(1000.0, 1.03))          # 1000PEPE against PEPE
        self.assertFalse(r.same_coin(1.2, 1.0))
        self.assertFalse(r.same_coin(float("nan"), 1.0))

    def test_listing_phase_entry_and_exit(self):
        nd = 90
        old = series(nd, 1, 0.0)                         # Binance, funded from day 1
        young = series(nd, 40, 0.001)                    # Hyperliquid lists on day 40, longs pay 0.1% a day
        other_b, other_h = series(nd, 1, 0.0), series(nd, 1, 0.0)   # sets Hyperliquid's data start at day 1
        u = v1.Universe(["X", "Y"], ["binance", "hyperliquid"], [[old, young], [other_b, other_h]], 0, nd)
        vset = [0, 1]
        launch = r.launches(u, vset)
        ev = r.events(u, vset, launch)
        self.assertEqual(ev.coin.tolist(), ["X"])
        self.assertEqual(ev.young.tolist(), ["hyperliquid"])
        rows, tr = r.run_book(u, vset, launch, 0.20, 10, 30)
        self.assertEqual(len(tr), 1)
        t = tr.iloc[0]
        self.assertEqual((t.entry_day, t.long, t.short), (42, "binance", "hyperliquid"))   # age 3 on day 42
        self.assertEqual(t.reason, "phase_end")          # age 36 on day 75
        self.assertEqual(t.exit_day, 75)
        self.assertGreater(t.funding_pnl, 0)
        self.assertEqual(rows.held.max(), 1)

    def test_venue_launch_is_not_a_listing(self):
        nd = 60
        old, young = series(nd, 1, 0.0), series(nd, 40, 0.001)
        u = v1.Universe(["X"], ["binance", "hyperliquid"], [[old, young]], 0, nd)
        launch = r.launches(u, [0, 1])                   # Hyperliquid's only coin starts on day 40: its launch
        self.assertEqual(len(r.events(u, [0, 1], launch)), 0)
        _, tr = r.run_book(u, [0, 1], launch, 0.20, 10, 30)
        self.assertEqual(len(tr), 0)

    def test_price_mismatch_blocks_entry(self):
        nd = 60
        old, young = series(nd, 1, 0.0, 10.0), series(nd, 40, 0.001, 13.0)
        ob, oh = series(nd, 1, 0.0), series(nd, 1, 0.0)
        u = v1.Universe(["X", "Y"], ["binance", "hyperliquid"], [[old, young], [ob, oh]], 0, nd)
        launch = r.launches(u, [0, 1])
        _, tr = r.run_book(u, [0, 1], launch, 0.20, 10, 30)
        self.assertEqual(len(tr), 0)


if __name__ == "__main__":
    unittest.main()
