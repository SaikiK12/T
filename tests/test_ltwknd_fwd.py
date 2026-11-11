"""scripts/run_ltwknd_fwd.py (R467): R465's Lighter weekend fade forward, offline: stub venue, fake clock."""
import importlib.util
import math
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("run_ltwknd_fwd", ROOT / "scripts" / "run_ltwknd_fwd.py")
fw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw)
MIN, H = fw.MIN, fw.H
UTC = lambda s: int(pd.Timestamp(s, tz="UTC").value // 10**6)  # noqa: E731
W1 = fw.rule.weekend(date(2026, 11, 13))
UNI = [{"coin": f"S{i}", "market_id": str(100 + i), "etf": "0", "ipo_424b4": ""} for i in range(4)]
COIN = {100 + i: f"S{i}" for i in range(4)}


class Clock:
    def __init__(self, t):
        self.t = int(t)

    def __call__(self):
        return self.t

    def sleep(self, sec):
        self.t += int(sec * 1000)


def paths(w):
    """S0 rises 1% over the weekend and gives half back by X1; S1 moves 10 bp; S2 lists 3 days before R; S3 falls
    2% and does not move after E."""
    def s0(t):
        return 100.0 if t < w["R"] + 5 * H else (101.0 if t < w["E"] + 30 * MIN else 100.5)

    def s3(t):
        return 50.0 if t < w["R"] + 5 * H else 49.0
    return {"S0": s0, "S1": lambda t: 20.0 if t < w["R"] + 5 * H else 20.02,
            "S2": lambda t: 10.0 if t < w["R"] else 11.0, "S3": s3}


class Venue:
    """Hourly candles (only those opened by now; the open one closes at now), hourly funding, a deep two-sided book
    2 bp either side of mid, and listed fees. S0's candle opening at E - 1 h did not trade (volume 0, a wild close)."""

    def __init__(self, clock, w, rate=1e-5, listed=None, fee="0.0000"):
        self.clock, self.w, self.p, self.rate, self.fee = clock, w, paths(w), rate, fee
        self.listed = listed or {"S2": w["R"] - 3 * 86_400_000}

    def candles(self, mid, start, end):
        coin = COIN[mid]
        t0 = max(start - start % H, self.listed.get(coin, 0))
        t0 -= t0 % H
        t = np.arange(t0, min(end, self.clock()) + 1, H, dtype=np.int64)
        c = [self.p[coin](min(x + H - 1, self.clock())) for x in t]
        v = [0.0 if (coin == "S0" and x == self.w["E"] - H) else 1.0 for x in t]
        c = [999.0 if vv == 0 else cc for cc, vv in zip(c, v)]
        return pd.DataFrame({"t": t, "close": c, "volume": v})

    def funding(self, mid, start, end):
        t = np.arange(start - start % H + H, end + 1, H, dtype=np.int64)
        return pd.DataFrame({"t": t, "rate": self.rate})

    def book(self, mid):
        m = self.p[COIN[mid]](self.clock())
        lv = lambda px: [{"price": str(px), "remaining_base_amount": "1000"}]  # noqa: E731
        return {"bids": lv(m * (1 - 2e-4)), "asks": lv(m * (1 + 2e-4))}

    def fees(self):
        return {mid: fw.fee_bp(self.fee) for mid in COIN}


def write_snapshots(d, w, coins=("S0", "S1", "S2"), cost=3.0, last=None):
    rows = []
    for coin in coins:
        for t in (w["E"] + 7 * MIN, w["X1"] + 10 * MIN, last or w["X1"] + 100 * MIN):
            rows.append({"ts": t, "market_id": 0, "symbol": coin, "bid": 99.9, "ask": 100.1, "half_spread_bp": 10.0,
                         "buy_1k_bp": cost, "sell_1k_bp": cost, "buy_10k_bp": 5.0, "sell_10k_bp": 5.0})
    b = pd.DataFrame(rows)
    (Path(d) / "lighter" / "books").mkdir(parents=True, exist_ok=True)
    for day, g in b.groupby(b.ts.map(fw.utc_day)):
        g.to_csv(Path(d) / "lighter" / "books" / f"{day}.csv", index=False)


class Pure(unittest.TestCase):
    def test_fee_is_a_percent(self):
        self.assertEqual(fw.fee_bp("0.0000"), 0.0)
        self.assertAlmostEqual(fw.fee_bp("0.0200"), 2.0)
        self.assertEqual(fw.fee_bp(""), 0.0)
        self.assertEqual(fw.fee_bp(None), 0.0)

    def test_book_walk_is_the_recorders(self):
        bk = {"bids": [{"price": "99", "remaining_base_amount": "5"}],
              "asks": [{"price": "101", "remaining_base_amount": "5"},
                       {"price": "102", "remaining_base_amount": "100"}]}
        bid, ask, mid, c = fw.book_fill(bk, "buy")
        self.assertEqual((bid, ask, mid), (99.0, 101.0, 100.0))
        rec = fw.lc.book_row(0, {"market_id": 1, "symbol": "X"}, bk)
        self.assertAlmostEqual(c[1000], rec["buy_1k_bp"], places=3)
        self.assertAlmostEqual(c[10000], rec["buy_10k_bp"], places=3)
        # $1k: $505 at 101 and $495 at 102, i.e. 5 + 4.8529... base; average price over mid
        self.assertAlmostEqual(c[1000], (1000 / (5 + 495 / 102) / 100 - 1) * 1e4, places=3)
        self.assertIsNone(fw.book_fill(bk, "sell")[3][1000])          # $495 of bids only
        self.assertIsNone(fw.book_fill({"bids": [], "asks": []}, "buy"))

    def test_prices_skip_untraded_candles(self):
        k = pd.DataFrame({"t": [0, H, 2 * H], "close": [1.0, 2.0, 3.0], "volume": [1.0, 0.0, 1.0]})
        listed, t, c = fw.prices(k)
        self.assertEqual(listed, 0)
        self.assertEqual(list(t), [0, 2 * H])
        self.assertEqual(fw.prices(pd.DataFrame(columns=["t", "close", "volume"]))[0], None)

    def test_weekend_of_and_due(self):
        self.assertEqual(fw.weekend_of(UTC("2026-11-15 23:30"))["friday"], date(2026, 11, 13))
        self.assertEqual(fw.weekend_of(UTC("2026-11-16 02:00"))["friday"], date(2026, 11, 13))
        self.assertIsNone(fw.weekend_of(UTC("2026-11-30 00:00")))      # Friday 11-27 closes early
        self.assertEqual(W1["E"], UTC("2026-11-16 00:00"))              # Sunday 19:00 EST
        self.assertEqual(W1["X1"], UTC("2026-11-16 03:00"))
        self.assertEqual(fw.due_weekends(W1["X1"] + 3 * H - 1), [])
        self.assertEqual([w["F"] for w in fw.due_weekends(W1["X1"] + 3 * H)], ["2026-11-13"])

    def test_nearest_snapshot_and_fallback(self):
        b = pd.DataFrame({"symbol": ["a", "a"], "ts": [0, 100 * MIN], "buy_1k_bp": [1.0, np.nan]})
        self.assertEqual(fw.nearest(b, "a", 40 * MIN, "buy_1k_bp"), 1.0)
        self.assertIsNone(fw.nearest(b, "a", 95 * MIN, "buy_1k_bp"))       # nearest is blank
        self.assertIsNone(fw.nearest(b, "a", -91 * MIN, "buy_1k_bp"))      # too far
        self.assertIsNone(fw.nearest(b, "b", 0, "buy_1k_bp"))


class TickAndScore(unittest.TestCase):
    def test_tickets_then_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            j, snaps = Path(tmp) / "journal", Path(tmp) / "snaps"
            clock = Clock(W1["E"] - 50 * MIN)
            v = Venue(clock, W1)
            run = lambda: fw.tick(venue=v, now=clock, sleep=clock.sleep, journal=j, universe=UNI)  # noqa: E731
            self.assertEqual(fw.tick(venue=v, now=Clock(W1["E"] - 80 * MIN), sleep=clock.sleep, journal=j,
                                     universe=UNI), "entry not due")
            self.assertEqual(run(), "entry")
            tk = pd.read_csv(j / "tickets.csv")
            st = dict(zip(tk.coin, tk.status))
            self.assertEqual(st, {"S0": "ok", "S1": "no_trade", "S2": "not_listed", "S3": "ok"})
            s0 = tk[tk.coin == "S0"].iloc[0]
            self.assertEqual(int(s0.side), -1)
            self.assertGreaterEqual(int(s0.tick_ts), W1["E"])
            self.assertAlmostEqual(s0.w_bp, 1e4 * math.log(1.01))       # the untraded 999 candle is skipped
            self.assertAlmostEqual(s0.cost_bp, 2.0, places=2)
            self.assertEqual(s0.fee_bp, 0.0)
            self.assertEqual(run(), "exit not due")
            clock.t = W1["X1"] - 30 * MIN
            self.assertEqual(run(), "exit")
            self.assertEqual(run(), "done")
            tk = pd.read_csv(j / "tickets.csv")
            self.assertEqual(len(tk[tk.phase == "exit"]), 2)
            # score: the recorder has not passed X1 + 90 min yet, then it has
            write_snapshots(snaps, W1, last=W1["X1"] + 60 * MIN)
            st = fw.score(snaps, now_ms=W1["X1"] + 3 * H, venue=v, journal=j, universe=UNI)
            self.assertFalse((j / "a_trades.csv").exists())
            self.assertEqual(st["traded_weekends"], 0)
            write_snapshots(snaps, W1)
            st = fw.score(snaps, now_ms=W1["X1"] + 3 * H, venue=v, journal=j, universe=UNI)
            a = pd.read_csv(j / "a_trades.csv").set_index("coin")
            self.assertEqual(a.status.to_dict(), {"S0": "ok", "S1": "no_trade", "S2": "not_listed", "S3": "ok"})
            r = a.loc["S0"]
            self.assertAlmostEqual(r.w_bp, 1e4 * math.log(1.01))
            self.assertAlmostEqual(r.price_bp, -1e4 * math.log(100.5 / 101))
            self.assertAlmostEqual(r.funding_bp, 0.3)                     # a short receives 3 hourly 1e-5
            self.assertEqual(r.fee_bp, 0.0)
            self.assertAlmostEqual(r.book_bp, 6.0)
            self.assertAlmostEqual(r.net_1x, r.gross_bp - 6.0)
            self.assertAlmostEqual(r.net_3x, r.gross_bp - 18.0)
            self.assertAlmostEqual(r.book10k_bp, 10.0)
            self.assertEqual(int(a.loc["S3"].fallback_fills), 2)          # no S3 snapshot: 10 bp a fill
            self.assertAlmostEqual(a.loc["S3"].book_bp, 20.0)
            self.assertEqual(int(a.loc["S3"].side), 1)
            b = pd.read_csv(j / "b_trades.csv").set_index("coin")
            rb = b.loc["S0"]
            self.assertEqual(rb.exit_src, "tick")
            self.assertAlmostEqual(rb.price_bp, -1e4 * math.log(100.5 / 101), places=6)
            self.assertAlmostEqual(rb.book_bp, 4.0, places=2)
            self.assertEqual(rb.a_status, "ok")
            self.assertEqual(st["traded_weekends"], 1)
            self.assertEqual(st["b_weekends"], 1)
            self.assertEqual(st["a_fallback_fills"], 2)
            self.assertIn("pending", st["decision"])
            # a second run adds nothing (append-only, scored once)
            fw.score(snaps, now_ms=W1["X1"] + 5 * H, venue=v, journal=j, universe=UNI)
            self.assertEqual(len(pd.read_csv(j / "a_trades.csv")), 4)
            self.assertEqual(len(pd.read_csv(j / "b_trades.csv")), 2)

    def test_a_listed_fee_is_charged(self):
        with tempfile.TemporaryDirectory() as tmp:
            j, snaps = Path(tmp) / "journal", Path(tmp) / "snaps"
            write_snapshots(snaps, W1)
            clock = Clock(W1["X1"] + 3 * H)
            fw.score(snaps, now_ms=clock(), venue=Venue(clock, W1, fee="0.0200"), journal=j, universe=UNI)
            r = pd.read_csv(j / "a_trades.csv").set_index("coin").loc["S0"]
            self.assertAlmostEqual(r.fee_bp, 4.0)
            self.assertAlmostEqual(r.net_1x, r.gross_bp - 10.0)

    def test_missed_entry_and_recorder_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            j, snaps = Path(tmp) / "journal", Path(tmp) / "snaps"
            clock = Clock(W1["E"] + 40 * MIN)
            v = Venue(clock, W1)
            self.assertEqual(fw.tick(venue=v, now=clock, sleep=clock.sleep, journal=j, universe=UNI), "entry missed")
            clock.t = W1["E"] - MIN
            fw.tick(venue=v, now=clock, sleep=clock.sleep, journal=j, universe=UNI)
            write_snapshots(snaps, W1)                                    # no exit ticket: priced from the recorder
            fw.score(snaps, now_ms=W1["X1"] + 3 * H, venue=v, journal=j, universe=UNI)
            b = pd.read_csv(j / "b_trades.csv").set_index("coin")
            self.assertEqual(b.loc["S0"].exit_src, "recorder")
            self.assertEqual(int(b.loc["S0"].exit_ts), W1["X1"] + 10 * MIN)
            self.assertAlmostEqual(b.loc["S0"].exit_cost_bp, 3.0)
            self.assertEqual(b.loc["S3"].status, "unpriced")               # S3 has no snapshot

    def test_entry_retried_after_a_total_outage(self):
        class Down(Venue):
            def candles(self, mid, start, end):
                raise RuntimeError("down")
        with tempfile.TemporaryDirectory() as tmp:
            j = Path(tmp) / "journal"
            clock = Clock(W1["E"] - MIN)
            fw.tick(venue=Down(clock, W1), now=clock, sleep=clock.sleep, journal=j, universe=UNI)
            self.assertEqual(set(pd.read_csv(j / "tickets.csv").status), {"fetch_failed"})
            self.assertEqual(fw.tick(venue=Venue(clock, W1), now=clock, sleep=clock.sleep, journal=j, universe=UNI),
                             "entry")
            self.assertEqual(fw.tick(venue=Venue(clock, W1), now=clock, sleep=clock.sleep, journal=j, universe=UNI),
                             "exit not due")

    def test_fetch_failure_retries_the_weekend_then_stalls(self):
        class Down(Venue):
            def funding(self, mid, start, end):
                if COIN[mid] == "S1":
                    raise RuntimeError("down")
                return super().funding(mid, start, end)
        with tempfile.TemporaryDirectory() as tmp:
            j, snaps = Path(tmp) / "journal", Path(tmp) / "snaps"
            write_snapshots(snaps, W1)
            clock = Clock(W1["X1"] + 3 * H)
            fw.score(snaps, now_ms=clock(), venue=Down(clock, W1), journal=j, universe=UNI)
            self.assertFalse((j / "a_trades.csv").exists())
            clock.t = W1["X1"] + fw.STALL_MS + H
            fw.score(snaps, now_ms=clock(), venue=Down(clock, W1), journal=j, universe=UNI)
            a = pd.read_csv(j / "a_trades.csv").set_index("coin")
            self.assertEqual(a.loc["S1"].status, "venue_error")
            self.assertEqual(a.loc["S0"].status, "ok")


def frames(a_vals, b_vals):
    """A and B journals with one ok trade a weekend, from per-weekend nets at 1x (2x = 1x - 5)."""
    fr = [str(pd.Timestamp("2026-11-13") + pd.Timedelta(weeks=i))[:10] for i in range(len(a_vals))]
    a = pd.DataFrame({"friday": fr, "coin": "S0", "status": "ok", "net_1x": a_vals,
                      "net_2x": np.asarray(a_vals) - 5, "net_3x": np.asarray(a_vals) - 10})
    b = pd.DataFrame({"friday": fr[:len(b_vals)], "coin": "S0", "status": "ok", "net_1x": b_vals,
                      "net_2x": np.asarray(b_vals) - 5, "net_3x": np.asarray(b_vals) - 10})
    return a, b


class Decision(unittest.TestCase):
    def test_futility(self):
        a, b = frames([-10.0] * 15, [])
        self.assertIn("NULL (futility", fw.decision(a, b)["decision"])

    def test_pending_then_pass_at_interim(self):
        rng = np.random.default_rng(0)
        good = list(40 + rng.normal(0, 30, 20))
        a, b = frames(good[:14], good[:14])
        self.assertIn("pending", fw.decision(a, b)["decision"])
        a, b = frames(good, good)
        self.assertIn("PASS at 20", fw.decision(a, b)["decision"])

    def test_tickets_decide_with_a(self):
        rng = np.random.default_rng(1)
        good = list(40 + rng.normal(0, 30, 30))
        a, b = frames(good, good[:10])                        # tickets cover 10 of 20, then 10 of 30
        self.assertIn("pending", fw.decision(*frames(good[:25], good[:10]))["decision"])
        self.assertIn("PARTIAL at 30", fw.decision(a, b)["decision"])
        a, b = frames(good, [-5.0] * 30)
        self.assertIn("ticketed fills lose", fw.decision(a, b)["decision"])
        a, b = frames(list(rng.normal(0, 30, 30)), good)
        d = fw.decision(a, b)["decision"]
        self.assertTrue(d.startswith("NULL"), d)


class Frozen(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "ltwknd_fwd" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        text = re.sub(r"\s+", " ", p.read_text())
        for phrase in ("2026-11-13", "50 bp", "Sunday 19:00", "Sunday 22:00", "Friday 20:00", "$1k", "90 minutes",
                       "10 bp", "3 hours", "48 hours", "70 minutes", "30 minutes", "6 hours", "7 days",
                       "15 traded weekends", "20 traded weekends", "30 traded weekends", "p < 0.01", "p < 0.04",
                       "best 3", "seed 467", "two thirds", "Trials:** 1", "R465", "100 orders", "volume > 0"):
            self.assertIn(phrase, text, phrase)
        self.assertEqual((fw.THETA_BP, fw.FUTILITY_N, fw.INTERIM_N, fw.FINAL_N, fw.SEED, fw.TOP_K, fw.SIZE_USD),
                         (50.0, 15, 20, 30, 467, 3, 1000))
        self.assertEqual((fw.ALPHA_INTERIM, fw.ALPHA_FINAL, fw.FALLBACK_BP, fw.DEPTH), (0.01, 0.04, 10.0, 100))


if __name__ == "__main__":
    unittest.main()
