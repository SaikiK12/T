import unittest

import numpy as np
import pandas as pd

from scripts import read_combined_gap3_fast as r


def lane(days, fund, net):
    return pd.DataFrame({"day": days, "fund_book": fund, "net_book": net})


class Combo3(unittest.TestCase):
    def test_combine_common_days(self):
        a = lane(["d1", "d2", "d3"], [1.0, 2.0, 3.0], [0.1, 0.2, 0.3])
        b = lane(["d2", "d3", "d4"], [3.0, 5.0, 7.0], [0.3, 0.5, 0.7])
        c = lane(["d3", "d4"], [8.0, 9.0], [0.9, 0.9])
        m = r.combine(a, b, c)
        self.assertEqual(m.day.tolist(), ["d3"])
        self.assertAlmostEqual(m.fund_book.iloc[0], 16.0 / 3)
        self.assertAlmostEqual(m.net_bitfinex.iloc[0], 0.9)
        self.assertTrue(r.combine(a, b, c.iloc[0:0]).empty)

    def test_decide(self):
        rng = np.random.default_rng(0)
        days = [f"d{i:03d}" for i in range(30)]
        good = 0.0005 + rng.normal(0, 0.0002, 30)
        c = r.combine(lane(days, good, good), lane(days, good, good), lane(days, good, good))
        self.assertEqual(r.decide(c.iloc[:10]), (None, "RUNNING"))
        self.assertEqual(r.decide(c.iloc[:20]), (20, "PASS"))
        bad = r.combine(*(lane(days, -np.abs(good), good) for _ in range(3)))
        self.assertEqual(r.decide(bad.iloc[:20]), (20, "FAIL"))
        crash = r.combine(lane(days, good, good), lane(days, good, good), lane(days, good, np.full(30, -0.002)))
        self.assertEqual(r.decide(crash.iloc[:20]), (None, "FAIL (a lane's kill switch)"))
        flat = r.combine(*(lane(days, rng.normal(0.00001, 0.001, 30), good) for _ in range(3)))
        self.assertIn(r.decide(flat)[1], ("NO EARLY PASS", "FAIL"))

    def test_runs_on_the_live_journals(self):
        c = r.combine(*r.lanes())
        self.assertIn("fund_book", c.columns)
        self.assertIn(r.decide(c)[1], ("RUNNING", "PASS", "FAIL", "NOT YET", "NO EARLY PASS", "FAIL (a lane's kill switch)"))


if __name__ == "__main__":
    unittest.main()
