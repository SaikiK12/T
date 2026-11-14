import unittest

import numpy as np

from lab import carry


class CarryTests(unittest.TestCase):
    def test_trailing_apr(self):
        f = np.zeros((48, 1))
        f[7::8, 0] = 0.0001                     # 1 bp every 8 h = 3 bp/day
        apr = carry.trailing_apr(f, look=24)
        self.assertTrue(np.isnan(apr[22, 0]))
        self.assertAlmostEqual(apr[47, 0], 0.0003 * 365, places=9)

    def test_collects_funding_pays_basis_and_four_trades(self):
        T, S = 30, 1
        fund = np.zeros((T, S)); fund[10, 0] = 0.001; fund[18, 0] = 0.001
        apr = np.zeros((T, S)); apr[5:20, 0] = 1.0       # signal on from row 5 to 19
        basis = np.zeros((T, S)); basis[12:, 0] = 0.0005  # basis widens while held: the short loses 5 bp
        elig = np.ones((T, S), bool)
        cost = np.full((T, S), 0.0005)
        out = carry.run(apr, fund, basis, elig, [True], cost, 0.001, 0.5, 0.25, 0, T, slots=1)
        self.assertAlmostEqual(out[:, 1].sum(), 0.002)
        self.assertAlmostEqual(out[:, 2].sum(), -0.0005)
        self.assertAlmostEqual(out[:, 3].sum(), 2 * (0.0005 + 0.001))
        self.assertEqual(out[:, 4].max(), 1)

    def test_no_spot_no_trade(self):
        T, S = 10, 1
        out = carry.run(np.ones((T, S)), np.full((T, S), 0.001), np.zeros((T, S)), np.ones((T, S), bool), [False],
                        np.zeros((T, S)), 0.0, 0.5, 0.25, 0, T)
        self.assertEqual(out[:, 1].sum(), 0)

    def test_spot_pair(self):
        spot = {"BONKUSDT", "BTCUSDT", "FILUSDT"}
        self.assertEqual(carry.spot_pair(["1000BONK"], spot), "BONKUSDT")
        self.assertEqual(carry.spot_pair(["BTC"], spot), "BTCUSDT")
        self.assertEqual(carry.spot_pair(["FILECOIN", "FIL"], spot), "FILUSDT")
        self.assertIsNone(carry.spot_pair(["XAU"], spot))


if __name__ == "__main__":
    unittest.main()
