import unittest

import numpy as np
import pandas as pd

from scripts import run_okxcarry as oc

T0 = pd.Timestamp("2026-01-01 16:00", tz="UTC")
T1 = pd.Timestamp("2026-01-31 16:00", tz="UTC")      # 30 days, 90 prints in (T0, T1]
INST = "BTC-USD_UM_XPERP-310404"


def funding(rate_fn, inst=INST, t0=T0, n=95):
    t = [t0 - pd.Timedelta(hours=8) + pd.Timedelta(hours=8 * k) for k in range(n)]
    return pd.DataFrame({"instId": inst, "fundingTime": [oc.ms(x) for x in t],
                         "fundingRate": [rate_fn(k) for k in range(n)], "realizedRate": [rate_fn(k) for k in range(n)],
                         "method": "current_period", "formulaType": "withRate"})


def candles(inst, price_fn, t0=T0, n=40):
    ts = [oc.ms(t0 - pd.Timedelta(days=2) + pd.Timedelta(days=k)) for k in range(n)]
    c = [price_fn(k) for k in range(n)]
    return pd.DataFrame({"instId": inst, "ts": ts, "o": c, "h": [x * 1.01 for x in c], "l": c, "c": c})


class OkxCarryTest(unittest.TestCase):
    def test_carry_arithmetic_on_capital(self):
        r = oc.carry(funding=0.03, basis=-0.001, days=100, tb=0.04, m=1, lev=2.0)
        self.assertAlmostEqual(r["net_on_notional"], 0.026)
        self.assertAlmostEqual(r["annual_on_capital"], 0.026 / 1.5 * 3.65)
        self.assertAlmostEqual(r["excess_over_tbill"], 0.026 / 1.5 * 3.65 - 0.04)
        self.assertAlmostEqual(oc.carry(0.03, 0.0, 100, 0.0, m=3, lev=1.0)["net_on_notional"], 0.03 - 0.009)

    def test_prints_are_half_open_and_fall_back_to_the_funding_rate(self):
        f = funding(lambda k: 1e-4)
        f.loc[5, "realizedRate"] = np.nan
        p = oc.prints(f, INST, T0, T1)
        self.assertEqual(len(p), 90)                                      # the print at T0 itself is excluded
        self.assertEqual(p.t.min(), T0 + pd.Timedelta(hours=8))
        self.assertEqual(p.t.max(), T1)
        self.assertEqual(int(p.fallback.sum()), 1)
        self.assertTrue(np.allclose(p.rate, 1e-4))

    def test_close_at_reads_the_bar_that_closes_at_t(self):
        c = candles("BTC-USD", lambda k: 100.0 + k)
        self.assertEqual(oc.close_at(c, "BTC-USD", T0), 101.0)          # the bar opening one day before T0
        with self.assertRaises(ValueError):
            oc.close_at(c, "BTC-USD", T0 + pd.Timedelta(hours=1))

    def test_tbill_mean_uses_a_two_day_lag(self):
        day = pd.Timedelta(days=1)
        series = [(oc.ms(T0 - 5 * day), 4.0), (oc.ms(T0 + 10 * day), 5.0)]
        # days T0..T0+11 see 4%; from T0+12 on (2-day lag) they see 5%
        want = (12 * 0.04 + 18 * 0.05) / 30
        self.assertAlmostEqual(oc.tbill_mean(series, T0, T1), want)
        with self.assertRaises(ValueError):
            oc.tbill_mean([(oc.ms(T1), 4.0)], T0, T1)

    def test_coin_result_end_to_end_on_a_flat_world(self):
        f = funding(lambda k: 1e-4)
        mk = candles(INST, lambda k: 100.0)
        ix = candles("BTC-USD", lambda k: 100.0)
        res, grid, path = oc.coin_result(f, mk, ix, "BTC", tb=0.0, t0=T0, t1=T1)
        self.assertEqual(res["prints"], 90)
        self.assertAlmostEqual(res["funding_sum"], 0.009)
        self.assertAlmostEqual(res["basis_pnl"], 0.0)
        self.assertAlmostEqual(res["baseline_share"], 1.0)
        prim = next(g for g in grid if g["cost_mult"] == 1 and g["leverage"] == 2.0)
        self.assertAlmostEqual(prim["annual_on_capital"], (0.009 - 0.003) / 1.5 * 365 / 30)   # 4.87%/yr
        self.assertEqual(res["verdict"], "FORWARD_WORTHY")
        self.assertAlmostEqual(res["max_rise"], 0.01)
        self.assertEqual(len(path), 30)
        self.assertAlmostEqual(path.equity.iloc[-1], (0.009 - 0.003) / 1.5)
        self.assertAlmostEqual(res["static_quantity_funding_sum"], 0.009)
        # the same carry against a 4% T-bill clears only 0.87%/yr: below the 2% excess bar
        res4, _, _ = oc.coin_result(f, mk, ix, "BTC", tb=0.04, t0=T0, t1=T1)
        self.assertFalse(res4["checks"]["excess_1x_L2_ge_2pct"])
        self.assertEqual(res4["verdict"], "NULL")

    def test_negative_or_fading_funding_is_null(self):
        f = funding(lambda k: 1e-4 if k < 60 else -2e-4)
        mk = candles(INST, lambda k: 100.0)
        ix = candles("BTC-USD", lambda k: 100.0)
        res, _, _ = oc.coin_result(f, mk, ix, "BTC", tb=0.0, t0=T0, t1=T1)
        self.assertFalse(res["checks"]["each_third_mean_rate_gt_0"])
        self.assertFalse(res["checks"]["negative_share_le_20pct"])
        self.assertEqual(res["verdict"], "NULL")

    def test_basis_and_rally_checks(self):
        f = funding(lambda k: 5e-4)
        mk = candles(INST, lambda k: 100.0 * (1.5 if 10 <= k < 12 else 1.0))   # a 50% spike inside the window
        ix = candles("BTC-USD", lambda k: 100.0)
        res, _, path = oc.coin_result(f, mk, ix, "BTC", tb=0.0, t0=T0, t1=T1)
        self.assertGreater(res["max_rise"], 0.4)
        self.assertFalse(res["checks"]["max_rise_lt_40pct"])
        self.assertEqual(res["verdict"], "NULL")
        self.assertLess(path.drawdown.min(), -0.2)                         # the short loses while the mark is high

    def test_xsection_summary(self):
        f = pd.concat([funding(lambda k: 1e-4), funding(lambda k: 3e-4, inst="ETH-USD_UM_XPERP-310404"),
                       funding(lambda k: -1e-4, inst="SOL-USD_UM_XPERP-310404", n=20)])
        d, s = oc.xsection(f, T0, T1, min_prints=50)
        self.assertEqual(s["instruments"], 3)
        self.assertEqual(s["with_at_least_50_prints"], 2)
        self.assertEqual(d.inst.iloc[0], "ETH-USD_UM_XPERP-310404")
        self.assertAlmostEqual(d.mean_annual_on_notional.iloc[0], 3e-4 * 3 * 365)
        self.assertEqual(s["share_with_mean_below_baseline_annual"], 0.0)


if __name__ == "__main__":
    unittest.main()
