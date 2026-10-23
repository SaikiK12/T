import json
import unittest

import numpy as np
import pandas as pd

from scripts import run_fundgate as fg


def panel(days=40, perps=60, seed=0):
    """A synthetic daily panel: perp k has rank k+1 every day except where a test changes it."""
    rng = np.random.default_rng(seed)
    d = pd.date_range("2021-01-02", periods=days, freq="D")
    rows = [{"day": day.date(), "perp": f"C{k}USDT" if k else "BTCUSDT", "ret": rng.normal(0, 0.03),
             "fund": rng.normal(3e-4, 2e-4), "rank_qvol30": float(k + 1)} for day in d for k in range(perps)]
    return pd.DataFrame(rows)


class MarketTest(unittest.TestCase):
    def test_trimmed_means_use_the_top_of_the_row_and_the_basket_the_top_of_the_day_before(self):
        df = panel()
        day5, day6 = pd.Timestamp("2021-01-06").date(), pd.Timestamp("2021-01-07").date()
        # on row 5, perp 55 (outside the top) has a huge return; on row 6 it is rank 1 but was not in row 5's top
        df.loc[(df.day == day5) & (df.perp == "C55USDT"), "ret"] = 5.0
        df.loc[(df.day == day6) & (df.perp == "C55USDT"), ["ret", "rank_qvol30"]] = [9.0, 1.0]
        mk = fg.market(df)
        r5 = df[(df.day == day5) & (df.rank_qvol30 <= 50)]
        self.assertAlmostEqual(mk.loc["2021-01-06", "R"], fg.sps.trim_mean(r5.ret, 0.1))
        self.assertAlmostEqual(mk.loc["2021-01-06", "F"], fg.sps.trim_mean(r5.fund, 0.1))
        b6 = df[(df.day == day6) & df.perp.isin(r5.perp)]
        self.assertAlmostEqual(mk.loc["2021-01-07", "B"], b6.ret.mean())
        self.assertNotIn("C55USDT", set(b6.perp))
        self.assertAlmostEqual(mk.loc["2021-01-07", "Bf"], b6.fund.mean())
        self.assertTrue(np.isnan(mk.B.iloc[0]))                         # no basket before the first row
        btc = df[(df.day == day6) & (df.perp == "BTCUSDT")]
        self.assertAlmostEqual(mk.loc["2021-01-07", "btc"], btc.ret.iloc[0])

    def test_too_few_coins_is_a_gap(self):
        df = panel(days=5)
        day = pd.Timestamp("2021-01-04").date()
        df = df[~((df.day == day) & (df.rank_qvol30 > 20))]                # 20 coins on that row
        mk = fg.market(df)
        self.assertTrue(np.isnan(mk.loc["2021-01-04", "F"]) and np.isnan(mk.loc["2021-01-04", "R"]))
        self.assertTrue(np.isnan(mk.loc["2021-01-04", "B"]))                # 20 of the held 50 traded
        self.assertTrue(np.isfinite(mk.loc["2021-01-05", "R"]))


class SignalTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        idx = pd.date_range("2021-01-02", periods=500, freq="D")
        self.R = pd.Series(rng.normal(0, 0.03, len(idx)), idx)
        self.F = pd.Series(3e-4 + 0.004 * self.R + rng.normal(0, 1e-4, len(idx)), idx)

    def test_slope_is_ols_over_the_trailing_window(self):
        s = fg.rolling_slope(self.F, self.R)
        self.assertTrue(s.iloc[:fg.NEED_LOOK - 1].isna().all())
        self.assertAlmostEqual(s.iloc[100], np.polyfit(self.R.iloc[71:101], self.F.iloc[71:101], 1)[0], places=10)
        R = self.R.copy()
        R.iloc[95:101] = np.nan                                              # 24 left in the window
        self.assertTrue(np.isnan(fg.rolling_slope(self.F, R).iloc[100]))

    def test_upday_funding(self):
        u = fg.upday_funding(self.F, self.R)
        w = slice(71, 101)
        up = self.R.iloc[w] > 0
        self.assertAlmostEqual(u.iloc[100], self.F.iloc[w][up].mean())
        R = pd.Series(-0.01, self.R.index)
        R.iloc[90:97] = 0.01                                                 # 7 up days
        self.assertTrue(np.isnan(fg.upday_funding(self.F, R).iloc[100]))

    def test_z_reads_only_the_past(self):
        m = fg.rolling_slope(self.F, self.R)
        z = fg.trailing_z(m)
        m2 = m.copy()
        m2.iloc[300:] += 1.0
        z2 = fg.trailing_z(m2)
        pd.testing.assert_series_equal(z.iloc[:300], z2.iloc[:300])
        self.assertEqual(z2.iloc[300], fg.ZCLIP)
        prev = m.iloc[400 - fg.ZLOOK:400]
        self.assertAlmostEqual(z.iloc[400], np.clip((m.iloc[400] - prev.mean()) / prev.std(), -3, 3))
        self.assertTrue(z.iloc[:fg.NEED_LOOK - 1 + fg.ZNEED].isna().all())

    def test_forward_sums_the_next_h_rows(self):
        r = pd.Series([0.1, 0.2, -0.1, 0.05, np.nan, 0.0], pd.date_range("2024-01-01", periods=6))
        y = fg.forward(r, 2)
        self.assertAlmostEqual(y.iloc[0], np.log(1.2) + np.log(0.9))
        self.assertTrue(np.isnan(y.iloc[2]) and np.isnan(y.iloc[3]) and np.isnan(y.iloc[5]))


class TableTest(unittest.TestCase):
    def test_targets_stay_inside_their_window(self):
        idx = pd.date_range("2023-06-01", "2024-03-01", freq="D")
        rng = np.random.default_rng(2)
        mk = pd.DataFrame({"F": rng.normal(3e-4, 1e-4, len(idx)), "R": rng.normal(0, 0.02, len(idx)),
                           "B": rng.normal(0, 0.02, len(idx)), "btc": rng.normal(0, 0.02, len(idx))}, idx)
        t = fg.table(mk)
        self.assertTrue(np.isfinite(t.loc["2023-12-24", "y7"]))
        self.assertTrue(np.isnan(t.loc["2023-12-25", "y7"]))             # would read 2024-01-01
        self.assertTrue(np.isnan(t.loc["2023-12-02", "y30"]) and np.isfinite(t.loc["2023-12-01", "y30"]))
        self.assertTrue(np.isfinite(t.loc["2024-01-01", "b7"]))
        self.assertEqual(t.loc["2023-12-31", "win"], "disc")


class PlantedTest(unittest.TestCase):
    def table(self, beta, seed):
        rng = np.random.default_rng(seed)
        idx = pd.date_range("2021-04-01", "2026-09-30", freq="D")
        t = pd.DataFrame(index=idx)
        t["win"] = fg.window_of(idx)
        for m in fg.MEASURES:
            t[f"x_{m}"] = pd.Series(rng.normal(0.3, 1, len(idx)), idx).rolling(10, min_periods=1).mean()
        t["mom30"] = rng.normal(0, 0.1, len(idx))
        r = pd.Series(rng.normal(0.001, 0.02, len(idx)), idx) + beta * 0.01 * t.x_slope.shift(1)
        for h in fg.HORIZONS:
            t[f"y{h}"] = fg.forward(r, h)
            t[f"b{h}"] = fg.forward(r + rng.normal(0, 0.01, len(idx)), h)
        return t

    def test_planted_claim_passes_crowding_passes_null_does_not(self):
        for beta, want in ((1.0, "claim"), (-1.0, "crowding")):
            res = fg.trial(self.table(beta, 3), "slope", 7)
            self.assertTrue(res["pass"], res)
            self.assertEqual(res["direction"], want)
            self.assertGreater(abs(res["valid"]["t_nonoverlap"]), 1.5)
            self.assertGreater(abs(res["valid_given_mom"]["t"]), fg.T_MIN)   # momentum here is unrelated noise
        null = fg.trial(self.table(0.0, 4), "upfund", 7)
        self.assertFalse(null["pass"])
        self.assertLess(abs(null["valid"]["t"]), fg.T_MIN)

    def test_drift_alone_is_not_a_slope(self):
        t = self.table(0.0, 5)
        t["y30"] = t.y30 + 0.05                                              # a strong market, the same every day
        self.assertLess(abs(fg.trial(t, "slope", 30)["valid"]["t"]), fg.T_MIN)


