import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import fetch_venue_history as fv


class FetchVenueHistoryTest(unittest.TestCase):
    def test_route(self):
        perps = {"BTCUSDT", "1000PEPEUSDT"}
        self.assertEqual(fv.route("BTC", perps), ("open", "BTCUSDT", 1))
        self.assertEqual(fv.route("PEPE", perps), ("open", "1000PEPEUSDT", 1000))
        self.assertEqual(fv.route("NOPE", perps), ("reserved", "", ""))

    def test_save_splits_2020_rows(self):
        df = pd.DataFrame({"t": [fv.OPEN_FROM_MS - fv.DAY, fv.OPEN_FROM_MS, fv.OPEN_FROM_MS + fv.DAY],
                           "rate": [0.1, 0.2, 0.3]})
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            fv.save(out, "funding", "AUSDTM", "open", df)
            fv.save(out, "funding", "BUSDTM", "reserved", df)
            fv.save(out, "funding", "CUSDTM", "open", df.iloc[1:])
            self.assertEqual(len(pd.read_parquet(out / "open/funding/AUSDTM.parquet")), 2)
            self.assertEqual(len(pd.read_parquet(out / "reserved/funding/AUSDTM.parquet")), 1)
            self.assertEqual(len(pd.read_parquet(out / "reserved/funding/BUSDTM.parquet")), 3)
            self.assertFalse((out / "open/funding/BUSDTM.parquet").exists())
            self.assertFalse((out / "reserved/funding/CUSDTM.parquet").exists())   # no 2020 rows: no file

    def test_time_round_trip(self):
        self.assertEqual(fv.ms(fv.iso(1_700_000_000_000)), 1_700_000_000_000)
        self.assertEqual(fv.ms("2023-10-31T23:00:01.133Z"), 1_698_793_201_000)


if __name__ == "__main__":
    unittest.main()
