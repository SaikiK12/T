"""er_v1 runner (scripts/run_effratio.py) on synthetic minute closes: the daily path and features see nothing after
the day they describe, the gate for a day uses the forecast made the evening before, a planted persistent trend-day
regime is found out of sample, and an iid regime is not."""
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_effratio as re_

T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
DAY = 86_400_000
WINDOWS = dict(DISC=("2021-04-20", "2021-12-31"), VALID=("2022-01-01", "2022-08-31"),
               HALVES=(("2022-01-01", "2022-04-30"), ("2022-05-01", "2022-08-31")))


def synth(days=610, persist=0.9, seed=0):
    """Minute closes for one coin. Each day is a trend day or a chop day; the state repeats with probability
    `persist`. Trend days drift all day in a random direction; chop days drift for the first hour and give it back by
    the close. Noise 1e-4 a minute."""
    rng = np.random.default_rng(seed)
    trend = np.empty(days, bool)
    trend[0] = True
    for i in range(1, days):
        trend[i] = trend[i - 1] if rng.random() < persist else not trend[i - 1]
    q = rng.choice([-1.0, 1.0], days)
    mu = np.empty((days, 1440))
    for i in range(days):
        if trend[i]:
            mu[i] = q[i] * 8e-6
        else:
            mu[i, :60] = q[i] * 8e-6
            mu[i, 60:] = -q[i] * 8e-6 * 60 / 1380
    r = mu.ravel() + rng.normal(0, 1e-4, days * 1440)
    return 100 * np.exp(np.cumsum(r)), trend


def funding(days, rate=1e-4):
    F = T0 + np.arange(1, days * 3 + 1) * 8 * 3_600_000
    return F.astype(np.int64), np.full(len(F), rate)


def run(persist, seed):
    days = 610
    dailies, fundings, regimes = {}, {}, {}
    for k, c in enumerate(re_.COINS):
        C, trend = synth(days, persist, seed + k)
        dailies[c] = re_.daily(C, t0=T0)
        fundings[c] = funding(days)
        regimes[c] = trend
    with mock.patch.multiple(re_, B=200, **WINDOWS):
        return re_.analyze(dailies, fundings), dailies, fundings, regimes


class RunEffratioTest(unittest.TestCase):
    def test_daily_path_and_prices(self):
        C = 100 * np.exp(np.cumsum(np.full(3 * 1440, 1e-5)))
        d = re_.daily(C, t0=T0)
        self.assertAlmostEqual(d.er[0], 1.0, places=9)          # day 0 lacks its first step: 287 of 288 is enough
        self.assertAlmostEqual(d.er[1], 1.0, places=9)          # a straight line is fully efficient
        self.assertEqual(d.p0[1], C[1439])                      # P(00:00) = the close of the 23:59 bar
        self.assertEqual(d.p1[1], C[1440 + 59])                 # P(01:00)
        self.assertEqual(d.entry[1], C[1440 + 60])              # P(01:01)
        self.assertEqual(d.exit[1], C[2 * 1440 - 1])            # P(24:00)
        zig = 100 * np.exp(np.tile([0.0, 1e-3], 2 * 720))
        self.assertLess(re_.daily(zig, t0=T0).er[1], 0.01)

    def test_features_do_not_see_later_days(self):
        C, _ = synth(260, seed=3)
        k = 200
        C2 = C.copy()
        C2[k * 1440:] *= np.exp(np.random.default_rng(9).normal(0, 0.01, len(C) - k * 1440))
        f1, f2 = re_.features(re_.daily(C, T0)), re_.features(re_.daily(C2, T0))
        cols = re_.FEATURES
        np.testing.assert_array_equal(f1[cols].values[:k], f2[cols].values[:k])
        self.assertFalse(np.allclose(f1[cols].values[k], f2[cols].values[k], equal_nan=True))
        self.assertNotEqual(f1.er_next[k - 1], f2.er_next[k - 1])   # the target is the next day

    def test_rule_side_entry_and_funding(self):
        C, _ = synth(30, seed=4)
        d = re_.daily(C, T0)
        F, rate = funding(30)
        tr = re_.rule_trades(d, F, rate)
        i = 10
        side = np.sign(C[i * 1440 + 59] - C[i * 1440 - 1])
        self.assertAlmostEqual(tr.gross[i], side * (C[i * 1440 + 1439] / C[i * 1440 + 60] - 1), places=12)
        self.assertAlmostEqual(tr.funding[i], side * 3e-4, places=12)   # 08:00, 16:00 and 24:00 settle in the hold

    def test_gate_uses_the_previous_evening_forecast(self):
        res, dailies, fundings, _ = run(0.9, 10)
        c = re_.COINS[0]
        t = dailies[c].t.values
        D = int(np.searchsorted(t, pd.Timestamp("2022-03-01", tz="UTC").value // 10**6))
        C, _ = synth(610, 0.9, 10)
        C2 = C.copy()
        C2[D * 1440:(D + 1) * 1440] *= 1.05                     # change day D only, after its 00:00
        d2 = dict(dailies)
        d2[c] = re_.daily(C2, t0=T0)
        with mock.patch.multiple(re_, B=200, **WINDOWS):
            res2 = re_.analyze(d2, fundings)
        self.assertEqual(res["forecast"][c][D], res2["forecast"][c][D])
        self.assertNotEqual(res["forecast"][c][D + 1], res2["forecast"][c][D + 1])

    def test_planted_regime_is_found(self):
        res, _, _, _ = run(0.9, 20)
        p = res["prediction"]
        self.assertGreater(p["auc_valid"], 0.65)
        self.assertTrue(p["predictable"])
        g, u = res["rule_gated"]["valid"], res["rule_ungated"]["valid"]
        self.assertLess(g["trades"], u["trades"])
        self.assertGreater(res["gate_lift_bp_per_trade_valid"], 5)
        self.assertTrue(res["gate_pass"])
        terc = res["gross_by_forecast_tercile"]
        self.assertGreater(terc["high_valid"]["gross_bp_per_trade"], terc["low_valid"]["gross_bp_per_trade"])

    def test_iid_regime_is_not_predictable(self):
        res, _, _, _ = run(0.5, 30)
        self.assertLess(abs(res["prediction"]["auc_valid"] - 0.5), 0.05)
        self.assertFalse(res["prediction"]["predictable"])
        self.assertFalse(res["gate_pass"])
        self.assertTrue(res["rule_pass"])                       # trend days still pay the ungated rule here


if __name__ == "__main__":
    unittest.main()
