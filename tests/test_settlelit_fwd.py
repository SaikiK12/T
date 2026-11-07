import gzip
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab import prereg
from scripts import forward_settlelit as fs
from scripts import settlelit_fwd_rule as rule

H, MIN, SEC = rule.H, rule.MIN, rule.SEC
T0 = 1_793_678_400_000                          # 2026-11-02 04:00 UTC, an invented settlement on a 4 h boundary


def stat(mid, rate_pct, ts, mid_price):
    """A Lighter market_stats row: the last settlement in percent, its stamp a few ms after the hour, the mid."""
    return {"market_id": mid, "funding_rate": f"{rate_pct:.4f}", "funding_timestamp": ts + 3,
            "mid_price": f"{mid_price}", "last_trade_price": f"{mid_price}"}


def lighter_book(mid, half=0.0005, size=50.0):
    b = fs.Book()
    b.snapshot({"bids": [{"price": str(mid * (1 - half)), "size": str(size)},
                         {"price": str(mid * (1 - 3 * half)), "size": str(size)}],
                "asks": [{"price": str(mid * (1 + half)), "size": str(size)},
                         {"price": str(mid * (1 + 3 * half)), "size": str(size)}],
                "nonce": 10}, 1)
    return b


def hop(d=-1, q=10.0, T=T0, sym="AAAUSDT", lighter="AAA", mid=1, e=-0.006, r=-0.006):
    return {"hop": f"{sym}:{T}", "T": T, "symbol": sym, "lighter": lighter, "market_id": mid, "d": d, "e": e, "r": r,
            "q": q, "fee_bp": 0.0}


