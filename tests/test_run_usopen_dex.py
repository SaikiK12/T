"""scripts/run_usopen_dex.py (R457): R371's picks on Lighter and Hyperliquid, offline, with stub venues."""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_usopen_dex", ROOT / "scripts" / "run_usopen_dex.py")
ud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ud)
MIN, H, DAY = ud.MIN, ud.H, ud.DAY
DAY0 = ud.FWD_START                                  # 2026-11-12, a Thursday (EST: D = 15:00 UTC)
D = DAY0 + 15 * H
ENTRY, EXIT = D + 3 * MIN, DAY0 + DAY + 3 * MIN
SYMS = [f"C{i:02d}USDT" for i in range(50)]


def signals(ticket="U20261112"):
    sig = np.linspace(-0.2, 0.2, 50)
    return pd.DataFrame({"ticket": ticket, "symbol": SYMS, "rank": np.arange(1, 51), "sig": sig,
                         "c_s": 10.0 / (1 + sig), "c_e": 10.0, "vol": 1e9})


class Venue:
    """Minute bars at 10.0 before D; each coin's price moves to 10 * (1 + move) by the exit."""

    def __init__(self, listed=40, move=None, odd=(), no_exit=(), fail=False, rate=1e-5):
        self.listed = {s[:-4] for s in SYMS[:listed]}
        self.move = move or {}
        self.odd, self.no_exit, self.fail, self.rate = set(odd), set(no_exit), fail, rate

    def names(self):
        return set(self.listed)

    def minutes(self, sym, start, end):
        if self.fail:
            raise RuntimeError("down")
        t = np.arange(start, end + 1, MIN)
        before = 15.0 if sym in self.odd else 10.0
        after = 10.0 * (1 + self.move.get(sym, 0.0))
        if start >= EXIT - MIN and sym in self.no_exit:
            return pd.DataFrame(columns=["t", "open", "close"])
        px = np.where(t < D, before, np.where(t >= EXIT - MIN, after, 10.0))
        return pd.DataFrame({"t": t, "open": px, "close": px})

    def funding(self, sym, start, end):
        t = np.arange(start - start % H, end, H)
        return pd.DataFrame({"t": t, "rate": self.rate})


def books(coin_col, k1, bp, coins):
    rows = [{"ts": t, coin_col: c, f"buy_{k1}_bp": bp, f"sell_{k1}_bp": bp}
            for t in (ENTRY - 20 * MIN, EXIT + 40 * MIN) for c in coins]
    return pd.DataFrame(rows)


class Pure(unittest.TestCase):
    def test_symbols(self):
        self.assertEqual(ud.venue_symbol("L", "1000PEPEUSDT", {"1000PEPE"}), "1000PEPE")
        self.assertEqual(ud.venue_symbol("L", "PEPEUSDT", {"1000PEPE"}), "1000PEPE")
        self.assertEqual(ud.venue_symbol("L", "1000SATSUSDT", {"SATS"}), "SATS")
        self.assertEqual(ud.venue_symbol("H", "1000PEPEUSDT", {"kPEPE"}), "kPEPE")
        self.assertEqual(ud.venue_symbol("H", "BTCUSDT", {"BTC"}), "BTC")
        self.assertIsNone(ud.venue_symbol("H", "BTCUSDC", {"BTC"}))
        self.assertIsNone(ud.venue_symbol("L", "XYZUSDT", {"BTC"}))
        self.assertEqual(ud.venue_symbol("L", "CLUSDT", {"WTI"}), "WTI")
        self.assertEqual(ud.venue_symbol("H", "XAUUSDT", {"BTC", "xyz:GOLD"}), "xyz:GOLD")   # R451's alias
        self.assertEqual(ud.venue_symbol("H", "TSLAUSDT", {"xyz:TSLA"}), "xyz:TSLA")
        self.assertIsNone(ud.venue_symbol("L", "TSLAUSDT", {"xyz:TSLA"}))
        fees = {"xyz:TSLA": [("2026-11-11", 4.5e-5)]}
        self.assertEqual(ud.fee_of("L", "BTC", fees, "2026-11-12"), 0.0)
        self.assertEqual(ud.fee_of("H", "BTC", fees, "2026-11-12"), 4.5e-4)
        self.assertEqual(ud.fee_of("H", "xyz:TSLA", fees, "2026-11-12"), 4.5e-5)
        self.assertEqual(ud.fee_of("H", "xyz:NVDA", fees, "2026-11-12"), 9e-4)        # none listed: 9 bp

    def test_minutes_funding_and_costs(self):
        bars = pd.DataFrame({"t": [D - 61 * MIN, D - MIN, D + 3 * MIN, D + 9 * MIN], "open": [1, 2, 3, 4],
                             "close": [1, 2, 3, 4]}).astype(float)
        bars["t"] = bars.t.astype(np.int64)
        self.assertEqual(ud.close_before(bars, D), 2.0)
        self.assertEqual(ud.fill_open(bars, D + 3 * MIN), 3.0)
        self.assertIsNone(ud.fill_open(bars, D + 3 * MIN + 1))      # the next bar is more than 5 minutes later
        f = pd.DataFrame({"t": [D, D + H + 32, EXIT - 3 * MIN, EXIT - 3 * MIN + H], "rate": [1.0, 2.0, 4.0, 8.0]})
        self.assertEqual(ud.funding_sum(f, ENTRY, EXIT), 6.0)        # 16:00 .. 00:00, not D and not 01:00
        bk = pd.DataFrame({"ts": [ENTRY - 80 * MIN, ENTRY + 100 * MIN], "symbol": "A", "buy_1k_bp": [2.0, 9.0],
                           "sell_1k_bp": [np.nan, 1.0]})
        self.assertAlmostEqual(ud.fill_cost(bk, "symbol", "A", ENTRY, "buy_1k_bp"), 2e-4)
        self.assertIsNone(ud.fill_cost(bk, "symbol", "A", ENTRY, "sell_1k_bp"))   # thin book
        self.assertIsNone(ud.fill_cost(bk, "symbol", "A", ENTRY - 3 * H, "buy_1k_bp"))
        hk = bk.rename(columns={"symbol": "coin", "buy_1k_bp": "buy_1000_bp", "sell_1k_bp": "sell_1000_bp"})
        ci, co, ci10, co10, fb = ud.leg_costs("H", hk, "A", "short", ENTRY, ENTRY, 4.5e-4)
        self.assertAlmostEqual(ci, 4.5e-4 + 1e-3)                    # short sells in: blank cell, 10 bp fallback
        self.assertAlmostEqual(co, 4.5e-4 + 2e-4)
        self.assertEqual(fb, 1)
        self.assertAlmostEqual(ci10, 4.5e-4 + 1e-3)                  # no $10k column: fallback, not counted


