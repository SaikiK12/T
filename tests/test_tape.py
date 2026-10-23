import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from lab import tape

ROOT = Path(__file__).resolve().parent.parent
T0 = 1_792_000_000_000                      # a whole second


def recorder_module():
    spec = importlib.util.spec_from_file_location("record_tape", ROOT / "scripts" / "record_tape.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class OfiTest(unittest.TestCase):
    def test_cases_of_cont_kukanov_stoikov(self):
        prev = (100.0, 5.0, 101.0, 4.0)
        self.assertEqual(tape.ofi(prev, (100.0, 7.0, 101.0, 4.0)), 2.0)      # bid size grows
        self.assertEqual(tape.ofi(prev, (100.5, 1.0, 101.0, 4.0)), 1.0)      # a new better bid
        self.assertEqual(tape.ofi(prev, (99.5, 3.0, 101.0, 4.0)), -5.0)      # the best bid is taken out
        self.assertEqual(tape.ofi(prev, (100.0, 5.0, 101.0, 6.0)), -2.0)     # ask size grows
        self.assertEqual(tape.ofi(prev, (100.0, 5.0, 100.5, 1.0)), -1.0)     # a new better ask
        self.assertEqual(tape.ofi(prev, (100.0, 5.0, 101.5, 2.0)), 4.0)      # the best ask is lifted
        self.assertEqual(tape.ofi(prev, prev), 0.0)


class TapeTest(unittest.TestCase):
    def test_book_seconds_and_settle(self):
        t = tape.Tape()
        t.on_book("binance", "BTC", T0 + 100, 100.0, 5.0, 101.0, 4.0, T0 + 130)
        t.on_book("binance", "BTC", T0 + 900, 100.0, 7.0, 101.0, 4.0, T0 + 980)
        t.on_book("binance", "BTC", T0 + 1_200, 100.5, 1.0, 101.0, 3.0, T0 + 1_210)
        self.assertEqual(t.drain(T0 + 2_500), {})                              # T0 is final only at T0 + 3 s
        out = t.drain(T0 + 3_000)
        book, trades = out["binance"]
        self.assertTrue(trades.empty)
        self.assertEqual(book.s.tolist(), [T0])
        r = book.iloc[0]
        self.assertEqual((r.bid, r.bid_sz, r.ask, r.ask_sz, r.n, r.lag_ms), (100.0, 7.0, 101.0, 4.0, 2, 80))
        self.assertEqual(r.ofi, 2.0)                                            # the first update has no predecessor
        self.assertTrue(math.isnan(r.bid_sz5))
        t.on_book("binance", "BTC", T0 + 500, 100.0, 9.0, 101.0, 4.0, T0 + 3_100)
        self.assertEqual(t.late, 1)                                             # its second is already written
        rest = t.drain(None)["binance"][0]
        self.assertEqual(rest.s.tolist(), [T0 + 1_000])
        self.assertEqual(rest.ofi.iloc[0], 1.0 - 3.0 + 4.0)                     # new better bid; ask size 4 -> 3

    def test_reset_after_reconnect(self):
        t = tape.Tape()
        t.on_book("mexc", "ETH", T0, 10.0, 1.0, 11.0, 1.0, T0)
        t.reset("mexc")
        t.on_book("mexc", "ETH", T0 + 10, 10.0, 9.0, 11.0, 1.0, T0 + 10)
        self.assertEqual(t.drain(None)["mexc"][0].ofi.iloc[0], 0.0)

    def test_trades(self):
        t = tape.Tape()
        for dt, px, q, side in ((10, 100.0, 1.0, 1), (20, 99.0, 2.0, -1), (30, 102.0, 0.5, 1), (1_010, 50.0, 1.0, -1)):
            t.on_trade("binance", "SOL", T0 + dt, px, q, side)
        tr = t.drain(None)["binance"][1]
        r = tr.iloc[0]
        self.assertEqual((r.buy_qty, r.sell_qty, r.buy_n, r.sell_n), (1.5, 2.0, 2, 1))
        self.assertAlmostEqual(r.notional, 100.0 + 198.0 + 51.0)
        self.assertEqual((r.px_first, r.px_last, r.px_min, r.px_max), (100.0, 102.0, 99.0, 102.0))
        self.assertEqual(tr.s.tolist(), [T0, T0 + 1_000])

    def test_combine_merges_a_restart_second(self):
        b = pd.DataFrame([(T0, "BTC", 1.0, 1.0, 2.0, 1.0, math.nan, math.nan, 3.0, 2, 10),
                          (T0, "BTC", 1.5, 2.0, 2.5, 1.0, math.nan, math.nan, -1.0, 1, 40),
                          (T0, "ETH", 5.0, 1.0, 6.0, 1.0, math.nan, math.nan, 0.0, 1, 5)], columns=tape.BOOK)
        m = tape.combine(b, "book")
        self.assertEqual(len(m), 2)
        r = m[m.sym == "BTC"].iloc[0]
        self.assertEqual((r.bid, r.bid_sz, r.ofi, r.n, r.lag_ms), (1.5, 2.0, 2.0, 3, 40))
        tr = pd.DataFrame([(T0, "BTC", 1.0, 0.0, 1, 0, 100.0, 100.0, 101.0, 99.0, 101.0),
                           (T0, "BTC", 0.0, 2.0, 0, 1, 200.0, 98.0, 97.0, 97.0, 98.0)], columns=tape.TRADES)
        r = tape.combine(tr, "trades").iloc[0]
        self.assertEqual((r.buy_qty, r.sell_qty, r.buy_n, r.sell_n, r.notional), (1.0, 2.0, 1, 1, 300.0))
        self.assertEqual((r.px_first, r.px_last, r.px_min, r.px_max), (100.0, 97.0, 97.0, 101.0))


class ParseTest(unittest.TestCase):
    def test_binance(self):
        book = {"stream": "btcusdt@bookTicker", "data": {"e": "bookTicker", "s": "BTCUSDT", "b": "82695.40",
                                                          "B": "12.835", "a": "82695.50", "A": "4.429", "T": T0}}
        self.assertEqual(tape.binance(book, "book"), [("book", "BTC", T0, 82695.4, 12.835, 82695.5, 4.429)])
        self.assertEqual(tape.binance(book, "trade"), [])
        trade = {"stream": "btcusdt@aggTrade", "data": {"e": "aggTrade", "s": "BTCUSDT", "p": "82668.50",
                                                         "q": "0.001", "T": T0, "m": True}}
        self.assertEqual(tape.binance(trade, "trade"), [("trade", "BTC", T0, 82668.5, 0.001, -1)])

    def test_mexc_contract_sizes(self):
        sizes = {"BTC_USDT": 0.0001}
        depth = {"channel": "push.depth.full", "symbol": "BTC_USDT", "ts": T0,
                 "data": {"asks": [[82670.4, 12557, 1], [82670.5, 4872, 1]],
                          "bids": [[82670.3, 22522, 7], [82669.9, 185, 1]]}}
        (ev,) = tape.mexc(depth, sizes)
        self.assertEqual(ev[:4], ("book", "BTC", T0, 82670.3))
        self.assertAlmostEqual(ev[4], 2.2522)                     # index 1 is volume in contracts
        self.assertAlmostEqual(ev[6], 1.2557)
        self.assertAlmostEqual(ev[7], (22522 + 185) * 0.0001)     # top-five coin quantity
        self.assertAlmostEqual(ev[8], (12557 + 4872) * 0.0001)
        crossing = {**depth, "ts": T0 + 900,
                    "data": {**depth["data"], "cts": T0 + 1_100}}
        (clocked,) = tape.mexc(crossing, sizes)
        self.assertEqual(clocked[2], T0 + 1_100)                   # matching-engine clock beats envelope clock
        bucket = tape.Tape(settle_ms=0)
        bucket.on_book("mexc", "BTC", clocked[2], clocked[3], clocked[4], clocked[5], clocked[6], clocked[2],
                       bid_sz5=clocked[7], ask_sz5=clocked[8])
        self.assertEqual(bucket.drain()["mexc"][0].s.tolist(), [T0 + 1_000])
        for invalid_cts in (T0 + 1.5, float("inf"), True):
            bad_clock = {**crossing, "data": {**crossing["data"], "cts": invalid_cts}}
            self.assertEqual(tape.mexc(bad_clock, sizes), [])    # malformed present cts does not fall back to ts
        malformed = {"channel": "push.depth.full", "symbol": "BTC_USDT", "ts": T0,
                     "data": {"asks": [[82670.4, 12557, 1.5]], "bids": [[82670.3, 22522, 7]]}}
        self.assertEqual(tape.mexc(malformed, sizes), [])
        deal = {"channel": "push.deal", "symbol": "BTC_USDT", "ts": T0,
                "data": [{"p": 82692.9, "v": 5, "T": 2, "t": T0 + 1, "cts": str(T0 + 1_001)},
                         {"p": 82693.0, "v": 10, "T": 1, "t": T0 + 2},
                         {"p": 82693.1, "v": 1, "T": 1, "cts": str(T0 + 1_002)}]}
        evs = tape.mexc(deal, sizes)
        self.assertEqual([e[5] for e in evs], [-1, 1, 1])
        self.assertEqual([e[2] for e in evs], [T0 + 1, T0 + 2, T0 + 1_002])  # trade t wins; cts fills a missing t
        self.assertAlmostEqual(evs[1][4], 0.001)
        bad_trade = {**deal, "data": [{"p": 1, "v": 1, "T": 1, "t": T0 + 1.5, "cts": str(T0 + 1)}]}
        self.assertEqual(tape.mexc(bad_trade, sizes), [])        # malformed present t does not fall back to cts
        self.assertEqual(tape.mexc(dict(deal, symbol="ETH_USDT"), sizes), [])


    def test_lighter(self):
        names = {1: "BTC"}
        tick = {"channel": "ticker:1", "type": "update/ticker", "timestamp": T0 + 30,
                "ticker": {"s": "BTC", "a": {"price": "84533.5", "size": "0.35489"},
                           "b": {"price": "84532.4", "size": "0.00020"}, "last_updated_at": T0 * 1000 + 181094}}
        self.assertEqual(tape.lighter(tick, names), [("book", "BTC", T0 + 181, 84532.4, 0.0002, 84533.5, 0.35489)])
        self.assertEqual(tape.lighter(dict(tick, channel="ticker:2"), names), [])
        trade = {"channel": "trade:1", "type": "update/trade",
                 "trades": [{"price": "84532.1", "size": "0.00013", "timestamp": T0 + 5, "is_maker_ask": False}],
                 "liquidation_trades": [{"price": "84863.0", "size": "0.5", "timestamp": T0 + 6, "is_maker_ask": True}]}
        self.assertEqual(tape.lighter(trade, names), [("trade", "BTC", T0 + 5, 84532.1, 0.00013, -1),
                                                      ("trade", "BTC", T0 + 6, 84863.0, 0.5, 1)])
        self.assertEqual(tape.lighter(dict(trade, type="subscribed/trade"), names), [])
        self.assertEqual(tape.lighter({"type": "connected"}, names), [])


class CompactTest(unittest.TestCase):
    def test_finished_days_merge_and_today_waits(self):
        rec = recorder_module()
        with tempfile.TemporaryDirectory() as tmp:
            parts, out = Path(tmp) / "_parts", Path(tmp)
            day0 = pd.Timestamp("2026-10-20", tz="UTC").value // 10**6
            old = parts / "binance" / "book" / "2026-10-20"
            new = parts / "binance" / "book" / "2026-10-21"
            for d in (old, new):
                d.mkdir(parents=True)
            row = lambda s, ofi: (s, "BTC", 1.0, 1.0, 2.0, 1.0, math.nan, math.nan, ofi, 1, 5)
            pd.DataFrame([row(day0, 1.0), row(day0 + 1_000, 2.0)], columns=tape.BOOK).to_parquet(old / "001000-1.parquet")
            pd.DataFrame([row(day0 + 1_000, 3.0)], columns=tape.BOOK).to_parquet(old / "002000-2.parquet")
            pd.DataFrame([row(day0 + 86_400_000, 1.0)], columns=tape.BOOK).to_parquet(new / "000500-2.parquet")
            done = rec.compact(day0 + 86_400_000 + 1_900_000, parts=parts, out=out)
            self.assertEqual(done, [("binance", "book", "2026-10-20", 2)])
            daily = pd.read_parquet(out / "binance" / "book" / "2026-10-20.parquet")
            self.assertEqual(daily.ofi.tolist(), [1.0, 5.0])
            self.assertFalse(old.exists())
            self.assertTrue((new / "000500-2.parquet").exists())                 # today's part is left alone
            self.assertEqual(rec.compact(day0 + 86_400_000 + 1_000_000, parts=parts, out=out), [])


if __name__ == "__main__":
    unittest.main()
