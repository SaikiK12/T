import unittest

import numpy as np

from lab import events


class EventTests(unittest.TestCase):
    def test_event_window_and_benchmark(self):
        ret = np.zeros((100, 2), np.float32)
        ret[10:20, 0] = 0.01
        bench = np.full(100, 0.001, np.float32)
        r, b = events.event_returns(ret, [(0, 5), (1, 95)], delay=5, hold=10, bench=bench)
        self.assertAlmostEqual(r[0], 0.10, places=6)
        self.assertAlmostEqual(b[0], 0.01, places=6)
        self.assertTrue(np.isnan(r[1]))                    # window passes the end

    def test_clustered_t_shrinks_with_correlated_events(self):
        rng = np.random.default_rng(0)
        common = np.repeat(rng.standard_normal(20), 10)    # 20 clusters of 10 identical shocks
        x = 0.1 + common + 0.1 * rng.standard_normal(200)
        n, mu, t_cl = events.clustered_t(x, np.repeat(np.arange(20), 10))
        _, _, t_iid = events.clustered_t(x, np.arange(200))
        self.assertLess(abs(t_cl), abs(t_iid) / 2)

    def test_book_short_hedged_with_costs(self):
        T = 24 * 10
        ret = np.zeros((T, 1), np.float32)
        ret[24:48, 0] = -0.01                              # the symbol falls 24 x 1%
        bench = np.zeros(T, np.float32)
        cost = np.full((T, 1), 0.001, np.float32)
        net, gross, n = events.book(ret, [(0, 23)], delay=1, hold=24, side=-1, bench=bench, cost=cost, slots=1)
        self.assertAlmostEqual(gross.sum(), 0.24, places=5)
        self.assertAlmostEqual(gross.sum() - net.sum(), 0.004, places=6)   # 2 legs x in and out x 10 bp


if __name__ == "__main__":
    unittest.main()
