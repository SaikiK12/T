import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import fetch_deribit_perps as f
from scripts import run_deribit_gap as g


class DeribitGap(unittest.TestCase):
    def test_perps_and_names(self):
        raw = [{"instrument_name": "BTC_USDC-PERPETUAL", "settlement_period": "perpetual", "instrument_type": "linear"},
               {"instrument_name": "BTC-PERPETUAL", "settlement_period": "perpetual", "instrument_type": "reversed"},
               {"instrument_name": "BTC_USDC-27DEC26", "settlement_period": "month", "instrument_type": "linear"}]
        self.assertEqual(f.perps(raw), [("BTC_USDC-PERPETUAL", "BTC")])
        self.assertEqual(g.hl_name("1000PEPE"), "kPEPE")
        self.assertEqual(g.hl_name("BTC"), "BTC")

    def test_static_book_holds_through_a_narrow_spread(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            der, hl = root / "der", root / "hl"
            for p in (der / "funding", der / "prices", hl / "funding", hl / "candles_1d"):
                p.mkdir(parents=True)
            t0 = int(pd.Timestamp("2024-01-01", tz="UTC").value // 10**6)
            days, H = 200, 3_600_000
            rng = np.random.default_rng(1)
            px = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, days)))
            hl_rate = np.full(days * 24, 0.0000125)                 # the floor, 10.95%/yr
            hl_rate[100 * 24:110 * 24] = 0.0                        # ten days at zero: R275 would exit, Static holds
            pd.DataFrame({"t": t0 + np.arange(days * 24) * H, "rate": 0.0}).to_parquet(der / "funding" / "BTC.parquet")
            pd.DataFrame({"t": t0 + np.arange(days * 24) * H, "rate": hl_rate}).to_parquet(hl / "funding" / "BTC.parquet")
            for path in (der / "prices" / "BTC.parquet", hl / "candles_1d" / "BTC.parquet"):
                pd.DataFrame({"t": t0 + np.arange(days) * 86_400_000, "close": px, "volume": 1.0}).to_parquet(path)
            u, sym = g.universe(der, hl, "2024-01-01", str((pd.Timestamp("2024-01-01") + pd.Timedelta(days=days - 1)).date()))
            self.assertEqual(sym.key.tolist(), ["BTC"])
            _, tr = g.book(u, 30, 0.0, 20, static=True)
            self.assertEqual(len(tr), 1)
            self.assertEqual((tr.iloc[0].long, tr.iloc[0].short, tr.iloc[0].reason), ("deribit", "hyperliquid", "end"))
            self.assertGreater(tr.iloc[0].funding_pnl, 0)


if __name__ == "__main__":
    unittest.main()
