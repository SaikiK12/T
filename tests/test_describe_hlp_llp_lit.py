import importlib.util
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("describe_hlp_llp_lit", ROOT / "scripts" / "describe_hlp_llp_lit.py")
d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d)


class DescribeTests(unittest.TestCase):
    def test_drawdowns_find_peak_trough_and_recovery(self):
        level = pd.Series([1.0, 2.0, 1.0, 1.5, 2.5, 2.0, 2.4],
                          index=["d1", "d2", "d3", "d4", "d5", "d6", "d7"])
        out = d.drawdowns(level, 3)
        self.assertEqual(out[0], {"peak": "d2", "trough": "d3", "fall_pct": -50.0, "recovered": "d5"})
        self.assertEqual(out[1], {"peak": "d5", "trough": "d6", "fall_pct": -20.0, "recovered": None})
        self.assertEqual(len(out), 2)

    def test_monthly_compounds_daily_returns(self):
        ret = pd.Series([0.10, 0.10, -0.50], index=["2026-01-30", "2026-01-31", "2026-02-01"])
        self.assertEqual(d.monthly(ret), {"2026-01": 21.0, "2026-02": -50.0})

    def test_extremes_orders_losses_and_gains(self):
        ret = pd.Series([0.01, -0.02, 0.03, -0.04], index=["a", "b", "c", "d"])
        out = d.extremes(ret, 2)
        self.assertEqual(out["largest_losses"], [["d", -4.0], ["b", -2.0]])
        self.assertEqual(out["largest_gains"], [["c", 3.0], ["a", 1.0]])

    def test_refuses_gate1_window(self):
        import sys
        argv = sys.argv
        sys.argv = ["x", "--data", ".", "--until", "2026-11-11"]
        try:
            with self.assertRaises(SystemExit) as cm:
                d.main()
            self.assertIn("gate-1", str(cm.exception))
        finally:
            sys.argv = argv


if __name__ == "__main__":
    unittest.main()
