import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import record_funding_board as rb

FIX = {
    "gate": [{"name": "BTC_USDT", "status": "trading", "funding_rate": "0.0001", "funding_interval": 28800,
              "funding_next_apply": 1792540800, "mark_price": "80000", "position_size": 5,
              "funding_rate_indicative": "0.00012"},
             {"name": "1000PEPE_USDT", "status": "trading", "funding_rate": "-0.0004", "funding_interval": 14400,
              "funding_next_apply": 1792540800, "mark_price": "0.004", "position_size": 9,
              "funding_rate_indicative": "0"},
             {"name": "OLD_USDT", "status": "delisting", "funding_rate": "0.01"}],
    "hyperliquid": [{"universe": [{"name": "BTC"}, {"name": "kPEPE"}, {"name": "MATIC", "isDelisted": True}]},
                    [{"funding": "0.0000125", "markPx": "80010", "openInterest": "10"},
                     {"funding": "0.00002", "markPx": "0.0041", "openInterest": "3"},
                     {"funding": "0.5", "markPx": "1", "openInterest": "1"}]],
    "okx": {"data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0.0002", "fundingTime": "1792540800000",
                      "nextFundingTime": "1792555200000", "settFundingRate": "0.00015"},
                     {"instId": "BTC-USD-SWAP", "fundingRate": "0.9"}]},
    "okx_mark": {"data": [{"instId": "BTC-USDT-SWAP", "markPx": "80005"}]},
    "bitget": {"data": [{"symbol": "BTCUSDT", "fundingRate": "0.00005", "fundingRateInterval": "8",
                         "nextUpdate": "1792540800000"}]},
    "bitget_tickers": {"data": [{"symbol": "BTCUSDT", "markPrice": "80001", "holdingAmount": "7"}]},
    "kucoin": {"data": [{"symbol": "XBTUSDTM", "baseCurrency": "XBT", "quoteCurrency": "USDT", "status": "Open",
                         "expireDate": None, "fundingFeeRate": 0.0003, "currentFundingRateGranularity": 28800000,
                         "nextFundingRateDateTime": 1792540800000, "markPrice": 80002, "openInterest": "11",
                         "predictedFundingFeeRate": None}]},
}


def fake(name, body=None):
    if name == "dydx":
        raise OSError("down")
    return FIX[name]


class FundingBoardTest(unittest.TestCase):
    def test_normalization(self):
        df, failed = rb.snapshot(fake, now_ms=1792530000000, clock_ms=lambda: 1792530000000)
        self.assertEqual(failed, ["dydx: OSError: down"])
        self.assertEqual(sorted(df.venue.unique()), ["bitget", "gate", "hyperliquid", "kucoin", "okx"])
        g = df[(df.venue == "gate") & (df.base == "PEPE")].iloc[0]
        self.assertAlmostEqual(g.rate_8h, -0.0008)                 # 4 h interval -> doubled
        h = df[(df.venue == "hyperliquid") & (df.base == "BTC")].iloc[0]
        self.assertAlmostEqual(h.rate_8h, 0.0001)                  # hourly x 8
        self.assertIn("PEPE", set(df[df.venue == "hyperliquid"].base))   # kPEPE -> PEPE
        self.assertNotIn("OLD", set(df.base))
        self.assertNotIn("MATIC", set(df.base))
        o = df[df.venue == "okx"]
        self.assertEqual(len(o), 1)                                # coin-margined swap dropped
        self.assertAlmostEqual(o.iloc[0].interval_h, 4.0)
        self.assertAlmostEqual(o.iloc[0].rate_8h, 0.0004)
        self.assertEqual(df[df.venue == "kucoin"].iloc[0].base, "BTC")

    def test_record_once_per_hour(self):
        with tempfile.TemporaryDirectory() as d:
            p, n, _ = rb.record(fake, now_ms=1792530000000, out=d, clock_ms=lambda: 1792530000000)
            self.assertGreater(n, 0)
            p2, n2, _ = rb.record(fake, now_ms=1792530000000 + 60_000, out=d)
            self.assertEqual((p2, n2), (p, 0))
            self.assertEqual(len(pd.read_parquet(p)), n)

    def test_board_spread(self):
        df, _ = rb.snapshot(fake, now_ms=1792530000000, clock_ms=lambda: 1792530000000)
        mexc = pd.DataFrame({"symbol": ["BTC_USDT"], "f_fundingRate": [-0.0001], "f_collectCycle": [8]})
        b = rb.board(df, mexc)
        btc = b[b.base == "BTC"].iloc[0]
        self.assertEqual(btc.venues, 6)
        self.assertEqual((btc.max_venue, btc.min_venue), ("okx", "mexc"))
        self.assertAlmostEqual(btc.spread_8h, 0.0004 + 0.0001)
        self.assertAlmostEqual(btc.spread_ann, 0.0005 * 3 * 365)
        pepe = b[b.base == "PEPE"].iloc[0]
        self.assertEqual(pepe.venues, 2)

    def test_each_venue_receipt_is_after_its_requests(self):
        start = 1792530000000
        stamps = iter(start + n for n in range(1, 13))
        df, failed = rb.snapshot(fake, now_ms=start, clock_ms=lambda: next(stamps))
        self.assertEqual(failed, ["dydx: OSError: down"])
        for i, venue in enumerate(("gate", "hyperliquid", "okx", "bitget", "kucoin")):
            rows = df[df.venue == venue]
            self.assertTrue((rows.request_start_ms == start).all())
            self.assertTrue((rows.venue_start_ms == start + 2 * i + 1).all())
            self.assertTrue((rows.recv_ms == start + 2 * i + 2).all())

    def test_clock_regression_leaves_no_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            start = 1792530000000
            stamps = iter((start + 1, start))
            with self.assertRaisesRegex(ValueError, "clock moved backwards"):
                rb.record(fake, now_ms=start, out=d, clock_ms=lambda: next(stamps))
            self.assertFalse(list(Path(d).rglob('*.parquet')))


if __name__ == "__main__":
    unittest.main()
