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


if __name__ == "__main__":
    unittest.main()
