"""Synthetic checks for R307's risk-reversal rules: no market data is read."""
import tempfile
import unittest
from math import exp, sqrt
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from scripts import run_rrskew as m

H, D = m.HOUR, m.DAY
N = NormalDist()


def strike(F, iv, T_years, delta):
    """The strike whose Black-Scholes delta on forward F is `delta` (calls > 0, puts < 0)."""
    d1 = N.inv_cdf(delta if delta > 0 else 1.0 + delta)
    s = iv / 100.0
    return F * exp(-(d1 * s * sqrt(T_years) - 0.5 * s * s * T_years))


def rows_for_day(day, expiry_days, specs, index=100.0, basis=0.0):
    """Option-hours on UTC day `day` (days after T0): specs = [(cp, delta, iv, hour)], one row each, all expiring
    `expiry_days` after the day's start at 08:00 UTC."""
    out = []
    for cp, delta, iv, hour in specs:
        t = m.T0 + day * D + hour * H
        expiry = m.T0 + (day + expiry_days) * D + 8 * H
        T = (expiry - (t + H / 2)) / m.YEAR_MS
        F = index * exp(basis * T)
        out.append({"t": t, "expiry_ms": expiry, "strike": strike(F, iv, T, delta), "cp": cp, "buy": 1.0,
                    "sell": 0.0, "iv": iv, "index_price": index})
    return pd.DataFrame(out)


class DeltaTest(unittest.TestCase):
    def test_atm_forward_and_put_parity(self):
        t = m.T0
        T = 0.25
        expiry = int(t + H / 2 + T * m.YEAR_MS)
        rows = pd.DataFrame({"t": [t, t], "expiry_ms": [expiry, expiry], "strike": [100.0, 100.0], "cp": ["C", "P"],
                             "iv": [80.0, 80.0], "index_price": [100.0, 100.0]})
        d, tdays = m.deltas(rows)
        self.assertAlmostEqual(d[0], N.cdf(0.5 * 0.8 * sqrt(T)), places=6)    # d1 = sigma sqrt(T) / 2 at F = K
        self.assertAlmostEqual(d[0] - d[1], 1.0, places=9)
        self.assertAlmostEqual(tdays[0], T * 365.25, places=6)

    def test_basis_moves_the_forward(self):
        r = rows_for_day(3, 90, [("C", 0.25, 70.0, 5)], basis=0.3)
        d0, _ = m.deltas(r)
        d1, _ = m.deltas(r, basis=[0.3])
        self.assertAlmostEqual(d1[0], 0.25, places=6)
        self.assertLess(d0[0], 0.20)                       # without the basis the call looks further out of the money

    def test_unusable_rows_are_nan(self):
        r = rows_for_day(3, 30, [("C", 0.25, 70.0, 5), ("P", -0.25, 70.0, 6)])
        r.loc[0, "iv"] = 0.0
        r.loc[1, "expiry_ms"] = r.loc[1, "t"]
        d, _ = m.deltas(r)
        self.assertTrue(np.isnan(d).all())