class TestRule(unittest.TestCase):
    def test_binance_base(self):
        self.assertEqual(rule.binance_base("KAITOUSDT"), "KAITO")
        self.assertEqual(rule.binance_base("1000PEPEUSDT"), "1000PEPE")
        self.assertIsNone(rule.binance_base("BTCUSDT_261225"))          # a dated future
        self.assertIsNone(rule.binance_base("ETHUSDC"))
        self.assertIsNone(rule.binance_base("USDT"))
        self.assertIsNone(rule.binance_base(None))

    def test_eligible_needs_the_cycle_seen_before_t_minus_one_hour(self):
        early = T0 - H - 5 * MIN
        seen = {"AAAUSDT": [T0, early, -0.006, early + 1, 1.0],               # 4 h coin, seen at the window's start
                "BBBUSDT": [T0, T0 - H + 2 * SEC, -0.009, T0 - H + 3, 1.0],    # 1 h coin: T showed after T - 1 h
                "CCCUSDT": [T0, T0 - H - SEC * 59, -0.009, T0 - H, 1.0],       # inside the 60 s margin
                "DDDUSDT": [T0 - H, early, -0.009, early, 1.0],                # settles at T - 1 h
                "EEEUSDT_261225": [T0, early, -0.02, early, 1.0]}              # not a perp
        self.assertEqual([x[0] for x in rule.eligible(T0, seen)], ["AAAUSDT"])
        self.assertEqual(rule.eligible(T0, seen)[0], ("AAAUSDT", -0.006, early + 1, early, 1.0))
        self.assertEqual(rule.eligible(T0 + H, {"AAAUSDT": [T0 + H, early, -0.006, early, 1.0]}), [])   # not 4 h

    def test_lighter_h(self):
        self.assertEqual(rule.lighter_h(stat(1, -0.0364, T0 - H, 1), T0), (T0 - H, -0.000364))
        self.assertEqual(rule.lighter_h(stat(1, 0.0012, T0 - 3 * H, 1), T0)[0], T0 - 3 * H)   # 2 h old: kept
        self.assertIsNone(rule.lighter_h(stat(1, 0.0012, T0 - 4 * H, 1), T0)[0])              # older: none
        self.assertIsNone(rule.lighter_h(stat(1, 0.0012, T0, 1), T0)[0])                     # after T - 1 h
        self.assertIsNone(rule.lighter_h({}, T0)[0])
        self.assertTrue(math.isnan(rule.lighter_h({"funding_timestamp": "x"}, T0)[1]))

    def test_lighter_mid_and_identity(self):
        self.assertEqual(rule.lighter_mid({"mid_price": "2.5", "last_trade_price": "2.4"}), 2.5)
        self.assertEqual(rule.lighter_mid({"mid_price": "0", "last_trade_price": "2.4"}), 2.4)
        self.assertTrue(math.isnan(rule.lighter_mid({})))
        self.assertTrue(rule.same_price(1.04, 1.0))
        self.assertFalse(rule.same_price(1.06, 1.0))
        self.assertFalse(rule.same_price(0.001, 1.0))            # a 1000x prefix on one venue only
        self.assertFalse(rule.same_price(math.nan, 1.0))

    def test_signal_takes_the_side_against_the_lump(self):
        e, d = rule.signal(-0.006, -0.0005)                      # Binance's longs receive: short Lighter
        self.assertAlmostEqual(e, -0.005)
        self.assertEqual(d, -1)
        e, d = rule.signal(0.004, 0.0001)                        # Binance's shorts receive: long Lighter
        self.assertEqual(d, 1)
        self.assertTrue(rule.side(-1, entry=True) is False)      # a short sells into the bids ...
        self.assertTrue(rule.side(-1, entry=False))              # ... and buys back on the asks
        self.assertTrue(rule.side(1, entry=True))
        self.assertFalse(rule.side(1, entry=False))

    def test_walk_never_fills_beyond_the_book(self):
        px, got, used = rule.walk([(100.0, 4.0), (101.0, 10.0)], 6.0)
        self.assertAlmostEqual(got, 6.0)
        self.assertAlmostEqual(px, (400 + 202) / 6)
        self.assertEqual(used, 2)
        px, got, used = rule.walk([(100.0, 4.0)], 6.0)
        self.assertAlmostEqual(got, 4.0)                         # thin: what is shown, no more
        self.assertAlmostEqual(px, 100.0)
        px, got, used = rule.walk([(100.0, math.nan), (101.0, 20.0)], 6.0)
        self.assertAlmostEqual(px, 101.0)
        self.assertTrue(math.isnan(rule.walk([], 1.0)[0]))

    def test_short_accounting(self):
        ent = {"ms": T0 - 10 * SEC, "mid": 100.0, "fill": 99.95}
        ext = {"ms": T0 + 60 * SEC, "mid": 99.0, "fill": 99.05}
        rates = [(T0 - H, -0.002), (T0, -0.001), (T0 + H, -0.003)]
        x = rule.leg(-1, ent, ext, rates, 0.0)
        self.assertAlmostEqual(x["gross_mid"], 0.01)
        self.assertAlmostEqual(x["fund"], -0.001)               # the short pays the negative settlement at T only
        self.assertEqual(x["n_fund"], 1)
        self.assertAlmostEqual(x["book_cost"], 0.001)
        self.assertAlmostEqual(x["net1"], 0.008)
        self.assertAlmostEqual(x["net2"], 0.007)
        self.assertAlmostEqual(x["net3"], 0.006)
        realised = -1 * (ext["fill"] - ent["fill"]) / ent["mid"] + x["fund"]
        self.assertAlmostEqual(x["net1"], realised)              # net1 is the paper position's own result
        y = rule.leg(-1, ent, ext, rates, 2.0)
        self.assertAlmostEqual(y["fee"], 2e-4 * (99.95 + 99.05) / 100)
        self.assertAlmostEqual(y["net2"], x["gross_mid"] + x["fund"] - 2 * (x["book_cost"] + y["fee"]))

    def test_long_accounting(self):
        x = rule.leg(1, {"ms": 0, "mid": 10.0, "fill": 10.01}, {"ms": 5, "mid": 10.2, "fill": 10.19}, [(3, 0.0005)],
                     0.0)
        self.assertAlmostEqual(x["gross_mid"], 0.02)
        self.assertAlmostEqual(x["fund"], -0.0005)               # the long pays a positive settlement
        self.assertAlmostEqual(x["book_cost"], 0.002)
        self.assertAlmostEqual(x["net1"], 0.0175)

    def test_round_trip_cost_gate(self):
        bids, asks = [(99.0, 1.0), (98.0, 10.0)], [(101.0, 1.0), (102.0, 10.0)]
        self.assertAlmostEqual(rule.round_trip(bids, asks, 1.0), 0.02)                    # (101 - 99) / 100
        self.assertAlmostEqual(rule.round_trip(bids[::-1], asks[::-1], 2.0), 0.03)       # any order; walks deeper
        self.assertEqual(rule.round_trip(bids, asks, 20.0), math.inf)                     # cannot hold q
        self.assertEqual(rule.round_trip([], asks, 1.0), math.inf)                        # one-sided
        self.assertAlmostEqual(rule.round_trip([(math.nan, 1.0)] + bids, asks, 1.0), 0.02)
        self.assertTrue(rule.round_trip([(99.95, 50.0)], [(100.05, 50.0)], 10.0) <= rule.MAX_RT)   # 10 bp: kept
        self.assertFalse(rule.round_trip([(99.9, 50.0)], [(100.1, 50.0)], 10.0) <= rule.MAX_RT)

    def test_theta_book(self):
        self.assertEqual(rule.theta_book(-0.005), 0.5)
        self.assertEqual(rule.theta_book(0.0049), 0.3)

    def test_bounds_are_obrien_fleming_shaped(self):
        self.assertAlmostEqual(rule.T_LOOK1, round(math.sqrt(2) * rule.T_FINAL, 2))
        self.assertEqual(rule.PRIMARY, (rule.ENTRIES[1], rule.EXITS[0]))
        self.assertEqual(len(rule.VARIANTS), 6)


