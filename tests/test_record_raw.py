"""scripts/record_raw.py: the raw-event rows of each venue message, order and clocks kept, the daily merge, the caps."""
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_raw as rr  # noqa: E402

T_MS = 1_793_217_600_000          # 2026-10-28 20:00:00 UTC
T_US = T_MS * 1000
OFF = 5_000_000                    # wall minus monotonic, microseconds


def book(s="BTCUSDC", u=100, b="80000.10", bq="1.500", a="80000.20", aq="2.250", T=T_MS, E=T_MS + 1):
    return {"stream": f"{s.lower()}@bookTicker", "data": {"e": "bookTicker", "u": u, "s": s, "b": b, "B": bq, "a": a,
                                                            "A": aq, "T": T, "E": E}}


def trade(s="BTCUSDC", a=7, p="80000.10", q="0.016", nq="0.016", f=70, l=72, m=False, T=T_MS, E=T_MS + 2):
    d = {"e": "aggTrade", "E": E, "a": a, "s": s, "p": p, "q": q, "f": f, "l": l, "T": T, "m": m}
    if nq is not None:
        d["nq"] = nq
    return {"stream": f"{s.lower()}@aggTrade", "data": d}


def depth(s="BTCUSDC", b=(), a=(), U=10, u=20, pu=9):
    return {"stream": f"{s.lower()}@rpiDepth@500ms", "data": {"e": "depthUpdate", "E": T_MS + 3, "T": T_MS + 1, "s": s,
                                                               "U": U, "u": u, "pu": pu, "b": [list(x) for x in b],
                                                               "a": [list(x) for x in a]}}


def bybit(s="BTCUSDT", kind="snapshot", b=(("80000.0", "3.0"),), a=(("80000.1", "4.0"),), u=5, seq=50, ts=T_MS + 9,
          cts=T_MS + 8):
    m = {"topic": f"orderbook.1.{s}", "type": kind, "ts": ts, "data": {"s": s, "b": [list(x) for x in b],
                                                                         "a": [list(x) for x in a], "u": u, "seq": seq}}
    if cts is not None:
        m["cts"] = cts
    return m


def liquidation(s="BTCUSDT", side="Buy", v="0.250", p="79500.50", T=T_MS + 4, shape="list"):
    d = {"T": T, "s": s, "S": side, "v": v, "p": p}
    return {"topic": f"allLiquidation.{s}", "type": "snapshot", "ts": T + 1, "data": [d] if shape == "list" else d}


def fx_book(u=9, b="1.0001160", bq="367685", a="1.0001170", aq="162299", T=T_MS, E=T_MS):
    return {"stream": "usdcusdt@bookTicker", "data": {"e": "bookTicker", "u": u, "s": "USDCUSDT", "ps": "USDCUSDT",
                                                      "b": b, "B": bq, "a": a, "A": aq, "T": T, "E": E, "st": 1}}


def ticker(kind="snapshot", s="BTCUSDT", ts=T_MS + 5, **fields):
    return {"topic": f"tickers.{s}", "type": kind, "ts": ts, "data": {"symbol": s, **fields}}


def pub_trade(s="BTCUSDT", rows=(("Buy", "80000.10", "0.946", False, False),), seq=700):
    return {"topic": f"publicTrade.{s}", "type": "snapshot", "ts": T_MS + 6,
            "data": [{"T": T_MS + 5, "s": s, "S": sd, "v": v, "p": p, "seq": seq, "BT": bt, "RPI": rpi}
                     for sd, p, v, bt, rpi in rows]}


def rpi_book(s="BTCPERP", kind="snapshot", b=(), a=(), u=1, seq=900, ts=T_MS + 7):
    return {"topic": f"orderbook.rpi.{s}", "type": kind, "ts": ts, "cts": ts - 1,
            "data": {"s": s, "b": [list(x) for x in b], "a": [list(x) for x in a], "u": u, "seq": seq}}


def k_snapshot(s="PF_XBTUSD", seq=100, bids=((80000.0, 1.5), (79999.0, 2.0)), asks=((80001.0, 0.5), (80002.0, 3.0))):
    return {"feed": "book_snapshot", "product_id": s, "timestamp": T_MS, "seq": seq,
            "bids": [{"price": p, "qty": q} for p, q in bids], "asks": [{"price": p, "qty": q} for p, q in asks]}


