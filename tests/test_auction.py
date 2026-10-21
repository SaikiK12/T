import unittest

import numpy as np
import pandas as pd

from lab import auction as au


class AuctionTest(unittest.TestCase):
    def test_vwap_and_bands_reset_at_each_session(self):
        h = np.array([11, 13, 11, 21, 21.0])
        l = np.array([9, 11, 9, 19, 19.0])
        c = np.array([10, 12, 10, 20, 20.0])            # typical prices 10, 12, 10 then 20, 20
        v = np.array([1, 1, 2, 1, 3.0])
        out = au.vwap_bands(h, l, c, v, session=au.session_ids([0, 1, 2, 3, 4], [0, 3]))
        self.assertAlmostEqual(out.vwap[1], 11.0)
        self.assertAlmostEqual(out.sd[1], 1.0)          # values 10 and 12 with equal weight
        self.assertAlmostEqual(out.vwap[2], 10.5)       # (10 + 12 + 2 x 10) / 4
        self.assertAlmostEqual(out.up2[1], 13.0)
        self.assertEqual(list(out.vwap[3:]), [20.0, 20.0])
        self.assertEqual(list(out.sd[3:]), [0.0, 0.0])

    def test_session_ids_count_anchors_at_or_before_each_bar(self):
        self.assertEqual(list(au.session_ids([5, 10, 15, 20, 25], [10, 20])), [-1, 0, 0, 1, 1])

    def test_volume_profile_spreads_each_bar_evenly_and_keeps_the_total(self):
        p = au.volume_profile([10.9, 12.5], [10.0, 12.0], [4.0, 6.0], tick=0.5)
        self.assertEqual(list(p.index), [10.0, 10.5, 11.0, 11.5, 12.0, 12.5])
        self.assertEqual(list(p), [2.0, 2.0, 0.0, 0.0, 3.0, 3.0])
        self.assertAlmostEqual(p.sum(), 10.0)

    def test_tpo_counts_each_block_once_per_bin(self):
        p = au.tpo_profile([2.5, 2.2, 2.1, 1.4], [2.0, 2.0, 1.0, 1.0], tick=1.0, period=2)
        self.assertEqual(dict(p), {1.0: 1.0, 2.0: 2.0})   # block 0 touched 2; block 1 touched 1 and 2

    def test_value_area_grows_toward_the_larger_neighbour(self):
        prof = pd.Series([1, 2, 10, 5, 1, 1.0], index=[1, 2, 3, 4, 5, 6.0])   # total 20, 70% = 14
        self.assertEqual(au.value_area(prof), (3.0, 3.0, 4.0))                # 10, then 5 above: 15 >= 14
        self.assertEqual(au.value_area(prof, share=0.9), (3.0, 2.0, 5.0))     # then 2 below, then a tie goes up
        self.assertTrue(np.isnan(au.value_area(pd.Series(dtype=float))[0]))

    def test_nodes_find_the_two_peaks_and_the_gap_between(self):
        x = np.r_[np.full(5, 1.0), np.full(5, 10.0), np.full(5, 1.0), np.full(5, 0.1), np.full(5, 1.0),
                  np.full(5, 8.0), np.full(5, 1.0)]
        x = x + np.linspace(0, 0.01, len(x))                     # break ties
        hvn, lvn = au.nodes(pd.Series(x, index=np.arange(len(x), dtype=float)), width=3)
        self.assertEqual(len(hvn), 2)
        self.assertTrue(5 <= hvn[0] <= 9 and 25 <= hvn[1] <= 29)
        self.assertTrue(any(15 <= p <= 19 for p in lvn))

    def test_initial_balance_uses_bars_that_close_inside_the_window(self):
        t = np.arange(0, 6) * 60_000
        hi, lo = np.array([5, 6, 7, 99, 8, 9.0]), np.array([1, 2, 3, -9, 4, 5.0])
        self.assertEqual(au.initial_balance(t, hi, lo, start_ms=0, minutes=3), (7.0, 1.0))
        self.assertTrue(np.isnan(au.initial_balance(t, hi, lo, start_ms=10**9)[0]))


if __name__ == "__main__":
    unittest.main()
