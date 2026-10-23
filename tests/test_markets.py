import json
import unittest
from pathlib import Path

from lab import markets

FIX = Path(__file__).parent / "fixtures" / "yahoo_eurusd.json"


class TestMarkets(unittest.TestCase):
    def test_parse_drops_missing_close_and_duplicate_stamps(self):
        df = markets.parse(json.loads(FIX.read_text()))
        self.assertEqual(list(df.columns), ["open", "high", "low", "close", "volume", "adjclose"])
        self.assertEqual(len(df), 4)                          # 6 rows: one duplicate stamp, one missing close
        self.assertTrue(df.index.is_monotonic_increasing)
        self.assertEqual(str(df.index.tz), "UTC")
        self.assertEqual(df.attrs["symbol"], "EURUSD=X")

    def test_parse_raises_on_error_payload(self):
        with self.assertRaises(markets.MarketError):
            markets.parse({"chart": {"result": None, "error": {"code": "Not Found"}}})


if __name__ == "__main__":
    unittest.main()
