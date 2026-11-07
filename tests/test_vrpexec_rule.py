import unittest

import numpy as np
import pandas as pd

from scripts import run_vrpsell2 as v
from scripts import vrpexec_rule as R

H, D = R.HOUR, R.DAY


def walk(n, seed=1, vol=0.8):
    rng = np.random.default_rng(seed)
    return 100.0 * np.exp(np.r_[0.0, np.cumsum(rng.normal(0, vol / np.sqrt(8760), n))])


class Hedge(unittest.TestCase):
    def test_hourly_taker_matches_r409(self):
        n = 168
        P = walk(n)
        F_t, F_r = np.array([8 * H, 16 * H, 24 * H, 100 * H]), np.array([1e-4, -2e-4, 3e-4, 1e-4])
        old = v.straddle(P, 100.0, 60.0, 0.0, 1, F_t, F_r, 0, n * H, t0=0)
        nan = np.full(n, np.nan)
        new = R.hedge(P, nan, nan, 100.0, 0.60, 0.0, False, 1, F_t, F_r, 0, n * H)
        self.assertAlmostEqual(new["pnl"], old["hedge_pnl"], places=9)
        self.assertAlmostEqual(new["fee"], old["hedge_fee"], places=9)
        self.assertAlmostEqual(new["funding"], old["funding"], places=9)

    def test_band_cuts_turnover(self):
        n = 168
        P = walk(n, seed=3)
        nan = np.full(n, np.nan)
        args = (np.array([], np.int64), np.array([], float), 0, n * H)
        t0 = R.hedge(P, nan, nan, 100.0, 0.6, 0.0, False, 1, *args)["turnover"]
        t1 = R.hedge(P, nan, nan, 100.0, 0.6, 0.10, False, 1, *args)["turnover"]
        t2 = R.hedge(P, nan, nan, 100.0, 0.6, 0.20, False, 1, *args)["turnover"]
        self.assertGreater(t0, t1)
        self.assertGreater(t1, t2)

    def test_maker_first_fills_and_misses(self):
        n = 48
        P = walk(n, seed=5)
        args = (np.array([], np.int64), np.array([], float), 0, n * H)
        lo, hi = np.full(n, 0.0), np.full(n, 1e9)                       # every hour trades through both ways
        tk = R.hedge(P, lo, hi, 100.0, 0.6, 0.0, False, 1, *args)
        mk = R.hedge(P, lo, hi, 100.0, 0.6, 0.0, True, 1, *args)
        self.assertAlmostEqual(mk["pnl"], tk["pnl"], places=9)           # filled at the posting price
        self.assertEqual(mk["fills"], mk["posts"])
        self.assertLess(mk["fee"], tk["fee"])
        never = np.full(n, np.nan)
        late = R.hedge(P, never, never, 100.0, 0.6, 0.0, True, 1, *args)
        self.assertEqual(late["fills"], 0)                                # every order crosses an hour late, at taker
        self.assertNotAlmostEqual(late["pnl"], tk["pnl"], places=6)


class Sale(unittest.TestCase):
    def setUp(self):
        self.K, self.Dm = 100.0, 7 * D
        self.E = self.Dm + 7 * D + 8 * H
        tau = (self.E - (self.Dm + 7 * H)) / R.YEAR_MS
        mark = R.leg(100.0, self.K, tau, 0.5, "C") / 100.0               # a 50% mark at 07:00, index 100
        self.mark = mark
        self.PH = np.full((self.E // H) + 2, 100.0)

    def trades(self, rows):
        base = {"timestamp": self.Dm + 7 * H, "price": self.mark, "mark_price": self.mark, "iv": 50.0,
                "index_price": 100.0, "direction": "sell", "amount": 1.0}
        return pd.DataFrame([base] + [{**base, **r} for r in rows])

    def test_implied_vol_round_trip(self):
        tau = 7 / 365
        for cp in "CP":
            p = R.leg(100.0, 103.0, tau, 0.7, cp)
            self.assertAlmostEqual(R.implied_vol(p, 100.0, 103.0, tau, cp), 0.7, places=6)

    def test_tick_up(self):
        self.assertAlmostEqual(R.tick_up(0.00231), 0.0024)
        self.assertAlmostEqual(R.tick_up(0.0213), 0.0215)
        self.assertAlmostEqual(R.tick_up(0.0215), 0.0215)

    def test_maker_fills_only_on_a_trade_through(self):
        post = self.Dm + 8 * H
        lim = R.maker_leg(self.trades([]), self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 1)["lim_c"]
        at = self.trades([{"timestamp": post + 60_000, "price": lim, "direction": "buy"}])
        sold_through = self.trades([{"timestamp": post + 60_000, "price": lim + 0.001, "direction": "sell"}])
        through = self.trades([{"timestamp": post + 60_000, "price": lim + 0.0005, "direction": "buy"}])
        late = self.trades([{"timestamp": self.Dm + 12 * H, "price": lim + 0.0005, "direction": "buy"}])
        for tr, want in ((at, False), (sold_through, False), (through, True), (late, False)):
            self.assertEqual(R.maker_leg(tr, self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 1)["filled"], want)
        f1 = R.maker_leg(through, self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 1)
        f2 = R.maker_leg(through, self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 2)
        f0 = R.maker_leg(through, self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 0)
        self.assertAlmostEqual(f1["price"], lim * 100.0, places=9)
        self.assertAlmostEqual(f2["price"], f0["price"], places=9)       # 2x gives the improvement back to the mid
        self.assertLess(f0["price"], f1["price"])
        self.assertEqual(f0["fee"], 0.0)

    def test_unfilled_leg_sells_at_taker_at_noon(self):
        tr = self.trades([])
        mk = R.maker_leg(tr, self.Dm, self.PH, 0, self.K, self.E, "C", 0.9, 1)
        tk = R.taker_leg(tr, self.Dm + 12 * H, 100.0, self.K, self.E, "C", 0.9, 1)
        self.assertFalse(mk["filled"])
        self.assertAlmostEqual(mk["price"], tk["price"], places=9)

    def test_reference_uses_trades_strictly_before(self):
        tr = self.trades([{"timestamp": self.Dm + 8 * H, "mark_price": self.mark * 2}])
        iv = R.mark_iv(tr, self.Dm + 8 * H, self.K, self.E, "C")
        self.assertAlmostEqual(iv, 0.5, places=6)
        self.assertIsNone(R.mark_iv(tr, self.Dm + 7 * H, self.K, self.E, "C"))


class Strike(unittest.TestCase):
    def test_point_in_time_nearest_lower_on_tie(self):
        Dm = 7 * D
        post = Dm + 8 * H
        rows = []
        for t, K in ((post - 3 * H, 100.0), (post - 2 * H, 110.0), (post, 105.0), (post - 30 * H, 104.0)):
            for cp in "CP":
                rows.append({"t": t, "strike": K, "cp": cp, "instrument": f"X-{K:g}-{cp}"})
        f = pd.DataFrame(rows)
        PH = np.full(post // H + 2, 105.0)
        self.assertEqual(R.pick_strike(f, Dm, PH, 0), (100.0, "X-100-C", "X-100-P"))   # 105 is at 08:00, 104 too old
        self.assertIsNone(R.pick_strike(f[f.cp == "C"], Dm, PH, 0))


if __name__ == "__main__":
    unittest.main()
