import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_flow_hlstock", ROOT / "scripts" / "run_flow_hlstock.py")
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)
H = fs.H


class FlowHLStock(unittest.TestCase):
    def test_xyz_coin_and_aliases(self):
        coins = {"xyz:TSLA", "xyz:GOLD", "xyz:SP500", "xyz:SMSN", "xyz:XYZ100"}
        self.assertEqual(fs.xyz_coin("TSLAUSDT", coins), "xyz:TSLA")
        self.assertEqual(fs.xyz_coin("XAUUSDT", coins), "xyz:GOLD")
        self.assertEqual(fs.xyz_coin("SPYUSDT", coins), "xyz:SP500")
        self.assertEqual(fs.xyz_coin("SAMSUNGUSDT", coins), "xyz:SMSN")
        self.assertIsNone(fs.xyz_coin("QQQUSDT", coins))          # no alias to XYZ100
        self.assertIsNone(fs.xyz_coin("XAGUSDT", coins))          # alias target not listed
        self.assertIsNone(fs.xyz_coin("TSLAUSDC", coins))

    def test_floor_costs(self):
        c = fs.floor_costs(np.array([[6e-4, 12e-4, np.nan]]))
        self.assertEqual(c[0, 0], fs.FEE_FLOOR)
        self.assertEqual(c[0, 1], 12e-4)
        self.assertTrue(np.isnan(c[0, 2]))

    def test_journal_grid_and_binance_returns(self):
        t0 = 1000 * H
        sig = pd.DataFrame({"t": [t0, t0, t0 + H, t0 + 5 * H], "symbol": ["AUSDT", "BUSDT", "AUSDT", "AUSDT"],
                            "rank": [3, 40, 3, 3], "close": [10.0, 5.0, 11.0, 12.0],
                            "tvc": [0, 2, 1, 0], "t24": [1, 0, 1, 1], "t4": [0, 0, 0, 0]})
        elig, rank, bclose, raw = fs.journal_grid(sig, ["AUSDT", "BUSDT"], t0, 3)
        self.assertEqual(elig.tolist(), [[True, True], [True, False], [False, False]])
        self.assertEqual(raw["tvc"].tolist(), [[True, False], [False, False], [False, False]])
        self.assertEqual(raw["t4"][0].tolist(), [True, True])
        r = fs.binance_returns(bclose)
        self.assertAlmostEqual(r[0, 0], 0.1)
        self.assertTrue(np.isnan(r[1, 0]) and np.isnan(r[2, 0]))


if __name__ == "__main__":
    unittest.main()
