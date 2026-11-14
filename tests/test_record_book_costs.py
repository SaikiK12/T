import time
import unittest

import numpy as np
import pandas as pd

from scripts import record_book_costs as b


class Fake:
    """A get() that answers from a dict of URL -> payload and raises for anything else."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url):
        self.calls.append(url)
        v = self.answers[url]
        if isinstance(v, Exception):
            raise v
        return v


class BookMath(unittest.TestCase):
    def test_impact_walks_levels_and_is_nan_when_thin(self):
        asks = [(101.0, 5.0), (102.0, 100.0)]          # 505 USD at 101, then 10,200 at 102
        mid = 100.0
        got = b.impact(asks, 1_000, mid)
        qty = 505 / 101 + 495 / 102
        self.assertAlmostEqual(got, (1_000 / qty / mid - 1) * 1e4, places=9)
        self.assertTrue(np.isnan(b.impact(asks, 20_000, mid)))

    def test_row_spread_depth_and_rejects_crossed(self):
        r = b.row(1, "dydx", "X-USD", "X", [(99.0, 100.0), (98.0, 100.0)], [(101.0, 100.0), (103.0, 100.0)],
                  vol24_usd="1234", oi_usd=5.0, taker_fee=None)
        self.assertAlmostEqual(r["half_spread_bp"], 100.0)
        self.assertAlmostEqual(r["bid_usd_1pct"], 99.0 * 100)       # 98 is 2% below the mid of 100
        self.assertAlmostEqual(r["ask_usd_1pct"], 101.0 * 100)
        self.assertEqual(r["vol24_usd"], 1234.0)
        self.assertTrue(np.isnan(r["taker_fee"]))
        self.assertIsNone(b.row(1, "dydx", "X", "X", [(101.0, 1.0)], [(100.0, 1.0)]))
        self.assertIsNone(b.row(1, "dydx", "X", "X", [], [(100.0, 1.0)]))
        self.assertEqual(b.row(1, "kucoin", "XBTUSDTM", "XBT", [(99.0, 1.0)], [(101.0, 1.0)])["base"], "BTC")


class Venues(unittest.TestCase):
    def test_dydx_keeps_active_markets_only(self):
        get = Fake({f"{b.DYDX}/perpetualMarkets": {"markets": {
            "A-USD": {"status": "ACTIVE", "volume24H": "10", "openInterest": "2", "oraclePrice": "3"},
            "B-USD": {"status": "FINAL_SETTLEMENT", "volume24H": "0", "openInterest": "0", "oraclePrice": "1"}}}})
        got = b.dydx_markets(get)
        self.assertEqual([(s, base) for s, base, _ in got], [("A-USD", "A")])
        self.assertEqual(got[0][2]["oi_usd"], 6.0)

    def test_kucoin_filters_and_converts_contracts(self):
        contracts = [
            {"symbol": "AUSDTM", "status": "Open", "isInverse": False, "quoteCurrency": "USDT", "expireDate": None,
             "multiplier": 10, "turnoverOf24h": 5.0, "openInterest": "3", "markPrice": 2.0, "baseCurrency": "A",
             "takerFeeRate": 0.0006, "makerFeeRate": 0.0002},
            {"symbol": "XBTUSDM", "status": "Open", "isInverse": True, "quoteCurrency": "USD", "expireDate": None},
            {"symbol": "CUSDCM", "status": "Open", "isInverse": False, "quoteCurrency": "USDC", "expireDate": None},
            {"symbol": "DUSDTM", "status": "Paused", "isInverse": False, "quoteCurrency": "USDT", "expireDate": None}]
        get = Fake({f"{b.KUCOIN}/contracts/active": {"data": contracts},
                    f"{b.KUCOIN}/level2/depth100?symbol=AUSDTM": {"data": {"bids": [[1.9, 4]], "asks": [[2.1, 5]]}}})
        got = b.kucoin_markets(get)
        self.assertEqual([s for s, _, _ in got], ["AUSDTM"])
        self.assertEqual(got[0][2]["oi_usd"], 60.0)
        bids, asks = b.kucoin_book(get, "AUSDTM", got[0][2]["mult"])
        self.assertEqual(bids, [(1.9, 40.0)])
        self.assertEqual(asks, [(2.1, 50.0)])

    def test_venue_rows_records_a_failed_book_and_continues(self):
        markets = {"markets": {m: {"status": "ACTIVE", "volume24H": "1", "openInterest": "1", "oraclePrice": "1"}
                               for m in ("A-USD", "B-USD")}}
        book = {"bids": [{"price": "99", "size": "100"}], "asks": [{"price": "101", "size": "100"}]}
        get = Fake({f"{b.DYDX}/perpetualMarkets": markets,
                    f"{b.DYDX}/orderbooks/perpetualMarket/A-USD": OSError("reset"),
                    f"{b.DYDX}/orderbooks/perpetualMarket/B-USD": book})
        rows, failed = b.venue_rows("dydx", 7, get=get, pace=0)
        self.assertEqual([r["symbol"] for r in rows], ["B-USD"])
        self.assertEqual(len(failed), 1)
        self.assertIn("A-USD", failed[0])

    def test_a_venue_down_is_recorded_not_fatal(self):
        rows, failed = b.venue_rows("dydx", 7, get=Fake({f"{b.DYDX}/perpetualMarkets": OSError("down")}), pace=0)
        self.assertEqual(rows, [])
        self.assertIn("market list", failed[0])


class Summary(unittest.TestCase):
    def frame(self, ts, symbol, side_bp, vol):
        r = {c: np.nan for c in b.COLS}
        r.update(ts=ts, venue="dydx", symbol=symbol, base=symbol, half_spread_bp=1.0, vol24_usd=vol)
        for n in b.SIZES:
            k = f"{n // 1000}k"
            r[f"buy_{k}_bp"] = r[f"sell_{k}_bp"] = side_bp
        return pd.DataFrame([r], columns=b.COLS)

    def test_unfilled_counts_as_infinite_and_bands_by_volume(self):
        frames = [self.frame(1, "A", 10.0, 1_000), self.frame(2, "A", np.nan, 1_000), self.frame(3, "A", np.nan, 1_000),
                  self.frame(1, "B", 20.0, 2_000), self.frame(2, "C", 5.0, 1e7)]
        s = b.summarize(frames)
        self.assertEqual(s["snapshots"], 3)
        rows = {r["band_usd"]: r for r in s["by_venue_band"]}
        low = rows["0-50000"]
        self.assertEqual(low["symbols"], 2)
        self.assertIsNone(low["median_side_1k_bp"])           # A's median is unfilled, so the median of {inf, 20} is inf
        self.assertEqual(low["unfilled_share_1k"], 0.5)
        self.assertEqual(rows["5e+06-inf"]["median_side_1k_bp"], 5.0)

    def test_slot_path_rounds_down_to_three_hours(self):
        now = time.strptime("2026-11-04 07:59", "%Y-%m-%d %H:%M")
        self.assertEqual(b.slot_path(now, "/x").as_posix(), "/x/2026-11-04/06.parquet")


if __name__ == "__main__":
    unittest.main()
