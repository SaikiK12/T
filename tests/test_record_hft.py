"""scripts/record_hft.py: 100 ms bucketing, the three venue parsers, part files and their daily merge, the cap."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_hft as rh  # noqa: E402

T0 = 1_793_217_600_000          # 2026-10-28 20:00:00 UTC


class BucketTests(unittest.TestCase):
    def test_book_keeps_last_quote_and_counts_updates(self):
        b = rh.Buckets()
        b.on_book("binance", "BTCUSDC", 100.0, 1.0, 100.5, 2.0, T0 - 50, T0 + 10)
        b.on_book("binance", "BTCUSDC", 100.1, 3.0, 100.6, 4.0, T0 - 30, T0 + 90)
        b.on_book("binance", "BTCUSDC", 100.2, 5.0, 100.7, 6.0, T0 + 20, T0 + 130)
        book, trades, fills = b.drain(T0 + 150)          # the T0 + 100 bucket is still open
        self.assertEqual(len(book), 1)
        r = book.iloc[0]
        self.assertEqual((r.t, r.v, r.s, r.bid, r.bq, r.ask, r.aq, r.n, r.lag, r.ro),
                         (T0, "binance", "BTCUSDC", 100.1, 3.0, 100.6, 4.0, 2, 120, 90))
        self.assertTrue(trades.empty and fills.empty)
        book = b.drain()[0]                              # everything else, once
        self.assertEqual((book.t.tolist(), book.n.tolist(), book.bid.tolist()), ([T0 + 100], [1], [100.2]))
        self.assertTrue(b.drain()[0].empty)

    def test_invalid_quotes_are_dropped(self):
        b = rh.Buckets()
        for q in ((0, 1, 2, 1), (1, 1, 0, 1), (2, 1, 1, 1), (-1, 1, 2, 1), (1, -1, 2, 1), (1, 1, 2, -1)):
            b.on_book("bybit", "BTCUSDT", q[0], q[1], q[2], q[3], T0, T0)
        self.assertTrue(b.drain()[0].empty)              # no bid, no ask, crossed, negative price or size
        b.on_book("bybit", "BTCUSDT", 1, 0, 1, 0, T0, T0)                    # locked and empty sizes are kept
        self.assertEqual(len(b.drain()[0]), 1)

    def test_each_venue_and_symbol_has_its_own_bucket(self):
        b = rh.Buckets()
        b.on_book("binance", "BTCUSDT", 1, 1, 2, 1, T0, T0 + 5)
        b.on_book("binance", "BTCUSDC", 1, 1, 2, 1, T0, T0 + 5)
        b.on_book("bybit", "BTCUSDT", 1, 1, 2, 1, T0, T0 + 5)
        book = b.drain()[0]
        self.assertEqual(sorted(zip(book.v, book.s)), [("binance", "BTCUSDC"), ("binance", "BTCUSDT"),
                                                       ("bybit", "BTCUSDT")])

    def test_trades_aggregate_by_aggressor_with_trade_through_extremes(self):
        b = rh.Buckets()
        b.on_trade("binance", "BTCUSDC", 100.0, 1.0, True, T0, T0 + 5)      # sell aggressor at 100.0
        b.on_trade("binance", "BTCUSDC", 99.9, 2.0, True, T0, T0 + 6)       # sell aggressor at 99.9
        b.on_trade("binance", "BTCUSDC", 100.2, 0.5, False, T0, T0 + 7)     # buy aggressor
        b.on_trade("binance", "BTCUSDC", 100.4, 0.25, False, T0 - 20, T0 + 8)
        b.on_trade("binance", "ETHUSDC", 10.0, 1.0, False, T0, T0 + 8)      # buys only: no sell price
        tr = b.drain()[1]
        btc = tr[tr.s == "BTCUSDC"].iloc[0]
        self.assertEqual((btc.nb, btc.qb, btc.hb, btc.ns, btc.qs, btc.ls, btc.lag), (2, 0.75, 100.4, 2, 3.0, 99.9, 28))
        eth = tr[tr.s == "ETHUSDC"].iloc[0]
        self.assertEqual((eth.nb, eth.ns, eth.qs), (1, 0, 0.0))
        self.assertTrue(math.isnan(eth.ls))
        b.on_trade("binance", "BTCUSDC", 0, 1.0, True, T0, T0 + 9)
        b.on_trade("binance", "BTCUSDC", 1.0, 0, True, T0, T0 + 9)
        self.assertTrue(b.drain()[1].empty)

    def test_a_clock_step_back_is_counted_not_written(self):
        b = rh.Buckets()
        b.on_book("binance", "BTCUSDT", 1, 1, 2, 1, T0, T0 + 500)
        b.on_book("binance", "BTCUSDT", 1, 1, 2, 1, T0, T0 + 100)
        self.assertEqual(b.late, 1)
        self.assertEqual(b.drain()[0].t.tolist(), [T0 + 500])

    def test_drain_is_time_ordered_across_symbols(self):
        b = rh.Buckets()
        b.on_book("a", "X", 1, 1, 2, 1, T0, T0 + 300)
        b.on_book("b", "Y", 1, 1, 2, 1, T0, T0 + 100)
        b.on_book("a", "X", 1, 1, 2, 1, T0, T0 + 400)
        self.assertEqual(b.drain()[0].t.tolist(), [T0 + 100, T0 + 300, T0 + 400])


class ParserTests(unittest.TestCase):
    def test_binance_book_and_trade(self):
        book = {"stream": "ethusdc@bookTicker", "data": {"e": "bookTicker", "u": 1, "s": "ETHUSDC", "b": "2356.26",
                                                         "B": "4.105", "a": "2356.27", "A": "28.460", "T": 5, "E": 7}}
        self.assertEqual(rh.binance(book, "book"), [("book", "binance", "ETHUSDC", 2356.26, 4.105, 2356.27, 28.46, 7)])
        self.assertEqual(rh.binance(book, "trade"), [])
        trade = {"data": {"e": "aggTrade", "E": 9, "s": "ETHUSDT", "p": "2357.50", "q": "0.009", "T": 8, "m": True}}
        self.assertEqual(rh.binance(trade, "trade"), [("trade", "binance", "ETHUSDT", 2357.5, 0.009, True, 8)])
        self.assertEqual(rh.binance({"result": None, "id": 1}, "book"), [])

    def test_bybit_depth_one_keeps_the_side_a_delta_leaves_out(self):
        p = rh.BybitBook()
        snap = {"topic": "orderbook.1.BTCUSDT", "ts": 10, "type": "snapshot",
                "data": {"s": "BTCUSDT", "b": [["100", "1"]], "a": [["101", "2"]]}}
        self.assertEqual(p(snap), [("book", "bybit", "BTCUSDT", 100.0, 1.0, 101.0, 2.0, 10)])
        delta = {"topic": "orderbook.1.BTCUSDT", "ts": 11, "type": "delta",
                 "data": {"s": "BTCUSDT", "b": [["100.5", "3"]], "a": []}}
        self.assertEqual(p(delta), [("book", "bybit", "BTCUSDT", 100.5, 3.0, 101.0, 2.0, 11)])
        gone = {"topic": "orderbook.1.BTCUSDT", "ts": 12, "type": "delta",
                "data": {"s": "BTCUSDT", "b": [["100.5", "0"]], "a": []}}
        self.assertEqual(p(gone), [])                    # no bid until the next message says which one
        self.assertEqual(p({"success": True, "op": "subscribe"}), [])
        other = {"topic": "orderbook.1.ETHUSDT", "ts": 13, "type": "snapshot",
                 "data": {"s": "ETHUSDT", "b": [["10", "1"]], "a": [["11", "1"]]}}
        self.assertEqual(p(other)[0][2], "ETHUSDT")      # symbols do not share state

    def test_hyperliquid_bbo(self):
        m = {"channel": "bbo", "data": {"coin": "BTC", "time": 5, "bbo": [{"px": "81166.0", "sz": "0.1", "n": 1},
                                                                          {"px": "81167.0", "sz": "7.1", "n": 39}]}}
        self.assertEqual(rh.hyperliquid(m), [("book", "hyperliquid", "BTC", 81166.0, 0.1, 81167.0, 7.1, 5)])
        m["data"]["bbo"][1] = None
        self.assertEqual(rh.hyperliquid(m), [])
        self.assertEqual(rh.hyperliquid({"channel": "subscriptionResponse", "data": {}}), [])

    def test_hyperliquid_trades_become_fills_with_their_wallets(self):
        t = {"coin": "BTC", "side": "B", "px": "81047.0", "sz": "0.55283", "time": 5, "hash": "0x0",
             "tid": 362897608494116, "users": ["0xaa", "0xbb"]}
        m = {"channel": "trades", "data": [t, dict(t, tid=2, users=["0xcc"])]}
        self.assertEqual(rh.hyperliquid(m),
                         [("fill", "BTC", "B", 81047.0, 0.55283, "0xaa", "0xbb", 362897608494116, 5)])


    def test_fills_keep_one_row_each_with_both_wallets(self):
        b = rh.Buckets()
        b.on_fill("BTC", "B", 81000.0, 0.5, "0xaa", "0xbb", 7, T0 - 40, T0 + 60)
        b.on_fill("BTC", "A", 81001.0, 0.25, "0xcc", "0xdd", 6, T0 - 50, T0 + 70)
        b.on_fill("BTC", "A", 0, 1.0, "0xcc", "0xdd", 8, T0, T0 + 70)           # no price: dropped
        fills = b.drain(T0 + 10)[2]                                              # fills are never held back
        self.assertEqual(fills.t.tolist(), [T0 - 50, T0 - 40])
        self.assertEqual(fills.tid.tolist(), [6, 7])
        self.assertEqual(fills.iloc[1].tolist(), [T0 - 40, "BTC", "B", 81000.0, 0.5, "0xaa", "0xbb", 7, 100])
        self.assertTrue(b.drain()[2].empty)


class FilesTests(unittest.TestCase):
    def frames(self, t0, k=3, fills=False):
        b = rh.Buckets()
        for i in range(k):
            b.on_book("binance", "BTCUSDT", 100 + i, 1, 101 + i, 1, t0, t0 + 100 * i + 5)
            b.on_trade("binance", "BTCUSDT", 100.5, 1, bool(i % 2), t0, t0 + 100 * i + 6)
            if fills:
                b.on_fill("BTC", "B", 100.5, 1, "0xaa", "0xbb", t0 + i, t0 + 100 * i, t0 + 100 * i + 450)
        return b.drain()

    def test_parts_are_split_by_utc_day_and_merged_once_the_day_is_over(self):
        day = pd.Timestamp("2026-10-27", tz="UTC").value // 10**6
        with tempfile.TemporaryDirectory() as d:
            parts, out = Path(d) / "_parts", Path(d)
            n = rh.write_parts(self.frames(day + 86_400_000 - 150), day + 86_400_000, parts)    # spans midnight
            n += rh.write_parts(self.frames(day + 3_600_000), day + 3_700_000, parts)
            self.assertEqual(n, 12)
            self.assertEqual(sorted(p.parts[-1] for p in parts.glob("*/*")), ["2026-10-27", "2026-10-27", "2026-10-28",
                                                                              "2026-10-28"])
            self.assertEqual(rh.compact(day + 86_400_000 + 600_000, parts, out), [])        # the day is not 30 min over
            done = rh.compact(day + 86_400_000 + 1_800_000, parts, out)
            self.assertEqual(sorted(done), [("book", "2026-10-27", 5), ("trades", "2026-10-27", 5)])
            book = pd.read_parquet(out / "book" / "2026-10-27.parquet")
            self.assertEqual(book.t.is_monotonic_increasing, True)
            self.assertEqual(len(book), 5)
            self.assertEqual(sorted(p.parts[-1] for p in parts.glob("*/*")), ["2026-10-28", "2026-10-28"])
            self.assertEqual(rh.compact(day + 86_400_000 + 1_800_000, parts, out), [])      # nothing left to merge

    def test_a_day_merged_twice_keeps_each_row_once(self):
        day = pd.Timestamp("2026-10-27", tz="UTC").value // 10**6
        with tempfile.TemporaryDirectory() as d:
            parts, out = Path(d) / "_parts", Path(d)
            late = day + 2 * 86_400_000
            rh.write_parts(self.frames(day + 1000), day + 5000, parts)
            rh.compact(late, parts, out)
            rh.write_parts(self.frames(day + 1000), day + 5000, parts)        # the same buckets arrive again
            rh.write_parts(self.frames(day + 9000), day + 15000, parts)
            rh.compact(late, parts, out)
            self.assertEqual(len(pd.read_parquet(out / "book" / "2026-10-27.parquet")), 6)

    def test_fills_are_written_and_merged_by_trade_id(self):
        day = pd.Timestamp("2026-10-27", tz="UTC").value // 10**6
        with tempfile.TemporaryDirectory() as d:
            parts, out = Path(d) / "_parts", Path(d)
            rh.write_parts(self.frames(day + 1000, fills=True), day + 5000, parts)
            rh.write_parts(self.frames(day + 1000, fills=True), day + 6000, parts)       # the same fills again
            done = rh.compact(day + 2 * 86_400_000, parts, out)
            self.assertIn(("fills", "2026-10-27", 3), done)
            self.assertEqual(pd.read_parquet(out / "fills" / "2026-10-27.parquet").tid.tolist(),
                             [day + 1000, day + 1001, day + 1002])

    def test_files_hold_sizes_as_thousandths_and_load_returns_coins(self):
        day = pd.Timestamp("2026-10-27", tz="UTC").value // 10**6
        b = rh.Buckets()
        b.on_book("binance", "ETHUSDC", 2356.26, 4.105, 2356.27, 28.46, day + 10, day + 1050)
        b.on_book("binance", "ETHUSDC", 2356.26, 4.1054, 2356.27, 0.0004, day + 20, day + 1150)
        b.on_trade("binance", "ETHUSDC", 2356.2, 0.25, True, day + 10, day + 1050)
        frames = b.drain()
        packed = rh.pack(frames[0], "book")
        self.assertEqual((packed.bq.dtype, packed.bq.tolist(), packed.aq.tolist()), ("int32", [4105, 4105], [28460, 0]))
        self.assertTrue(rh.pack(packed, "book").equals(packed))                   # idempotent
        self.assertEqual(rh.unpack(packed, "book").bq.tolist(), [4.105, 4.105])
        with tempfile.TemporaryDirectory() as d:
            parts, out = Path(d) / "_parts", Path(d)
            rh.write_parts(frames, day + 5000, parts)
            self.assertIsNone(rh.load("book", "2026-10-27", out))                 # not merged yet
            rh.compact(day + 2 * 86_400_000, parts, out)
            book = rh.load("book", "2026-10-27", out)
            self.assertEqual((book.bq.dtype, book.bq.tolist(), book.aq.tolist()),
                             ("float64", [4.105, 4.105], [28.46, 0.0]))
            self.assertEqual(pd.read_parquet(out / "book" / "2026-10-27.parquet").bq.dtype, "int32")
            tr = rh.load("trades", "2026-10-27", out)
            self.assertEqual((tr.qs.tolist(), tr.ls.tolist()), ([0.25], [2356.2]))

    def test_a_part_written_with_float_sizes_merges_with_packed_ones(self):
        day = pd.Timestamp("2026-10-27", tz="UTC").value // 10**6
        with tempfile.TemporaryDirectory() as d:
            parts, out = Path(d) / "_parts", Path(d)
            old = self.frames(day + 1000)[0]
            legacy = parts / "book" / "2026-10-27"
            legacy.mkdir(parents=True)
            old.to_parquet(legacy / "old.parquet", index=False)                  # float sizes, as the first run wrote
            rh.write_parts(self.frames(day + 9000), day + 15000, parts)
            rh.compact(day + 2 * 86_400_000, parts, out)
            book = rh.load("book", "2026-10-27", out)
            self.assertEqual((len(book), book.bq.dtype), (6, "float64"))
            self.assertEqual(book.bq.tolist(), [1.0] * 6)

    def test_the_cap_and_the_free_floor_stop_writing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            with mock.patch.object(rh, "free_gb", return_value=9.0), mock.patch.object(rh, "hft_gb", return_value=0.1):
                self.assertEqual(rh.full(out), "")
            with mock.patch.object(rh, "free_gb", return_value=rh.MIN_FREE_GB - 0.1):
                self.assertIn("free", rh.full(out))
            with mock.patch.object(rh, "free_gb", return_value=9.0), \
                    mock.patch.object(rh, "hft_gb", return_value=rh.MAX_GB):
                self.assertIn("cap", rh.full(out))
        self.assertGreater(rh.MIN_FREE_GB, 2.0)          # above record_tape.py's floor: the older recorder first


if __name__ == "__main__":
    unittest.main()