def rows(nets, net2=None, T=None):
    return [{"hop": f"h{k}", "net1": v, "net2": (net2 if net2 is not None else v - 0.0004), "T": T or k,
             "entry_ms": k, "on_time": True, "e": -0.004, "symbol": f"C{k % 7}"} for k, v in enumerate(nets)]


class TestVerdict(unittest.TestCase):
    def test_pending_and_futility(self):
        self.assertEqual(rule.verdict(rows([0.001] * 10), 0)[0], "PENDING")
        state, text = rule.verdict(rows([0.001] * 10 + [-0.002] * 10), 0)
        self.assertEqual(state, "NULL")
        self.assertIn("futility at 20", text)

    def test_interim_pass_needs_t_and_2x(self):
        good = [0.003 + 0.001 * ((k % 5) - 2) for k in range(40)]
        self.assertEqual(rule.verdict(rows(good), 0)[0], "PASS")
        self.assertEqual(rule.verdict(rows(good, net2=-0.0001), 0)[0], "PENDING")
        self.assertEqual(rule.verdict(rows(good + [-1.0] * 30), 0)[0], "PASS")   # later hops cannot change it

    def test_final_look_and_end_date(self):
        noisy = [0.0015 + 0.01 * ((k * 7919) % 11 - 5) / 5 for k in range(80)]
        state, text = rule.verdict(rows(noisy), 0)
        self.assertIn(state, ("PASS", "NULL"))
        self.assertIn("final look at 80", text)
        self.assertEqual(rule.verdict(rows([0.001] * 10), rule.END_MS)[0], "INCONCLUSIVE")
        self.assertIn("final look at 30", rule.verdict(rows([0.001 + 0.002 * (k % 2) for k in range(30)]),
                                                       rule.END_MS)[1])

    def test_primary_filter_and_order(self):
        rs = rows([0.001, 0.002, 0.003])
        rs[0]["entry_ms"], rs[2]["entry_ms"] = 9, 1
        rs[1]["on_time"] = False
        rs.append({**rs[0], "hop": "small", "e": 0.0029, "entry_ms": 0})
        self.assertEqual([r["hop"] for r in rule.primary(rs)], ["h2", "h0"])


class Journal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.p = [mock.patch.object(fs, "JOURNAL", root / "journal"), mock.patch.object(fs, "DATA", root / "data"),
                  mock.patch.object(fs, "log", lambda *a: None)]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in reversed(self.p):
            p.stop()
        self.tmp.cleanup()


