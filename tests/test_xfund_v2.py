"""lab/xfund_v2 (M468): the three audit fixes, each against the frozen lab/xfund behaviour."""
import math
import unittest

import numpy as np

from lab import xfund as v1
from lab import xfund_v2 as v2

DAY, H = v2.DAY, v2.H


def daily(close, fresh=None, rates=None, mark=None):
    nd = len(close)
    fresh = np.ones(nd, bool) if fresh is None else np.asarray(fresh, bool)
    f = np.zeros(nd) if rates is None else np.asarray(rates, float)
    n = np.ones(nd, np.int64)
    return v2.Daily.build(np.asarray(close, float), fresh, f, n, mark)


class FreshnessTests(unittest.TestCase):
    def test_an_hourly_venue_that_traded_at_10_00_is_fresh(self):
        t0, nd = 0, 3
        t = np.array([DAY + 10 * H], float)                 # one hourly bar inside day 2's window (DAY, 2 DAY]
        c, vol = np.array([5.0]), np.array([1.0])
        _, fresh1 = v1.daily_prices(t, c, vol, H, t0, nd)
        close2, fresh2 = v2.daily_prices(t, c, vol, H, t0, nd)
        self.assertFalse(fresh1[2])
        self.assertTrue(fresh2[2])
        self.assertEqual(close2[2], 5.0)

    def test_daily_bars_are_fresh_the_same_way_in_both(self):
        t0, nd = 0, 4
        t = np.array([0, DAY, 2 * DAY], float)
        c, vol = np.array([1.0, 2.0, 3.0]), np.ones(3)
        self.assertEqual(list(v1.daily_prices(t, c, vol, DAY, t0, nd)[1]),
                         list(v2.daily_prices(t, c, vol, DAY, t0, nd)[1]))

    def test_a_bar_without_volume_is_not_fresh(self):
        _, fresh = v2.daily_prices(np.array([10 * H], float), np.array([5.0]), np.array([0.0]), H, 0, 2)
        self.assertFalse(fresh.any())


class MarkTests(unittest.TestCase):
    def test_marks_override_trades_where_held(self):
        m = v2.daily_marks(np.array([0, 23 * H], float), np.array([0.5, 0.6]), H, 0, 3)
        d = daily([1.19, 1.19, 1.19], mark=m)
        self.assertTrue(math.isnan(m[0]))
        self.assertEqual(list(d.val), [1.19, 0.6, 0.6])


def universe(a, b):
    return v1.Universe(["X"], ["A", "B"], [[a, b]], 0, len(a.close), corr_days=3, corr_min=-2.0, corr_obs=0)


class BookTests(unittest.TestCase):
    def pair(self, a, b, d=0):
        book = v2.Book([0, 1], lookback=1, threshold=0.0, slots=1)
        book.open = [v2.Position(0, 0, 1, d, 1.0, pl_e=float(a.val[d]), ph_e=float(b.val[d]))]
        return book

    def test_fixed_quantity_round_trip_earns_nothing(self):
        a, b = daily([100.0, 200.0, 100.0, 100.0]), daily([100.0] * 4)
        u, book = universe(a, b), None
        book = self.pair(a, b)
        g = [book.interval(u, d)[0] for d in range(3)]
        self.assertAlmostEqual(sum(g), 0.0)                 # constant notional would book +100% - 50% = +50%

    def test_no_price_gain_is_credited_on_an_interval_a_leg_did_not_trade(self):
        a = daily([1.0, 3.0, 3.0])                          # long leg pumps
        b = daily([1.0, 1.0, 1.0], fresh=[True, False, True])   # the short leg did not trade on day 1
        u = universe(a, b)
        book = self.pair(a, b)
        g, _, unobs = book.interval(u, 0)
        self.assertEqual((g, unobs), (0.0, 1))
        a2 = daily([1.0, 0.5, 0.5])
        book = self.pair(a2, b)
        self.assertAlmostEqual(book.interval(universe(a2, b), 0)[0], -0.5)   # a loss is kept

    def test_funding_is_paid_on_current_notional(self):
        a = daily([1.0, 1.0, 1.0])
        b = daily([1.0, 2.0, 2.0], rates=[0.0, 0.0, 0.01])  # the short leg doubles, then settles 1%
        u = universe(a, b)
        book = self.pair(a, b)
        book.interval(u, 0)
        _, f, _ = book.interval(u, 1)
        self.assertAlmostEqual(f, 0.02)

    def test_blowout_exit(self):
        a, b = daily([1.0, 1.3, 1.3]), daily([1.0, 1.0, 1.0])
        u = universe(a, b)
        book = self.pair(a, b)
        out = book.exits(u, 1)
        self.assertEqual([r for _, r in out], ["blowout"])

    def test_replay_records_reasons_and_pnl(self):
        path = [1.0, 1.1, 1.0, 1.2, 1.2, 1.2]                 # identical moves: the identity guard needs 3 returns
        a = daily(path, rates=[0] * 6)
        b = daily(path, rates=[0, 0.02, 0.02, 0.02, 0.02, 0.02])
        u = universe(a, b)
        rows, trades = v2.replay(u, v2.Book([0, 1], lookback=1, threshold=0.5, slots=1), 3)
        self.assertEqual(trades[0]["long"], "A")
        self.assertEqual(trades[0]["reason"], "end")
        self.assertAlmostEqual(trades[0]["funding_pnl"], 0.04)
        self.assertEqual(list(rows.unobserved), [0, 0])


if __name__ == "__main__":
    unittest.main()


class ParityTests(unittest.TestCase):
    def test_same_trades_as_the_frozen_rule_when_no_fix_binds(self):
        """Daily bars, every day traded, no blowout: v2 must open and close the same pairs on the same days as v1."""
        rng = np.random.default_rng(7)
        nd, keys = 120, ["C0", "C1", "C2", "C3"]
        series1, series2 = [], []
        for _ in keys:
            px = np.exp(np.cumsum(rng.normal(0, 0.02, nd)))
            row1, row2 = [], []
            for _venue in range(2):
                close = px * np.exp(rng.normal(0, 0.001, nd))
                rates = np.r_[0.0, rng.normal(0.0003, 0.0004, nd - 1)]
                n = np.ones(nd, np.int64)
                row1.append(v1.Daily.build(close, np.ones(nd, bool), rates, n))
                row2.append(v2.Daily.build(close, np.ones(nd, bool), rates, n))
            series1.append(row1)
            series2.append(row2)
        u1 = v1.Universe(keys, ["A", "B"], series1, 0, nd, corr_days=30, corr_min=0.5, corr_obs=20)
        u2 = v1.Universe(keys, ["A", "B"], series2, 0, nd, corr_days=30, corr_min=0.5, corr_obs=20)
        w0 = v1.window_start(u1, [0, 1], 14)
        _, t1 = v1.replay(u1, v1.Book([0, 1], 14, 0.05, 2), w0)
        _, t2 = v2.replay(u2, v2.Book([0, 1], 14, 0.05, 2), w0)
        key = lambda t: [(x["coin"], x["long"], x["entry_day"], x["exit_day"] if x["exit_day"] is not None
                          else nd - 1) for x in t]
        self.assertGreater(len(t1), 3)
        self.assertEqual(key(t1), key(t2))
        self.assertTrue(all(x["reason"] in ("spread", "end") for x in t2))
