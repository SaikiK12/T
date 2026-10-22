import unittest

import numpy as np

from lab import orderflow as of


class OrderflowTest(unittest.TestCase):
    def test_delta_is_taker_buys_minus_taker_sells_and_cvd_resets_by_session(self):
        d = of.delta([10, 10, 4, 6], [7, 2, 4, 3])
        self.assertEqual(list(d), [4, -6, 4, 0])
        self.assertEqual(list(of.cvd(d)), [4, -2, 2, 2])
        self.assertEqual(list(of.cvd(d, session=[0, 0, 1, 1])), [4, -2, 4, 4])

    def test_delta_profile_keeps_the_sign_and_the_total(self):
        p = of.delta_profile([10.9, 12.5], [10.0, 12.0], [4.0, -6.0], tick=0.5)
        self.assertEqual(list(p), [2.0, 2.0, 0.0, 0.0, -3.0, -3.0])

    def test_absorption_flags_big_aggression_that_did_not_move_price(self):
        n = 30
        d = np.r_[np.full(n, 1.0), 10.0, -10.0, 10.0]
        r = np.r_[np.tile([0.01, -0.01], n // 2), 0.001, 0.001, 0.05]
        a = of.absorption(d, r, window=20, k=3.0, m=0.5)
        self.assertEqual(list(a[:n]), [0] * n)
        self.assertEqual(list(a[n:]), [1, -1, 0])          # the last bar moved price: not absorption

    def test_exhaustion_flags_a_new_high_on_weaker_running_delta(self):
        hi = np.array([10, 11, 12, 13, 12, 11, 14.0])
        lo = hi - 1
        d = np.array([5, 5, 5, 5, -9, -9, 1.0])            # running sum 5 10 15 20 11 2 3
        e = of.exhaustion(hi, lo, d, window=4)
        self.assertEqual(list(e), [0, 0, 0, 0, 0, 0, -1])  # 14 is a new high, 3 < max(20, 11, 2, ...)

        e2 = of.exhaustion(hi, lo, np.array([5, 5, 5, 5, -9, -9, 30.0]), window=4)
        self.assertEqual(e2[-1], 0)                        # a new high confirmed by the running sum

    def test_volume_buckets_split_bars_and_follow_a_changing_size(self):
        end, share = of.volume_buckets([1, 1, 2, 0, 1], [1, 0, 1, 0, 1], 2.0)
        self.assertEqual(list(end), [1, 2])                 # bucket 2 fills inside bar 2; the last half-bucket waits
        self.assertEqual(list(share), [0.5, 0.5])
        end, share = of.volume_buckets([3, 1], [3, 0], 2.0)
        self.assertEqual(list(end), [0, 1])
        self.assertEqual(list(share), [1.0, 0.5])           # one unit of bar 0's buying spills into bucket 2
        end, share = of.volume_buckets([2, 2, np.nan], [2, 0, np.nan], [1.0, 2.0, 2.0])
        self.assertEqual(list(end), [0, 0, 1])
        self.assertEqual(list(share), [1.0, 1.0, 0.0])

    def test_vpin_is_the_mean_bucket_imbalance(self):
        v = of.vpin([1.0, 0.5, 0.0, 0.5], n=2)
        self.assertTrue(np.isnan(v[0]))
        self.assertEqual(list(v[1:]), [0.5, 0.5, 0.5])

    def test_bvc_buy_splits_volume_by_the_normal_cdf(self):
        b = of.bvc_buy([10.0, 10.0, 10.0], [0.0, 1.0, -1.0], 1.0)
        self.assertAlmostEqual(b[0], 5.0)
        self.assertAlmostEqual(b[1] + b[2], 10.0)
        self.assertAlmostEqual(b[1], 8.413447, places=5)


if __name__ == "__main__":
    unittest.main()
