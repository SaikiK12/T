import unittest

import numpy as np

from lab import sizecarry, xfund


def universe(nd=120, spreads=(3e-4, 9e-4, 1.8e-3), seed=0, gaps=None):
    """Two venues per coin; venue 1 settles 3 times a day `spreads[c]` more than venue 0, so every coin's book is
    long on 0 and short on 1, with spreads that differ by coin. gaps = (coin, first day, last day) without venue 1
    settlements."""
    rng = np.random.default_rng(seed)
    series = []
    for c, sp in enumerate(spreads):
        px = 10 * np.exp(np.cumsum(rng.normal(0, 0.01, nd)))
        fresh, n = np.ones(nd, bool), np.full(nd, 3)
        f1 = np.full(nd, 3 * sp)
        if gaps and gaps[0] == c:
            f1[gaps[1]:gaps[2] + 1] = 0.0
        s0 = xfund.Daily.build(px.copy(), fresh, np.zeros(nd), n)
        s1 = xfund.Daily.build(px * np.exp(rng.normal(0, 0.0005 * (c + 1), nd)), fresh, f1, n)
        series.append([s0, s1])
    return xfund.Universe([f"C{c}" for c in range(len(spreads))], ["v0", "v1"], series, 0, nd)


class WeightsTest(unittest.TestCase):
    def test_weights_average_one_and_respect_the_cap(self):
        w = sizecarry.weights([1, 1, 1, 100], cap=3.0)
        self.assertAlmostEqual(w.sum(), 4.0)
        self.assertAlmostEqual(w.max(), 3.0)
        np.testing.assert_allclose(w[:3], [1 / 3] * 3)
        np.testing.assert_allclose(sizecarry.weights([2, 2]), [1, 1])
        np.testing.assert_allclose(sizecarry.weights([0, 0, 0]), [1, 1, 1])
        self.assertEqual(len(sizecarry.weights([])), 0)

    def test_water_filling_redistributes_twice(self):
        w = sizecarry.weights([100, 90, 1, 1, 1, 1], cap=2.0)
        np.testing.assert_allclose(w[:2], [2, 2])
        np.testing.assert_allclose(w[2:], [0.5] * 4)


class SizeCarryTest(unittest.TestCase):
    def test_equal_is_the_twin(self):
        u = universe()
        w0 = xfund.window_start(u, [0, 1], 14)
        want, trades = xfund.replay(u, xfund.Book([0, 1], 14, 0.05, 20), w0)
        got = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "equal")
        self.assertTrue(len(trades) >= 3)
        for col in ("gross", "funding", "legs", "held"):
            np.testing.assert_array_equal(got[col].to_numpy(), want[col].to_numpy())
        self.assertEqual(got.max_w.max(), 1.0)

    def test_spread_sizing_holds_the_same_pairs_and_tilts_to_the_widest(self):
        u = universe()
        w0 = xfund.window_start(u, [0, 1], 14)
        eq = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "equal")
        sp = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "spread")
        np.testing.assert_array_equal(sp.held.to_numpy(), eq.held.to_numpy())
        last = sp.iloc[-2]
        # spreads 1 : 3 : 6 -> weights 0.3, 0.9, 1.8 once all three are held
        self.assertAlmostEqual(last.max_w, 1.8, places=6)
        self.assertGreater(sp.funding.sum(), eq.funding.sum())     # more notional where the spread is wider

    def test_a_score_only_uses_days_up_to_the_decision(self):
        u = universe()
        book = xfund.Book([0, 1], 14, 0.05, 20)
        w0 = xfund.window_start(u, [0, 1], 14)
        for d in range(w0, w0 + 20):
            book.exits(u, d)
            book.entries(u, d)
        p, d = book.open[0], w0 + 19
        before = {k: sizecarry.score(u, p, d, book, k) for k in sizecarry.SCORES}
        later = universe()                                        # the same history, then a different future
        for c in range(3):
            for s in later.series[c]:
                s.close[d + 1:] *= 2.0
                s.cumf[d + 1:] += 1.0
        after = {k: sizecarry.score(later, p, d, book, k) for k in sizecarry.SCORES}
        self.assertEqual(before, after)

    def test_persistence_falls_after_a_funding_gap(self):
        u = universe(gaps=(0, 40, 60))                             # coin 0 (0.33/yr) stops paying the spread
        book = xfund.Book([0, 1], 14, 0.05, 20)
        p = xfund.Position(0, 0, 1, 30, 0.33)
        self.assertEqual(sizecarry.score(u, p, 39, book, "persist"), 1.0)
        per = sizecarry.score(u, p, 60, book, "persist")
        self.assertGreater(per, 0.0)
        self.assertLess(per, 0.5)
        self.assertEqual(sizecarry.score(u, p, 60, book, "spread"), 0.0)

    def test_rebalancing_is_charged_beyond_the_band(self):
        u = universe()
        w0 = xfund.window_start(u, [0, 1], 14)
        eq = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "equal")
        iv = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "inv_vol", band=0.0)
        wide = sizecarry.run(u, xfund.Book([0, 1], 14, 0.05, 20), w0, "inv_vol", band=10.0)
        self.assertGreater(iv.legs.sum(), wide.legs.sum())
        self.assertEqual(eq.legs.sum(), 2.0 * 2 * 3)             # 3 pairs, each entered and closed once


if __name__ == "__main__":
    unittest.main()