class TestDecision(Journal):
    def window(self):
        early = T0 - H - 5 * MIN
        seen = {"AAAUSDT": [T0, early, -0.0062, early, 1.00],          # deep: selected
                "BBBUSDT": [T0, early, -0.0045, early, 2.00],          # Lighter's mid 1000x: identity fails
                "CCCUSDT": [T0, early, -0.0024, early, 3.00],          # |e| 0.24%: logged below 0.3%
                "DDDUSDT": [T0, early, -0.0100, early, 4.00],          # not on Lighter
                "EEEUSDT": [T0, T0 - H + SEC, -0.0200, T0 - H + SEC, 5.0],   # a 1 h coin
                "FFFUSDT": [T0, early, 0.0040, early, 6.00],           # no live Lighter rate
                "GGGUSDT": [T0, early, 0.0001, early, 7.00]}           # quiet
        for k in range(6):                                             # six more deep coins: slots fill
            seen[f"S{k}USDT"] = [T0, early, -0.004 - k * 1e-4, early, 10.0 + k]
        details = [{"symbol": s, "market_id": m, "status": "active", "taker_fee": "0.0000",
                    "funding_premium_multiplier": 100}
                   for s, m in (("AAA", 1), ("1000BBB", 2), ("CCC", 3), ("EEE", 5), ("FFF", 6), ("GGG", 7))]
        details += [{"symbol": f"S{k}", "market_id": 10 + k, "status": "active", "taker_fee": "0.0000",
                     "funding_premium_multiplier": 100} for k in range(6)]
        details.append({"symbol": "XAU", "market_id": 90, "status": "active", "funding_premium_multiplier": 50})
        stats = {1: stat(1, -0.01, T0 - H, 1.01), 2: stat(2, -0.01, T0 - H, 2000.0), 3: stat(3, 0.0, T0 - H, 3.0),
                 5: stat(5, -0.01, T0 - H, 5.0), 6: stat(6, 0.01, T0 - 4 * H, 6.0), 7: stat(7, 0.0, T0 - H, 7.0)}
        stats.update({10 + k: stat(10 + k, 0.0, T0 - H, 10.0 + k) for k in range(6)})
        return seen, stats, details, early

    def test_select(self):
        seen, stats, details, early = self.window()
        asked = []
        cheap = lambda m, q: asked.append(m) or 0.0002
        sig, dec, hops = fs.select(T0, T0 - H + 20 * SEC, seen, stats, details, early, {1: -0.0049}, cheap)
        status = {r["symbol"]: r["status"] for r in sig}
        self.assertEqual(next(r["feed_r8"] for r in sig if r["symbol"] == "AAAUSDT"), -0.0049)
        self.assertEqual(status["AAAUSDT"], "selected")
        self.assertTrue(status["BBBUSDT"].startswith("identity"))
        self.assertEqual(status["CCCUSDT"], "below 0.3%")
        self.assertEqual(status["FFFUSDT"], "no live Lighter rate")
        self.assertNotIn("DDDUSDT", status)
        self.assertNotIn("EEEUSDT", status)
        self.assertNotIn("GGGUSDT", status)
        self.assertEqual([h["symbol"] for h in hops], ["AAAUSDT", "S5USDT", "S4USDT", "S3USDT", "S2USDT"])
        self.assertEqual(status["S1USDT"], "slots full")
        self.assertEqual(asked, [1, 15, 14, 13, 12])                   # the gate reads only the books it needs
        a = hops[0]
        self.assertEqual(next(r["rt_bp"] for r in sig if r["symbol"] == "AAAUSDT"), 2.0)
        self.assertAlmostEqual(a["e"], -0.0062 + 2 * 0.0001)
        self.assertEqual(a["d"], -1)
        self.assertAlmostEqual(a["q"], 1000 / 1.01)
        self.assertEqual((dec["eligible"], dec["on_lighter"], dec["candidates"], dec["selected"]), (12, 11, 8, 5))
        self.assertEqual(dec["error"], "")
        fs.append("signals", sig)
        rebuilt = fs.selected_hops(T0)
        self.assertEqual([h["hop"] for h in rebuilt], [h["hop"] for h in hops])
        self.assertAlmostEqual(rebuilt[0]["q"], a["q"])

    def test_late_window_and_late_decision(self):
        seen, stats, details, early = self.window()
        late_first = T0 - H - 30 * SEC
        moved = {s: [v[0], late_first, *v[2:]] for s, v in seen.items()}
        sig, dec, hops = fs.select(T0, T0 - H + 20 * SEC, moved, stats, details, late_first)
        self.assertEqual((dec["eligible"], hops), (0, []))
        self.assertIn("cycles not observed", dec["error"])
        sig, dec, hops = fs.select(T0, T0 - H + 11 * MIN, seen, stats, details, early)
        self.assertEqual(hops, [])
        self.assertTrue(all(r["status"] == "late decision" for r in sig if r.get("rank")))

    def test_cost_gate(self):
        seen, stats, details, early = self.window()

        def cost(m, q):
            if m == 13:
                raise OSError("REST down")
            return {15: 0.0011, 14: math.inf}.get(m, 0.0010)

        sig, dec, hops = fs.select(T0, T0 - H + 20 * SEC, seen, stats, details, early, None, cost)
        status = {r["symbol"]: r["status"] for r in sig}
        rt = {r["symbol"]: r.get("rt_bp") for r in sig}
        self.assertEqual([h["symbol"] for h in hops], ["AAAUSDT", "S2USDT", "S1USDT", "S0USDT"])
        self.assertEqual((status["S5USDT"], rt["S5USDT"]), ("book cost above 0.10%", 11.0))
        self.assertEqual((status["S4USDT"], rt["S4USDT"]), ("book cannot hold q", "inf"))
        self.assertEqual((status["S3USDT"], rt["S3USDT"]), ("no book at the decision", ""))
        self.assertEqual(dec["selected"], 4)
        none = fs.select(T0, T0 - H + 20 * SEC, seen, stats, details, early)[2]
        self.assertEqual(none, [])                                      # no cost read: nothing is selected
        with mock.patch.object(fs, "rest_book", return_value=lighter_book(1.0)):
            self.assertAlmostEqual(fs.rest_cost(1, 10.0), 0.001)       # 1.0005 - 0.9995 on a mid of 1

    def test_one_hop_per_lighter_market(self):
        seen, stats, details, early = self.window()
        seen["1000AAAUSDT"] = [T0, early, -0.0070, early, 1.0]
        sig, dec, hops = fs.select(T0, T0 - H + 20 * SEC, seen, stats, details, early, None, lambda m, q: 0.0)
        self.assertEqual([h["symbol"] for h in hops].count("AAAUSDT") + [h["symbol"] for h in hops].count(
            "1000AAAUSDT"), 1)
        self.assertIn("Lighter market already selected", {r["status"] for r in sig})

    def test_stream_handlers(self):
        seen, meta = {}, {}
        msg = {"stream": "!markPrice@arr", "data": [
            {"e": "markPriceUpdate", "E": 100, "s": "AAAUSDT", "p": "1.0", "r": "-0.006", "T": T0},
            {"e": "markPriceUpdate", "E": 100, "s": "BADUSDT", "p": "x", "r": "0", "T": T0}]}
        self.assertEqual(fs.on_binance_all(msg, seen, meta), 1)
        msg["data"][0].update({"E": 200, "r": "-0.007"})
        fs.on_binance_all(msg, seen, meta)
        self.assertEqual(seen["AAAUSDT"], [T0, 100, -0.007, 200, 1.0])     # first seen kept, rate updated
        msg["data"][0].update({"E": 300, "T": T0 + H})
        fs.on_binance_all(msg, seen, meta)
        self.assertEqual(seen["AAAUSDT"][:2], [T0 + H, 300])                # a new next funding time starts again
        self.assertEqual(meta["first_ms"], 100)
        stats = {}
        fs.on_lighter_stats({"type": "subscribed/market_stats", "market_stats": {"1": {"market_id": 1, "x": 1}}},
                            stats)
        fs.on_lighter_stats({"type": "update/market_stats", "market_stats": {"market_id": 2, "x": 2}}, stats)
        self.assertEqual(sorted(stats), [1, 2])


