"""scripts/run_flow_hlstock_mc.py (R453): fees, nearest snapshots and the measured cost matrix, offline."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_flow_hlstock_mc", ROOT / "scripts" / "run_flow_hlstock_mc.py")
mc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mc)
H = mc.H


class Fees(unittest.TestCase):
    def test_hip3_taker_fee(self):
        self.assertAlmostEqual(mc.taker_fee("enabled", 1.0), 0.9e-4)
        self.assertAlmostEqual(mc.taker_fee("", 1.0), 9e-4)
        self.assertAlmostEqual(mc.taker_fee("disabled", 0.5), 4.5e-4 * 1.5)
        self.assertAlmostEqual(mc.taker_fee("enabled", 3.0), 4.5e-4 * 6 * 0.1)

    def test_fee_on_the_latest_listed_day(self):
        m = pd.DataFrame({"coin": ["xyz:A", "xyz:A"], "day": ["2026-11-11", "2026-11-20"],
                          "growthMode": ["enabled", ""], "deployerFeeScale": [1.0, 1.0]})
        f = mc.fee_lookup(m)
        self.assertAlmostEqual(mc.fee_at(f, "xyz:A", "2026-11-15"), 0.9e-4)
        self.assertAlmostEqual(mc.fee_at(f, "xyz:A", "2026-11-20"), 9e-4)
        self.assertAlmostEqual(mc.fee_at(f, "xyz:A", "2026-11-10"), 9e-4)      # nothing listed yet
        self.assertAlmostEqual(mc.fee_at(f, "xyz:B", "2026-11-15"), 9e-4)


class Snapshots(unittest.TestCase):
    def test_nearest_within_the_gap(self):
        ts = [0, 60 * 60_000, 4 * 60 * 60_000]
        out = mc.nearest_slip(ts, [1.0, 2.0, 3.0], [10 * 60_000, 50 * 60_000, 150 * 60_000, 3 * 60 * 60_000],
                              90 * 60_000)
        self.assertEqual(out[0], 1.0)
        self.assertEqual(out[1], 2.0)
        self.assertEqual(out[2], 2.0)                    # 90 minutes from the 01:00 snapshot exactly
        self.assertEqual(out[3], 3.0)
        self.assertTrue(np.isnan(mc.nearest_slip(ts, [1.0, 2.0, 3.0], [8 * 60 * 60_000], 90 * 60_000)[0]))

    def test_measured_costs_fall_back_to_r451_and_hit_the_right_row(self):
        t0 = 1_794_441_600_000                           # 2026-11-12 00:00 UTC
        assumed = np.array([[9e-4, 12e-4, np.nan]] * 4)
        syms, mp = ["AUSDT", "BUSDT", "CUSDT"], {"AUSDT": "xyz:A", "BUSDT": None, "CUSDT": "xyz:C"}
        empty = pd.DataFrame(columns=["coin", "ts", "buy_1000_bp", "sell_1000_bp"])
        c, meas = mc.measured_costs(assumed, syms, mp, t0, empty, {})
        np.testing.assert_array_equal(np.nan_to_num(c, nan=-1), np.nan_to_num(assumed, nan=-1))
        self.assertFalse(meas.any())
        books = pd.DataFrame({"coin": ["xyz:A", "xyz:C"], "ts": [t0 + 2 * H + 7 * 60_000] * 2,
                              "buy_1000_bp": [3.0, 1.0], "sell_1000_bp": [1.0, 1.0]})
        fees = mc.fee_lookup(pd.DataFrame({"coin": ["xyz:A"], "day": ["2026-11-12"], "growthMode": ["enabled"],
                                           "deployerFeeScale": [1.0]}))
        c, meas = mc.measured_costs(assumed, syms, mp, t0, books, fees, max_gap_min=30)
        # row 1 trades at the close of the bar opening at t0 + H, i.e. t0 + 2H: 7 minutes from the snapshot
        self.assertAlmostEqual(c[1, 0], 0.9e-4 + 2e-4)
        self.assertEqual(c[0, 0], 9e-4)                  # 67 minutes away: R451's cost
        self.assertEqual(c[1, 1], 12e-4)                 # unmapped: untouched
        self.assertTrue(np.isnan(c[1, 2]))               # no R451 cost (no rank): stays out
        self.assertEqual(int(meas.sum()), 1)


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        text = (ROOT / "experiments" / "flow_hlstock_mc_v1" / "PREREG.md").read_text()
        flat = " ".join(text.split())
        self.assertIn("taker fee of 4.5 bp", flat)
        self.assertEqual(mc.BASE_TAKER, 4.5e-4)
        self.assertIn("cost of a $1k market order", flat)
        self.assertEqual(mc.SIZE_USD, 1_000)
        self.assertIn("within 90 minutes", flat)
        self.assertEqual(mc.MAX_GAP_MIN, 90)
        self.assertIn("$1k (primary), $5k and $10k", flat)
        self.assertEqual(mc.SIZES, (1_000, 5_000, 10_000))
        self.assertIn("times 0.1 when growth mode", flat)


if __name__ == "__main__":
    unittest.main()
