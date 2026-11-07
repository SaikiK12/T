"""Synthetic checks for R385's helpers: no panel return and no DVOL value is read."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_dvolbeta as dv


class BetaTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(1)
        self.days = pd.date_range("2022-01-01", periods=200, freq="D")
        self.x = pd.Series(rng.normal(0, 0.03, 200), index=self.days)
        slopes = np.array([-2.0, 0.0, 1.5])
        noise = rng.normal(0, 0.01, (200, 3))
        self.R = pd.DataFrame(self.x.to_numpy()[:, None] * slopes + noise, index=self.days, columns=list("ABC"))

    def test_recovers_slope_and_starts_after_a_full_window(self):
        b = dv.rolling_beta(self.R, self.x)
        self.assertTrue(b.iloc[: dv.WIN - 1].isna().all().all())
        np.testing.assert_allclose(b.iloc[-1].to_numpy(), [-2.0, 0.0, 1.5], atol=0.25)

    def test_matches_polyfit_on_the_window(self):
        b = dv.rolling_beta(self.R, self.x)
        i = 150
        sl = slice(i - dv.WIN + 1, i + 1)
        want = np.polyfit(self.x.iloc[sl], self.R["A"].iloc[sl], 1)[0]
        self.assertAlmostEqual(b["A"].iloc[i], want, places=8)

    def test_future_rows_do_not_change_row_d(self):
        b0 = dv.rolling_beta(self.R, self.x)
        R2, x2 = self.R.copy(), self.x.copy()
        R2.iloc[151:] = 9.0
        x2.iloc[151:] = np.random.default_rng(2).normal(0, 1, 49)
        b1 = dv.rolling_beta(R2, x2)
        pd.testing.assert_series_equal(b0.iloc[150], b1.iloc[150])

    def test_min_obs_and_missing_rows(self):
        R = self.R.copy()
        R.iloc[120:, 0] = np.nan                                  # A has too few pairs by row 199
        b = dv.rolling_beta(R, self.x)
        self.assertTrue(np.isnan(b["A"].iloc[199]))
        self.assertTrue(np.isfinite(b["B"].iloc[199]))
        x = self.x.copy()
        x.iloc[100:130] = np.nan                                  # 30 missing days: 60 pairs left at row 129, ok
        self.assertTrue(np.isfinite(dv.rolling_beta(self.R, x)["B"].iloc[129]))
        x.iloc[100:131] = np.nan                                  # 31 missing: 59 left
        self.assertTrue(np.isnan(dv.rolling_beta(self.R, x)["B"].iloc[130]))


class DvolDailyTest(unittest.TestCase):
    def test_row_d_takes_the_last_bar_of_day_d_minus_1(self):
        import tempfile
        t = pd.date_range("2022-03-01", periods=72, freq="h")
        d = pd.DataFrame({"t": t.as_unit("ms").astype("int64").to_numpy(), "close": np.arange(72, dtype=float)})
        with tempfile.TemporaryDirectory() as tmp:
            p = f"{tmp}/d.parquet"
            d.to_parquet(p)
            s = dv.dvol_daily(p, pd.date_range("2022-03-01", periods=5, freq="D"))
        self.assertTrue(np.isnan(s.iloc[0]))                      # nothing before 00:00 of 2022-03-01
        self.assertEqual(s.iloc[1], 23.0)                         # bar opening 23:00 of 03-01 closes at 00:00 of 03-02
        self.assertEqual(s.iloc[2], 47.0)
        self.assertEqual(s.iloc[3], 71.0)
        self.assertTrue(np.isnan(s.iloc[4]))

    def test_change_is_a_log_difference_with_gaps(self):
        s = pd.Series([50.0, 55.0, np.nan, 60.0])
        c = dv.dvol_change(s)
        self.assertAlmostEqual(c.iloc[1], np.log(1.1))
        self.assertTrue(np.isnan(c.iloc[2]) and np.isnan(c.iloc[3]))


class ScoreTest(unittest.TestCase):
    def test_sides_are_mirrors_and_start_at_first_pred(self):
        days = pd.date_range("2021-12-30", periods=5, freq="D")
        beta = pd.DataFrame([[-1.0, 0.0, 1.0]] * 5, index=days, columns=list("ABC"))
        uni = pd.DataFrame(True, index=days, columns=beta.columns)
        lh, hl = dv.scores(beta, uni, "LH"), dv.scores(beta, uni, "HL")
        self.assertEqual(lh.index.get_level_values(0).min(), pd.Timestamp("2022-01-01"))
        self.assertEqual(lh.loc[(pd.Timestamp("2022-01-01"), "A")], 1.0)    # lowest beta scores highest: long leg
        self.assertEqual(hl.loc[(pd.Timestamp("2022-01-01"), "A")], -1.0)


class PipelineTest(unittest.TestCase):
    def test_four_books_run_on_a_synthetic_panel(self):
        rng = np.random.default_rng(3)
        days = pd.date_range("2021-09-01", "2024-06-30", freq="D")
        perps = [f"C{i:03d}USDT" for i in range(60)]
        n = len(days)
        mk = rng.normal(0, 0.03, n)
        dd = pd.Series(rng.normal(0, 0.05, n), index=days)
        slopes = rng.normal(0, 1, 60)
        r = mk[:, None] + dd.to_numpy()[:, None] * slopes + rng.normal(0, 0.03, (n, 60))
        close = 100 * np.cumprod(1 + r, axis=0)
        df = pd.DataFrame({"day": np.repeat(days.values, 60), "perp": np.tile(perps, n), "close": close.ravel(),
                           "ret": r.ravel(), "fund": 0.0001, "rank_qvol30": np.tile(np.arange(1, 61.0), n)})
        out = dv.analyze(df, lambda d: {c: dd.reindex(d) for c in dv.DVOL})
        res, ics, reps, desc, pick, passes, checks = out
        self.assertEqual(len(res), 4)
        self.assertIn(pick, [f"{c} {s}" for c, s in dv.BOOKS] + [None])
        for c in dv.DVOL:                                          # the mirror books' gross sums to zero
            a = np.array([x["gross"] for x in res[(c, "LH")]])
            b = np.array([x["gross"] for x in res[(c, "HL")]])
            np.testing.assert_allclose(a, -b, atol=1e-12)
        self.assertGreater(len(res[("BTC", "LH")]), 100)


if __name__ == "__main__":
    unittest.main()