class TestBook(Journal):
    def test_snapshot_deltas_and_gap(self):
        b = fs.Book()
        b.snapshot({"bids": [{"price": "99", "size": "1"}, {"price": "98", "size": "0"}],
                    "asks": [{"price": "101", "size": "2"}], "nonce": 5}, 10)
        self.assertEqual(b.bids, {99.0: 1.0})
        b.update({"bids": [{"price": "99.5", "size": "3"}], "asks": [{"price": "101", "size": "0.00000"}],
                  "begin_nonce": 5, "nonce": 7}, 11)
        self.assertEqual(b.best()[0], 99.5)
        self.assertTrue(math.isnan(b.best()[1]))                    # the ask was removed: a one-sided book
        self.assertEqual(b.levels(False), [(99.5, 3.0), (99.0, 1.0)])
        with self.assertRaises(fs.Gap):
            b.update({"bids": [], "asks": [], "begin_nonce": 8, "nonce": 9}, 12)
        self.assertFalse(b.live)

    def test_entry_walks(self):
        h = hop(d=-1, q=10.0)
        b = lighter_book(100.0, size=50.0)
        at = T0 - 10 * SEC
        r = fs.entry_walk(h, -10 * SEC, b, (-0.006, 100.2), at + 30)
        self.assertEqual(r["status"], "entered")
        self.assertAlmostEqual(r["fill"], 100 * (1 - 0.0005))      # a short sells at the best bid
        self.assertEqual((r["late_ms"], r["b_r"]), (30, -0.006))
        self.assertEqual(fs.entry_walk(h, -10 * SEC, lighter_book(100.0, size=4.0), None, at)["status"],
                         "thin: not entered")
        self.assertEqual(fs.entry_walk(h, -300 * SEC, lighter_book(100.0, size=4.0), None, T0 - 300 * SEC)["status"],
                         "thin")
        self.assertEqual(fs.entry_walk(h, -10 * SEC, None, None, at)["status"], "no live book: not entered")
        self.assertEqual(fs.entry_walk(h, -10 * SEC, b, None, T0 - 500)["status"], "too late: not entered")
        one = fs.Book()
        one.snapshot({"bids": [{"price": "99", "size": "50"}], "asks": [], "nonce": 1}, 1)
        self.assertEqual(fs.entry_walk(h, -10 * SEC, one, None, at)["status"], "one-sided book: not entered")

    def test_exit_finishes_over_later_books(self):
        h = hop(d=-1, q=10.0)
        x = fs.Exit(h, 60 * SEC)
        self.assertFalse(x.step(None, T0 + 60 * SEC))
        self.assertFalse(x.step(lighter_book(100.0, size=3.0), T0 + 61 * SEC))    # 6 of 10 shown
        self.assertTrue(x.step(lighter_book(100.0, size=50.0), T0 + 62 * SEC))
        row = x.row((-0.001, 99.0))
        self.assertEqual((row["parts"], row["thin"], row["late_ms"], row["ms"]), (2, 1, 1000, T0 + 62 * SEC))
        self.assertEqual(row["status"], "walked")
        self.assertAlmostEqual(row["filled"], 10.0)
        a, b = 100 * 1.0005, 100 * 1.0015
        self.assertAlmostEqual(row["fill"], (3 * a + 3 * b + 4 * a) / 10)   # the short buys back on the asks
        y = fs.Exit(h, 60 * SEC)
        self.assertTrue(y.step(lighter_book(100.0), T0 + 90 * SEC, source="rest"))
        self.assertEqual(y.row()["status"], "walked late")

    def test_routing_and_recording(self):
        h = hop(mid=7, lighter="AAA")
        books, rec = {7: fs.Book()}, fs.Recording(T0, [h])
        by = {7: h}
        fs.on_lighter({"type": "subscribed/order_book", "channel": "order_book:7", "timestamp": 5,
                       "order_book": {"bids": [{"price": "1", "size": "5"}], "asks": [{"price": "1.1", "size": "5"}],
                                      "nonce": 1}}, books, rec, by, 5)
        fs.on_lighter({"type": "update/order_book", "channel": "order_book:7", "timestamp": 6,
                       "order_book": {"bids": [], "asks": [{"price": "1.05", "size": "1"}], "begin_nonce": 1,
                                      "nonce": 2}}, books, rec, by, 6)
        self.assertEqual(books[7].best(), (1.0, 1.05))
        trade = {"type": "update/trade", "channel": "trade:7",
                 "trades": [{"timestamp": 7, "trade_id": 1, "price": "1.05", "size": "2", "is_maker_ask": True,
                             "type": "trade"}]}
        fs.on_lighter(trade, books, rec, by, 7)
        fs.on_lighter(trade, books, rec, by, 8)                     # sent again after a reconnect
        fs.on_lighter({"type": "update/market_stats", "channel": "market_stats:7",
                       "market_stats": {"market_id": 7, "mark_price": "1.02", "funding_rate": "-0.0100"}},
                      books, rec, by, 9)
        fs.on_lighter({"type": "update/order_book", "channel": "order_book:99", "order_book": {}}, books, rec, by, 9)
        rec.sample(books, by, 10)
        fs.on_binance_sym({"data": {"e": "markPriceUpdate", "E": 11, "s": "AAAUSDT", "p": "1.0", "i": "1.0",
                                    "r": "-0.006", "T": T0}}, {}, rec, {"AAAUSDT": h})
        with self.assertRaises(fs.Gap):
            fs.on_lighter({"type": "update/order_book", "channel": "order_book:7", "timestamp": 12,
                           "order_book": {"bids": [], "asks": [], "begin_nonce": 9, "nonce": 10}}, books, rec, by, 12)
        out = rec.write()
        kinds = {r["kind"]: r for r in out}
        self.assertEqual(sorted(kinds), ["bmark", "book", "stats", "trades"])
        self.assertEqual(kinds["trades"]["rows"], 1)
        self.assertEqual(kinds["book"]["rows"], 3)                  # one bid, two asks
        p = Path(fs.DATA) / str(T0) / "AAA_book.csv.gz"
        self.assertTrue(gzip.decompress(p.read_bytes()).decode().startswith("ms,book_ms,side,level,price,size"))
        again = rec.write()
        self.assertEqual([r["sha256"] for r in again], [r["sha256"] for r in out])   # bytes depend on rows only


