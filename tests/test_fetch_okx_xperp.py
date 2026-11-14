import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import fetch_okx_xperp as fx


class FetchOkxXperpTest(unittest.TestCase):
    def test_only_crypto_xperps_are_kept(self):
        inst = [{"instId": "BTC-USD_UM_XPERP-310330", "instCategory": "1"},
                {"instId": "NVDA-USD_UM_XPERP-310330", "instCategory": "3"},
                {"instId": "BTC-USD-261225", "instCategory": "1"}]
        self.assertEqual([i["instId"] for i in fx.crypto_xperps(inst)], ["BTC-USD_UM_XPERP-310330"])

    def test_funding_frame_parses_numbers_and_keeps_missing_fields(self):
        rows = [{"instId": "BTC-USD_UM_XPERP-310330", "fundingTime": "1786000000000", "fundingRate": "0.0001",
                 "realizedRate": "0.0001", "method": "current_period", "formulaType": "withRate"},
                {"instId": "ETH-USD_UM_XPERP-310330", "fundingTime": "1786028800000", "fundingRate": ""}]
        f = fx.funding_frame(rows)
        self.assertEqual(f.fundingTime.dtype, "int64")
        self.assertAlmostEqual(f.fundingRate.iloc[0], 1e-4)
        self.assertTrue(pd.isna(f.fundingRate.iloc[1]))
        self.assertTrue(pd.isna(f.realizedRate.iloc[1]))

    def test_candle_frame_takes_the_first_five_fields(self):
        c = fx.candle_frame([["1786000000000", "1", "2", "0.5", "1.5", "1"]], "BTC-USD")
        self.assertEqual(list(c.columns), ["instId", "ts", "o", "h", "l", "c"])
        self.assertEqual(c.ts.iloc[0], 1786000000000)
        self.assertEqual(c.c.iloc[0], 1.5)

    def test_merge_keeps_old_rows_and_replaces_a_repeated_key(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.parquet"
            fx.merge(p, pd.DataFrame({"instId": ["A", "A"], "fundingTime": [1, 2], "fundingRate": [0.1, 0.2]}),
                     ["instId", "fundingTime"])
            m = fx.merge(p, pd.DataFrame({"instId": ["A", "B"], "fundingTime": [2, 1], "fundingRate": [0.3, 0.4]}),
                         ["instId", "fundingTime"])
            self.assertEqual(len(m), 3)                               # the API dropping a row never drops it here
            self.assertEqual(m.set_index(["instId", "fundingTime"]).fundingRate[("A", 2)], 0.3)
            self.assertEqual(len(pd.read_parquet(p)), 3)

    def test_pages_walk_back_until_empty(self):
        calls = []
        pages = {"": [{"fundingTime": "3"}, {"fundingTime": "2"}], "2": [{"fundingTime": "1"}], "1": []}

        def fake(path):
            calls.append(path)
            return pages[path.split("&after=")[1] if "&after=" in path else ""]
        orig, fx.get = fx.get, fake
        try:
            rows = fx.pages("x?instId=A", "fundingTime")
        finally:
            fx.get = orig
        self.assertEqual([r["fundingTime"] for r in rows], ["3", "2", "1"])
        self.assertEqual(len(calls), 3)


if __name__ == "__main__":
    unittest.main()
