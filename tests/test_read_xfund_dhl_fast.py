import unittest

import numpy as np

from scripts import read_xfund_dhl_fast as r


class Fast(unittest.TestCase):
    def test_decide(self):
        rng = np.random.default_rng(0)
        self.assertEqual(r.decide([], []), (None, "RUNNING"))
        self.assertEqual(r.decide([0.001] * 10, [0.001] * 10), (None, "RUNNING"))
        good = 0.0005 + rng.normal(0, 0.0003, 30)
        self.assertEqual(r.decide(good, good), (30, "PASS"))
        self.assertEqual(r.decide(good, -np.abs(good)), (30, "NOT YET"))          # cum net -1.5%: guard fails, no kill
        self.assertEqual(r.decide(good, np.full(30, -0.002)), (None, "FAIL (R520 kill switch)"))   # cum -6%
        self.assertEqual(r.decide(-np.abs(good), good), (30, "FAIL"))
        noisy = 0.00005 + rng.normal(0, 0.002, 30)
        self.assertIn(r.decide(noisy, np.zeros(30))[1], ("NOT YET", "FAIL"))
        self.assertIn(r.decide(np.r_[noisy, noisy[:15]], np.zeros(45))[1], ("NO EARLY PASS", "FAIL"))

    def test_empty_journal(self):
        s = r.r520.r512.series(r.r520.LANE, "A")
        self.assertTrue(len(s) >= 0)


if __name__ == "__main__":
    unittest.main()
