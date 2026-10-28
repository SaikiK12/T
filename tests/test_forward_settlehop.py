import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from lab import prereg
from scripts import forward_settlehop as fs
from scripts import settlehop_rule as rule

H, DAY, MIN = rule.H, rule.DAY, rule.MIN
T0 = 1_793_678_400_000                          # 2026-11-02 04:00 UTC, an invented settlement


def book(mid, half=0.0005, usd=50_000.0):
    q = usd / mid
    return {"bids": [(mid * (1 - half), q), (mid * (1 - 2 * half), q)],
            "asks": [(mid * (1 + half), q), (mid * (1 + 2 * half), q)]}


def walk_closes(seed, end_ms, n=40):
    """{00:00 UTC ms: close} for n days up to the day of end_ms."""
    r = np.random.default_rng(seed).normal(0, 0.03, n)
    px = 100 * np.exp(np.cumsum(r))
    days = end_ms // DAY * DAY - DAY * np.arange(n - 1, -1, -1)
    return {int(t): float(p) for t, p in zip(days, px)}


class TestPure(unittest.TestCase):
    def test_canon(self):
        self.assertEqual(rule.canon("1000PEPE"), "PEPE")
        self.assertEqual(rule.canon("1000000MOG"), "MOG")
        self.assertEqual(rule.canon("kPEPE"), "PEPE")
        self.assertEqual(rule.canon("KAITO"), "KAITO")            # an upper case K is part of the name
        self.assertEqual(rule.canon("KSM"), "KSM")
        self.assertEqual(rule.canon("btc"), "BTC")
        self.assertEqual(rule.canon(None), "")

    def test_lighter_crypto(self):
        self.assertTrue(rule.lighter_crypto({"funding_premium_multiplier": 100}))
        self.assertFalse(rule.lighter_crypto({"funding_premium_multiplier": 50}))     # stocks, FX, metals
        self.assertFalse(rule.lighter_crypto({"funding_premium_multiplier": 1}))      # pre-IPO
        self.assertFalse(rule.lighter_crypto({}))
        details = [{"symbol": "1000PEPE", "market_id": 4, "status": "active", "taker_fee": "0.0000",
                    "funding_premium_multiplier": 100},
                   {"symbol": "XAU", "market_id": 92, "status": "active", "taker_fee": "0.0000",
                    "funding_premium_multiplier": 50},
                   {"symbol": "OLD", "market_id": 9, "status": "inactive", "taker_fee": "0.0000",
                    "funding_premium_multiplier": 100}]
        with mock.patch.object(fs.carrylane, "_lighter_details", lambda: details):
            self.assertEqual(fs.lighter_markets(), {"PEPE": ("1000PEPE", 4, 0.0)})

    def test_signal(self):
        e, d = rule.signal(-0.01, 0.0001)
        self.assertAlmostEqual(e, -0.0102)
        self.assertEqual(d, -1)                                  # long S, short Lighter
        e, d = rule.signal(0.004, -0.001)
        self.assertAlmostEqual(e, 0.006)
        self.assertEqual(d, 1)

    def test_walk_and_fills(self):
        asks = [(100.0, 5.0), (101.0, 10.0)]
        px, got = rule.walk(asks, 1000)
        self.assertAlmostEqual(got, 1000)
        self.assertAlmostEqual(px, 1000 / (5 + 500 / 101))
        thin = {"bids": [(99.0, 2.0)], "asks": [(100.0, 6.0)]}
        px, got, flag = rule.side_fill(thin, buy=True)
        self.assertTrue(flag)
        self.assertAlmostEqual(got, 600)
        px, got, flag = rule.side_fill(thin, buy=True, complete=False)   # an exit closes the rest at the last level
        self.assertTrue(flag)
        self.assertAlmostEqual(got, 1000)
        self.assertAlmostEqual(px, 100.0)
        px, got, flag = rule.side_fill(thin, buy=False, complete=False)
        self.assertAlmostEqual(px, 99.0)
        self.assertTrue(math.isnan(rule.walk([], 1000)[0]))
        px, got = rule.walk([(100.0, math.nan), (101.0, 20.0)], 1000)     # a NaN level is skipped, not filled
        self.assertAlmostEqual(px, 101.0)

    def test_side_cost(self):
        self.assertAlmostEqual(rule.side_cost(101.0, 100.0, True), 0.01)
        self.assertAlmostEqual(rule.side_cost(99.0, 100.0, False), 0.01)
        self.assertAlmostEqual(rule.side_cost(99.5, 100.0, True), -0.005)

    def test_daily_closes_keep_only_the_bar_ending_at_midnight(self):
        bars = [(T0 - 4 * H - k * H, 10.0 + k) for k in range(30)]          # opens from 00:00 back
        got = rule.daily_closes(bars)
        self.assertTrue(all(t % DAY == 0 for t in got))
        self.assertEqual(got[T0 - 4 * H], 11.0)                              # the bar opening 23:00 closes at 00:00

    def test_same_coin(self):
        a = walk_closes(1, T0)
        ok, c = rule.same_coin(a, {t: 2 * p for t, p in a.items()}, T0)        # a size prefix scales the price only
        self.assertTrue(ok)
        self.assertAlmostEqual(c, 1.0)
        ok, c = rule.same_coin(a, walk_closes(2, T0), T0)
        self.assertFalse(ok)
        short = dict(sorted(a.items())[-20:])                                 # 19 returns: too few pairs
        ok, c = rule.same_coin(a, short, T0)
        self.assertFalse(ok)
        self.assertTrue(math.isnan(c))

    def test_last_settled_and_window(self):
        f = [(T0 - 3 * H, 0.1), (T0 - H, 0.2), (T0, 0.3)]
        self.assertEqual(rule.last_settled(f, T0 - H), (T0 - H, 0.2))
        t, r = rule.last_settled(f, T0 - 4 * H)
        self.assertIsNone(t)
        self.assertTrue(math.isnan(r))
        self.assertEqual(rule.window(f, T0 - H, T0), [(T0, 0.3)])          # (a, b]: the entry's own hour is out

    def test_theta_book(self):
        self.assertEqual(rule.theta_book(0.005), 0.5)
        self.assertEqual(rule.theta_book(-0.006), 0.5)
        self.assertEqual(rule.theta_book(-0.0049999), 0.3)
        self.assertEqual(rule.theta_book(0.003), 0.3)

    def test_decide_stats_cr1(self):
        mu, t = rule.decide_stats([1.0, 2.0, 3.0, 6.0], ["a", "a", "b", "b"])
        self.assertAlmostEqual(mu, 3.0)
        self.assertAlmostEqual(t, 2.0)                    # cluster sums -3, +3: var 18/16 x 2 = 2.25
        self.assertTrue(math.isnan(rule.decide_stats([1.0, 2.0], ["a", "a"])[1]))
        self.assertTrue(math.isnan(rule.decide_stats([], [])[0]))


