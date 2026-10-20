import csv
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from lab import venues


def touch(root, rel):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"t": [0]}).to_parquet(p)


class VenuesTest(unittest.TestCase):
    def test_binance_perp_name_rule(self):
        perps = {"BTCUSDT", "1000PEPEUSDT", "1000000MOGUSDT"}
        self.assertEqual(venues.binance_perp("BTC", perps), ("BTCUSDT", 1))
        self.assertEqual(venues.binance_perp("PEPE", perps), ("1000PEPEUSDT", 1000))
        self.assertEqual(venues.binance_perp("MOG", perps), ("1000000MOGUSDT", 1_000_000))
        self.assertEqual(venues.binance_perp("1000PEPE", perps), ("1000PEPEUSDT", 1))
        self.assertIsNone(venues.binance_perp("ETH", perps))
        self.assertEqual(venues.hl_base("kPEPE"), "1000PEPE")
        self.assertEqual(venues.hl_base("kaito"), "kaito")

    def test_table_maps_every_source(self):
        with tempfile.TemporaryDirectory() as root:
            for s in ("BTCUSDT", "1000PEPEUSDT", "ETHUSDT"):
                touch(root, f"klines_1h/{s}.parquet")
                touch(root, f"fundingRate/{s}.parquet")
            for c in ("BTC_USDT", "PEPE_USDT"):
                touch(root, f"gate_hist/open/candlesticks_1h/{c}.parquet")
                touch(root, f"gate_hist/open/funding_applies/{c}.parquet")
            with open(Path(root) / "gate_hist/contracts.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "route", "candlesticks_1h_months"])
                w.writerows([["BTC_USDT", "open", "60"], ["PEPE_USDT", "open", "30"], ["XYZ_USDT", "reserved", "5"]])
            for c in ("BTC", "kPEPE"):
                touch(root, f"hyperliquid/candles_1d/{c}.parquet")
                touch(root, f"hyperliquid/funding/{c}.parquet")
            touch(root, "mexc_hist/klines_1h/ETH_USDT.parquet")
            touch(root, "mexc_hist/funding/ETH_USDT.parquet")
            (Path(root) / "mexc_hist/contracts.json").write_text(json.dumps(
                [{"symbol": "ETH_USDT", "base": "ETH", "settle": "USDT", "type": 1}]))
            for k in ("candles_1d", "funding"):
                touch(root, f"kucoin_hist/open/{k}/XBTUSDTM.parquet")
            with open(Path(root) / "kucoin_hist/contracts.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["symbol", "base", "route"])
                w.writerows([["XBTUSDTM", "BTC", "open"], ["ONLYUSDTM", "ONLY", "reserved"]])
            touch(root, "upbit_hist/open/candles_1d/KRW-ETH.parquet")
            with open(Path(root) / "upbit_hist/contracts.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["symbol", "base", "route"])
                w.writerow(["KRW-ETH", "ETH", "open"])
            touch(root, "coinmetrics/open/btc.parquet")
            touch(root, "coinmetrics/open/pepe.parquet")
            touch(root, "defillama/open/ETHUSDT.parquet")
            t, _ = venues.table(root)
            self.assertEqual(t["BTCUSDT"]["gate"], ("BTC_USDT", 1))
            self.assertEqual(t["BTCUSDT"]["hyperliquid"], ("BTC", 1))
            self.assertEqual(t["BTCUSDT"]["kucoin"], ("XBTUSDTM", 1))
            self.assertEqual(t["BTCUSDT"]["coinmetrics"], ("btc", 1))
            self.assertEqual(t["1000PEPEUSDT"]["gate"], ("PEPE_USDT", 1000))
            self.assertEqual(t["1000PEPEUSDT"]["hyperliquid"], ("kPEPE", 1))
            self.assertEqual(t["1000PEPEUSDT"]["coinmetrics"], ("pepe", 1000))
            self.assertEqual(t["ETHUSDT"]["mexc"], ("ETH_USDT", 1))
            self.assertEqual(t["ETHUSDT"]["upbit"], ("KRW-ETH", 1))
            self.assertEqual(t["ETHUSDT"]["defillama"], ("ETHUSDT", 1))
            self.assertNotIn("kucoin", t["ETHUSDT"])
            rows = venues.rows(root)
            self.assertEqual([r["key"] for r in rows], ["1000PEPEUSDT", "BTCUSDT", "ETHUSDT"])
            self.assertEqual(rows[1]["dydx"], "")


if __name__ == "__main__":
    unittest.main()