class TestScore(Journal):
    def book_tickets(self, d=-1, exit_mid=99.0):
        h = hop(d=d, q=10.0)
        b0 = lighter_book(100.0)
        fs.append("tickets", [fs.entry_walk(h, -300 * SEC, b0, None, T0 - 300 * SEC),
                              fs.entry_walk(h, -10 * SEC, b0, None, T0 - 10 * SEC)])
        for off in rule.EXITS:
            x = fs.Exit(h, off)
            x.step(lighter_book(exit_mid), T0 + off)
            fs.append("tickets", [x.row()])
        return h

    def test_score_waits_for_the_settlement_then_scores(self):
        h = self.book_tickets()
        self.assertEqual(fs.due(T0 + 60 * SEC + 19 * MIN), [])
        due = fs.due(T0 + 60 * SEC + 20 * MIN)
        self.assertEqual([x[0] for x in due], [h["hop"]])
        k = due[0][1]
        self.assertIsNone(fs.score_hop(h["hop"], k, [(T0 - H, -0.001)], T0 + H))      # not in history yet
        row = fs.score_hop(h["hop"], k, [(T0 - H, -0.001), (T0, -0.001)], T0 + H)
        self.assertAlmostEqual(row["gross_mid"], 0.01)
        self.assertAlmostEqual(row["fund"], -0.001)
        book = 0.0005 + 99.0 * 0.0005 / 100                  # both half-spreads, as fractions of the entry notional
        self.assertAlmostEqual(row["book_cost"], book)
        self.assertAlmostEqual(row["net1"], 0.01 - 0.001 - book)
        self.assertTrue(row["on_time"])
        self.assertEqual(row["rates"], f"{T0}:-0.001")
        for c in ("in300_out60", "in300_out120", "in300_out300", "in10_out120", "in10_out300"):
            self.assertAlmostEqual(row[c], row["net1"])
        self.assertAlmostEqual(row["in10_out60"], row["net1"])
        late = fs.score_hop(h["hop"], k, [], T0 + rule.FUND_WAIT)
        self.assertEqual((late["fund_missing"], late["fund"]), (1, 0))
        fs.append("scored", [row])
        self.assertEqual(fs.due(T0 + 2 * H), [])
        s = fs.status(T0 + 2 * H)
        self.assertEqual((s["scored"], s["tickets"], s["open"], s["state"]), (1, 1, 0, "PENDING"))
        self.assertAlmostEqual(s["mean_net"], row["net1"])
        self.assertTrue((Path(fs.JOURNAL) / "status.json").exists())

    def test_owed_exit_on_the_rest_book(self):
        h = hop(d=-1, q=10.0)
        fs.append("tickets", [fs.entry_walk(h, -10 * SEC, lighter_book(100.0), None, T0 - 10 * SEC)])
        self.assertEqual(fs.owed_exits(T0 + rule.BOOK_TO - 1), [])
        owed = fs.owed_exits(T0 + rule.BOOK_TO)
        self.assertEqual([x.hop["hop"] for x in owed], [h["hop"]])
        with mock.patch.object(fs, "clock_ms", lambda: T0 + 20 * MIN):
            self.assertFalse(fs.rest_exit_step(owed[0], lighter_book(100.0, size=4.0)))
            self.assertTrue(fs.rest_exit_step(owed[0], lighter_book(100.0, size=50.0)))
        k = fs.tickets_by_hop()[h["hop"]]
        self.assertEqual((k["out60"]["source"], k["out60"]["status"]), ("rest", "walked late"))
        self.assertEqual(fs.owed_exits(T0 + H), [])
        self.assertEqual(fs.status(T0 + H)["rest_exits"], 1)

    def test_status_on_an_empty_journal(self):
        s = fs.status(T0, write=False)
        self.assertEqual((s["state"], s["scored"], s["tickets"]), ("PENDING", 0, 0))
        json.dumps(s)


