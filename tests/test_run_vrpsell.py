import unittest

import numpy as np
import pandas as pd

from scripts import run_vrpsell as v

H, D = v.HOUR, v.DAY


class Pricing(unittest.TestCase):
    def test_put_call_parity_and_atm_straddle(self):
        c, p, d1 = v.bs(100.0, 95.0, 7 / 365, 0.5)
        self.assertAlmostEqual(c - p, 5.0, places=9)
        c, p, _ = v.bs(100.0, 100.0, 7 / 365, 0.5)
        self.assertAlmostEqual((c + p) / 100.0, 0.8 * 0.5 * np.sqrt(7 / 365), places=3)   # ATM approximation

    def test_fridays_are_fridays_and_expiry_inside_data(self):
        fr = v.fridays()
        self.assertTrue(all(pd.Timestamp(x, unit="ms").weekday() == 4 for x in fr))
        self.assertLessEqual(fr[-1] + 7 * D + 8 * H, v.T1)


class Book(unittest.TestCase):
    def flat(self, n, S=100.0):
        return np.full(n + 1, S)

    def test_flat_path_at_strike_keeps_premium_less_costs(self):
        t0 = 0
        te, E = 0, 168 * H
        P = self.flat(168)
        none = np.array([], np.int64), np.array([], float)
        r0 = v.straddle(P, 100.0, 50.0, 0.0, 0, *none, te, E, t0=t0)
        self.assertAlmostEqual(r0["net"], r0["premium"], places=9)          # no payoff, no hedge P&L, no cost
        self.assertEqual(r0["payoff"], 0.0)
        r1 = v.straddle(P, 100.0, 50.0, 1.0, 1, *none, te, E, t0=t0)
        r2 = v.straddle(P, 100.0, 50.0, 1.0, 2, *none, te, E, t0=t0)
        self.assertLess(r1["premium"], r0["premium"])                       # sold at the bid
        self.assertLess(r2["net"], r1["net"])                               # costs scale with m
        self.assertAlmostEqual(r1["opt_fee"] * 2, r2["opt_fee"], places=12)

    def test_hedged_straddle_loses_when_realized_exceeds_implied(self):
        rng = np.random.default_rng(1)
        n = 168
        steps = rng.normal(0, 1.5 / np.sqrt(v.YEAR_H), n)                   # 150% realized vs 50% implied
        P = 100.0 * np.exp(np.r_[0.0, np.cumsum(steps)])
        none = np.array([], np.int64), np.array([], float)
        r = v.straddle(P, 100.0, 50.0, 0.0, 0, *none, 0, n * H, t0=0)
        self.assertLess(r["net"], 0.0)
        self.assertGreater(r["rv"], 100.0)

    def test_funding_long_hedge_pays_positive_rate(self):
        n = 24
        P = np.linspace(100.0, 110.0, n + 1)                                 # rising: the hedge is long
        none = np.array([], np.int64), np.array([], float)
        base = v.straddle(P, 100.0, 50.0, 0.0, 0, *none, 0, n * H, t0=0)
        fund = v.straddle(P, 100.0, 50.0, 0.0, 0, np.array([8 * H, 16 * H]), np.array([1e-3, 1e-3]), 0, n * H, t0=0)
        self.assertGreater(fund["funding"], 0.0)
        self.assertAlmostEqual(base["net"] - fund["net"], fund["funding"], places=12)

    def test_missing_price_skips_the_week(self):
        P = self.flat(10)
        P[5] = np.nan
        none = np.array([], np.int64), np.array([], float)
        self.assertIsNone(v.straddle(P, 100.0, 50.0, 0.0, 1, *none, 0, 10 * H, t0=0))


class Entry(unittest.TestCase):
    def test_picks_nearest_two_legged_strike_in_first_usable_hour(self):
        Dm = 7 * D                                                           # any instant; t0 = 0 below
        E = Dm + 7 * D + 8 * H
        rows = pd.DataFrame([
            {"t": Dm + 8 * H, "expiry_ms": E, "strike": 100.0, "cp": "C", "iv": 50.0},     # call only at 08:00
            {"t": Dm + 9 * H, "expiry_ms": E, "strike": 100.0, "cp": "C", "iv": 50.0},
            {"t": Dm + 9 * H, "expiry_ms": E, "strike": 100.0, "cp": "P", "iv": 52.0},
            {"t": Dm + 9 * H, "expiry_ms": E, "strike": 105.0, "cp": "C", "iv": 48.0},
            {"t": Dm + 9 * H, "expiry_ms": E, "strike": 105.0, "cp": "P", "iv": 49.0},
        ])
        PH = np.full((E // H) + 2, 104.0)
        e, why = v.pick_entry(rows, Dm, PH, t0=0)
        self.assertIsNone(why)
        self.assertEqual(e, (Dm + 9 * H, 105.0, 48.0, 49.0))
        e, why = v.pick_entry(rows.iloc[:1], Dm, PH, t0=0)
        self.assertIsNone(e)
        self.assertEqual(why, "no_two_legged_strike")


class Decide(unittest.TestCase):
    def test_pass_needs_every_check(self):
        good = {"mean_bp": 10, "t_nw": 3.0, "halves_bp": [5, 6], "trimmed_bp": 4, "wo_best_bp": 2}
        self.assertEqual(v.decide(good, {"mean_bp": 1}), "PASS")
        for k, bad in (("t_nw", 2.0), ("halves_bp", [5, -1]), ("trimmed_bp", -1), ("wo_best_bp", -1)):
            self.assertEqual(v.decide({**good, k: bad}, {"mean_bp": 1}), "NULL")
        self.assertEqual(v.decide(good, {"mean_bp": -1}), "NULL")


if __name__ == "__main__":
    unittest.main()
