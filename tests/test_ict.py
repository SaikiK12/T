import unittest

import numpy as np

from lab import ict


def col(*vals):
    return np.array(vals, dtype=np.float32).reshape(-1, 1)


class FvgTests(unittest.TestCase):
    def test_bullish_gap_forms_reports_distance_and_dies_on_fill(self):
        high = col(10, 11, 14, 14.5, 14, 12, 9)
        low = col(9, 10, 12, 11, 12, 10.5, 8)
        close = col(9.5, 10.5, 13, 14, 13, 11, 8.5)
        atr = np.ones_like(close)
        bd, ba, sd, sa = ict.fvg(high, low, close, atr, 0.0)
        self.assertTrue(np.isnan(bd[1, 0]))                       # nothing yet
        self.assertAlmostEqual(float(bd[2, 0]), 1.0)               # zone [10, 12]; close 13 is 1 ATR above its top
        self.assertEqual(float(ba[2, 0]), 0.0)
        self.assertEqual(float(ba[3, 0]), 1.0)
        self.assertAlmostEqual(float(bd[5, 0]), 0.0)               # close 11 is inside the zone [10, 12]: distance 0
        self.assertTrue(np.isnan(bd[6, 0]))                        # low 8 <= bottom 10: filled
        self.assertTrue(np.isnan(sd[:6]).all())                    # the last bar's drop is a real bearish gap, so stop at 5

    def test_gap_smaller_than_min_gap_is_ignored(self):
        high = col(10, 11, 14)
        low = col(9, 10, 12)
        close = col(9.5, 10.5, 13)
        bd = ict.fvg(high, low, close, np.ones_like(close), 3.0)[0]
        self.assertTrue(np.isnan(bd).all())                        # gap of 2 < 3 ATR

    def test_bearish_gap(self):
        high = col(11, 10, 8, 9)
        low = col(10, 9, 7, 6.5)
        close = col(10.5, 9.5, 7.5, 7)
        _, _, sd, sa = ict.fvg(high, low, close, np.ones_like(close), 0.0)
        # zone [high[2], low[0]] = [8, 10]; close 7.5 is 0.5 below its bottom
        self.assertAlmostEqual(float(sd[2, 0]), 0.5)
        self.assertEqual(float(sa[3, 0]), 1.0)


class SweepTests(unittest.TestCase):
    def test_bullish_sweep_needs_close_back_above(self):
        low = col(5, 5, 5, 4, 5, 3.5)
        high = col(6, 6, 6, 6, 6, 6)
        close = col(5.5, 5.5, 5.5, 6, 5.5, 3.8)
        bs, ss = ict.sweep(high, low, close, 3)
        self.assertEqual(float(bs[3, 0]), 0.0)                     # low 4 < 5, close 6 > 5
        self.assertEqual(float(bs[4, 0]), 1.0)
        self.assertEqual(float(bs[5, 0]), 2.0)                     # low 3.5 < 4 but close 3.8 < 4: not a sweep
        self.assertTrue(np.isnan(bs[2, 0]))


class StructureTests(unittest.TestCase):
    def test_break_of_swing_high_sets_state_up(self):
        low = col(1, 0.5, 1, 1.2, 1.1, 2.0, 2.4, 2.2)
        high = low + 1
        close = (high + low) / 2
        state, since, pdisc, ote = ict.structure(high, low, close, 1)
        self.assertTrue(np.isnan(state[:5, 0]).all())
        self.assertEqual(float(state[5, 0]), 1.0)
        self.assertEqual(float(since[5, 0]), 0.0)
        self.assertEqual(float(since[6, 0]), 1.0)
        # row 4 (low 1.1) is itself a confirmed swing low by row 5, so the range is [1.1, 2.2]
        self.assertAlmostEqual(float(pdisc[5, 0]), (2.5 - 1.1) / (2.2 - 1.1), places=5)

    def test_a_high_exceeded_by_the_next_bar_is_not_a_swing(self):
        low = col(1, 0.5, 1, 1.5, 1.2, 1.0)
        high = col(2, 1.5, 2, 3.0, 3.5, 2.0)                       # row 3 is not a swing high: row 4 is higher
        close = (high + low) / 2
        self.assertTrue(np.isnan(ict.structure(high, low, close, 1)[0]).all())


class OrderBlockTests(unittest.TestCase):
    def test_bullish_block_and_mitigation(self):
        open_ = col(10, 10, 10, 10, 9, 12, 12)
        close = col(10, 10, 10, 9, 12, 12.5, 8)
        high = col(10.5, 10.5, 10.5, 10.5, 12.5, 13, 12.2)
        low = col(9.5, 9.5, 9.5, 8.5, 9, 11.5, 7.5)
        atr = np.ones_like(close)
        bd, sd = ict.order_block(open_, high, low, close, atr, 2.0, 3)
        # bar 4 is the displacement (+3 >= 2 ATR); bar 3 is the last down-close bar: zone [8.5, 10.5]
        self.assertAlmostEqual(float(bd[4, 0]), (12 - 10.5) / 1.0)
        self.assertAlmostEqual(float(bd[5, 0]), 2.0)
        self.assertTrue(np.isnan(bd[6, 0]))                        # close 8 < 8.5 kills it


class CausalityTests(unittest.TestCase):
    def test_rows_up_to_a_cutoff_ignore_everything_after(self):
        rng = np.random.default_rng(7)
        T, S = 600, 5
        close = (100 * np.exp(np.cumsum(rng.normal(0, 0.01, (T, S)), 0))).astype(np.float32)
        open_ = np.vstack([close[:1], close[:-1]])
        high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.005, (T, S))).astype(np.float32)
        low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.005, (T, S))).astype(np.float32)
        atr = (close * 0.01).astype(np.float32)

        def run(h, l, c, o, a):
            out = list(ict.fvg(h, l, c, a, 0.0)) + list(ict.order_block(o, h, l, c, a, 1.5, 5))
            out += list(ict.sweep(h, l, c, 20)) + list(ict.structure(h, l, c, 3))
            return out

        full = run(high, low, close, open_, atr)
        for cut in (150, 333, 480):
            cropped = [x.copy() for x in (high, low, close, open_, atr)]
            for x in cropped:
                x[cut + 1:] = np.nan
            part = run(*cropped)
            for a, b in zip(full, part):
                np.testing.assert_array_equal(a[: cut + 1], b[: cut + 1])
        self.assertGreater(sum(int(np.isfinite(x).sum()) for x in full), 1000)  # the test is not vacuous


if __name__ == "__main__":
    unittest.main()
