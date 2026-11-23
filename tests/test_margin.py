import math
import unittest

from lab import margin as m


class Margin(unittest.TestCase):
    def test_liq_move_long_and_short(self):
        # $1,000 equity, $3,000 long at 5% maintenance: 1000 - 3000x = 0.05*3000*(1-x) -> x = 850/2850
        self.assertAlmostEqual(m.liq_move(1000, [(3000, 0.05)]), 850 / 2850, places=12)
        # the same short: 1000 - 3000x = 0.05*3000*(1+x) -> x = 850/3150
        self.assertAlmostEqual(m.liq_move(1000, [(-3000, 0.05)]), 850 / 3150, places=12)
        self.assertEqual(m.liq_move(100, [(3000, 0.05)]), 0.0)
        self.assertEqual(m.liq_move(1000, [(3000, 0.05), (-3000, 0.05)]), math.inf)

    def test_split_equalises(self):
        e1, e2 = m.split(2000, 3000, 0.05, 0.05)
        self.assertAlmostEqual(e1 + e2, 2000, places=6)
        self.assertAlmostEqual(m.liq_move(e1, [(3000, 0.05)]), m.liq_move(e2, [(-3000, 0.05)]), places=6)

    def test_rebalance(self):
        x = m.rebalance(600, 1400, 3000, 0.05, 0.05, 0.20)          # long needs 150 + 2850*0.2 = 720
        self.assertGreater(x, 0)                                   # the long venue needs collateral
        self.assertAlmostEqual(x, 120.0, places=9)
        self.assertGreaterEqual(m.liq_move(600 + x, [(3000, 0.05)]), 0.20 - 1e-9)
        self.assertIsNone(m.rebalance(100, 100, 3000, 0.05, 0.05, 0.5))


if __name__ == "__main__":
    unittest.main()
