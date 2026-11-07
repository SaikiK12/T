import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_mlrank as ml


def synth(n_perps=40, start="2021-01-02", end="2023-06-30", seed=0, plant=0.0, missing=()):
    """A synthetic daily panel. Each perp has a fixed taker-buy share; with `plant`, the next day's return leans on
    it. `missing` = [(perp index, day)] rows that do not exist (the perp did not trade)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    rows = []
    for i in range(n_perps):
        tb = 0.5 + 0.05 * (i / (n_perps - 1) - 0.5)          # 0.475 .. 0.525
        lean = plant * (tb - 0.5) / 0.025                    # -plant .. +plant per day
        r = rng.normal(lean, 0.02, len(days))
        r[0] = 0.0
        close = 100 * np.cumprod(1 + r)
        for j, d in enumerate(days):
            rows.append({"day": d.date(), "perp": f"P{i:02d}USDT", "close": close[j], "ret": r[j] if j else np.nan,
                         "range": abs(r[j]) + 0.01, "qvol": 1e6 * (1 + i), "trades": 1000 + i, "taker_buy": tb,
                         "fund": rng.normal(0.0001, 0.0001), "premium": 0.0, "basis": 0.0, "spot_qvol": 5e5,
                         "wick_up": 0.001, "wick_dn": -0.001, "oi_usd": 1e7, "top_ls_pos": 1.0, "ls_acc": 1.0,
                         "taker_ls": 1.0, "n_venues": 3, "upbit_rel": np.nan, "age_days": np.nan,
                         "rank_qvol30": n_perps - i, "mcap_est": 1e9 * (1 + i)})
    df = pd.DataFrame(rows)
    for c in ml.COLS:
        if c not in df:
            df[c] = np.nan
    if missing:
        drop = {(f"P{i:02d}USDT", pd.Timestamp(d).date()) for i, d in missing}
        df = df[[(p, d) not in drop for p, d in zip(df.perp, df.day)]]
    return df.reset_index(drop=True)


class FeatureTest(unittest.TestCase):
    def test_features_use_only_the_past(self):
        df = synth(n_perps=8, end="2021-06-30")
        cut = pd.Timestamp("2021-05-01").date()
        later = df.day > cut
        df2 = df.copy()
        for c in ("close", "ret", "range", "qvol", "fund", "taker_buy", "oi_usd", "mcap_est"):
            df2.loc[later, c] = df2.loc[later, c] * 3 + 1
        f1, f2 = ml.features(ml.wide(df)), ml.features(ml.wide(df2))
        for k in f1:
            a, b = f1[k].loc[:"2021-05-01"], f2[k].loc[:"2021-05-01"]
            pd.testing.assert_frame_equal(a, b, obj=k)

    def test_ranks_are_centred_and_missing_is_neutral(self):
        df = synth(n_perps=5, end="2021-03-31")
        w = ml.wide(df)
        f = ml.features(w)
        f["basis"].iloc[:, 0] = np.nan                        # one perp without spot
        uni = ml.universe(w)
        X = ml.stack(f, ["qvol30", "basis"], uni)
        day = X.xs(pd.Timestamp("2021-03-01"), level=0)
        self.assertAlmostEqual(day.qvol30.sum(), 0.0)
        self.assertAlmostEqual(day.qvol30.max(), 0.4)       # 5 names: -0.4 .. +0.4
        self.assertEqual(day.basis.iloc[0], 0.0)

    def test_targets(self):
        df = synth(n_perps=2, end="2021-01-20", missing=[(0, "2021-01-12")])
        w = ml.wide(df)
        c = w["close"]["P00USDT"]
        r1, f1 = ml.targets(w, 1)
        d = pd.Timestamp("2021-01-10")
        self.assertAlmostEqual(r1.loc[d, "P00USDT"], c[d + pd.Timedelta(days=1)] / c[d] - 1)
        self.assertEqual(r1.loc[pd.Timestamp("2021-01-11"), "P00USDT"], 0.0)   # next row missing: flat
        self.assertTrue(np.isnan(r1.loc[pd.Timestamp("2021-01-12"), "P00USDT"]))  # no entry
        r3, f3 = ml.targets(w, 3)
        d = pd.Timestamp("2021-01-11")
        self.assertAlmostEqual(r3.loc[d, "P00USDT"], c[d + pd.Timedelta(days=3)] / c[d] - 1)
        fund = w["fund"]["P00USDT"]
        self.assertAlmostEqual(f3.loc[d, "P00USDT"], fund[d + pd.Timedelta(days=2)] + fund[d + pd.Timedelta(days=3)])
        self.assertTrue(r3.iloc[-3:].isna().all().all())


class ModelTest(unittest.TestCase):
    def test_models_recover_a_linear_signal(self):
        rng = np.random.default_rng(1)
        days = np.repeat(np.arange(200), 50)
        X = rng.uniform(-0.5, 0.5, (len(days), 3))
        y = 0.3 * X[:, 0] - 0.2 * X[:, 1] + rng.normal(0, 0.3, len(days))
        Xte = rng.uniform(-0.5, 0.5, (500, 3))
        for m in ("ridge", "ic", "gbm"):
            p, w = ml.fit_predict(m, X, y, Xte, days_tr=days)
            self.assertGreater(np.corrcoef(p, 0.3 * Xte[:, 0] - 0.2 * Xte[:, 1])[0, 1], 0.8, m)
            if w is not None:
                self.assertGreater(w[0], 0)
                self.assertLess(w[1], 0)

    def test_walk_forward_is_purged(self):
        df = synth(n_perps=35, end="2022-04-30")
        w, f, uni = ml.prepare(df)
        X = ml.stack(f, ml.PIT, uni)
        ret, fund = ml.targets(w, 7)
        y = ml.rank_target(ret - fund, uni).stack(future_stack=True).reindex(X.index)
        seen = []

        def fake(model, X_tr, y_tr, X_te, days_tr=None):
            seen.append(pd.DatetimeIndex(days_tr).max())
            return np.zeros(len(X_te)), None

        with mock.patch.object(ml, "fit_predict", fake):
            pred, _ = ml.walk_forward(X, y, "ridge", 7, ml.PIT)
        months = ml.month_starts(X.index.get_level_values(0).unique())
        self.assertEqual(len(seen), len(months))
        for m0, last in zip(months, seen):
            self.assertLessEqual(last, m0 - pd.Timedelta(days=8))
        self.assertEqual(pred.index.get_level_values(0).min(), pd.Timestamp(ml.FIRST_PRED))


class BookTest(unittest.TestCase):
    def test_legs_and_random_ties(self):
        idx = pd.MultiIndex.from_product([pd.date_range("2022-01-01", periods=14), [f"S{i:02d}" for i in range(40)]])
        pred = pd.Series(np.tile(np.arange(40.0), 14), index=idx)
        lg = ml.legs(pred, 1)
        L, S = lg[pd.Timestamp("2022-01-01")]
        self.assertEqual(len(L), 8)
        self.assertEqual(set(L), {f"S{i:02d}" for i in range(32, 40)})
        self.assertEqual(set(S), {f"S{i:02d}" for i in range(8)})
        self.assertEqual(len(ml.legs(pred, 7)), 2)
        flat = pd.Series(0.0, index=idx)                        # all tied: legs are random, not alphabetical
        lgf = ml.legs(flat, 1)
        self.assertNotEqual(set(lgf[pd.Timestamp("2022-01-01")][0]), {f"S{i:02d}" for i in range(32, 40)})
        self.assertNotEqual(lgf[pd.Timestamp("2022-01-01")][0], lgf[pd.Timestamp("2022-01-02")][0])

    def test_book_and_windows(self):
        days = pd.date_range("2022-01-01", periods=3)
        ret = pd.DataFrame({"A": [0.02, 0.01, 0.0], "B": [-0.01, np.nan, 0.0]}, index=days)
        fund = pd.DataFrame({"A": [0.001, 0.0, 0.0], "B": [0.002, 0.0, 0.0]}, index=days)
        rows = ml.book({days[0]: (("A",), ("B",)), days[1]: (("A",), ("B",))}, ret, fund)
        self.assertEqual(len(rows), 1)                           # B has no return on day 2: no book
        self.assertAlmostEqual(rows[0]["gross"], (0.02 - 0.001) + (0.01 + 0.002))
        end = pd.Timestamp("2023-12-31").value // 10**6
        self.assertEqual(list(ml.window_mask(np.array([end - 7 * ml.DAY, end - 6 * ml.DAY]), 7, "disc")),
                         [True, False])


class EndToEndTest(unittest.TestCase):
    def test_planted_signal_is_found_and_null_is_not(self):
        df = synth(n_perps=40, end="2024-06-30", plant=0.004, seed=3)
        res, ics, weights = ml.build(df, models=("ridge", "ic"))
        out = ml.analyze(res, ics, weights)
        r = out["strategies"]["ridge h1 pit"]
        self.assertGreater(r["disc"]["rank_ic"]["mean"], 0.05)
        self.assertGreater(r["valid"]["gross"]["mean_bp"], 0)
        self.assertGreater(out["linear_weights"]["ic h1 pit"]["taker7"], 0)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertIn("ridge h1", out["all_minus_pit"])
        null = ml.analyze(*ml.build(synth(n_perps=40, end="2024-06-30", seed=4), models=("ridge",)))
        self.assertLess(abs(null["strategies"]["ridge h1 pit"]["valid"]["rank_ic"]["mean"]), 0.05)

    def test_plumbing_reads_no_return(self):
        df = synth(n_perps=35, end="2022-03-31")
        out = ml.plumbing(df)
        self.assertEqual(out["universe_median"], 35.0)
        self.assertEqual(out["prediction_months"], 3)
        self.assertIn("taker7", out["coverage_in_universe"])


if __name__ == "__main__":
    unittest.main()
