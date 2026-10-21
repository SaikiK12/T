import unittest

import numpy as np

from lab import levcarry, xfund


def universe(nd=80, coins=3, pump=None, seed=0):
    """Two venues; venue 1 pays 3e-4 per settlement more than venue 0, so the book is long on 0 and short on 1.
    pump = (coin, day, size): venue 1's high on that day is size above the previous close."""
    rng = np.random.default_rng(seed)
    series, ranges = [], []
    for c in range(coins):
        px = 10 * np.exp(np.cumsum(rng.normal(0, 0.01, nd)))
        fresh = np.ones(nd, bool)
        n = np.full(nd, 3)
        s0 = xfund.Daily.build(px.copy(), fresh, np.zeros(nd), n)
        s1 = xfund.Daily.build(px.copy(), fresh, np.full(nd, 9e-4), n)
        hi, lo = px * 1.01, px * 0.99
        r1 = (hi.copy(), lo.copy())
        if pump and pump[0] == c:
            r1[0][pump[1]] = px[pump[1] - 1] * (1 + pump[2])
        series.append([s0, s1])
        ranges.append([(hi, lo), r1])
    u = xfund.Universe([f"C{c}" for c in range(coins)], ["v0", "v1"], series, 0, nd)
    return u, ranges


class LevCarryTest(unittest.TestCase):
    def test_without_liquidation_it_is_the_twin(self):
        u, ranges = universe()
        w0 = xfund.window_start(u, [0, 1], 14)
        want, trades = xfund.replay(u, xfund.Book([0, 1], 14, 0.05, 20), w0)
        got, events = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_daily", mm=-1e9)
        self.assertEqual(events, [])
        self.assertTrue(len(trades) > 0)
        for col in ("gross", "funding", "legs", "held"):
            np.testing.assert_allclose(got[col].to_numpy(), want[col].to_numpy(), atol=1e-12)

    def test_a_pump_liquidates_the_short_leg_at_3x_not_2x(self):
        u, ranges = universe(pump=(0, 50, 0.40))
        w0 = xfund.window_start(u, [0, 1], 14)
        _, ev2 = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 2, "iso_daily")
        days, ev3 = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_daily")
        self.assertEqual(ev2, [])
        self.assertEqual([(e["coin"], e["day"], e["leg"], e["venue"]) for e in ev3], [("C0", 50, "short", "v1")])
        row = days[days.day == 49].iloc[0]
        self.assertLess(row.gross, -1 / 3 + 0.05)          # the short's margin is gone; the long kept its day
        self.assertEqual(days[days.day == 50].iloc[0].legs, 4.0)   # its exit next day, and the rule re-enters it
        self.assertEqual(days[days.day == 50].iloc[0].held, 3)

    def test_a_cross_margin_account_absorbs_one_pump(self):
        u, ranges = universe(pump=(0, 50, 0.40))
        w0 = xfund.window_start(u, [0, 1], 14)
        _, ev = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "cross_daily")
        self.assertEqual(ev, [])
        _, ev = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 10, "cross_daily")
        self.assertEqual({e["venue"] for e in ev}, {"v1"})             # 3 x 1/10 cannot cover 0.40 + 0.02
        self.assertTrue(all(e["account"] for e in ev))

    def test_daily_range_maps_bars_to_the_day_they_end(self):
        day = xfund.DAY
        t = np.array([0, 23, 24, 47]) * xfund.H
        hi, lo = levcarry.daily_range(t, [1, 5, 2, 3], [1, 0.5, 2, 1], xfund.H, 0, 3)
        self.assertTrue(np.isnan(hi[0]))
        self.assertEqual((hi[1], lo[1]), (5, 0.5))
        self.assertEqual((hi[2], lo[2]), (3, 1))
        self.assertEqual(day, 86_400_000)


if __name__ == "__main__":
    unittest.main()
