import unittest

import numpy as np
import pandas as pd

from scripts import read_combined_gap_fast as r


def lane(days, fund, net):
    return pd.DataFrame({"day": days, "fund_book": fund, "net_book": net})


class Combo(unittest.TestCase):
    def test_combine_common_days(self):
        a = lane(["d1", "d2", "d3"], [1.0, 2.0, 3.0], [0.1, 0.2, 0.3])
        b = lane(["d2", "d3", "d4"], [3.0, 5.0, 7.0], [0.3, 0.5, 0.7])
        c = r.combine(a, b)
        self.assertEqual(c.day.tolist(), ["d2", "d3"])
        self.assertEqual(c.fund_book.tolist(), [2.5, 4.0])
        self.assertTrue(r.combine(a, b.iloc[0:0]).empty)

    def test_decide(self):
        rng = np.random.default_rng(0)
        days = [f"d{i:03d}" for i in range(30)]
        good = 0.0005 + rng.normal(0, 0.0002, 30)
        c = r.combine(lane(days, good, good), lane(days, good, good))
        self.assertEqual(r.decide(c.iloc[:10]), (None, "RUNNING"))
        self.assertEqual(r.decide(c.iloc[:20]), (20, "PASS"))
        bad = r.combine(lane(days, -np.abs(good), good), lane(days, -np.abs(good), good))
        self.assertEqual(r.decide(bad.iloc[:20]), (20, "FAIL"))
        crash = r.combine(lane(days, good, np.full(30, -0.002)), lane(days, good, good))
        self.assertEqual(r.decide(crash.iloc[:20]), (None, "FAIL (a lane's kill switch)"))

    def test_runs_on_the_live_journals(self):
        c = r.combine(r.r510.series(), r.r520.r512.series(r.r520.LANE, "A"))
        self.assertIn("fund_book", c.columns)


if __name__ == "__main__":
    unittest.main()
