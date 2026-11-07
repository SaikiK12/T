"""Synthetic checks for R380's gate, residualisation, timing and pipeline. No panel return is read."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_hvrev as hv


def synth(n_perps=100, days=1700, seed=1):
    rng = np.random.default_rng(seed)
    d = pd.date_range("2021-01-02", periods=days, freq="D")
    scale = rng.uniform(0.01, 0.08, n_perps)
    ret = rng.normal(0, 1, (days, n_perps)) * scale
    df = pd.DataFrame({"day": np.repeat(d, n_perps), "perp": np.tile([f"P{i:03d}USDT" for i in range(n_perps)], days),
                       "ret": ret.ravel(), "fund": rng.normal(0, 1e-4, days * n_perps),
                       "rank_qvol30": np.tile(np.arange(1, n_perps + 1, dtype=float), days)})
    df["close"] = df.groupby("perp").ret.transform(lambda r: 100 * (1 + r).cumprod())
    df["day"] = df.day.dt.date
    return df


class DayPredTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = synth()
        cls.w = hv.wide(cls.df)
        cls.uni, cls.sig = hv.universe(cls.w), hv.signals(cls.w)
        cls.d = pd.Timestamp("2023-06-04")
        cls.perps = np.array(cls.w["close"].columns)

    def test_gate_keeps_the_top_tercile_by_vol30(self):
        idx, p, r2, n = hv.day_pred(self.sig, self.uni, self.d, 9, "hv", False, np.random.default_rng(1))
        self.assertEqual(n, 100 // 3)
        v = self.sig["vol30"].loc[self.d]
        self.assertGreaterEqual(v.iloc[idx].min(), np.sort(v.to_numpy())[-34] - 1e-12)

    def test_raw_score_is_minus_the_lookback_return_ranked(self):
        idx, p, r2, n = hv.day_pred(self.sig, self.uni, self.d, 9, "all", False, np.random.default_rng(1))
        m = self.sig["mom63"].loc[self.d].to_numpy()[idx]
        self.assertEqual(int(np.argmax(p)), int(np.argmin(m)))
        self.assertEqual(int(np.argmin(p)), int(np.argmax(m)))

    def test_residual_is_orthogonal_to_the_tilt_ranks(self):
        idx, e, r2, n = hv.day_pred(self.sig, self.uni, self.d, 9, "hv", True, np.random.default_rng(1))
        X = np.column_stack([self.sig[c].loc[self.d].to_numpy()[idx] for c in ("vol30", "mom7", "max7")])
        A = np.column_stack([np.ones(n), *[hv.rk(X[:, j]) for j in range(3)]])
        self.assertTrue(np.allclose(A.T @ e, 0, atol=1e-9))
        self.assertTrue(0 <= r2 < 1)

    def test_prediction_reads_rows_up_to_d_only(self):
        a = hv.day_pred(self.sig, self.uni, self.d, 10, "hv", True, np.random.default_rng(1))
        df2 = self.df.copy()
        later = pd.to_datetime(df2.day) > self.d
        df2.loc[later, "ret"] = 0.5
        w2 = hv.wide(df2)
        b = hv.day_pred(hv.signals(w2), hv.universe(w2), self.d, 10, "hv", True, np.random.default_rng(1))
        self.assertTrue(np.array_equal(a[0], b[0]))
        self.assertTrue(np.allclose(a[1], b[1]))


class PipelineTest(unittest.TestCase):
    def test_build_and_analyze_on_noise(self):
        res, extra = hv.build(synth())
        self.assertEqual(set(res), set(hv.STRATS))
        self.assertEqual(hv.TRIALS, 8)
        out = hv.analyze(res, extra)
        self.assertIn(out["verdict"], ("PARTIAL", "NULL"))
        self.assertEqual(len(out["strategies"]), 8)
        self.assertIn(out["pick"], [hv.label(k) for k in hv.FAMILY] + [None])      # never a control
        rows = res[hv.FAMILY[0]]
        self.assertTrue(all(r["n_long"] == r["n_short"] for r in rows))
        self.assertEqual(rows[0]["t"], int(pd.Timestamp(hv.FIRST_PRED).value // 10**6))
        gaps = np.diff([r["t"] for r in rows]) // 86_400_000
        self.assertTrue(set(gaps) <= {7, 14})                                      # weekly grid, skipped weeks only
        s = out["strategies"][hv.label(hv.FAMILY[0])]
        self.assertGreater(s["disc"]["1x"]["periods"], 80)
        self.assertLess(s["disc"]["3x"]["mean_bp"], s["disc"]["1x"]["mean_bp"])    # costs bite


if __name__ == "__main__":
    unittest.main()