class RiskReversalTest(unittest.TestCase):
    def setUp(self):
        self.days = np.arange(m.T0, m.T0 + 10 * D, D, dtype=np.int64)

    def test_rr_is_call_minus_put_on_the_next_decision_day(self):
        specs = [("C", 0.25, 60.0, h) for h in (1, 2, 3)] + [("P", -0.25, 70.0, h) for h in (4, 5, 6)]
        rr = m.daily_rr(rows_for_day(4, 30, specs), self.days)
        self.assertAlmostEqual(rr["30d"][5], -10.0, places=9)   # rows of day 4 feed the decision at 00:00 of day 5
        self.assertTrue(np.isnan(rr["30d"][4]))
        self.assertTrue(np.isnan(rr["90d"]).all())               # 30 days to expiry is not in the 90 d bucket

    def test_amount_weights_wings_and_minimum_rows(self):
        specs = [("C", 0.25, 60.0, 1), ("C", 0.20, 66.0, 2), ("C", 0.30, 63.0, 3), ("C", 0.50, 10.0, 4),
                 ("P", -0.25, 70.0, 5), ("P", -0.30, 70.0, 6)]                    # 2 put rows: below MIN_ROWS
        r = rows_for_day(4, 90, specs)
        r.loc[0, "buy"] = 3.0                                                     # amount 3 against 1 and 1
        rr = m.daily_rr(r, self.days)
        self.assertTrue(np.isnan(rr["90d"][5]))
        r2 = pd.concat([r, rows_for_day(4, 90, [("P", -0.20, 76.0, 7)])], ignore_index=True)
        rr2 = m.daily_rr(r2, self.days)
        call = (3 * 60.0 + 66.0 + 63.0) / 5                                       # the 0.50-delta call is outside
        put = (70.0 + 70.0 + 76.0) / 3
        self.assertAlmostEqual(rr2["90d"][5], call - put, places=6)

    def test_basis_per_hour_and_rows_without_one_dropped(self):
        specs = [("C", 0.16, 60.0, h) for h in (1, 2, 3)] + [("P", -0.25, 70.0, h) for h in (4, 5, 6)]
        rows = rows_for_day(4, 90, specs, basis=0.4)
        b = np.full(m.NH + 1, 0.4)
        self.assertAlmostEqual(m.daily_rr(rows, self.days, b)["90d"][5], -10.0, places=9)
        self.assertTrue(np.isnan(m.daily_rr(rows, self.days)["90d"][5]))     # zero basis: the calls fall below 0.15
        b[4 * 24 + 4] = np.nan                                                   # one put row loses its basis
        self.assertTrue(np.isnan(m.daily_rr(rows, self.days, b)["90d"][5]))


