import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import record_deribit_chain as rd
from scripts import record_lighter_book as rl


def book(asks, bids):
    f = lambda xs: [{"price": str(p), "remaining_base_amount": str(q)} for p, q in xs]
    return {"asks": f(asks), "bids": f(bids)}


DETAILS = {"order_book_details": [
    {"symbol": "BTC", "market_id": 1, "status": "active", "mark_price": "100", "index_price": "100.1",
     "daily_quote_token_volume": 5e8, "open_interest": "10", "taker_fee": "0.0000", "maker_fee": "0.0000"},
    {"symbol": "THIN", "market_id": 2, "status": "active", "mark_price": "1", "index_price": "1",
     "daily_quote_token_volume": 1e3, "open_interest": "1", "taker_fee": "0.0000", "maker_fee": "0.0000"},
    {"symbol": "OLD", "market_id": 3, "status": "inactive"}]}
BOOKS = {1: book([(100.01, 5), (100.03, 200)], [(99.99, 5), (99.97, 200)]),
         2: book([(1.01, 100)], [])}


def fake_lighter(path):
    if path.startswith("/orderBookDetails"):
        return DETAILS
    return BOOKS[int(path.split("market_id=")[1].split("&")[0])]


class LighterTest(unittest.TestCase):
    def test_impact_walks_the_book(self):
        side = [(100.01, 5), (100.03, 200)]
        # 1k fills inside the first level (500.05 USD), then the rest at the second
        expected_1k = None
        left, paid, qty = 1000.0, 0.0, 0.0
        for p, q in side:
            take = min(left, p * q)
            paid, qty, left = paid + take, qty + take / p, left - take
        expected_1k = abs(paid / qty / 100.0 - 1) * 1e4
        self.assertAlmostEqual(rl.impact(side, 1000, 100.0), expected_1k)
        self.assertGreater(rl.impact(side, 1000, 100.0), rl.impact(side, 100, 100.0))
        self.assertTrue(np.isnan(rl.impact([(100.01, 1)], 1000, 100.0)))

    def test_snapshot_skips_inactive_and_one_sided_books(self):
        df, failed = rl.snapshot(get=fake_lighter, pace=0)
        self.assertEqual(list(df.symbol), ["BTC"])
        self.assertEqual(failed, [])
        r = df.iloc[0]
        self.assertAlmostEqual(r.half_spread_bp, 1.0, places=6)            # (100.01 - 99.99) / 100 / 2
        self.assertAlmostEqual(r.buy_1k_bp, rl.impact([(100.01, 5), (100.03, 200)], 1000, 100.0))
        self.assertEqual(r.taker_fee, 0.0)

    def test_one_hour_is_written_once(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(rl, "OUT", Path(d)), \
                mock.patch.object(rl, "ROOT", Path(d)), mock.patch.object(rl, "http", fake_lighter), \
                mock.patch.object(rl, "PACE_S", 0):
            p1 = rl.main([])
            m1 = p1.stat().st_mtime_ns
            p2 = rl.main([])
            self.assertEqual(p1, p2)
            self.assertEqual(p2.stat().st_mtime_ns, m1)
            self.assertEqual(len(pd.read_parquet(p1)), 1)


CHAIN = {
    "BTC": [{"instrument_name": "BTC-27NOV26-100000-C", "open_interest": 10.0, "mark_iv": 50.0, "mark_price": 0.01,
             "bid_price": 0.009, "ask_price": 0.011, "underlying_price": 100000.0, "underlying_index": "BTC-27NOV26",
             "estimated_delivery_price": 99950.0, "volume_usd": 1000.0},
            {"instrument_name": "BTC-27NOV26-100000-P", "open_interest": 4.0, "mark_iv": 50.0, "mark_price": 0.01,
             "bid_price": None, "ask_price": 0.011, "underlying_price": 100000.0, "underlying_index": "BTC-27NOV26",
             "estimated_delivery_price": 99950.0, "volume_usd": 10.0},
            {"instrument_name": "BTC-PERPETUAL", "open_interest": 1.0}],
    "ETH": [{"instrument_name": "ETH-5DEC26-4000-C", "open_interest": 0.0, "mark_iv": 60.0,
             "underlying_price": 4000.0}],
}


def fake_deribit(c):
    if c == "USDC":
        raise OSError("down")
    return CHAIN[c]


class DeribitTest(unittest.TestCase):
    def test_parse(self):
        base, exp, k, cp = rd.parse("BTC-27NOV26-73000-P")
        self.assertEqual((base, k, cp), ("BTC", 73000.0, "P"))
        self.assertEqual(pd.Timestamp(exp, unit="ms", tz="UTC"), pd.Timestamp("2026-11-27 08:00", tz="UTC"))
        self.assertEqual(rd.parse("SOL_USDC-5DEC26-1d5-C")[0::2], ("SOL", 1.5))
        self.assertIsNone(rd.parse("BTC-PERPETUAL"))

    def test_gex_matches_black76_and_sign_convention(self):
        ts = int(pd.Timestamp("2026-10-28 08:00", tz="UTC").value // 10**6)
        df = pd.DataFrame(rd.rows("BTC", CHAIN["BTC"], ts), columns=rd.COLS)
        g = rd.gex(df).set_index("strike")
        T = 30 / 365.25
        s, F = 0.5, 100000.0
        d1 = 0.5 * s * s * T / (s * math.sqrt(T))
        gamma = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi) / (F * s * math.sqrt(T))
        self.assertAlmostEqual(g.loc[100000.0, "call_gex"], 10 * gamma * F * F * 0.01, places=3)
        self.assertAlmostEqual(g.loc[100000.0, "put_gex"], 4 * gamma * F * F * 0.01, places=3)
        self.assertAlmostEqual(g.loc[100000.0, "net_gex"], 6 * gamma * F * F * 0.01, places=3)

    def test_failed_currency_is_skipped_and_hour_written_once(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(rd, "OUT", Path(d)), \
                mock.patch.object(rd, "ROOT", Path(d)):
            p = rd.main(get=fake_deribit)
            df = pd.read_parquet(p)
            self.assertEqual(sorted(df.instrument), ["BTC-27NOV26-100000-C", "BTC-27NOV26-100000-P",
                                                     "ETH-5DEC26-4000-C"])
            m = p.stat().st_mtime_ns
            self.assertEqual(rd.main(get=fake_deribit), p)
            self.assertEqual(p.stat().st_mtime_ns, m)


if __name__ == "__main__":
    unittest.main()
