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

    def test_largest_gap_between_messages_is_kept_per_stream(self):
        t = rr.Tape()
        for dt in (0, 5_000, 1_205_000):
            t.binance(book(u=int(dt) + 1), T_US + dt, OFF)
        self.assertEqual(t.stat["max_gap_ms"][("bbo", "BTCUSDC")], 1200)


class WindowTests(unittest.TestCase):
    def test_hours_window(self):
        at = lambda h: (T_MS // 1000 - 20 * 3600 + h * 3600) * 10**9
        self.assertTrue(rr.in_window(at(13), (13, 17)) and rr.in_window(at(16), (13, 17)))
        self.assertFalse(rr.in_window(at(17), (13, 17)) or rr.in_window(at(12), (13, 17)))
        self.assertTrue(rr.in_window(at(23), (22, 2)) and rr.in_window(at(1), (22, 2)))
        self.assertFalse(rr.in_window(at(5), (22, 2)))
        self.assertTrue(rr.in_window(at(5), None))
        self.assertEqual(rr.parse_hours("13-17"), (13, 17))


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

    def test_clock_and_rtt_frames(self):
        df = rr.frame("rtt", [(T_US, 0, 204_000), (T_US + 30_000_000, 2, 254_000)])
        self.assertEqual(list(df.columns), ["t", "c", "us"])
        self.assertEqual(rr.RTT_CONN, {"binance_public": 0, "binance_market": 1, "bybit": 2})
        self.assertEqual(len(rr.frame("clock", [(T_US, 123)])), 1)


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