class BasisTest(unittest.TestCase):
    def test_nearest_quarterly_with_14_days_left_and_gap_fill(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            t = np.arange(m.ms("2020-12-20"), m.ms("2021-04-01"), H, dtype=np.int64)
            pd.DataFrame({"t": t, "close": 100.0}).to_parquet(root / "BTCUSD_PERP.parquet")
            for name, b in (("210326", 0.2), ("210625", 0.1)):
                exp_ms = m.ms("20" + name) + 8 * H
                tau = (exp_ms - (t + H)) / m.YEAR_MS                           # bar t closes at t + 1 h
                keep = tau > 0
                pd.DataFrame({"t": t[keep], "close": 100.0 * np.exp(b * tau[keep])}).to_parquet(
                    root / f"BTCUSD_{name}.parquet")
            pd.DataFrame({"t": t, "close": 100.0}).to_parquet(root / "BTCUSD_201225.parquet")   # expired before T0
            self.assertEqual([p.stem for p, _ in m.quarterlies("BTC", root)], ["BTCUSD_210326", "BTCUSD_210625"])
            bb = m.hourly_basis("BTC", root)
            k = lambda day, h=0: (m.ms(day) - m.T0) // H + h
            self.assertAlmostEqual(bb[k("2021-03-01")], 0.2, places=9)
            self.assertAlmostEqual(bb[k("2021-03-11")], 0.2, places=9)              # 15 days and 8 h left
            self.assertAlmostEqual(bb[k("2021-03-13")], 0.1, places=9)              # 13 days left: the next one
            self.assertTrue(np.isnan(bb[0]))                                         # T0 itself: no bar ends there yet
            # a gap in the futures bars is carried for 24 hours, not longer
            f = pd.read_parquet(root / "BTCUSD_210625.parquet")
            f = f[(f.t < m.ms("2021-03-20")) | (f.t >= m.ms("2021-03-22"))]
            f.to_parquet(root / "BTCUSD_210625.parquet")
            bb = m.hourly_basis("BTC", root)
            self.assertAlmostEqual(bb[k("2021-03-20", 20)], 0.1, places=9)
            self.assertTrue(np.isnan(bb[k("2021-03-21", 12)]))

    def test_rows_outside_the_archive_window_are_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.parquet"
            pd.DataFrame({"t": [m.T0 - H, m.T0, m.T1 - H, m.T1], "close": [1.0, 2.0, 3.0, 4.0]}).to_parquet(p)
            C = m.bar_closes(p)
            self.assertEqual(C[1], 2.0)
            self.assertEqual(C[-1], 3.0)
            self.assertEqual(int(np.isfinite(C).sum()), 2)


class SignalTest(unittest.TestCase):
    def test_rolling_z_uses_only_past_values(self):
        x = np.array([1.0, -1.0] * 30 + [10.0])
        z = m.rolling_z(x)
        prev = x[:60]
        self.assertAlmostEqual(z[60], (10.0 - prev.mean()) / prev.std(ddof=1), places=9)
        self.assertTrue(np.isnan(z[59]))                     # 59 previous values: fewer than 60

    def test_chg7(self):
        x = np.arange(200, dtype=float) % 13
        s = m.signals(x)
        self.assertTrue(np.isnan(s["chg7"][:7 + 60]).all())
        self.assertTrue(np.isfinite(s["chg7"][7 + 60]))
        np.testing.assert_array_equal(s["sign"], x)


class BookTest(unittest.TestCase):
    def test_costs_on_entries_flips_and_exits(self):
        c = m.COST
        sig = np.array([1.0, 1.0, -1.0, np.nan, 1.0])
        r = np.array([0.01, 0.02, -0.03, 0.05, 0.01])
        out = m.book(sig, r, np.zeros(5), "follow", 1)
        np.testing.assert_allclose(out[[0, 1, 2, 4]], [0.01 - c, 0.02, 0.03 - 3 * c, 0.01 - 2 * c])
        self.assertTrue(np.isnan(out[3]))
        self.assertAlmostEqual(np.nansum(out) - np.nansum(np.array([0.01, 0.02, 0.03, 0.01])), -6 * c)
        fade = m.book(sig, r, np.zeros(5), "fade", 2)
        np.testing.assert_allclose(fade[[0, 2]], [-0.01 - 2 * c, -0.03 - 6 * c])

    def test_funding_and_missing_return(self):
        out = m.book(np.array([1.0, -1.0, 1.0]), np.array([0.0, 0.0, np.nan]), np.array([0.001, 0.001, 0.0]),
                     "follow", 0)
        np.testing.assert_allclose(out[:2], [-0.001, 0.001])
        self.assertTrue(np.isnan(out[2]))

    def test_mondays_and_week_returns(self):
        days = np.arange(m.T0, m.T0 + 30 * D, D, dtype=np.int64)
        idx = m.mondays(days)
        self.assertEqual(idx[0], 3)                          # 2021-01-01 is a Friday
        self.assertTrue((np.diff(idx) == 7).all())
        P = np.linspace(100, 129, 30)
        ft = np.array([days[3], days[3] + 8 * H, days[10], days[10] + H])
        fr = np.array([0.5, 0.01, 0.02, 0.5])
        r, fund = m.week_returns(P, ft, fr, days, idx)
        self.assertAlmostEqual(r[0], P[10] / P[3] - 1)
        self.assertAlmostEqual(fund[0], 0.03)               # (D, D + 7 d]: not the one at D, not the one after
        self.assertTrue(np.isnan(r[-1]))                     # the last Monday's week runs past the data

    def test_trials_and_decision(self):
        self.assertEqual(m.TRIALS, 24)
        self.assertEqual(len(set(m.BOOKS)), 24)
        rep = {"a": {"disc": {"1x": {"mean_bp": 5.0, "t": 1.0}},
                     "valid": {"1x": {"t": 2.5, "wo_best10_bp": 1.0}, "2x": {"mean_bp": 1.0}}},
               "b": {"disc": {"1x": {"mean_bp": -5.0, "t": 3.0}}, "valid": {}}}
        self.assertEqual(m.decide(rep), ("a", True, {"t_1x": True, "mean_2x": True, "wo_best": True}))


if __name__ == "__main__":
    unittest.main()