def k_book(side, price, qty, seq, s="PF_XBTUSD"):
    return {"feed": "book", "product_id": s, "side": side, "seq": seq, "price": price, "qty": qty,
            "timestamp": T_MS + seq}


def k_trade(side="buy", price=80001.0, qty=0.0246, seq=5, kind="fill", s="PF_XBTUSD"):
    return {"feed": "trade", "product_id": s, "uid": "x", "side": side, "type": kind, "time": T_MS + 3, "qty": qty,
            "price": price, "seq": seq}


class ParseTests(unittest.TestCase):
    def test_book_row_keeps_both_stamps_and_the_update_id(self):
        t = rr.Tape()
        t.binance(book(T=T_MS, E=T_MS + 3, u=101), T_US + 55_000, OFF)
        row = t.rows[("bbo", "BTCUSDC")][0]
        self.assertEqual(row, (T_US + 55_000, OFF, 101, T_MS, 3, 8_000_010, 1500, 10, 2250))
        self.assertEqual(t.mid["BTCUSDC"], 80000.15)
        d = rr.decode(rr.frame("bbo", t.rows[("bbo", "BTCUSDC")]), "bbo")
        self.assertAlmostEqual(d.ask[0], 80000.20)
        self.assertEqual(d.mono_us[0], T_US + 55_000 - OFF)

    def test_invalid_and_crossed_books_are_counted_not_stored(self):
        t = rr.Tape()
        t.binance(book(b="80000.30", a="80000.20"), T_US, OFF)
        t.binance(book(b="0", a="80000.20"), T_US, OFF)
        self.assertEqual(t.stat["bad_book"], 2)
        self.assertNotIn(("bbo", "BTCUSDC"), t.rows)

    def test_repeated_or_backwards_update_ids_are_counted(self):
        t = rr.Tape()
        for u in (10, 11, 11, 9, 12):
            t.binance(book(u=u), T_US, OFF)
        self.assertEqual(t.stat["u_back"], {("bbo", "BTCUSDC"): 2})

    def test_unknown_symbol_is_ignored_and_rounding_loss_is_counted(self):
        t = rr.Tape()
        t.binance(book(s="SOLUSDT"), T_US, OFF)
        self.assertFalse(t.rows)
        t.binance(book(b="80000.123"), T_US, OFF)
        self.assertGreaterEqual(t.stat["lossy"], 1)

    def test_trade_keeps_nq_and_the_rpi_part(self):
        t = rr.Tape()
        t.binance(trade(q="0.050", nq="0.020", f=70, l=73, m=True), T_US, OFF)
        t.binance(trade(q="0.010", nq="0.010", a=8), T_US, OFF)
        t.binance(trade(q="0.010", nq=None, a=9), T_US, OFF)
        rows = t.rows[("trade", "BTCUSDC")]
        self.assertEqual(rows[0], (T_US, OFF, 7, T_MS, 2, 8_000_010, 50, 20, 70, 4, 1))
        self.assertEqual((t.stat["trades"], t.stat["q_ne_nq"], t.stat["no_nq"]), (3, 1, 1))
        d = rr.decode(rr.frame("trade", rows), "trade")
        self.assertAlmostEqual(d.rpi_q[0], 0.03)
        self.assertEqual(d.rpi_q[1], 0.0)
        self.assertTrue(pd.isna(d.rpi_q[2]) and pd.isna(d.nq[2]))

    def test_rpi_depth_keeps_levels_near_the_mid_of_the_stored_symbols_only(self):
        t = rr.Tape()
        msg = depth(b=[("80000.10", "1.0"), ("79000.00", "9.0")], a=[("80000.20", "0.0"), ("81000.0", "5.0")])
        t.binance(msg, T_US, OFF)                                 # no bookTicker yet: summary row only
        self.assertEqual(t.stat["rpi_nomid"], 1)
        self.assertEqual(t.rows[("rpimsg", "BTCUSDC")][0][-3:], (2, 2, -1))
        self.assertNotIn(("rpilv", "BTCUSDC"), t.rows)
        t.binance(book(), T_US, OFF)
        t.binance(msg, T_US + 500_000, OFF)
        self.assertEqual(t.rows[("rpilv", "BTCUSDC")], [(T_US + 500_000, 0, 8_000_010, 1000),
                                                         (T_US + 500_000, 1, 8_000_020, 0)])
        self.assertEqual(t.rows[("rpimsg", "BTCUSDC")][1][-3:], (2, 2, 2))
        t.binance(book(s="BTCUSDT"), T_US, OFF)
        t.binance(depth(s="BTCUSDT", b=[("80000.10", "1.0")]), T_US, OFF)
        self.assertNotIn(("rpilv", "BTCUSDT"), t.rows)
        self.assertEqual(len(t.rows[("rpimsg", "BTCUSDT")]), 1)

    def test_bybit_keeps_ts_cts_flags_and_merges_one_sided_deltas(self):
        t = rr.Tape()
        t.bybit(bybit(), T_US, OFF)
        t.bybit(bybit(kind="delta", b=[("80000.0", "3.5")], a=[], u=6, seq=51), T_US + 10_000, OFF)
        t.bybit(bybit(kind="delta", b=[], a=[("80000.1", "0")], u=7, seq=52), T_US + 20_000, OFF)   # ask side emptied
        rows = t.rows[("bybit", "BTCUSDT")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (T_US, OFF, 5, 50, T_MS + 9, 1, 7, 8_000_000, 3000, 10, 4000))
        self.assertEqual(rows[1][2:], (6, 51, T_MS + 9, 1, 1, 8_000_000, 3500, 10, 4000))
        t.bybit(bybit(kind="delta", b=[("80000.0", "3.6")], a=[], u=8, seq=40), T_US + 30_000, OFF)
        self.assertEqual(t.stat["seq_back"], 1)

    def test_bybit_without_cts_marks_it_missing(self):
        t = rr.Tape()
        t.bybit(bybit(cts=None), T_US, OFF)
        self.assertEqual(t.rows[("bybit", "BTCUSDT")][0][5], -1)

    def test_liquidation_prints_become_rows_with_the_long_liquidated_side(self):
        t = rr.Tape()
        t.bybit(liquidation(), T_US, OFF)
        t.bybit(liquidation(side="Sell", v="1.5", p="79600", shape="dict"), T_US + 500_000, OFF)
        rows = t.rows[("liq", "BTCUSDT")]
        self.assertEqual(rows[0], (T_US, OFF, T_MS + 4, 1, 250, 7_950_050))
        self.assertEqual(rows[1][3:], (0, 1500, 7_960_000))
        d = rr.decode(rr.frame("liq", rows), "liq")
        self.assertAlmostEqual(d.v[0], 0.25)
        self.assertAlmostEqual(d.p[0], 79500.50)
        self.assertEqual(t.stat["liq_raw"], 0)

    def test_a_liquidation_message_that_does_not_parse_is_kept_whole(self):
        t = rr.Tape()
        odd = {"topic": "allLiquidation.BTCUSDT",
               "data": [{"T": T_MS, "s": "BTCUSDT", "S": "Short", "v": "1", "p": "2"}]}
        t.bybit(odd, T_US, OFF)
        t.bybit({"topic": "allLiquidation.ETHUSDT", "data": "oops"}, T_US, OFF)
        self.assertNotIn(("liq", "BTCUSDT"), t.rows)
        self.assertEqual(t.stat["liq_raw"], 2)
        self.assertEqual(t.drain_raw()[0], {"t": T_US, "msg": odd})
        self.assertEqual(t.drain_raw(), [])

    def test_largest_gap_between_messages_is_kept_per_stream(self):
        t = rr.Tape()
        for dt in (0, 5_000, 1_205_000):
            t.binance(book(u=int(dt) + 1), T_US + dt, OFF)
        self.assertEqual(t.stat["max_gap_ms"][("bbo", "BTCUSDC")], 1200)


