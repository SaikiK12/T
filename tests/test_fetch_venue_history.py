import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

    def test_lighter_windows_sign_and_finished_bars(self):
        H, t0 = fv.HOUR, 1_740_000_000_000 // fv.HOUR * fv.HOUR
        now = t0 + 1000 * H
        calls = []

        def fake(path, **q):
            calls.append((path, q))
            if path == "fundings":                      # seconds, both ends inclusive like the API
                hours = range(q["start_timestamp"] * 1000, q["end_timestamp"] * 1000 + 1, H)
                return {"fundings": [{"timestamp": t // 1000, "rate": "0.0012", "value": "1.0",
                                      "direction": "long" if (t // H) % 2 else "short"} for t in hours]}
            size = fv.DAY if q["resolution"] == "1d" else H
            first = max(q["start_timestamp"], t0) // size * size
            return {"c": [{"t": t, "o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 3, "V": 4}
                          for t in range(first, q["end_timestamp"] + 1, size)]}

        with mock.patch.object(fv, "lighter_get", fake), mock.patch.object(fv, "_lighter_listed", {}):
            f = fv.lighter_funding(7, now, 0)
            c = fv.lighter_candles(7, "1h", now, 0)
        start = t0 // fv.DAY * fv.DAY                   # windows start at the first daily candle
        self.assertEqual(f.t.iloc[0], start)
        self.assertTrue(f.t.is_unique and (f.t.diff().dropna() == H).all())
        self.assertEqual(f.t.iloc[-1], now)
        sign = [1 if (t // H) % 2 else -1 for t in f.t]
        self.assertTrue(((f.rate * 1e6).round().astype(int) == [12 * s for s in sign]).all())
        self.assertTrue(c.t.is_unique and c.t.iloc[-1] + H <= now)      # the bar still open at `now` is dropped
        self.assertTrue(all(q["end_timestamp"] - q["start_timestamp"] <= 700 * 3600
                            for p, q in calls if p == "fundings"))

    def test_time_round_trip(self):
        self.assertEqual(fv.ms(fv.iso(1_700_000_000_000)), 1_700_000_000_000)
        self.assertEqual(fv.ms("2023-10-31T23:00:01.133Z"), 1_698_793_201_000)


if __name__ == "__main__":
    unittest.main()
