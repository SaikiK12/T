"""dealerflow_v1 runner (scripts/run_dealerflow.py) on synthetic data: taker positions and IVs per option and day,
point in time; the dealer GEX sign and value; the next-day hourly autocorrelation; a planted gamma effect on next-day
volatility and autocorrelation is found out of sample, and an unrelated series is not."""
import unittest

import numpy as np
import pandas as pd

from lab import exposure
from scripts import run_dealerflow as rd

DAY, HOUR = rd.DAY, rd.HOUR


def rows(*trades):
    """trades: (instrument, t, expiry_day, strike, cp, buy, sell, block_buy, block_sell, iv)."""
    f = pd.DataFrame(trades, columns=["instrument", "t", "expiry_day", "strike", "cp", "buy", "sell", "block_buy",
                                      "block_sell", "iv"])
    f["expiry_ms"] = f.pop("expiry_day") * DAY + 8 * HOUR
    f["instrument"] = f.instrument.astype("category")
    return f


class GridTest(unittest.TestCase):
    def setUp(self):
        self.flow = rows(
            ("A", 2 * DAY + 3 * HOUR, 20, 100.0, "C", 5.0, 0.0, 0.0, 0.0, 50.0),
            ("A", 4 * DAY + 23 * HOUR, 20, 100.0, "C", 0.0, 2.0, 0.0, 1.0, 60.0),   # 23:00, still day 4
            ("B", 11 * DAY, 20, 90.0, "P", 1.0, 0.0, 0.0, 0.0, 80.0),
            ("C", 1 * DAY, 6, 95.0, "P", 2.0, 0.0, 0.0, 0.0, np.nan))

    def grid(self, d_last=40):
        g = rd.daily_grid(self.flow, d_last)
        name = dict(enumerate(self.flow.instrument.cat.categories))
        return g.assign(name=g.code.map(name)).set_index(["name", "day"])

    def test_positions_life_and_blocks(self):
        g = self.grid()
        a = g.loc["A"]
        self.assertEqual(list(a.index), list(range(2, 20)))           # first trade day .. last close before expiry
        self.assertEqual(a.pos[2], 5.0)
        self.assertEqual(a.pos[3], 5.0)
        self.assertEqual(a.pos[4], 3.0)
        self.assertEqual(a.pos[19], 3.0)
        self.assertEqual(a.pos_ex[4], 4.0)                            # the block sell of 1 left out
        self.assertEqual(list(g.loc["C"].index), [1, 2, 3, 4, 5])
        self.assertTrue(bool(g.loc["A"].call.all()) and not bool(g.loc["B"].call.any()))
        self.assertEqual(list(self.grid(d_last=8).loc["A"].index), list(range(2, 9)))

    def test_iv_carry_and_expiry_median(self):
        a = self.grid().loc["A"]
        self.assertEqual(a.iv[3], 50.0)
        self.assertEqual(a.iv[10], 60.0)                              # last traded IV, 6 days old
        self.assertTrue(np.isnan(a.iv_own[11]))                       # 7 days old: too stale
        self.assertEqual(a.iv[11], 80.0)                              # the median over the same expiry that day
        self.assertTrue(np.isnan(self.grid().loc["C"].iv).all())      # no IV anywhere for that expiry

    def test_point_in_time(self):
        later = pd.concat([self.flow, rows(("A", 9 * DAY, 20, 100.0, "C", 7.0, 0.0, 0.0, 0.0, 99.0))])
        later["instrument"] = later.instrument.astype(str).astype("category")
        g1 = self.grid()
        g2 = rd.daily_grid(later, 40)
        g2 = g2.assign(name=g2.code.map(dict(enumerate(later.instrument.cat.categories)))).set_index(["name", "day"])
        self.assertEqual(g1.loc[("A", 8)].pos, g2.loc[("A", 8)].pos)  # a trade at 00:00 of day 9 is not known on day 8
        self.assertEqual(g2.loc[("A", 9)].pos, 10.0)


