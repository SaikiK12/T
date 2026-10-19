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

    def test_completed_signal_last_excludes_open_and_unmarked_return_bars(self):
        # At 15:22 the 13:00 signal is the latest one whose entry and next bar
        # close are known; the 14:00 bar is still the current/open bar.
        self.assertEqual(mexc.completed_signal_last(14 * mexc.HOUR, 15 * mexc.HOUR + 22 * 60_000), 13 * mexc.HOUR)
        self.assertEqual(mexc.completed_signal_last(10 * mexc.HOUR, 15 * mexc.HOUR), 10 * mexc.HOUR)


if __name__ == "__main__":
    unittest.main()
