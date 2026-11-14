import unittest

import pandas as pd

from lab import mexc


class MapSymbols(unittest.TestCase):
    def test_prefix_alias_and_tradfi(self):
        table = pd.DataFrame({"symbol": ["BTC_USDT", "PEPE_USDT", "FILECOIN_USDT", "NVDASTOCK_USDT", "SHIB_USDT"],
                              "type": [1, 1, 1, 2, 1]})
        got = mexc.map_symbols(["BTCUSDT", "1000PEPEUSDT", "FILUSDT", "NVDAUSDT", "XAGUSDT", "1000000SHIBUSDT"], table)
        self.assertEqual(got, {"BTCUSDT": "BTC_USDT", "1000PEPEUSDT": "PEPE_USDT", "FILUSDT": "FILECOIN_USDT",
                               "NVDAUSDT": None, "XAGUSDT": None, "1000000SHIBUSDT": "SHIB_USDT"})

    def test_stock_contract_never_matches(self):
        table = pd.DataFrame({"symbol": ["MSTR_USDT"], "type": [2]})
        self.assertIsNone(mexc.map_symbols(["MSTRUSDT"], table)["MSTRUSDT"])


if __name__ == "__main__":
    unittest.main()
