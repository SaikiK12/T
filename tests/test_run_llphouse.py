"""scripts/run_llphouse.py (R484): prior-only thresholds, the t+1 trade window, book signs, costs and funding sign."""
import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_llphouse", ROOT / "scripts" / "run_llphouse.py")
lh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lh)
DAY, HOUR = lh.DAY, lh.HOUR


def prices_from(returns, first="2025-01-16", hour=20):
    """Share prices stamped at `hour` UTC each day, starting at 1.0 on `first`, then compounding `returns`."""
    t0 = lh.rx.ms(first) + hour * HOUR
    v = np.cumprod(np.r_[1.0, 1 + np.asarray(returns, float)])
    return pd.Series(v, index=[t0 + i * DAY for i in range(len(v))])


def candles(days, opens, closes):
    df = pd.DataFrame({"open_ms": [lh.rx.ms(d) for d in days], "open": opens, "close": closes})
    return lh.frame_by_day(df)


class TestThreshold(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.r = rng.normal(0.001, 0.01, 200)
        self.sig = lh.llp_signals(prices_from(self.r))

    def test_threshold_is_the_prior_90_days_only(self):
        i = 120                                  # signal row i holds return r[i]
        row = self.sig.iloc[i]
        prior = self.r[i - lh.LOOKBACK:i]
        self.assertEqual(row.n_prior, 90)
        self.assertAlmostEqual(row.p_lo, np.percentile(prior, 10), places=12)
        self.assertAlmostEqual(row.p_hi, np.percentile(prior, 90), places=12)

    def test_own_and_future_returns_do_not_move_the_threshold(self):
        r2 = self.r.copy()
        r2[120:] = -0.5                          # day 120 itself and every later day
        sig2 = lh.llp_signals(prices_from(r2))
        self.assertAlmostEqual(sig2.p_lo.iloc[120], self.sig.p_lo.iloc[120], places=12)
        self.assertAlmostEqual(sig2.p_hi.iloc[120], self.sig.p_hi.iloc[120], places=12)
        self.assertEqual(sig2.kind.iloc[120], "loss")

    def test_classification_and_minimum_history(self):
        r = np.full(100, 0.001)
        r[np.arange(0, 100, 7)] = 0.0             # spread so the 10th percentile sits below 0.001
        r[95] = -0.02
        r[96] = 0.02
        sig = lh.llp_signals(prices_from(r))
        self.assertEqual(sig.kind.iloc[95], "loss")
        self.assertEqual(sig.kind.iloc[96], "win")
        self.assertTrue(np.isnan(sig.p_lo.iloc[lh.MIN_PRIOR - 1]))          # 59 prior returns
        self.assertFalse(np.isnan(sig.p_lo.iloc[lh.MIN_PRIOR]))             # 60
        self.assertEqual(lh.first_signal_day(sig), sig.day.iloc[lh.LOOKBACK])


class TestTrade(unittest.TestCase):
    def setUp(self):
        self.days = ["2025-05-01", "2025-05-02", "2025-05-03"]
        self.cd = candles(self.days, [100.0, 100.0, 110.0], [100.0, 105.0, 121.0])
        self.fund = pd.Series(dtype=float)

    def test_window_is_day_t_plus_1_open_to_close(self):
        row = lh.trade_row("2025-05-02", self.cd, self.fund)
        self.assertEqual(row["trade_day"], "2025-05-03")
        self.assertEqual(row["open_ms"], lh.rx.ms("2025-05-03"))
        self.assertAlmostEqual(row["dir_ret"], 0.05)          # day t close-to-close: 105 / 100
        self.assertEqual(row["d"], 1)
        self.assertAlmostEqual(row["move"], 0.10)             # day t+1 open-to-close: 121 / 110
        self.assertIsNone(lh.trade_row("2025-05-03", self.cd, self.fund))   # no t+1 bar

    def test_trade_opens_after_the_stamp(self):
        r = np.full(100, 0.001)
        sig = lh.llp_signals(prices_from(r, first="2025-01-16", hour=21))
        day = sig.day.iloc[95]
        t0 = lh.rx.ms(day)
        cd = candles([lh.rx.day_label(t0 + k * DAY) for k in (-1, 0, 1)], [1.0, 1.0, 1.0], [1.0, 1.01, 1.02])
        ev, pool = lh.build(sig, cd, self.fund, day, day, "BTC")
        self.assertEqual(len(pool), 1)
        self.assertLess(pool.stamp_ms.iloc[0], pool.open_ms.iloc[0])
        self.assertEqual(pool.stamp_hour.iloc[0], 21)
        bad = candles([lh.rx.day_label(t0 + k * DAY) for k in (-1, 0, 1)], [1.0, 1.0, 1.0], [1.0, 1.01, 1.02])
        bad.loc[lh.rx.day_label(t0 + DAY), "open_ms"] = t0 + 20 * HOUR       # a bar opening before the stamp
        with self.assertRaises(ValueError):
            lh.trade_row(day, bad, self.fund)

    def test_book_signs_and_cost_scaling(self):
        n = lh.book_nets(1, 0.10, 0.0)
        self.assertAlmostEqual(n["F_net_1x"], 0.10 - 0.0013)
        self.assertAlmostEqual(n["R_net_1x"], -0.10 - 0.0013)
        self.assertAlmostEqual(n["F_net_2x"], 0.10 - 0.0026)
        self.assertAlmostEqual(n["F_net_3x"], 0.10 - 0.0039)
        m = lh.book_nets(-1, 0.10, 0.0)
        self.assertAlmostEqual(m["F_net_1x"], -0.10 - 0.0013)
        self.assertAlmostEqual(m["R_net_1x"], 0.10 - 0.0013)
        self.assertAlmostEqual(lh.COST_RT, 0.0013)

    def test_funding_sign_longs_pay_positive(self):
        n = lh.book_nets(1, 0.0, 0.001)          # F is long, R short; positive funding
        self.assertAlmostEqual(n["F_fund"], -0.001)
        self.assertAlmostEqual(n["R_fund"], 0.001)
        self.assertAlmostEqual(n["F_net_1x"], -0.001 - 0.0013)

    def test_held_funding_counts_hours_in_the_held_day(self):
        o = lh.rx.ms("2025-05-03")
        hours = [o + k * HOUR for k in range(0, 26)]          # 00:00 of t+1 through 01:00 of t+2
        fund = pd.Series(1.0, index=hours)
        s, h = lh.held_funding(fund, o)
        self.assertEqual(h, 24)                               # 01:00 .. 24:00
        self.assertEqual(s, 24.0)


class TestStats(unittest.TestCase):
    def test_placebo_and_decision(self):
        pool = np.r_[np.full(50, -0.001), np.full(50, 0.001)]
        pl = lh.placebo(pool, 30, 0.01, reps=200)
        self.assertEqual(pl["pctile"], 100.0)
        rep = {"1x": lh.mean_t(np.full(40, 0.01) + np.linspace(-1e-3, 1e-3, 40)),
               "2x": {"mean": 0.008}, "placebo_1x": pl}
        self.assertEqual(lh.decide(rep), "EARNED")
        rep["1x"] = lh.mean_t(np.linspace(-1e-3, 1e-3, 20) + 0.01)
        self.assertEqual(lh.decide(rep), "NULL")              # fewer than 30 events

    def test_block_bootstrap_brackets_the_mean(self):
        x = np.random.default_rng(3).normal(0.01, 0.001, 60)
        b = lh.block_bootstrap(x, reps=500)
        self.assertLess(b["lo"], x.mean())
        self.assertGreater(b["hi"], x.mean())
        self.assertEqual(b["p_le_0"], 0.0)


if __name__ == "__main__":
    unittest.main()
