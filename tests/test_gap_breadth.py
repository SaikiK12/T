import unittest

import numpy as np

from scripts import run_gap_breadth as g


class Breadth(unittest.TestCase):
    def test_stats_and_pairs(self):
        self.assertEqual(len(g.FLOORLESS) * len(g.FLOOR), 12)
        self.assertEqual(len([1 for a in g.FLOORLESS for b in g.FLOOR if (a, b) not in g.KNOWN]), 9)
        s = g.stats(np.full(40, 0.001))
        self.assertAlmostEqual(s["ann_pct"], 36.5)
        self.assertEqual(s["max_dd_pct"], 0.0)
        self.assertEqual(g.stats([0.1] * 5), {"days": 5})


if __name__ == "__main__":
    unittest.main()
