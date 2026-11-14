"""R349 minflow_v1: loading without 2020, thresholds from past hours only, signals, trade timing, ticks, funding and
the family's decision, on invented bars."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_minflow as mf

D0 = mf.ms("2021-01-01")


def bars_from(close, open_=None, volume=None, tbv=None, high=None, low=None):
    close = np.asarray(close, float)
    open_ = close.copy() if open_ is None else np.asarray(open_, float)
    volume = np.full(len(close), 10.0) if volume is None else np.asarray(volume, float)
    tbv = volume / 2 if tbv is None else np.asarray(tbv, float)
    high = np.maximum(open_, close) if high is None else np.asarray(high, float)
    low = np.minimum(open_, close) if low is None else np.asarray(low, float)
    return {"open": open_, "high": high, "low": low, "close": close, "volume": volume, "tbv": tbv}


class Load(unittest.TestCase):
    def test_2020_rows_never_reach_the_grid_and_invalid_bars_are_nan(self):
        t = np.array([mf.ms("2020-12-31") + 59 * 60_000, D0, D0 + 60_000, D0 + 120_000], dtype=np.int64)
        k = pd.DataFrame({"t": t, "open": [1.0, 2, 3, 4], "high": [1.0, 2, 3, 4], "low": [1.0, 2, 3, 4],
                          "close": [9.0, 2, 3, 4], "volume": 1.0, "quote_volume": 1.0, "count": [5, 5, 0, 5],
                          "taker_buy_volume": 0.5, "taker_buy_quote_volume": 0.5})
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "X.parquet"
            k.to_parquet(p, row_group_size=2)
            b = mf.load_bars(p, D0, D0 + 4 * 60_000)
            f = pd.DataFrame({"t": [mf.ms("2020-12-31"), D0 + 8 * 3_600_000 + 7], "interval_h": 8, "rate": [0.5, 0.01]})
            f.to_parquet(Path(tmp) / "F.parquet")
            F, rate = mf.load_funding(Path(tmp) / "F.parquet", D0, D0 + 86_400_000)
        np.testing.assert_array_equal(b["close"][[0, 2]], [2.0, 4.0])
        self.assertTrue(np.isnan(b["close"][1]))            # count 0
        self.assertTrue(np.isnan(b["close"][3]))            # no row
        self.assertNotIn(9.0, b["close"])                   # the 2020 bar
        np.testing.assert_array_equal(F, [D0 + 8 * 3_600_000])
        np.testing.assert_array_equal(rate, [0.01])


class Statistics(unittest.TestCase):
    def test_kret_and_kflow(self):
        c = np.array([100.0, 101, np.nan, 103, 104])
        r = mf.kret(c, 1)
        self.assertAlmostEqual(r[1], np.log(1.01))
        self.assertTrue(np.isnan(r[2]) and np.isnan(r[3]))
        self.assertAlmostEqual(mf.kret(c, 3)[4], np.log(104 / 101))
        d = np.array([1.0, 2, np.nan, 4, 5])
        f = mf.kflow(d, 2)
        self.assertEqual(f[1], 3.0)
        self.assertTrue(np.isnan(f[2]) and np.isnan(f[3]))
        self.assertEqual(f[4], 9.0)

    def test_an_hours_threshold_uses_only_the_hours_before_it(self):
        x = np.ones(60 * 10)
        x[60 * 5: 60 * 6] = 1000.0                         # hour 5 is wild
        thr = mf.hourly_quantile(x, q=0.995, win_h=3, min_n=60)
        self.assertEqual(thr[5], 1.0)                      # hours 2-4 only
        self.assertEqual(thr[6], 1000.0)                   # hour 5 now in the past window
        self.assertTrue(np.isnan(thr[0]))                  # nothing before hour 0
        self.assertEqual(len(mf.per_bar(thr, 600)), 600)
        self.assertEqual(mf.per_bar(thr, 600)[5 * 60 + 59], 1.0)

    def test_hourly_beta_recovers_the_slope_from_past_bars(self):
        rng = np.random.default_rng(1)
        x = rng.normal(0, 1, 60 * 30)
        y = 1.5 * x + rng.normal(0, 0.01, len(x))
        y[60 * 20:] = -2 * x[60 * 20:]                     # the slope changes at hour 20
        b = mf.hourly_beta(x, y, win_h=5, min_n=200)
        self.assertAlmostEqual(b[10], 1.5, places=2)
        self.assertAlmostEqual(b[20], 1.5, places=2)       # hour 20's own bars are not used
        self.assertAlmostEqual(b[25], -2.0, places=2)

    def test_fire(self):
        s = np.array([0.5, -3.0, 3.0, np.nan, 2.0, 0.0])
        thr = np.array([1.0, 2.0, 2.0, 1.0, np.nan, 0.0])
        np.testing.assert_array_equal(mf.fire(s, thr), [0, -1, 1, 0, 0, 0])

    def test_month_ticks(self):
        n = 3 * 1440
        close = 100 + 0.5 * np.round(np.random.default_rng(2).normal(0, 4, n))
        t = mf.month_ticks(bars_from(close))
        self.assertTrue(np.allclose(t, 0.5))


class Trades(unittest.TestCase):
    def test_entry_next_open_exit_h_later_half_tick_against_and_one_position_at_a_time(self):
        n = 40
        close = 100.0 + np.arange(n)
        open_ = close - 0.5
        b = bars_from(close, open_)
        tick = np.full(n, 0.2)
        sig = np.zeros(n, np.int8)
        sig[[3, 5, 9, 20]] = [1, 1, -1, 1]                 # 5 falls inside the first trade
        t = mf.trades(b, tick, np.array([], np.int64), np.array([]), sig, h=5)
        np.testing.assert_array_equal(t.i, [3, 9, 20])
        r0 = t.iloc[0]
        self.assertAlmostEqual(r0.pe, open_[4] + 0.1)      # long: pays half a tick more
        self.assertAlmostEqual(r0.px, close[8] - 0.1)      # exit at the close of bar 3 + 5
        self.assertEqual(r0.te, D0 + 4 * 60_000)
        self.assertEqual(r0.tx, D0 + 9 * 60_000)           # five minutes of holding
        r1 = t.iloc[1]                                     # short from bar 9 (bar 8 was the first's exit)
        self.assertAlmostEqual(r1.pe, open_[10] - 0.1)
        self.assertAlmostEqual(r1.gross, -1 * ((close[14] + 0.1) / (open_[10] - 0.1) - 1))
        late = mf.trades(b, tick, np.array([], np.int64), np.array([]), sig, h=5, delay=1)
        self.assertAlmostEqual(late.iloc[0].pe, close[4] + 0.1)
        self.assertAlmostEqual(late.iloc[0].px, close[9] - 0.1)
        self.assertEqual(late.iloc[0].te, D0 + 5 * 60_000)

    def test_a_trade_with_a_missing_price_is_skipped_and_blocks_nothing(self):
        n = 30
        b = bars_from(100.0 + np.arange(n))
        b["close"][8] = np.nan                              # the exit of a signal at bar 3 with h 5
        sig = np.zeros(n, np.int8)
        sig[[3, 4]] = 1
        t = mf.trades(b, np.zeros(n), np.array([], np.int64), np.array([]), sig, h=5)
        np.testing.assert_array_equal(t.i, [4])

    def test_funding_inside_the_hold_is_paid_by_a_long_and_received_by_a_short(self):
        n = 600
        b = bars_from(np.full(n, 100.0))
        sig = np.zeros(n, np.int8)
        sig[[100, 300]] = [1, -1]
        F = np.array([D0 + 130 * 60_000, D0 + 400 * 60_000], np.int64)
        t = mf.trades(b, np.zeros(n), F, np.array([0.001, 0.002]), sig, h=60)
        self.assertAlmostEqual(t.fund.iloc[0], 0.001)      # long across a +0.1% settlement pays it
        self.assertAlmostEqual(t.fund.iloc[1], 0.0)        # the short exits at 361, before 400
        net = mf.net(t, 0.25)
        self.assertAlmostEqual(net[0], -0.001 - 0.5e-4)


class Signals(unittest.TestCase):
    def test_keys_and_the_lead_rule_buys_an_alt_that_lagged_btc(self):
        n = 60 * 24 * 6 + 600
        rng = np.random.default_rng(3)
        rb = rng.normal(0, 1e-4, n)
        btc_close = 100 * np.exp(np.cumsum(rb))
        alt_close = 50 * np.exp(np.cumsum(rb + rng.normal(0, 2e-5, n)))
        jump = n - 300
        btc_close[jump:] *= 1.01                           # BTC jumps 1% in one minute; the alt stays
        btc = bars_from(btc_close)
        alt = bars_from(alt_close)
        r = {k: mf.kret(btc_close, k) for k in mf.KS}
        sig = mf.coin_signals(alt, {"close": btc_close, "r": r, "thr": {k: mf.hourly_quantile(r[k]) for k in mf.KS}})
        self.assertEqual(sig["lead_k1"][jump], 1)          # buy the alt
        self.assertEqual(sorted(k for k in sig if not k.startswith("lead")),
                         sorted(mf.coin_signals(btc).keys()))
        names = mf.variant_names()
        self.assertEqual(len(names), mf.TRIALS)
        self.assertEqual(mf.TRIALS, 57)
        self.assertEqual({n.rsplit("_h", 1)[0] for n in names}, set(sig))

    def test_a_planted_reversal_is_booked_by_the_fade_and_lost_by_the_follow(self):
        n = 60 * 24 * 8
        rng = np.random.default_rng(4)
        r = rng.normal(0, 1e-4, n)
        shock = np.arange(60 * 24 * 6, n - 100, 97)
        r[shock] += np.where(rng.random(len(shock)) < 0.5, 1, -1) * 2e-3
        r[shock + 2] -= r[shock] * 0.5                      # half of each shock comes back two minutes later
        close = 100 * np.exp(np.cumsum(r))
        b = bars_from(close, np.r_[close[0], close[:-1]])
        sig = mf.coin_signals(b)
        fade = mf.trades(b, np.zeros(n), np.array([], np.int64), np.array([]), sig["ret_fade_k1"], h=5)
        follow = mf.trades(b, np.zeros(n), np.array([], np.int64), np.array([]), sig["ret_follow_k1"], h=5)
        self.assertGreater(len(fade), 10)
        self.assertGreater(fade.gross.mean(), 5e-4)
        self.assertLess(follow.gross.mean(), -5e-4)


class Decision(unittest.TestCase):
    def test_reality_check_and_pass_rule(self):
        n_days = (mf.T1 - mf.T0) // mf.DAY
        rng = np.random.default_rng(5)
        names = ["a", "b", "c"]
        noise = {v: rng.normal(0, 1e-3, n_days) for v in names}
        dec = mf.decide(names, noise, noise, n_days, seed=1)
        self.assertGreater(dec["rc_p"], 0.05)
        self.assertFalse(dec["pass"])
        strong = dict(noise)
        strong["b"] = noise["b"] + 5e-4
        dec = mf.decide(names, strong, strong, n_days, seed=1)
        self.assertEqual(dec["best"], "b")
        self.assertLess(dec["rc_p"], 0.01)
        self.assertGreater(dec["valid_t1"], 2)
        self.assertTrue(dec["pass"])
        weak2x = dict(strong)
        weak2x["b"] = strong["b"] - 1e-3                   # positive at 1x, negative at 2x
        dec = mf.decide(names, strong, weak2x, n_days, seed=1)
        self.assertFalse(dec["pass"])

    def test_book_divides_each_coin_by_three_and_charges_its_walk(self):
        t = pd.DataFrame({"gross": [0.001, 0.002], "fund": [0.0, 0.0], "day": [0, 0]})
        x = mf.book({"BTCUSDT": t}, 3)
        self.assertAlmostEqual(x[0], (0.003 - 4 * mf.WALK_BP["BTCUSDT"] / 1e4) / 3)
        x = mf.book({"BTCUSDT": t}, 3, mult=2)
        self.assertAlmostEqual(x[0], (0.003 - 8 * mf.WALK_BP["BTCUSDT"] / 1e4) / 3)
        x = mf.book({"BTCUSDT": t}, 3, cost=3.0)
        self.assertAlmostEqual(x[0], (0.003 - 12 / 1e4) / 3)


if __name__ == "__main__":
    unittest.main()
