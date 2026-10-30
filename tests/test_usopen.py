import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import forward_usopen as fu  # noqa: E402
import usopen_rule as rule  # noqa: E402

H, MIN, DAY = rule.H, rule.MIN, rule.DAY
ms = lambda s: pd.Timestamp(s, tz="UTC").value // 10**6
DAY_MS = ms("2026-10-29")
D = rule.decision_ms(DAY_MS)


def bars(sig=0.0, vol=1.0, D=D, day_ms=DAY_MS, traded_start=True, traded_end=True, extra_future=False):
    t = np.arange(D - 720 * H, D, H)
    close = np.full(len(t), 100.0)
    close[t == D - H] = 100.0 * (1 + sig)
    q = np.full(len(t), vol)
    if not traded_start:
        q[t == day_ms - H] = 0.0
    if not traded_end:
        q[t == D - H] = 0.0
    df = pd.DataFrame({"t": t, "close": close, "quote_volume": q})
    if extra_future:
        df = pd.concat([df, pd.DataFrame({"t": [D, D + H], "close": [1e9, 1e9], "quote_volume": [1e9, 1e9]})])
    return df


def world(n=60, extra_future=False):
    """S00USDT .. S59USDT: volume rises with i, move since 00:00 UTC is (i - 30) / 1000."""
    return {f"S{i:02d}USDT": bars(sig=(i - 30) / 1000, vol=1.0 + i, extra_future=extra_future) for i in range(n)}


def table(n=40, taker="0.0002"):
    return pd.DataFrame({"symbol": [f"S{i:02d}_USDT" for i in range(n)], "base": [f"S{i:02d}" for i in range(n)],
                         "type": 1, "state": 0, "taker": float(taker), "maker": 0.0, "contract_size": 1, "settle": "USDT"})


class Clock(unittest.TestCase):
    def test_decision_follows_new_york_summer_and_winter_time(self):
        self.assertEqual(D, ms("2026-10-29 14:00"))
        self.assertEqual(rule.decision_ms(ms("2026-11-02")), ms("2026-11-02 15:00"))     # clocks went back on 11-01
        self.assertEqual(rule.decision_ms(ms("2026-03-10")), ms("2026-03-10 14:00"))     # and forward on 03-08

    def test_trading_days_skip_weekends_and_holidays(self):
        self.assertTrue(rule.is_nyse_day(DAY_MS))
        self.assertFalse(rule.is_nyse_day(ms("2026-10-31")))          # Saturday
        self.assertFalse(rule.is_nyse_day(ms("2026-11-26")))          # Thanksgiving
        self.assertFalse(rule.is_nyse_day(ms("2026-12-25")))
        days = [d for d, _ in rule.decision_days(ms("2026-10-30"), 3)]
        self.assertEqual(days, [ms("2026-10-30"), ms("2026-11-02"), ms("2026-11-03")])


class CrossSection(unittest.TestCase):
    def test_rank_is_by_volume_and_signal_by_close_over_close(self):
        cs = rule.cross_section(world(), DAY_MS, D)
        self.assertEqual(cs.symbol.iloc[0], "S59USDT")
        self.assertEqual(list(cs["rank"].iloc[:3]), [1, 2, 3])
        r = cs.set_index("symbol")
        self.assertAlmostEqual(r.loc["S59USDT", "sig"], 0.029)
        self.assertAlmostEqual(r.loc["S00USDT", "sig"], -0.030)

    def test_bars_at_or_after_the_decision_are_never_read(self):
        a = rule.cross_section(world(), DAY_MS, D)
        b = rule.cross_section(world(extra_future=True), DAY_MS, D)
        pd.testing.assert_frame_equal(a, b)

    def test_a_symbol_not_trading_at_the_decision_is_left_out_and_one_not_trading_at_midnight_has_no_signal(self):
        f = world()
        f["S58USDT"] = bars(sig=0.5, vol=59.0, traded_end=False)
        f["S57USDT"] = bars(sig=0.5, vol=58.0, traded_start=False)
        cs = rule.cross_section(f, DAY_MS, D).set_index("symbol")
        self.assertNotIn("S58USDT", cs.index)
        self.assertTrue(np.isnan(cs.loc["S57USDT", "sig"]))
        self.assertIn("S57USDT", cs.index)

    def test_pick_takes_the_three_strongest_and_weakest_of_the_top_fifty(self):
        longs, shorts, n = rule.pick(rule.cross_section(world(), DAY_MS, D))
        self.assertEqual(longs, ["S59USDT", "S58USDT", "S57USDT"])
        self.assertEqual(shorts, ["S10USDT", "S11USDT", "S12USDT"])       # S00..S09 are outside the top 50 by volume
        self.assertEqual(n, 50)

    def test_pick_needs_thirty_eligible_names_and_breaks_ties_by_symbol(self):
        self.assertIsNone(rule.pick(rule.cross_section(world(29), DAY_MS, D)))
        f = {f"T{i:02d}USDT": bars(sig=0.01, vol=1.0 + i) for i in range(40)}
        longs, shorts, _ = rule.pick(rule.cross_section(f, DAY_MS, D))
        self.assertEqual(shorts, ["T00USDT", "T01USDT", "T02USDT"])
        self.assertEqual(set(longs), {"T39USDT", "T38USDT", "T37USDT"})


