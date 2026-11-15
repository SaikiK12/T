"""The sizing rule must be ex-ante, and the split must not leak."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("cs", ROOT / "scripts/run_capsizing.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()
        cls.cv = {"kucoin": {"a_bp": 0.5, "beta": 0.5, "depth_usd": 8000.0},
                  "gate": {"a_bp": 0.33, "beta": 0.567, "depth_usd": 7846.0}}

    def row(self, spread=0.30, hold=30, long="kucoin", short="gate"):
        return pd.Series({"spread_in_ann": spread, "hold": hold, "long": long, "short": short}).to_frame().T.iloc[0]

    def test_size_depends_only_on_entry_fields(self):
        r = self.row()
        n1, _, _ = self.m.size_of(r, 1.0, self.cv)
        r2 = r.copy()
        r2["gross"] = 99.0          # realised PnL must not change the chosen size
        r2["price_pnl"] = 99.0
        n2, _, _ = self.m.size_of(r2, 1.0, self.cv)
        self.assertEqual(n1, n2)

    def test_bigger_entry_spread_gets_a_bigger_size(self):
        n_lo, _, _ = self.m.size_of(self.row(spread=0.05), 1.0, self.cv)
        n_hi, _, _ = self.m.size_of(self.row(spread=0.80), 1.0, self.cv)
        self.assertGreater(n_hi, n_lo)

    def test_nonpositive_forecast_takes_the_floor_not_zero(self):
        n, b, _ = self.m.size_of(self.row(spread=-0.1), 1.0, self.cv)
        self.assertEqual(n, self.m.MIN_N)
        self.assertEqual(b, "nonpositive_forecast")

    def test_missing_curve_is_named_not_silently_zero(self):
        n, b, _ = self.m.size_of(self.row(long="nowhere", short="nowhere"), 1.0, self.cv)
        self.assertEqual(b, "no_curve")
        self.assertEqual(n, self.m.MIN_N)

    def test_worse_leg_is_charged(self):
        cheap = self.m.capacity.cost_bp(10000, self.cv["gate"]["a_bp"], self.cv["gate"]["beta"])
        dear = self.m.capacity.cost_bp(10000, self.cv["kucoin"]["a_bp"], self.cv["kucoin"]["beta"])
        self.assertEqual(self.m.worse("gate", "kucoin", self.cv, 10000), max(cheap, dear))

    def test_size_is_capped(self):
        n, _, _ = self.m.size_of(self.row(spread=5.0, hold=200), 1.0, self.cv)
        self.assertLessEqual(n, self.m.CAP)

    def test_discovery_fit_uses_only_discovery_rows(self):
        t = self.m.load()
        d = t[t.entry < self.m.SPLIT]
        k, hold = self.m.fit_discovery(d)
        self.assertTrue(np.isfinite(k))
        self.assertGreater(k, 0)
        self.assertEqual(hold, float(d.hold.median()))
        self.assertTrue((d.entry < self.m.SPLIT).all())

    def test_bootstrap_of_a_zero_difference_is_centred(self):
        lo, hi, p = self.m.block_bootstrap_diff(np.zeros(500))
        self.assertAlmostEqual(lo, 0.0, places=9)
        self.assertAlmostEqual(hi, 0.0, places=9)

    def test_bootstrap_detects_a_clear_positive_difference(self):
        rng = np.random.default_rng(0)
        lo, hi, p = self.m.block_bootstrap_diff(rng.normal(5.0, 1.0, 800))
        self.assertGreater(lo, 0.0)
        self.assertLess(p, 0.05)


if __name__ == "__main__":
    unittest.main()