class TestReported(unittest.TestCase):
    def test_trimmed_and_leave_two_coins_out(self):
        x = list(range(25))                                  # 0 .. 24
        self.assertAlmostEqual(rule.trimmed(x), np.mean(range(10, 15)))
        self.assertTrue(math.isnan(rule.trimmed(x[:20])))
        nets = [5.0, 4.0, 1.0, 1.0, -1.0]
        coins = ["A", "B", "C", "C", "D"]
        self.assertAlmostEqual(rule.leave_two_coins_out(nets, coins), 1 / 3)     # A and B out
        self.assertTrue(math.isnan(rule.leave_two_coins_out([1.0], ["A"])))


class TestScore(unittest.TestCase):
    def hop(self):
        a, b = T0 - H + 90_000, T0 + H + 30_000
        enter = {"d": -1, "ms": a, "venue": "mexc", "s_bid": 99.9, "s_ask": 100.1, "s_fill": 100.15,
                 "h_bid": 99.95, "h_ask": 100.05, "h_fill": 99.9, "fee_s_bp": 4.0, "fee_h_bp": 0.0}
        exit_ = {"d": -1, "ms": b, "venue": "mexc", "s_bid": 98.95, "s_ask": 99.05, "s_fill": 98.9,
                 "h_bid": 99.15, "h_ask": 99.25, "h_fill": 99.3, "fee_s_bp": 4.0, "fee_h_bp": 0.0}
        return a, b, enter, exit_

    def test_long_s_short_lighter_accounting(self):
        a, b, enter, exit_ = self.hop()
        s_rates = [(T0 - 4 * H, -0.02), (a, -0.5), (T0, -0.01), (b + 1, -0.5)]       # only T is held
        h_rates = [(T0 - H, -0.5), (T0, -0.001), (T0 + H, -0.001)]
        r = rule.score(enter, exit_, s_rates, h_rates)
        self.assertAlmostEqual(r["gross_mid"], -1 * ((99.2 / 100 - 1) - (99 / 100 - 1)))
        self.assertAlmostEqual(r["fund_s"], 0.01)                 # the long receives the negative lump
        self.assertAlmostEqual(r["fund_h"], -0.002)               # the Lighter short pays two negative hours
        self.assertAlmostEqual(r["fund"], 0.008)
        self.assertEqual((r["n_s"], r["n_h"]), (1, 2))
        book_ = 0.0015 + (1 - 98.9 / 99) + 0.001 + (99.3 / 99.2 - 1)
        self.assertAlmostEqual(r["book_cost"], book_)
        self.assertAlmostEqual(r["fee_web"], 0.0008)
        self.assertAlmostEqual(r["fee_api"], 0.0016)              # MEXC API taker 8 bp a side
        for k in (1, 2, 3):
            self.assertAlmostEqual(r[f"net{k}_web"], r["gross_mid"] + 0.008 - k * (book_ + 0.0008))
            self.assertAlmostEqual(r[f"net{k}_api"], r["gross_mid"] + 0.008 - k * (book_ + 0.0016))
        self.assertEqual(r["path_n"], 0)

    def test_adverse_excursion_signs(self):
        a, b, enter, exit_ = self.hop()
        path = [{"ms": a + MIN, "s_mark": 98.0, "h_mark": 100.0},        # the long S leg is 2% under
                {"ms": a + 2 * MIN, "s_mark": 100.0, "h_mark": 101.0},   # the short Lighter leg is 1% under
                {"ms": b + MIN, "s_mark": 50.0, "h_mark": 150.0},        # after the exit: ignored
                {"ms": a + 3 * MIN, "s_mark": "", "h_mark": 100.0}]      # a missed quote: ignored
        r = rule.score(enter, exit_, [], [], path)
        self.assertAlmostEqual(r["mae_s"], -0.02)
        self.assertAlmostEqual(r["mae_h"], -0.01)
        self.assertAlmostEqual(r["mae_pair"], -0.02)
        self.assertEqual(r["path_n"], 2)