class GexTest(unittest.TestCase):
    def test_sign_value_and_short_dated_variant(self):
        flow = rows(("X", 0, 10, 100.0, "C", 10.0, 0.0, 0.0, 0.0, 60.0),
                    ("Y", 0, 6, 100.0, "C", 4.0, 0.0, 0.0, 0.0, 60.0))
        grid = rd.daily_grid(flow, 20)
        close = pd.Series(100.0, index=range(0, 21))
        gex = rd.gex_daily(grid, close)
        T = (10 * DAY + 8 * HOUR - 4 * DAY) / exposure.YEAR_MS
        gx = exposure.greeks(100.0, 100.0, T, 0.6, True).gamma[0] * 100 * 100 * 0.01
        Ty = (6 * DAY + 8 * HOUR - 4 * DAY) / exposure.YEAR_MS
        gy = exposure.greeks(100.0, 100.0, Ty, 0.6, True).gamma[0] * 100 * 100 * 0.01
        self.assertAlmostEqual(gex.gex[3], -(10 * gx + 4 * gy), places=9)   # takers long: dealers short gamma
        self.assertLess(gex.gex[3], 0)
        Ty5 = (6 * DAY + 8 * HOUR - 6 * DAY) / exposure.YEAR_MS             # Y expires 8 hours after day 5's close
        self.assertLess(Ty5 * exposure.YEAR_MS, DAY)
        T5 = (10 * DAY + 8 * HOUR - 6 * DAY) / exposure.YEAR_MS
        g5 = exposure.greeks(100.0, 100.0, T5, 0.6, True).gamma[0] * 100 * 100 * 0.01
        self.assertAlmostEqual(gex.gex_ex_24h[5], -10 * g5, places=9)       # Y left out of the 24 h variant
        self.assertEqual(gex.dropped_share[3], 0.0)


class PerpTest(unittest.TestCase):
    def bars(self, step):
        C = 100 * np.exp(np.cumsum(step))
        return {"close": C, "quote_volume": np.full(len(C), 2.0)}

    def test_hourly_autocorrelation(self):
        trend = rd.perp_daily(self.bars(np.full(3 * 1440, 1e-5)), t0=0)
        self.assertAlmostEqual(trend.ac[1], 23 / 24, places=9)
        sign = np.repeat(np.tile([1.0, -1.0], 36), 60)
        zig = rd.perp_daily(self.bars(sign * 1e-4), t0=0)
        self.assertAlmostEqual(zig.ac[1], -23 / 24, places=6)
        self.assertTrue(np.isnan(zig.ac[0]))                         # day 0 has no previous close
        self.assertEqual(zig.qv[1], 2.0 * 1440)
        self.assertEqual(list(zig.day), [0, 1, 2])


def synth(seed, planted):
    """frame() inputs per coin over the lane's days: g an AR(1); next-day log variance and hourly autocorrelation
    respond to g when `planted`."""
    rng = np.random.default_rng(seed)
    d0, d1 = rd.T0 // DAY, rd.T1 // DAY
    n = d1 - d0
    g = np.zeros(n)
    for i in range(1, n):
        g[i] = 0.9 * g[i - 1] + rng.normal(0, 0.44)
    k = 1.0 if planted else 0.0
    lv = np.zeros(n)
    ac = np.zeros(n)
    for i in range(1, n):
        lv[i] = -8 + 0.6 * (lv[i - 1] + 8) - 0.3 * k * g[i - 1] + rng.normal(0, 0.3)
        ac[i] = -0.15 * k * g[i - 1] + rng.normal(0, 0.2)
    lv[0] = -8
    days = np.arange(d0, d1)
    perp = pd.DataFrame({"day": days, "t": days * DAY, "var": np.exp(lv), "qv": 1e9, "ac": ac, "close": 100.0})
    gex = pd.DataFrame({"gex": g * 1e9, "gex_ex_blocks": g * 1e9, "gex_ex_24h": g * 1e9, "dropped_share": 0.0},
                       index=days)
    return rd.frame(perp, gex)


class AnalyzeTest(unittest.TestCase):
    def test_frame_targets_are_next_day(self):
        f = synth(1, True)
        self.assertEqual(f.y[100], f.lv1[101])
        self.assertTrue(np.isnan(f.g[10]))                           # ADV needs 20 days
        self.assertAlmostEqual(f.g[200], f.gex[200] / 1e9)

    def test_planted_effect_is_found(self):
        res = rd.analyze({"BTC": synth(2, True), "ETH": synth(3, True)})
        self.assertTrue(res["passes"]["vol_g"])
        self.assertTrue(res["passes"]["ac_g"])
        self.assertEqual(res["verdict"], "PARTIAL")
        self.assertGreater(res["tests"]["g"]["vol"]["dm_t"], rd.T_MIN)

    def test_unrelated_series_is_not(self):
        res = rd.analyze({"BTC": synth(4, False), "ETH": synth(5, False)})
        self.assertEqual(res["verdict"], "NULL")
        self.assertLess(res["tests"]["g"]["vol"]["dm_t"], rd.T_MIN)


if __name__ == "__main__":
    unittest.main()
