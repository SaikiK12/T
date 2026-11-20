import math
import unittest

import numpy as np

from lab import sizing


class Sizing(unittest.TestCase):
    def test_lambda(self):
        self.assertAlmostEqual(sizing.rck_lambda(0.8, 0.05), math.log(0.05) / math.log(0.8))
        self.assertAlmostEqual(sizing.rck_lambda(0.8, 0.05), 13.425, places=3)

    def test_constraint_bounds_drawdown_by_simulation(self):
        rng = np.random.default_rng(3)
        r = rng.normal(0.002, 0.02, 2000)                          # a noisy positive edge
        lev, _ = sizing.rck_leverage(r, 0.8, 0.05)
        self.assertGreater(lev, 0)
        paths = rng.choice(r, size=(2000, 500))                    # resampled 500-period paths at that leverage
        wealth = np.cumprod(1 + lev * paths, axis=1)
        self.assertLess(float((wealth.min(axis=1) < 0.8).mean()), 0.05)

    def test_no_edge_no_leverage_and_shrink(self):
        rng = np.random.default_rng(1)
        r = rng.normal(0.0, 0.01, 1000)
        r = r - r.mean() - 1e-4                                     # a small negative mean
        self.assertEqual(sizing.rck_leverage(r)[0], 0.0)
        s = sizing.scale_mean(r + 0.001, 0.5)
        self.assertAlmostEqual(s.mean(), (r.mean() + 0.001) * 0.5)
        self.assertAlmostEqual(s.std(), r.std())

    def test_liquidation_cap_binds(self):
        self.assertAlmostEqual(sizing.liquidation_cap(0.30, 0.03), 0.5 / 0.33)
        rng = np.random.default_rng(2)
        out = sizing.size(rng.normal(0.0007, 0.002, 1000), adverse_move=0.30)
        self.assertEqual(out["binding"], "liquidation")
        self.assertAlmostEqual(out["leverage"], 0.5 * 0.5 / 0.33)


if __name__ == "__main__":
    unittest.main()
