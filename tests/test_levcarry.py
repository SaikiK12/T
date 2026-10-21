import unittest

import numpy as np

from lab import levcarry, xfund


def flat_universe(f_long, f_short, nd=80, seed=0):
    """One coin quoted alike on two venues with tiny moves; venue 0 settles f_long a day, venue 1 f_short."""
    rng = np.random.default_rng(seed)
    px = 10 * np.exp(np.cumsum(rng.normal(0, 1e-4, nd)))
    fresh, n = np.ones(nd, bool), np.full(nd, 3)
    s0 = xfund.Daily.build(px.copy(), fresh, np.full(nd, f_long), n)
    s1 = xfund.Daily.build(px.copy(), fresh, np.full(nd, f_short), n)
    u = xfund.Universe(["C0"], ["v0", "v1"], [[s0, s1]], 0, nd)
    return u, [[(px * 1.0005, px * 0.9995), (px * 1.0005, px * 0.9995)]]


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

    def test_funding_paid_drains_an_isolated_margin(self):
        """Codex's counterexample (#7): flat quotes, the long pays 2% a day and the short earns 4%. At 3x the long's
        isolated margin (1/3) is gone after about 15 days of debits; a margin reset every day survives them."""
        u, ranges = flat_universe(0.02, 0.04)
        w0 = xfund.window_start(u, [0, 1], 14)
        _, ev = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_hold")
        self.assertTrue(ev)
        self.assertEqual(ev[0]["leg"], "long")
        self.assertTrue(14 <= ev[0]["day"] - w0 <= 17, ev[0]["day"] - w0)
        _, ev = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_daily")
        self.assertEqual(ev, [])

    def test_an_unknown_range_falls_back_to_the_close_and_is_counted(self):
        u, ranges = universe(pump=(0, 50, 0.40))
        for c in range(len(ranges)):
            ranges[c][1] = None                          # venue 1 (every short leg) has no range
        w0 = xfund.window_start(u, [0, 1], 14)
        days, ev = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_daily")
        self.assertEqual(ev, [])                         # the pump is in the unseen high only
        np.testing.assert_array_equal(days.unknown.to_numpy(), days.exposed.to_numpy() / 2)
        s0 = u.series[0][1]
        w, known = levcarry.adverse(s0, None, -1, 49)
        self.assertFalse(known)
        self.assertAlmostEqual(w, max(0.0, s0.close[50] / s0.close[49] - 1))

    def test_the_runner_summary_counts_and_scales(self):
        from scripts import run_levcarry
        u, ranges = universe(pump=(0, 50, 0.40))
        w0 = xfund.window_start(u, [0, 1], 14)
        days1, _ = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 1, "iso_daily")
        days3, ev3 = levcarry.run(u, ranges, xfund.Book([0, 1], 14, 0.05, 20), w0, 3, "iso_daily")
        s1 = run_levcarry.summarize(days1, [], 20, 1)
        s3 = run_levcarry.summarize(days3, ev3, 20, 3)
        self.assertEqual((s3["liquidated_legs"], s3["pairs_closed"], s3["days"]), (1, 1, len(days3)))
        self.assertEqual(s1["unknown_range_share"], 0.0)
        self.assertLess(s3["worst_day_pct"], s1["worst_day_pct"])       # the lost margin shows on its day
        self.assertLess(s3["max_dd_pct"], 0)
        self.assertGreater(s3["ann_1x_pct"], s3["ann_3x_pct"])


if __name__ == "__main__":
    unittest.main()