class Money(unittest.TestCase):
    def test_book_return_longs_pay_funding_and_shorts_receive_it(self):
        L = [{"ret": 0.02, "fund": 0.0003}, {"ret": 0.04, "fund": 0.0001}]
        S = [{"ret": -0.01, "fund": 0.0002}, {"ret": -0.03, "fund": 0.0002}]
        price, fund = rule.book_return(L, S)
        self.assertAlmostEqual(price, 0.03 + 0.02)
        self.assertAlmostEqual(fund, 0.0002 - 0.0002)

    def test_costs(self):
        self.assertAlmostEqual(rule.api_cost(1), 0.0034)
        self.assertAlmostEqual(rule.api_cost(3), 0.0102)
        self.assertAlmostEqual(rule.leg_cost(0.0002, 0.0001, 0.0003), 0.0008)
        self.assertAlmostEqual(rule.web_cost([0.0008, 0.0010], [0.0006]), 0.0009 + 0.0006)

    def test_summary_and_verdict(self):
        days = [DAY_MS + i * DAY for i in range(30)]
        nets = [0.01 if i % 2 else -0.004 for i in range(30)]
        s = rule.summarize(days, nets, [x - 0.001 for x in nets])
        self.assertEqual(s["n"], 30)
        self.assertAlmostEqual(s["mean"], 0.003)
        self.assertIsNotNone(s["t"])
        self.assertIsNotNone(s["mean_wo_best"])
        self.assertEqual(rule.verdict(s), "pending (30 of 500 scored)")
        self.assertEqual(rule.verdict({**s, "n": 130, "mean": -0.01, "t": -1.5}), "NULL (futility at 125)")
        full = {**s, "n": 500, "t": 2.4, "mean_2x": 0.001, "mean_wo_best": 0.0005}
        self.assertEqual(rule.verdict(full), "PASS")
        self.assertEqual(rule.verdict({**full, "mean_wo_best": -0.0001}), "NULL")
        self.assertEqual(rule.verdict({**full, "t": 1.9}), "NULL")

    def test_decision_is_read_once_and_kept(self):
        rng = np.random.default_rng(7)
        days = [DAY_MS + i * DAY for i in range(520)]
        bad = list(rng.normal(-0.02, 0.01, 125))            # the first 125 days: clearly negative, t well below -1
        good = list(rng.normal(0.05, 0.01, 395))            # then a recovery that would flip a live reading
        nets = bad + good
        two = [x - 0.001 for x in nets]
        s, v = rule.decision(days[:130], nets[:130], two[:130])
        self.assertEqual((s["n"], v), (125, "NULL (futility at 125)"))
        s, v = rule.decision(days[:400], nets[:400], two[:400])
        self.assertEqual((s["n"], v), (125, "NULL (futility at 125)"))
        s, v = rule.decision(days, nets, two)                # the stop at day 125 stands at day 520 too
        self.assertEqual((s["n"], v), (125, "NULL (futility at 125)"))
        s, v = rule.decision(days[:100], nets[:100], two[:100])
        self.assertEqual((s["n"], v), (100, "pending (100 of 500 scored)"))
        order = rng.permutation(130)                         # the order the rows arrive in does not matter
        shuf = rule.decision([days[i] for i in order], [nets[i] for i in order], [two[i] for i in order])
        self.assertEqual(shuf[1], "NULL (futility at 125)")

    def test_day_500_is_read_on_the_first_500_days_only(self):
        rng = np.random.default_rng(11)
        days = [DAY_MS + i * DAY for i in range(620)]
        nets = list(rng.normal(0.004, 0.02, 500)) + [-0.5] * 120
        s, v = rule.decision(days[:499], nets[:499], [x - 0.002 for x in nets[:499]])
        self.assertEqual((s["n"], v), (499, "pending (499 of 500 scored)"))
        s, v = rule.decision(days, nets, [x - 0.002 for x in nets])
        self.assertEqual((s["n"], v), (500, "PASS"))

    def test_a_positive_book_passes_at_500_and_extra_days_do_nothing(self):
        rng = np.random.default_rng(3)
        days = [DAY_MS + i * DAY for i in range(620)]
        nets = list(rng.normal(0.004, 0.02, 500)) + [-0.5] * 120
        two = [x - 0.002 for x in nets]
        s, v = rule.decision(days, nets, two)
        self.assertEqual((s["n"], v), (500, "PASS"))

    def test_empty_summary_has_no_numbers(self):
        s = rule.summarize([], [])
        self.assertEqual((s["n"], s["mean"], s["t"]), (0, None, None))
        self.assertEqual(rule.verdict(s), "pending (0 of 500 scored)")


