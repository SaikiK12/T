import unittest

import numpy as np
import pandas as pd

from scripts import run_fundvol as fv


class FundVolTest(unittest.TestCase):
    def test_scale_gate_and_no_lookahead(self):
        rng = np.random.default_rng(0)
        r = pd.Series(rng.normal(0, 0.01, 300), index=pd.date_range("2022-01-01", periods=300))
        r.iloc[200:210] *= 10
        v = fv.trailing_vol(r, 7, r.index)
        self.assertTrue(v.iloc[:8].isna().all())  # 7-day window plus the two-day lag
        ws, wg = fv.weights(v, "scale"), fv.weights(v, "gate")
        self.assertTrue((ws >= 0).all() and (ws <= fv.CAP).all())
        self.assertTrue(set(wg.unique()) <= {0.0, 1.0})
        self.assertEqual(wg.iloc[205], 0.0)  # the spike's trailing vol is above the expanding 80th percentile
        self.assertLess(ws.iloc[206], 1.0)
        r2 = r.copy()
        r2.iloc[250:] *= 5  # the future changes; earlier weights must not
        w2 = fv.weights(fv.trailing_vol(r2, 7, r.index), "scale")
        self.assertTrue(np.allclose(ws.iloc[:252], w2.iloc[:252]))

    def test_sized_cost_of_changing_weight(self):
        ix = pd.date_range("2022-01-01", periods=3)
        net = pd.Series([0.001, 0.001, 0.001], index=ix)
        w = pd.Series([1.0, 0.0, 1.0], index=ix)
        s = fv.sized(net, w, pd.Series(20.0, index=ix), 2)
        self.assertAlmostEqual(s.iloc[0], 0.001)
        self.assertAlmostEqual(s.iloc[1], -0.0014)  # full book unwound at 2x: 14 bp
        self.assertAlmostEqual(s.iloc[2], 0.001 - 0.0014)

    def test_boot_p(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0.001, 0.01, 800)
        d, p = fv.boot_p(x, x, reps=500)
        self.assertEqual(d, 0.0)
        self.assertGreater(p, 0.05)
        y = x + rng.normal(0, 0.0005, 800)
        z = x + 0.004 + rng.normal(0, 0.0005, 800)
        d, p = fv.boot_p(z, y, reps=500)
        self.assertGreater(d, 0)
        self.assertLess(p, 0.05)


if __name__ == "__main__":
    unittest.main()