class ResidualTest(unittest.TestCase):
    def test_residual_removes_the_linear_part(self):
        idx = pd.date_range("2024-01-01", periods=50)
        z = pd.Series(np.arange(50.0), idx)
        x = 2.0 * z + 1.0 + pd.Series(np.sin(np.arange(50.0)), idx)
        x.iloc[3] = np.nan
        r = fg.residual(x, z)
        self.assertTrue(np.isnan(r.iloc[3]))
        self.assertAlmostEqual(float(np.corrcoef(r.dropna(), z[r.notna()])[0, 1]), 0.0, places=10)


class RuleTest(unittest.TestCase):
    def test_gate_positions_costs_and_funding(self):
        idx = pd.date_range("2024-01-01", periods=5)
        x = pd.Series([1.0, 0.5, -1.0, np.nan, 2.0], idx)
        r = pd.Series([0.0, 0.01, 0.02, 0.03, 0.04], idx)
        f = pd.Series([0.0, 0.001, 0.001, 0.001, 0.001], idx)
        net, p, sw = fg.rule_days(x, r, f, "claim", 1e-3)
        np.testing.assert_array_equal(p, [1, 1, 0, 0, 1])
        np.testing.assert_array_equal(sw, [1, 0, 1, 0, 1])
        self.assertAlmostEqual(net.iloc[0], 0.01 - 0.001 - 1e-3)          # entry on row 1, earns row 2
        self.assertAlmostEqual(net.iloc[1], 0.02 - 0.001)
        self.assertAlmostEqual(net.iloc[2], -1e-3)                         # the exit costs, flat earns nothing
        net, p, _ = fg.rule_days(x, r, f, "crowding", 0.0)
        np.testing.assert_array_equal(p, [0, 0, 1, 0, 0])                  # NaN is flat on both sides


class EndToEndTest(unittest.TestCase):
    def test_analyze_runs_on_a_full_length_panel_and_serializes(self):
        rng = np.random.default_rng(6)
        days = pd.date_range("2021-01-02", "2026-09-30", freq="D")
        n, k = len(days), 52
        df = pd.DataFrame({"day": np.repeat(days.date, k), "perp": np.tile(["BTCUSDT"] + [f"C{i}USDT" for i in
                                                                                         range(1, k)], n),
                           "ret": rng.normal(0, 0.03, n * k), "fund": rng.normal(3e-4, 2e-4, n * k),
                           "rank_qvol30": np.tile(np.arange(1.0, k + 1), n)})
        mk, t = fg.build(df)
        res = fg.analyze(t, mk)
        self.assertEqual(len(res["tests"]), fg.TRIALS)
        self.assertIn(res["verdict"], ("NULL", "PARTIAL"))
        self.assertEqual(set(res["descriptives"]["by_year"]), {str(y) for y in range(2021, 2027)})
        self.assertIn("api", res["rules"]["slope claim btc"]["valid"])
        self.assertGreater(res["rules"]["upfund crowding basket"]["disc"]["1x"]["days"], 800)
        json.dumps(res, default=str)
        p = fg.plumbing(mk, t)
        self.assertEqual(p["median_top_coins"], 50.0)


if __name__ == "__main__":
    unittest.main()
