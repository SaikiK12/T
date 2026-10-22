import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import lighter_table as lt


class LighterTableTest(unittest.TestCase):
    def test_open_contracts_with_files_and_a_binance_perp_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for folder in ("klines_1h", "fundingRate"):
                (root / folder).mkdir()
                for p in ("BTCUSDT", "1000PEPEUSDT", "ETHUSDT"):
                    (root / folder / f"{p}.parquet").touch()
            for kind in ("candles_1h", "funding"):
                (root / "lighter_hist/open" / kind).mkdir(parents=True)
                for s in ("BTC", "1000PEPE", "kPEPE", "SPY"):
                    (root / "lighter_hist/open" / kind / f"{s}.parquet").touch()
            (root / "lighter_hist/open/candles_1h/ETH.parquet").touch()          # no funding file: left out
            pd.DataFrame({"symbol": ["BTC", "1000PEPE", "kPEPE", "ETH", "SPY", "XYZ"],
                          "route": ["open", "open", "open", "open", "reserved", "reserved"],
                          "binance_perp": ["BTCUSDT", "1000PEPEUSDT", "1000PEPEUSDT", "ETHUSDT", "", ""]}
                         ).to_csv(root / "lighter_hist/contracts.csv", index=False)
            rows = lt.build(["gate"], root)
        self.assertEqual([(r["key"], r["lighter"], r["gate"]) for r in rows],
                         [("1000PEPEUSDT", "kPEPE", ""), ("BTCUSDT", "BTC", "")])   # the shorter name wins


if __name__ == "__main__":
    unittest.main()