class Lane(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = Path(self.tmp.name) / "journal"
        fu._warmed.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def tick(self, now, frames=None, tbl=None):
        with mock.patch.object(fu, "fetch_frames", return_value=frames if frames is not None else world()), \
                mock.patch.object(fu, "mexc_table", return_value=tbl if tbl is not None else table()), \
                mock.patch.object(fu, "bulk_quotes", return_value={"S39_USDT": (99.0, 101.0)}):
            return fu.tick(now, journal=self.j)

    def test_one_ticket_with_both_books_is_written_once_and_in_the_window(self):
        self.tick(D - 10 * MIN)                                   # too early to do anything
        self.assertEqual(fu.read("tickets", self.j), [])
        self.tick(D - 3 * MIN)                                    # inside the warm-up window, still no ticket
        self.assertEqual(fu.read("tickets", self.j), [])
        self.tick(D + 1000)                                       # the bar that closed at D needs a moment
        self.assertEqual(fu.read("tickets", self.j), [])
        s = self.tick(D + 20_000)
        t = fu.read("tickets", self.j)
        self.assertEqual([(r["ticket"], r["status"], r["n_b"], r["n_m"]) for r in t], [("U20261029", "ok", "50", "40")])
        self.assertEqual(float(t[0]["late_s"]), 20.0)
        legs = fu.read("legs", self.j)
        self.assertEqual(len(legs), 12)
        b = [(r["side"], r["symbol"]) for r in legs if r["book"] == "B"]
        self.assertEqual(b[:3], [("long", "S59USDT"), ("long", "S58USDT"), ("long", "S57USDT")])
        m = [r for r in legs if r["book"] == "M"]
        self.assertEqual([r["symbol"] for r in m if r["side"] == "long"], ["S39USDT", "S38USDT", "S37USDT"])
        self.assertEqual({r["contract"] for r in m}, {"S39_USDT", "S38_USDT", "S37_USDT", "S00_USDT", "S01_USDT", "S02_USDT"})
        self.assertEqual(len(fu.read("signals", self.j)), 50)
        self.tick(D + 50_000)
        self.assertEqual(len(fu.read("tickets", self.j)), 1)
        self.assertEqual(len(fu.read("legs", self.j)), 12)
        self.assertEqual(s["tickets"], 1)

    def test_a_late_start_is_a_missed_row_and_a_stale_cache_is_retried(self):
        self.tick(D + rule.TICKET_DEADLINE_MS + 1000)
        t = fu.read("tickets", self.j)
        self.assertEqual([(r["ticket"], r["status"]) for r in t], [("U20261029", "missed")])
        self.tick(D + rule.TICKET_DEADLINE_MS + 5000)
        self.assertEqual(len(fu.read("tickets", self.j)), 1)
        self.assertEqual(fu.read("legs", self.j), [])
        other = Path(self.tmp.name) / "other"
        stale = {s: b[b.t < D - H] for s, b in world().items()}
        with mock.patch.object(fu, "fetch_frames", return_value=stale), mock.patch.object(fu, "mexc_table", return_value=table()):
            fu.tick(D + 10_000, journal=other)
        self.assertEqual(fu.read("tickets", other), [])

    def test_too_few_mexc_coins_is_a_ticket_without_book_m(self):
        self.tick(D + 10_000, tbl=table(20))
        t = fu.read("tickets", self.j)[0]
        self.assertEqual(t["status"], "no_book_m")
        legs = fu.read("legs", self.j)
        self.assertEqual({r["book"] for r in legs}, {"B"})

    def test_days_before_the_start_are_not_ticketed(self):
        old = ms("2026-10-28")
        self.tick(rule.decision_ms(old) + 10_000)
        self.assertEqual(fu.read("tickets", self.j), [])

    def test_journals_refuse_a_column_outside_their_header(self):
        with self.assertRaises(ValueError):
            fu.append("skipped", [{"ticket": "x", "book": "B", "reason": "r", "detail": "d", "noted_at": "t", "extra": 1}],
                      self.j)


class Scoring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = Path(self.tmp.name) / "journal"
        fu._warmed.clear()
        with mock.patch.object(fu, "fetch_frames", return_value=world()), mock.patch.object(fu, "mexc_table", return_value=table()), \
                mock.patch.object(fu, "bulk_quotes", return_value={}):
            fu.tick(D + 10_000, journal=self.j)
        self.X = DAY_MS + DAY
        self.ticket = fu.read("tickets", self.j)[0]
        self.legs = fu.read("legs", self.j)

    def tearDown(self):
        self.tmp.cleanup()

    def bars_of(self, sym, a, b):
        leg = next(x for x in self.legs if x["book"] == "B" and x["symbol"] == sym)
        r = 0.01 if leg["side"] == "long" else -0.01
        t = np.arange(a, b, H)
        c = float(leg["c_e"]) * (1 + r)
        return pd.DataFrame({"t": t, "close": np.where(t == b - H, c, 100.0), "quote_volume": 1.0})

    def funding_b(self, sym, a, b):
        leg = next(x for x in self.legs if x["book"] == "B" and x["symbol"] == sym)
        return pd.DataFrame({"t": [a + 2 * H, b - 1 * H, b], "rate": [0.0002 if leg["side"] == "long" else 0.0001] * 2 + [0.5]}
                            ).query("t < @b")

    def open_at(self, c, m):
        short = c in ("S00_USDT", "S01_USDT", "S02_USDT")
        if m < self.X:
            return D + 3 * MIN, 100.0
        return self.X + 3 * MIN, 99.0 if short else 101.0

    def test_both_books_net_of_their_own_costs(self):
        now = self.X + 30 * MIN
        res, err = fu.score_ticket(now, self.ticket, self.legs, bars_of=self.bars_of, funding_b=self.funding_b,
                                   open_at=self.open_at,
                                   funding_m=lambda c, a, b: pd.DataFrame({"t": [a], "rate": [0.0001]}),
                                   spread_of=lambda m, c: 0.0002)
        self.assertEqual(err, "")
        out, skipped = res
        self.assertEqual(skipped, [])
        b, m = {r["book"]: r for r in out}["B"], {r["book"]: r for r in out}["M"]
        self.assertAlmostEqual(b["price"], 0.02)
        self.assertAlmostEqual(b["funding"], 0.0002 - 0.0004)                  # two settlements: shorts get 2 x 1 bp, longs pay 2 x 2 bp
        self.assertAlmostEqual(b["cost_1x"], 0.0034)
        self.assertAlmostEqual(b["net_2x"], b["gross"] - 2 * 0.0034)
        self.assertAlmostEqual(m["price"], 0.02)
        self.assertAlmostEqual(m["funding"], 0.0)                              # same rate both sides
        self.assertAlmostEqual(m["cost_1x"], 0.0016)                           # 2 x 2 bp fee + 2 x 2 bp half-spread, a side, 2 sides
        self.assertAlmostEqual(m["net_3x"], m["gross"] - 3 * 0.0016)
        self.assertEqual(m["stopped"], 0)

    def test_a_missing_minute_bar_skips_book_m_only(self):
        now = self.X + 30 * MIN
        res, err = fu.score_ticket(now, self.ticket, self.legs, bars_of=self.bars_of, funding_b=self.funding_b,
                                   open_at=lambda c, m: (None, None), funding_m=lambda c, a, b: pd.DataFrame(columns=["t", "rate"]),
                                   spread_of=lambda m, c: None)
        out, skipped = res
        self.assertEqual([r["book"] for r in out], ["B"])
        self.assertEqual([(r["book"], r["reason"]) for r in skipped], [("M", "unpriced")])

    def test_a_data_error_defers_the_whole_ticket(self):
        def boom(*a):
            raise OSError("network down")
        res, err = fu.score_ticket(self.X + 30 * MIN, self.ticket, self.legs, bars_of=boom)
        self.assertIsNone(res)
        self.assertIn("network down", err)

    def test_a_coin_that_stops_trading_exits_at_entry_and_missing_spread_uses_the_fallback(self):
        dead = lambda sym, a, b: pd.DataFrame({"t": np.arange(a, b, H), "close": 50.0, "quote_volume": 0.0})
        res, _ = fu.score_ticket(self.X + 30 * MIN, self.ticket, self.legs, bars_of=dead, funding_b=lambda s, a, b: pd.DataFrame(columns=["t", "rate"]),
                                 open_at=self.open_at, funding_m=lambda c, a, b: pd.DataFrame(columns=["t", "rate"]),
                                 spread_of=lambda m, c: None)
        r = {x["book"]: x for x in res[0]}
        self.assertEqual(r["B"]["stopped"], 6)
        self.assertAlmostEqual(r["B"]["price"], 0.0)
        self.assertEqual(r["M"]["spread_flag"], True)
        self.assertAlmostEqual(r["M"]["cost_1x"], 2 * (2 * 0.0002 + 2 * rule.SPREAD_FALLBACK))

    def test_tick_scores_once_after_the_exit_and_status_reports_book_m(self):
        patches = dict(default_bars=self.bars_of, default_funding_b=self.funding_b, default_funding_m=lambda c, a, b: pd.DataFrame(columns=["t", "rate"]))
        with mock.patch.object(fu, "fetch_frames", return_value=world()), mock.patch.object(fu, "mexc_table", return_value=table()), \
                mock.patch.object(fu, "mexc_open", side_effect=self.open_at), mock.patch.object(fu, "half_spread", return_value=0.0002), \
                mock.patch.object(fu, "bulk_quotes", return_value={}):
            early = fu.tick(self.X + 5 * MIN, journal=self.j)
            self.assertEqual(early["scored"], 0)
            self.assertEqual(early["open"], 1)
            with mock.patch.object(fu, "score_ticket", wraps=lambda *a, **k: fu.score_ticket.__wrapped__(*a, **k)) if False else mock.patch.object(fu, "live", mock.MagicMock()):
                pass
        # call score_ticket directly through tick with the injected sources
        orig = fu.score_ticket
        with mock.patch.object(fu, "score_ticket", side_effect=lambda now, t, legs, journal=None: orig(
                now, t, legs, bars_of=self.bars_of, funding_b=self.funding_b, open_at=self.open_at,
                funding_m=lambda c, a, b: pd.DataFrame(columns=["t", "rate"]), spread_of=lambda m, c: 0.0002)):
            s = fu.tick(self.X + 30 * MIN, journal=self.j)
            again = fu.tick(self.X + 60 * MIN, journal=self.j)
        self.assertEqual(s["scored"], 1)
        self.assertEqual(s["open"], 0)
        self.assertEqual(len(fu.read("scored", self.j)), 2)
        self.assertEqual(again["scored"], 1)
        self.assertEqual(len(fu.read("scored", self.j)), 2)
        self.assertEqual(s["decision"], "pending (1 of 500 scored)")
        self.assertAlmostEqual(s["book_m"]["mean"], s["mean_net"], places=6)
        self.assertTrue((self.j / "status.json").exists())


if __name__ == "__main__":
    unittest.main()
