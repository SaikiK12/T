import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_minflow_alts as alts
from scripts import run_minflow as r349

MIN = r349.MIN


def bars_with_spike(n=12 * 1440, spike_at=None, seed=0):
    """Invented 1-minute bars: a random walk with steady two-sided flow, and one bar of extreme buying."""
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    open_ = np.r_[close[0], close[:-1]]
    vol = np.full(n, 10.0)
    tbv = 5 + rng.normal(0, 0.5, n)
    if spike_at is not None:
        tbv[spike_at] = 10.0                      # every taker bought: delta +10, far above the week's range
    return {"open": open_, "high": np.maximum(open_, close) + 0.01, "low": np.minimum(open_, close) - 0.01,
            "close": close, "volume": vol, "tbv": tbv}


def table(day, gross, side=1):
    """A trade table in R349's layout with the given entry days and gross returns."""
    day = np.asarray(day)
    return pd.DataFrame({"i": np.arange(len(day)), "side": np.full(len(day), side, np.int8), "te": 0, "tx": 0,
                         "pe": 1.0, "px": 1.0, "gross": np.asarray(gross, float), "fund": 0.0, "day": day})


class TestCosts(unittest.TestCase):
    def test_frozen_costs_match_r348_rounded(self):
        walk = {c.removesuffix("USDT"): v + 0.004 for c, v in alts.WALK_BP.items()}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "summary.json"
            p.write_text(json.dumps({"walk_cost_bp": walk}))
            alts.check_costs(p)
            walk["LTC"] = 4.2
            p.write_text(json.dumps({"walk_cost_bp": walk}))
            with self.assertRaises(ValueError):
                alts.check_costs(p)


class TestSignal(unittest.TestCase):
    def test_pick_is_r349s_flow_fade_k5_h5(self):
        b = bars_with_spike(spike_at=10 * 1440 + 30)
        tick = np.full(len(b["close"]), 0.01)
        F, rate = np.array([0], np.int64), np.array([0.0])
        mine = alts.simulate(b, tick, F, rate)
        theirs = r349.trades(b, tick, F, rate, r349.coin_signals(b)["flow_fade_k5"], 5, 0)
        pd.testing.assert_frame_equal(mine, theirs)
        self.assertIn(10 * 1440 + 30, mine.i.tolist())               # the spike bar trades
        self.assertEqual(int(mine.side[mine.i == 10 * 1440 + 30].iloc[0]), -1)   # against the buying

    def test_full_tick_costs_one_more_tick_a_round_trip(self):
        b = bars_with_spike(spike_at=10 * 1440 + 30)
        tick = np.full(len(b["close"]), 0.01)
        F, rate = np.array([0], np.int64), np.array([0.0])
        half = alts.simulate(b, tick, F, rate)
        full = alts.simulate(b, tick, F, rate, tick_mult=2.0)
        self.assertEqual(half.i.tolist(), full.i.tolist())
        self.assertTrue((full.gross < half.gross).all())


class TestBook(unittest.TestCase):
    def test_each_coin_holds_a_ninth_and_idle_coins_add_nothing(self):
        per = {c: table([], []) for c in alts.COINS}
        per["BNBUSDT"] = table([3], [0.0009])                       # +9 bp gross, cost 2 x 0.81 bp
        x = alts.book(per, 1)
        self.assertAlmostEqual(x[3], (0.0009 - 2 * 0.81e-4) / 9)
        self.assertEqual(np.count_nonzero(x), 1)
        self.assertAlmostEqual(alts.book(per, cost=3.0)[3], (0.0009 - 6e-4) / 9)


class TestDecide(unittest.TestCase):
    def days(self, a, b):
        return np.flatnonzero(alts.sel(a, b))

    def planted(self, early_bp, late_bp, recent_bp, coins=alts.COINS, noise=0.0005, seed=1):
        """Two trades a day per coin with a planted 1x net per trade (bp) in each part of the window; coins left
        out of `coins` lose gross instead."""
        rng = np.random.default_rng(seed)
        per = {}
        for c in alts.COINS:
            parts = []
            for (a, b), bp in ((alts.HALVES[0], early_bp), (("2024-01-01", "2025-06-30"), late_bp),
                               (alts.RECENT, recent_bp)):
                d = np.repeat(self.days(a, b), 2)
                mean = (bp + 2 * alts.WALK_BP[c]) / 1e4 if c in coins else -abs(bp) / 1e4   # net bp, or a gross loss
                g = mean + rng.normal(0, noise, len(d))
                parts.append(table(d, g))
            per[c] = pd.concat(parts, ignore_index=True)
        return per

    def test_live_when_everything_holds(self):
        d = alts.decide(self.planted(8, 8, 8))
        self.assertEqual(d["verdict"], "LIVE")
        self.assertEqual(d["coins_positive_gross"], 9)

    def test_replicates_but_not_live_when_the_recent_window_is_flat(self):
        d = alts.decide(self.planted(8, 8, 0))
        self.assertEqual(d["verdict"], "REPLICATES")
        self.assertLess(d["recent_t1"], 2)

    def test_null_when_one_half_loses(self):
        d = alts.decide(self.planted(-3, 8, 8))
        self.assertLess(d["halves_net1_day_bp"][0], 0)
        self.assertEqual(d["verdict"], "NULL")

    def test_null_when_fewer_than_six_coins_earn_gross(self):
        d = alts.decide(self.planted(20, 20, 20, coins=alts.COINS[:5]))
        self.assertEqual(d["coins_positive_gross"], 5)
        self.assertEqual(d["verdict"], "NULL")


class TestWindows(unittest.TestCase):
    def test_years_are_clipped_to_the_lane_window(self):
        w = alts.windows()
        self.assertEqual(int(w["2021"].sum()), int(alts.sel("2021-04-01", "2021-12-31").sum()))
        self.assertEqual(int(w["2026"].sum()), int(alts.sel("2026-01-01", "2026-09-30").sum()))
        self.assertEqual(int(w["all"].sum()), int(w["early"].sum() + w["late"].sum()))


if __name__ == "__main__":
    unittest.main()