class VenueStreamTests(unittest.TestCase):
    def test_usdcusdt_book_keeps_seven_decimals(self):
        t = rr.Tape()
        t.binance(fx_book(), T_US, OFF)
        row = t.rows[("fx", "USDCUSDT")][0]
        self.assertEqual(row[5:], (10_001_160, 367_685_000, 10, 162_299_000))
        d = rr.decode(rr.frame("fx", t.rows[("fx", "USDCUSDT")]), "fx")
        self.assertAlmostEqual(d.bid[0], 1.000116, places=9)
        self.assertAlmostEqual(d.ask[0], 1.000117, places=9)
        self.assertEqual(t.stat["lossy"], 0)
        self.assertNotIn(("bbo", "USDCUSDT"), t.rows)

    def test_ticker_deltas_merge_and_only_changes_are_rows(self):
        t = rr.Tape()
        t.bybit(ticker(markPrice="81303.99", indexPrice="81348.57", openInterest="62391.764", fundingRate="0.00009177"),
                T_US, OFF)
        t.bybit(ticker("delta", ask1Price="81303.00"), T_US + 1, OFF)                 # no tracked field: no row
        t.bybit(ticker("delta", markPrice="81304.10", ts=T_MS + 9), T_US + 2, OFF)
        t.bybit(ticker("delta", markPrice="81304.10"), T_US + 3, OFF)                 # unchanged: no row
        t.bybit(ticker("delta", openInterest="62392.000", fundingRate="-0.0001"), T_US + 4, OFF)
        rows = t.rows[("bticker", "BTCUSDT")]
        self.assertEqual(rows[0], (T_US, OFF, T_MS + 5, 8_130_399, 8_134_857, 62_391_764, 9_177))
        self.assertEqual(rows[1][3:], (8_130_410, 8_134_857, 62_391_764, 9_177))
        self.assertEqual(rows[2][3:], (8_130_410, 8_134_857, 62_392_000, -10_000))
        self.assertEqual(len(rows), 3)
        d = rr.decode(rr.frame("bticker", rows), "bticker")
        self.assertAlmostEqual(d.fr.iloc[2], -0.0001)
        self.assertAlmostEqual(d.oi.iloc[0], 62391.764)

    def test_a_ticker_delta_before_any_snapshot_waits_for_a_full_state(self):
        t = rr.Tape()
        t.bybit(ticker("delta", markPrice="81304.10"), T_US, OFF)
        self.assertNotIn(("bticker", "BTCUSDT"), t.rows)

    def test_public_trades_keep_side_flags_and_spot_symbols_are_suffixed(self):
        t = rr.Tape()
        t.bybit(pub_trade(rows=(("Buy", "80000.10", "0.946", False, False), ("Sell", "80000.00", "0.002", True, True))),
                T_US, OFF)
        t.bybit(pub_trade(s="BTCUSDT", rows=(("Sell", "80001.1", "0.000833", False, True),), seq=11), T_US + 1, OFF,
                rr.SPOT_SUFFIX)
        rows = t.rows[("btrade", "BTCUSDT")]
        self.assertEqual(rows[0], (T_US, OFF, T_MS + 5, 700, 1, 8_000_010, 946_000, 0))
        self.assertEqual(rows[1][4:], (0, 8_000_000, 2_000, 3))                 # RPI and block
        spot = t.rows[("btrade", "BTCUSDT_SPOT")][0]
        self.assertEqual(spot[4:], (0, 8_000_110, 833, 1))
        self.assertEqual(t.stat["lossy"], 0)
        d = rr.decode(rr.frame("btrade", t.rows[("btrade", "BTCUSDT_SPOT")]), "btrade")
        self.assertAlmostEqual(d.v[0], 0.000833)

    def test_rpi_book_keeps_five_levels_deltas_delete_and_unchanged_tops_are_not_rows(self):
        t = rr.Tape()
        bids = [("100.0", "1.0", "0.5"), ("99.9", "0", "2.0"), ("99.8", "0.1", "0"), ("99.7", "0.1", "0"),
                ("99.6", "0.1", "0"), ("99.5", "0.1", "0"), ("99.4", "0.1", "0")]
        t.bybit(rpi_book(b=bids, a=[("100.1", "0.3", "0")]), T_US, OFF)
        first = t.rows[("rpibook", "BTCPERP")][0]
        self.assertEqual(first[6], 4)                                          # snapshot flag
        self.assertEqual(first[7:10], (10_000, 1_000_000, 500_000))              # best bid: price, ordinary, RPI
        self.assertEqual(first[7 + 12:7 + 15], (9_960, 100_000, 0))             # fifth bid level
        self.assertEqual(first[7 + 15:7 + 18], (10_010, 300_000, 0))            # best ask
        self.assertEqual(first[7 + 18:7 + 21], (0, 0, 0))                       # no second ask
        t.bybit(rpi_book(kind="delta", b=[("99.4", "0.2", "0")], u=2), T_US + 1, OFF)       # outside the top five
        self.assertEqual(len(t.rows[("rpibook", "BTCPERP")]), 1)
        self.assertEqual(t.stat["rpi_same"], 1)
        t.bybit(rpi_book(kind="delta", b=[("100.0", "0", "0"), ("99.55", "0.4", "0")], u=3), T_US + 2, OFF)
        row = t.rows[("rpibook", "BTCPERP")][1]
        self.assertEqual(row[6], 0)
        self.assertEqual(row[7:10], (9_990, 0, 2_000_000))                       # 100.0 deleted: 99.9 is best
        d = rr.decode(rr.frame("rpibook", t.rows[("rpibook", "BTCPERP")]), "rpibook")
        self.assertAlmostEqual(d.b0p[1], 99.9)
        self.assertAlmostEqual(d.b0r[1], 2.0)

    def test_rpi_book_state_follows_messages_outside_the_window_but_writes_only_inside(self):
        t = rr.Tape(hours=(20, 21))
        noon = T_US - 8 * 3600 * 1_000_000
        t.bybit(rpi_book(b=[("100.0", "1.0", "0")], a=[("100.1", "1.0", "0")]), noon, OFF)
        t.bybit(rpi_book(kind="delta", b=[("100.0", "0", "0"), ("99.0", "2.0", "0")], u=2), noon + 1, OFF)
        self.assertNotIn(("rpibook", "BTCPERP"), t.rows)
        t.bybit(rpi_book(kind="delta", a=[("100.2", "1.0", "0")], u=3), T_US, OFF)
        row = t.rows[("rpibook", "BTCPERP")][0]
        self.assertEqual(row[7:10], (9_900, 2_000_000, 0))                       # the deleted bid stayed deleted

    def test_a_failed_subscription_is_recorded(self):
        t = rr.Tape()
        t.bybit({"op": "subscribe", "success": False, "ret_msg": "handler not found"}, T_US, OFF)
        t.bybit({"op": "subscribe", "success": True, "ret_msg": ""}, T_US, OFF)
        self.assertEqual(t.stat["sub_fail"], ["handler not found"])

    def test_kraken_snapshot_updates_trades_and_sequence_gaps(self):
        t = rr.Tape()
        t.kraken(k_snapshot(), T_US, OFF)
        t.kraken(k_book("buy", 80000.0, 0.0, 101), T_US + 1, OFF)                  # removes the best bid
        t.kraken(k_book("sell", 80003.0, 1.25, 102), T_US + 2, OFF)
        t.kraken(k_book("sell", 80004.0, 1.0, 104), T_US + 3, OFF)                 # 103 missing
        t.kraken(k_trade(), T_US + 4, OFF)
        t.kraken(k_trade(kind="liquidation", side="sell", seq=6), T_US + 5, OFF)
        t.kraken({"event": "subscribed", "feed": "book", "product_ids": ["PF_XBTUSD"]}, T_US, OFF)
        t.kraken(k_book("buy", 1.0, 1.0, 1, s="PF_SOLUSD"), T_US, OFF)            # unknown product
        book_rows = t.rows[("kbook", "PF_XBTUSD")]
        snap = [r for r in book_rows if r[7] == 1]
        self.assertEqual(len(snap), 4)
        self.assertEqual(snap[0][4:7], (0, 8_000_000, 1_500_000))                  # best bid
        self.assertEqual(snap[2][4:7], (1, 8_000_100, 500_000))                    # best ask
        upd = [r for r in book_rows if r[7] == 0]
        self.assertEqual([(r[4], r[5], r[6]) for r in upd], [(0, 8_000_000, 0), (1, 8_000_300, 1_250_000),
                                                             (1, 8_000_400, 1_000_000)])
        self.assertEqual(t.stat["kseq_gap"], {"PF_XBTUSD": 1})
        trades = t.rows[("ktrade", "PF_XBTUSD")]
        self.assertEqual(trades[0][4:], (1, 0, 8_000_100, 24_600))
        self.assertEqual(trades[1][4:6], (0, 1))                                    # liquidation type code
        self.assertEqual(t.stat["lossy"], 0)

    def test_kraken_book_outside_the_window_is_followed_and_a_snapshot_opens_the_window(self):
        t = rr.Tape(hours=(20, 21))
        noon = T_US - 8 * 3600 * 1_000_000
        t.kraken(k_snapshot(), noon, OFF)
        t.kraken(k_book("buy", 80000.0, 0.0, 101), noon + 1, OFF)
        t.kraken(k_trade(), noon + 2, OFF)
        self.assertNotIn(("kbook", "PF_XBTUSD"), t.rows)
        self.assertNotIn(("ktrade", "PF_XBTUSD"), t.rows)
        t.kraken(k_book("sell", 80001.0, 0.75, 102), T_US, OFF)
        rows = t.rows[("kbook", "PF_XBTUSD")]
        snap = [r for r in rows if r[7] == 1]
        self.assertEqual([r[5] for r in snap if r[4] == 0], [7_999_900])           # the removed bid is gone
        self.assertEqual(rows[-1][4:8], (1, 8_000_100, 750_000, 0))
        t.kraken(k_book("sell", 80001.0, 0.5, 103), T_US + 1, OFF)
        self.assertEqual(len([r for r in t.rows[("kbook", "PF_XBTUSD")] if r[7] == 1]), len(snap))   # only one snapshot

    def test_new_kinds_round_trip_through_parts(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            t = rr.Tape()
            t.binance(fx_book(), T_US, OFF)
            t.bybit(ticker(markPrice="81303.99", indexPrice="81348.57", openInterest="62391.764",
                           fundingRate="0.00009177"), T_US, OFF)
            t.bybit(pub_trade(), T_US, OFF)
            t.bybit(rpi_book(b=[("100.0", "1.0", "0.5")], a=[("100.1", "0.3", "0")]), T_US, OFF)
            t.kraken(k_snapshot(), T_US, OFF)
            t.kraken(k_trade(), T_US, OFF)
            kinds = sorted({k for k, _ in t.rows})
            self.assertEqual(rr.write_parts(t.drain(), T_US / 1e6, out / "_parts"), 9)
            day = rr.utc_day(T_US)
            rr.compact(now=T_US / 1e6 + 86_400, parts=out / "_parts", out=out)
            for kind in kinds:
                sym = {"fx": "USDCUSDT", "kbook": "PF_XBTUSD", "ktrade": "PF_XBTUSD"}.get(kind, "BTCUSDT")
                if kind == "rpibook":
                    sym = "BTCPERP"
                df = rr.load(kind, sym, day, out)
                self.assertIsNotNone(df, kind)
                self.assertEqual(list(df.columns), rr.COLS[kind])
                rr.decode(df, kind)

    def test_ticker_and_rpi_topics_are_parsed_at_any_hour_and_trades_only_in_the_window(self):
        rec = rr.Recorder(out=Path(tempfile.gettempdir()), hours=(13, 17))
        at = lambda h: (T_MS // 1000 - 20 * 3600 + h * 3600) * 10**9
        self.assertTrue(rec.keep('{"topic":"tickers.BTCUSDT","data":{}}', at(3)))
        self.assertTrue(rec.keep('{"topic":"orderbook.rpi.BTCPERP","data":{}}', at(3)))
        self.assertFalse(rec.keep('{"topic":"publicTrade.BTCUSDT","data":[]}', at(3)))
        self.assertTrue(rec.keep('{"topic":"publicTrade.BTCUSDT","data":[]}', at(14)))
        self.assertEqual(rec.tape.hours, (13, 17))

    def test_bybit_topics_are_subscribed_in_small_messages(self):
        msgs = rr.subscribe([f"t{i}" for i in range(19)])
        self.assertEqual([len(m["args"]) for m in msgs], [8, 8, 3])
        self.assertTrue(all(m["op"] == "subscribe" for m in msgs))


class WindowTests(unittest.TestCase):
    def test_hours_window(self):
        at = lambda h: (T_MS // 1000 - 20 * 3600 + h * 3600) * 10**9
        self.assertTrue(rr.in_window(at(13), (13, 17)) and rr.in_window(at(16), (13, 17)))
        self.assertFalse(rr.in_window(at(17), (13, 17)) or rr.in_window(at(12), (13, 17)))
        self.assertTrue(rr.in_window(at(23), (22, 2)) and rr.in_window(at(1), (22, 2)))
        self.assertFalse(rr.in_window(at(5), (22, 2)))
        self.assertTrue(rr.in_window(at(5), None))
        self.assertEqual(rr.parse_hours("13-17"), (13, 17))

    def test_liquidations_are_kept_at_any_hour_and_book_messages_only_in_the_window(self):
        rec = rr.Recorder(out=Path(tempfile.gettempdir()), hours=(13, 17))
        at = lambda h: (T_MS // 1000 - 20 * 3600 + h * 3600) * 10**9
        liq = '{"topic":"allLiquidation.BTCUSDT","data":[]}'
        book_msg = '{"topic":"orderbook.1.BTCUSDT","data":{}}'
        self.assertTrue(rec.keep(liq, at(3)) and rec.keep(book_msg, at(14)))
        self.assertFalse(rec.keep(book_msg, at(3)))
        self.assertFalse(rec.keep(b"{}", at(3)))


class FileTests(unittest.TestCase):
    def tape(self, n, t0, sym="BTCUSDC", u0=1):
        t = rr.Tape()
        for i in range(n):
            t.binance(book(s=sym, u=u0 + i, b=f"{80000 + i % 7}.10", a=f"{80000 + i % 7}.20", T=t0 // 1000 + i),
                      t0 + i * 1000, OFF)
        return t

    def test_parts_keep_arrival_order_and_merge_into_a_daily_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            first = self.tape(5, T_US)
            second = self.tape(5, T_US + 10_000_000, u0=100)
            with mock.patch.object(rr.os, "getpid", return_value=1):
                rr.write_parts(first.drain(), T_US / 1e6, out / "_parts")
            with mock.patch.object(rr.os, "getpid", return_value=2):
                rr.write_parts(second.drain(), T_US / 1e6 + 600, out / "_parts")
            day = rr.utc_day(T_US)
            self.assertEqual(len(list((out / "_parts" / "bbo" / "BTCUSDC" / day).glob("*.parquet"))), 2)
            self.assertEqual(rr.compact(now=T_US / 1e6 + 3600, parts=out / "_parts", out=out), [])    # day not over
            done = rr.compact(now=T_US / 1e6 + 86_400, parts=out / "_parts", out=out)
            self.assertEqual(done, [("bbo", "BTCUSDC", day, 10)])
            self.assertFalse((out / "_parts" / "bbo" / "BTCUSDC" / day).exists())
            df = rr.load("bbo", "BTCUSDC", day, out)
            self.assertEqual(list(df.u), [1, 2, 3, 4, 5, 100, 101, 102, 103, 104])
            self.assertEqual(df.t.iloc[0], T_US)
            self.assertEqual(str(df.dtypes["bq"]), "int64")
            self.assertIsNone(rr.load("bbo", "BTCUSDC", "2026-01-01", out))

    def test_rows_split_by_symbol_and_by_utc_day(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            midnight = (T_MS // 86_400_000 + 1) * 86_400_000_000
            t = rr.Tape()
            t.binance(book(s="BTCUSDC", u=1), midnight - 1_000, OFF)
            t.binance(book(s="BTCUSDC", u=2), midnight + 1_000, OFF)
            t.binance(book(s="ETHUSDC", b="2300.10", a="2300.11", u=3), midnight + 2_000, OFF)
            self.assertEqual(rr.write_parts(t.drain(), midnight / 1e6, out / "_parts"), 3)
            names = sorted(str(p.relative_to(out / "_parts")).rsplit("/", 1)[0] for p in
                           (out / "_parts").rglob("*.parquet"))
            self.assertEqual(names, ["bbo/BTCUSDC/2026-10-28", "bbo/BTCUSDC/2026-10-29", "bbo/ETHUSDC/2026-10-29"])

    def test_a_rerun_of_the_merge_adds_to_an_existing_daily_file_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            with mock.patch.object(rr.os, "getpid", return_value=1):
                rr.write_parts(self.tape(3, T_US).drain(), T_US / 1e6, out / "_parts")
            rr.compact(now=T_US / 1e6 + 86_400, parts=out / "_parts", out=out)
            with mock.patch.object(rr.os, "getpid", return_value=2):
                rr.write_parts(self.tape(2, T_US + 5_000_000, u0=50).drain(), T_US / 1e6 + 5, out / "_parts")
            rr.compact(now=T_US / 1e6 + 86_400, parts=out / "_parts", out=out)
            self.assertEqual(list(rr.load("bbo", "BTCUSDC", rr.utc_day(T_US), out).u), [1, 2, 3, 50, 51])

    def test_liquidation_rows_round_trip_and_raw_messages_reach_the_side_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            rec = rr.Recorder(out=out, hours=None)
            rec.tape.bybit(liquidation(), T_US, OFF)
            rec.tape.bybit({"topic": "allLiquidation.ETHUSDT", "data": "oops"}, T_US + 1, OFF)
            with mock.patch.object(rr, "free_gb", return_value=9.0):
                rec.flush()
            day = rr.utc_day(T_US)
            self.assertEqual(rr.compact(now=T_US / 1e6 + 86_400, parts=out / "_parts", out=out),
                             [("liq", "BTCUSDT", day, 1)])
            self.assertEqual(list(rr.load("liq", "BTCUSDT", day, out).sd), [1])
            self.assertEqual(len((out / "liq_raw.jsonl").read_text().splitlines()), 1)
            self.assertIn('"liq_raw": 1', (out / "status.json").read_text())

    def test_clock_and_rtt_frames(self):
        df = rr.frame("rtt", [(T_US, 0, 204_000), (T_US + 30_000_000, 2, 254_000)])
        self.assertEqual(list(df.columns), ["t", "c", "us"])
        self.assertEqual(rr.RTT_CONN, {"binance_public": 0, "binance_market": 1, "bybit": 2, "bybit_spot": 3,
                                       "kraken": 4})
        self.assertEqual(len(rr.frame("clock", [(T_US, 123)])), 1)


class SslTests(unittest.TestCase):
    def test_an_unreadable_ca_bundle_falls_back_to_the_default_context(self):
        with mock.patch.object(rr.Path, "exists", side_effect=PermissionError(13, "Permission denied")):
            self.assertIsNotNone(rr.ssl_context())


class CapTests(unittest.TestCase):
    def test_free_space_floor_and_size_cap(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            with mock.patch.object(rr, "free_gb", return_value=9.0):
                self.assertEqual(rr.full(out), "")
                with mock.patch.object(rr, "used_gb", return_value=rr.MAX_GB):
                    self.assertIn("cap", rr.full(out))
            with mock.patch.object(rr, "free_gb", return_value=rr.MIN_FREE_GB - 0.1):
                self.assertIn("free", rr.full(out))

    def test_a_full_disk_stops_the_recorder_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "_parts").mkdir()
            try:
                import asyncio
                rec = rr.Recorder(out=out, hours=None)
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
                rec = rr.Recorder(out=out, hours=None)
            rec.tape.binance(book(), T_US, OFF)
            with mock.patch.object(rr, "free_gb", return_value=0.5):
                rec.flush()
            self.assertTrue(rec.stop.is_set())
            self.assertIn("not written", rec.why_stopped)
            self.assertFalse(list((out / "_parts").rglob("*.parquet")))
            self.assertIn("trades_with_rpi", (out / "status.json").read_text())


if __name__ == "__main__":
    unittest.main()