def prim_rows(nets, nets2=None, per_T=1):
    return [{"hop": f"h{i}", "venue": "mexc", "theta_book": "0.5", "on_time": "True", "entry_ms": str(T0 + i * H),
             "T": str(T0 + (i // per_T) * 4 * H), "net1_web": str(x),
             "net2_web": str(x - 0.001 if nets2 is None else nets2[i])} for i, x in enumerate(nets)]


class TestVerdict(unittest.TestCase):
    def test_pending_and_futility(self):
        self.assertEqual(rule.verdict(prim_rows([0.003] * 19), T0)[0], "PENDING")
        state, text = rule.verdict(prim_rows([-0.001] * 20), T0)
        self.assertEqual(state, "NULL")
        self.assertIn("futility at 20", text)
        rows = prim_rows([0.002] * 20 + [-0.01] * 20)              # mean of the first 40 below 0
        self.assertIn("futility at 40", rule.verdict(rows, T0)[1])

    def test_interim_pass_needs_t_and_2x(self):
        rng = np.random.default_rng(3)
        strong = list(0.004 + 0.004 * rng.standard_normal(40))
        state, text = rule.verdict(prim_rows(strong), T0)
        self.assertEqual(state, "PASS")
        self.assertIn("interim", text)
        state, _ = rule.verdict(prim_rows(strong, nets2=[-0.01] * 40), T0)     # 2x below 0: no pass
        self.assertEqual(state, "PENDING")

    def test_final_look_at_80_or_the_end_date(self):
        rng = np.random.default_rng(5)
        z = rng.standard_normal(80)
        z = (z - z.mean()) / z.std()
        x = list(0.0025 + 0.0075 * z)                    # t over 80 near 2.98; over 40 below the interim bound
        mu40, t40 = rule.decide_stats(x[:40], [str(i) for i in range(40)])
        self.assertLess(t40, rule.T_LOOK1)
        self.assertEqual(rule.verdict(prim_rows(x[:60]), T0)[0], "PENDING")
        state, text = rule.verdict(prim_rows(x), T0)
        self.assertEqual(state, "PASS")
        self.assertIn("final look at 80", text)
        state, text = rule.verdict(prim_rows(x[:60]), rule.END_MS)
        self.assertIn("final look at 60", text)
        self.assertEqual(rule.verdict(prim_rows([0.01] * 15), rule.END_MS)[0], "INCONCLUSIVE")
        flat = list(0.0001 + 0.0075 * z)
        self.assertEqual(rule.verdict(prim_rows(flat), T0)[0], "NULL")

    def test_primary_filter_and_order(self):
        rows = prim_rows([0.001, 0.002, 0.003])
        rows[0]["on_time"] = "False"
        rows[1]["theta_book"] = "0.3"
        rows.append({**rows[2], "hop": "g", "venue": "gate"})
        rows.append({**rows[2], "hop": "early", "entry_ms": str(T0 - H)})
        self.assertEqual([r["hop"] for r in rule.primary(rows)], ["early", "h2"])


class TestJournal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = mock.patch.object(fs, "JOURNAL", Path(self.tmp.name) / "journal")
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def test_append_is_append_only_with_a_fixed_header(self):
        fs.append("path", [{"ms": 1, "hop": "a"}])
        fs.append("path", [{"ms": 2, "hop": "b", "s_mark": 3.5}])
        rows = fs.read("path")
        self.assertEqual([r["hop"] for r in rows], ["a", "b"])
        self.assertEqual(rows[0]["s_mark"], "")
        self.assertEqual(fs.path_of("path").read_text().count("ms,hop"), 1)
        with self.assertRaises(ValueError):
            fs.append("path", [{"ms": 3, "hop": "c", "surprise": 1}])
        self.assertEqual(fs.read("scored"), [])                      # a journal not yet written reads empty

    def test_one_writer(self):
        with fs.writer_lock():
            with self.assertRaises(SystemExit):
                with fs.writer_lock():
                    pass

    def test_ensure_starts_the_daemon_only_when_no_writer_holds_the_lock(self):
        with mock.patch.object(fs, "check") as chk, mock.patch.object(fs.subprocess, "Popen") as popen, \
                mock.patch.object(fs, "LOG", Path(self.tmp.name) / "logs" / "settlehop_fwd.log"), \
                mock.patch.object(fs, "log", lambda *a: None):
            with fs.writer_lock():
                self.assertEqual(fs.ensure(), 0)
            popen.assert_not_called()
            chk.assert_not_called()
            self.assertEqual(fs.ensure(), 0)
            chk.assert_called_once()
            self.assertEqual(popen.call_args.args[0][-1], "run")
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_no_tick_unless_the_prereg_and_the_rule_are_unchanged(self):
        lane = Path(self.tmp.name) / "lane"
        lane.mkdir()
        rel = "scripts/settlehop_rule.py"
        sha = prereg.sha256_file(fs.ROOT / rel)
        spec = lane / "PREREG.md"
        with self.assertRaises(prereg.PreregError):            # not frozen yet
            fs.check(lane)
        spec.write_text(f"# PREREG\n\n```fixed\n{sha}  {rel}\n```\n")
        prereg.freeze(spec)
        self.assertEqual(fs.fixed_inputs(spec), {rel: sha})
        fs.check(lane)
        bad = lane.parent / "lane2"
        bad.mkdir()
        (bad / "PREREG.md").write_text(f"# PREREG\n\n```fixed\n{'0' * 64}  {rel}\n```\n")
        prereg.freeze(bad / "PREREG.md")
        with self.assertRaises(prereg.PreregError):            # the rule file no longer matches
            fs.check(bad)
        spec.write_text(spec.read_text() + "an edit after the freeze\n")
        with self.assertRaises(prereg.PreregError):
            fs.check(lane)


class TestTick(unittest.TestCase):
    """A whole hop on invented venues: decided at T - 1 h, exited at T + 1 h, scored 20 minutes later."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = T0 - H + 20_000
        self.px = {"s": 100.0, "h": 100.0}
        closes = walk_closes(7, T0)
        other = walk_closes(8, T0)
        settle = {"AAA_USDT": ("AAA", -0.012, 4, 1.0, 4.0, -0.02),       # |e| 1.22%: the primary book
                  "BBB_USDT": ("BBB", 0.0001, 4, 1.0, 4.0, 0.02),        # |e| 0.01%: not logged
                  "CCC_USDT": ("CCC", -0.004, 4, 1.0, 4.0, -0.02),       # |e| 0.42%: fails the identity check
                  "DDD_USDT": ("DDD", 0.01, 8, 1.0, 4.0, 0.02)}          # not on Lighter
        lighter = [(T0 - 2 * H, 0.0001), (T0 - H, 0.0001), (T0, -0.001), (T0 + H, -0.001)]
        self.patches = [
            mock.patch.object(fs, "JOURNAL", Path(self.tmp.name) / "journal"),
            mock.patch.object(fs, "clock_ms", lambda: self.now),
            mock.patch.object(fs, "log", lambda *a: None),
            mock.patch.object(fs.time, "sleep", lambda s: None),
            mock.patch.dict(fs.SETTLING, {"mexc": lambda T: settle if T == T0 else {}, "gate": lambda T: {}}),
            mock.patch.object(fs, "lighter_markets",
                              lambda: {"AAA": ("AAA", 1, 0.0), "BBB": ("BBB", 2, 0.0), "CCC": ("1000CCC", 3, 0.0)}),
            mock.patch.object(fs, "lighter_fundings", lambda m, a, b: [x for x in lighter if a <= x[0] <= b]),
            mock.patch.object(fs, "binance_rates", lambda: {"AAA": -0.009}),
            mock.patch.dict(fs.CLOSES, {"mexc": lambda s, e: closes, "gate": lambda s, e: closes}),
            mock.patch.object(fs, "closes_lighter", lambda s, e: other if s == "1000CCC" else closes),
            mock.patch.dict(fs.BOOK, {"mexc": lambda s, size: book(self.px["s"]), "gate": lambda s, size: book(1)}),
            mock.patch.object(fs, "book_lighter", lambda m: book(self.px["h"], half=0.0002)),
            mock.patch.object(fs, "contract_size", lambda v, s: 1.0),
            mock.patch.object(fs, "s_funding", lambda v, s, a, b: [(T0 - 4 * H, -0.003), (T0, -0.012)]),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_a_hop_from_decision_to_score(self):
        s = fs.tick(self.now)
        tickets = fs.read("tickets")
        self.assertEqual([t["hop"] for t in tickets], [f"mexc:AAA_USDT:{T0}"])
        t = tickets[0]
        self.assertEqual((t["action"], t["d"], t["theta_book"], t["late_s"]), ("enter", "-1", "0.5", "20"))
        self.assertAlmostEqual(float(t["e"]), -0.0122)
        self.assertAlmostEqual(float(t["s_fill"]), 100.05)                  # long S: buys at the ask
        self.assertAlmostEqual(float(t["h_fill"]), 99.98)                   # short Lighter: sells at the bid
        sig = {r["symbol"]: r for r in fs.read("signals")}
        self.assertEqual(set(sig), {"AAA_USDT", "CCC_USDT"})
        self.assertEqual(sig["CCC_USDT"]["status"], "identity check failed")
        self.assertEqual(sig["AAA_USDT"]["binance_F"], "-0.009")
        self.assertEqual(sig["AAA_USDT"]["h_prev_t"], str(T0 - H))
        dec = {r["venue"]: r for r in fs.read("decisions")}
        self.assertEqual((dec["mexc"]["settling"], dec["mexc"]["on_lighter"], dec["mexc"]["candidates"],
                          dec["mexc"]["entered"]), ("4", "3", "2", "1"))
        self.assertEqual(dec["gate"]["settling"], "0")
        self.assertEqual((s["state"], s["open"], s["tickets"]), ("PENDING", 1, 1))

        self.now = T0 - H + 5 * MIN                         # the same hour again: decided once
        fs.tick(self.now)
        self.assertEqual(len(fs.read("decisions")), 2)
        self.assertEqual(len(fs.read("tickets")), 1)

        self.now = T0 + H + 20_000                          # exit at T + 1 h, after the price fell on S
        self.px.update(s=99.0, h=99.2)
        fs.tick(self.now)
        ex = [t for t in fs.read("tickets") if t["action"] == "exit"]
        self.assertEqual(len(ex), 1)
        self.assertEqual((ex[0]["late_s"], ex[0]["thin"]), ("20", ""))
        self.assertEqual(fs.read("scored"), [])             # funding is read 20 minutes after the exit

        self.now = T0 + H + 21 * MIN
        s = fs.tick(self.now)
        r = fs.read("scored")[0]
        self.assertEqual((r["on_time"], r["n_s"], r["n_h"]), ("True", "1", "2"))
        self.assertAlmostEqual(float(r["fund"]), 0.012 - 0.002)
        gross = -1 * ((99.2 / 100 - 1) - (99.0 / 100 - 1))
        self.assertAlmostEqual(float(r["gross_mid"]), gross)
        book_ = 0.0005 * 2 + 0.0002 * 2
        self.assertAlmostEqual(float(r["book_cost"]), book_)
        self.assertAlmostEqual(float(r["net1_web"]), gross + 0.010 - book_ - 0.0008)
        self.assertEqual((s["scored"], s["open"], s["state"]), (1, 0, "PENDING"))
        self.assertEqual(s["go_real"]["n"], 1)
        self.assertEqual(s["books"]["mexc th0.5%"]["scored"], 1)
        self.assertEqual(s["books"]["mexc th0.3%"]["scored"], 1)
        fs.tick(self.now + MIN)                             # scoring is idempotent
        self.assertEqual(len(fs.read("scored")), 1)

    def test_no_decision_after_the_on_time_window(self):
        self.now = T0 - H + 11 * MIN
        fs.tick(self.now)
        self.assertEqual(fs.read("decisions"), [])
        self.assertEqual(fs.read("tickets"), [])

    def test_entries_stop_at_the_deadline(self):
        start = self.now
        calls = iter([start + 9 * MIN, start + 11 * MIN])   # past T - 1 h + 10 min once the books are read
        with mock.patch.object(fs, "clock_ms", lambda: next(calls, start + 12 * MIN)):
            fs.tick(start)
        self.assertEqual(fs.read("tickets"), [])
        sig = {r["symbol"]: r["status"] for r in fs.read("signals")}
        self.assertEqual(sig["AAA_USDT"], "past the on-time window")

    def test_no_contract_size_no_entry(self):
        settle = {"AAA_USDT": ("AAA", -0.012, 4, math.nan, 4.0, -0.02)}
        with mock.patch.dict(fs.SETTLING, {"mexc": lambda T: settle if T == T0 else {}}):
            fs.tick(self.now)
        self.assertEqual(fs.read("tickets"), [])
        self.assertEqual(fs.read("signals")[0]["status"], "no contract size")

    def test_a_failed_venue_is_logged_and_the_other_decides(self):
        def boom(T):
            raise RuntimeError("gate down")
        with mock.patch.dict(fs.SETTLING, {"gate": boom}):
            fs.tick(self.now)
        dec = {r["venue"]: r for r in fs.read("decisions")}
        self.assertIn("gate down", dec["gate"]["error"])
        self.assertEqual(dec["mexc"]["entered"], "1")

    def test_a_late_exit_is_off_time(self):
        fs.tick(self.now)
        self.now = T0 + H + 15 * MIN                        # the container was down at T + 1 h
        fs.tick(self.now)
        self.now += 21 * MIN
        s = fs.tick(self.now)
        self.assertEqual(fs.read("scored")[0]["on_time"], "False")
        self.assertEqual(s["scored"], 0)


if __name__ == "__main__":
    unittest.main()
