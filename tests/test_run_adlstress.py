"""Tests for scripts/run_adlstress.py (R487) on synthetic candles: no network, no lane data."""
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("run_adlstress", ROOT / "scripts" / "run_adlstress.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

DAY = ra.DAY
T0 = ra.ms(ra.D)
ENTRY = "2025-09-01"
TE = ra.ms(ENTRY)


def daily(rows):
    """rows: [(date, o, h, l, c)] -> candle dict with UTC-aligned daily bars."""
    return {"d": ra._frame([(ra.ms(d), o, h, l, c) for d, o, h, l, c in rows]), "h": ra._frame([])}


def leg(entry_close, o, h, l, c, close_0909=None):
    """A venue's candles: the bar before ENTRY closes at entry_close; D's bar is (o, h, l, c)."""
    return daily([("2025-08-31", 1, 1, 1, entry_close), ("2025-10-09", 1, 1, 1, close_0909 or o),
                  (ra.D, o, h, l, c)])


PAIR = {"coin": "XUSDT", "long": "gate", "short": "hyperliquid", "entry_day": ENTRY, "exit_day": "2025-11-01"}


class Bound(unittest.TestCase):
    def test_naked_long_when_short_profits_on_adl_venue(self):
        # price fell on the short venue: the short profits; hyperliquid ADLs it; gate's long is naked
        c = {("gate", "XUSDT"): leg(2.0, 10, 12, 6, 7), ("hyperliquid", "XUSDT"): leg(2.0, 10, 12, 6, 7)}
        r = ra.pair_stress(PAIR, c, {"hyperliquid"}, 0.0)
        self.assertTrue(r["stressed"])
        self.assertEqual(r["naked"], "long")
        self.assertAlmostEqual(r["r"], (12 - 6) / 12)
        self.assertAlmostEqual(r["N"], 12 / 2.0)
        self.assertAlmostEqual(r["r"] * r["N"], (12 - 6) / 2.0)       # q x (H - L), q = 1 / P_e
        self.assertEqual(r["candle_fill"], "")
        self.assertEqual(r["notional_fill"], "")

    def test_naked_short_when_long_profits_on_adl_venue(self):
        p = dict(PAIR, long="hyperliquid", short="gate")
        c = {("gate", "XUSDT"): leg(4.0, 10, 15, 8, 14), ("hyperliquid", "XUSDT"): leg(4.0, 10, 15, 8, 14)}
        r = ra.pair_stress(p, c, {"hyperliquid"}, 0.0)
        self.assertEqual(r["profitable"], "long")
        self.assertEqual(r["naked"], "short")
        self.assertAlmostEqual(r["r"], (15 - 8) / 8)
        self.assertAlmostEqual(r["r"] * r["N"], (15 - 8) / 4.0)

    def test_profitable_leg_off_the_adl_set_gives_zero(self):
        c = {("gate", "XUSDT"): leg(2.0, 10, 12, 6, 7), ("hyperliquid", "XUSDT"): leg(2.0, 10, 12, 6, 7)}
        r = ra.pair_stress(PAIR, c, {"gate"}, 0.0)          # short (hyperliquid) profits, but only gate ADLs
        self.assertFalse(r["stressed"])
        self.assertEqual([r[f"loss_{k}"] for k in (1, 2, 3)], [0.0, 0.0, 0.0])

    def test_cost_scaling(self):
        c = {("gate", "XUSDT"): leg(2.0, 10, 12, 6, 7), ("hyperliquid", "XUSDT"): leg(2.0, 10, 12, 6, 7)}
        r = ra.pair_stress(PAIR, c, {"hyperliquid"}, 0.0)
        base = r["r"] * r["N"]
        for k, cst in ra.COSTS.items():
            self.assertAlmostEqual(r[f"loss_{k}"], base + 2 * cst * r["N"])
        self.assertAlmostEqual(r["loss_3"] - r["loss_2"], r["loss_2"] - r["loss_1"])

    def test_missing_naked_candle_uses_other_venue(self):
        c = {("hyperliquid", "XUSDT"): leg(2.0, 10, 12, 6, 7)}
        r = ra.pair_stress(PAIR, c, {"hyperliquid"}, 0.0)
        self.assertEqual(r["candle_fill"], "other_venue")
        self.assertAlmostEqual(r["r"], 0.5)
        self.assertEqual(r["notional_fill"], "other_close_0909")
        self.assertAlmostEqual(r["N"], 10 / 2.0)

    def test_both_missing_uses_book_max_and_unit_notional(self):
        r = ra.pair_stress(PAIR, {}, {"hyperliquid"}, 0.3)
        self.assertTrue(r["stressed"])
        self.assertEqual(r["candle_fill"], "book_max")
        self.assertEqual(r["notional_fill"], "unit")
        self.assertAlmostEqual(r["loss_1"], 0.3 + 2 * 0.0007)
        self.assertFalse(ra.pair_stress(PAIR, {}, {"binance"}, 0.3)["stressed"])

    def test_book_bound_and_fill_count(self):
        c = {("gate", "XUSDT"): leg(2.0, 10, 12, 6, 7), ("hyperliquid", "XUSDT"): leg(2.0, 10, 12, 6, 7)}
        pairs = [PAIR, dict(PAIR, coin="YUSDT")]
        rows, pct, cnt = ra.book_bound(pairs, c, {"hyperliquid"}, slots=20)
        self.assertEqual(cnt["stressed"], 2)
        self.assertEqual(cnt["candle_fills"], 1)
        self.assertAlmostEqual(cnt["fill_r"], 0.5)
        self.assertAlmostEqual(pct[1], 100 * sum(r["loss_1"] for r in rows) / 40)

    def test_unaligned_daily_falls_back_to_hourly(self):
        hours = [(T0 + i * 3_600_000, 10, 10 + i, 9 - i * 0.1, 9.5) for i in range(24)]
        c = {"d": ra._frame([(T0 + 8 * 3_600_000, 1, 1, 1, 1)]), "h": ra._frame(hours)}
        o = ra.day_ohlc(c)
        self.assertEqual(o[4], "1h")
        self.assertAlmostEqual(o[1], 33)
        self.assertAlmostEqual(o[2], 9 - 2.3)
        self.assertIsNone(ra.day_ohlc({"d": c["d"], "h": ra._frame(hours[:5])}))

    def test_verdicts(self):
        self.assertEqual(ra.book_call(0.99, 12.0), "SURVIVES")
        self.assertEqual(ra.book_call(1.0, 12.0), "EXPOSED")
        self.assertEqual(ra.lane_verdict(["SURVIVES"] * 6), "PASS")
        self.assertEqual(ra.lane_verdict(["SURVIVES"] * 3 + ["EXPOSED"] * 3), "PARTIAL")
        self.assertEqual(ra.lane_verdict(["SURVIVES"] * 2 + ["EXPOSED"] * 4), "NULL")


class Parse(unittest.TestCase):
    def test_venue_bodies(self):
        g = ra.parse("gate", json.dumps([{"t": T0 // 1000, "o": "1", "h": "2", "l": "0.5", "c": "1.5"}]).encode())
        k = ra.parse("kucoin", json.dumps({"code": "200000", "data": [[T0, 1, 2, 0.5, 1.5, 9]]}).encode())
        m = ra.parse("mexc", json.dumps({"success": True, "data": {"time": [T0 // 1000], "open": [1], "high": [2],
                                                                  "low": [0.5], "close": [1.5]}}).encode())
        h = ra.parse("hyperliquid", json.dumps([{"t": T0, "o": "1", "h": "2", "l": "0.5", "c": "1.5"}]).encode())
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("X-1d.csv", f"open_time,open,high,low,close\n{T0},1,2,0.5,1.5,9\n")
        b = ra.parse("binance", buf.getvalue())
        for f in (g, k, m, h, b):
            self.assertEqual(f.t.tolist(), [T0])
            self.assertEqual(f[["o", "h", "l", "c"]].iloc[0].tolist(), [1, 2, 0.5, 1.5])
        self.assertTrue(ra.aligned(g))

    def test_manifest_check_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "gate").mkdir()
            body = json.dumps([{"t": T0 // 1000, "o": "1", "h": "2", "l": "0.5", "c": "1.5"}]).encode()
            (d / "gate" / "XUSDT_1d.json").write_bytes(body)
            man = {"legs": {"gate/XUSDT": {"symbol": "X_USDT", "first_entry": ENTRY}},
                   "requests": [{"file": "gate/XUSDT_1d.json"}, {"file": None}],
                   "files": {"gate/XUSDT_1d.json": hashlib.sha256(body).hexdigest()}}
            (d / "manifest.json").write_text(json.dumps(man))
            got = ra.load_candles(d, ra.verify_raw(d))
            self.assertEqual(ra.day_ohlc(got[("gate", "XUSDT")])[:4], (1.0, 2.0, 0.5, 1.5))
            (d / "gate" / "XUSDT_1d.json").write_bytes(body + b" ")
            with self.assertRaises(ra.InputError):
                ra.verify_raw(d)


if __name__ == "__main__":
    unittest.main()