class TestLane(Journal):
    def test_append_only_with_a_fixed_header(self):
        fs.append("recordings", [{"hop": "a", "T": 1}])
        fs.append("recordings", [{"hop": "b", "T": 2, "rows": 3}])
        rs = fs.read("recordings")
        self.assertEqual([r["hop"] for r in rs], ["a", "b"])
        self.assertEqual(fs.path_of("recordings").read_text().count("hop,T,kind"), 1)
        with self.assertRaises(ValueError):
            fs.append("recordings", [{"hop": "c", "surprise": 1}])
        self.assertEqual(fs.read("scored"), [])

    def test_one_writer(self):
        with fs.writer_lock():
            with self.assertRaises(SystemExit):
                with fs.writer_lock():
                    pass

    def test_ensure_starts_the_daemon_only_when_no_writer_holds_the_lock(self):
        with mock.patch.object(fs, "check") as chk, mock.patch.object(fs.subprocess, "Popen") as popen, \
                mock.patch.object(fs, "LOG", Path(self.tmp.name) / "logs" / "settlelit_fwd.log"):
            with fs.writer_lock():
                self.assertEqual(fs.ensure(), 0)
            popen.assert_not_called()
            chk.assert_not_called()
            self.assertEqual(fs.ensure(), 0)
            chk.assert_called_once()
            self.assertEqual(popen.call_args.args[0][-1], "run")
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_no_decision_unless_the_prereg_and_the_rule_are_unchanged(self):
        lane = Path(self.tmp.name) / "lane"
        lane.mkdir()
        rel = "scripts/settlelit_fwd_rule.py"
        sha = prereg.sha256_file(fs.ROOT / rel)
        spec = lane / "PREREG.md"
        with self.assertRaises(prereg.PreregError):
            fs.check(lane)
        spec.write_text(f"# PREREG\n\n```fixed\n{sha}  {rel}\n```\n")
        prereg.freeze(spec)
        self.assertEqual(fs.fixed_inputs(spec), {rel: sha})
        fs.check(lane)
        bad = lane.parent / "lane2"
        bad.mkdir()
        (bad / "PREREG.md").write_text(f"# PREREG\n\n```fixed\n{'0' * 64}  {rel}\n```\n")
        prereg.freeze(bad / "PREREG.md")
        with self.assertRaises(prereg.PreregError):
            fs.check(bad)
        spec.write_text(spec.read_text() + "an edit after the freeze\n")
        with self.assertRaises(prereg.PreregError):
            fs.check(lane)

    def test_next_settlement(self):
        self.assertEqual(fs.next_T(T0 - H + 19 * SEC), T0)
        self.assertEqual(fs.next_T(T0 - H + 20 * SEC), T0 + rule.STEP)
        self.assertEqual(fs.next_T(T0 - 3 * H), T0)
        self.assertEqual(fs.next_T(T0 - rule.STEP - H + 21 * SEC), T0)


if __name__ == "__main__":
    unittest.main()