class Day(unittest.TestCase):
    def tk(self):
        return {"ticket": "U20261112", "day_ms": DAY0, "d_ms": D}

    def test_picks_prices_funding_and_cost(self):
        move = {"C39": 0.02, "C38": 0.01, "C37": 0.0, "C00": -0.03, "C01": 0.0, "C02": 0.0}
        v = Venue(listed=40, move=move, odd={"C39"})               # C39 trades 50% away from Binance: not the asset
        bk = books("symbol", "1k", 2.0, [s[:-4] for s in SYMS])
        row, legs = ud.score_day("L", self.tk(), signals(), v, v.names(), bk)
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["eligible"], 39)
        self.assertEqual(row["longs"], "C38USDT|C37USDT|C36USDT")   # strongest listed first; C40+ unlisted, C39 odd
        self.assertEqual(row["shorts"], "C00USDT|C01USDT|C02USDT")
        self.assertAlmostEqual(row["price"], (0.01 + 0 + 0) / 3 - (-0.03) / 3)
        self.assertAlmostEqual(row["funding"], 0.0)                 # equal rates: shorts receive what longs pay
        self.assertAlmostEqual(row["cost_1x"], 2 * (2e-4 + 2e-4))   # Lighter: no fee, 2 bp a fill, a side each
        self.assertAlmostEqual(row["net_2x"], row["gross"] - 2 * row["cost_1x"])
        self.assertAlmostEqual(row["cost_10k"], 2 * 2 * 1e-3)       # no $10k column in the stub: 10 bp a fill
        self.assertEqual(row["fallback_fills"], 0)
        self.assertEqual(len(legs), 6)
        h, _ = ud.score_day("H", self.tk(), signals(), v, v.names(), books("coin", "1000", 2.0, []))
        self.assertAlmostEqual(h["cost_1x"], 2 * 2 * (4.5e-4 + 1e-3))   # no snapshot: fee + fallback
        self.assertEqual(h["fallback_fills"], 12)

    def test_no_book_and_unpriced(self):
        v = Venue(listed=29)
        self.assertEqual(ud.score_day("L", self.tk(), signals(), v, v.names(), None)[0]["status"], "no_book")
        v = Venue(listed=40, no_exit={"C00"})
        self.assertEqual(ud.score_day("L", self.tk(), signals(), v, v.names(), None)[0]["status"], "unpriced")


class Forward(unittest.TestCase):
    def test_journal_once_retry_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            par, j = Path(d) / "parent", Path(d) / "j"
            par.mkdir()
            pd.DataFrame([{"ticket": "U20261111", "day_ms": DAY0 - DAY, "d_ms": D - DAY, "status": "ok"},
                          {"ticket": "U20261112", "day_ms": DAY0, "d_ms": D, "status": "ok"},
                          {"ticket": "U20261113", "day_ms": DAY0 + DAY, "d_ms": D + DAY, "status": "missed"}]
                         ).to_csv(par / "tickets.csv", index=False)
            pd.concat([signals("U20261111"), signals()]).to_csv(par / "signals.csv", index=False)
            now = EXIT + 3 * H + MIN
            with mock.patch.object(ud, "PARENT", par), mock.patch.object(ud, "J", j):
                ud.forward(d, now_ms=EXIT + 2 * H, venues={"L": Venue(), "H": Venue()})
                self.assertFalse((j / "scored.csv").exists())           # not yet 3 h after the exit
                ud.forward(d, now_ms=now, venues={"L": Venue(), "H": Venue(fail=True)})
                df = pd.read_csv(j / "scored.csv")
                self.assertEqual(list(df.book), ["L"])                  # before FWD_START and missed: none; H retried
                st = ud.forward(d, now_ms=now, venues={"L": Venue(), "H": Venue()})
                df = pd.read_csv(j / "scored.csv")
                self.assertEqual(sorted(df.book), ["H", "L"])           # L not scored twice
                self.assertEqual(len(pd.read_csv(j / "legs.csv")), 12)
                self.assertTrue(st["L"]["decision"].startswith("pending (1 of 500"))
                self.assertTrue(st["H"]["decision"].startswith("reported only"))


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "usopen_dex_fwd" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in ("2026-11-12", "within 10%", "D + 3 minutes", "within 5 minutes", "90 minutes", "4.5 bp",
                       "Standard account", "$1k market order", "10 bp", "3 hours", "d3cfa47e", "dba0257e",
                       "Trials:** 2", "book L decides"):
            self.assertIn(phrase, text, phrase)


if __name__ == "__main__":
    unittest.main()
