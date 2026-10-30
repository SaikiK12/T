import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from scripts import run_settlehop as sh
from scripts import run_settlehop_pred as sp

H, DAY = sh.H, sh.DAY
D0 = 1_740_009_600_000                         # 2025-02-20 00:00 UTC, an invented day inside the lane's rows


def prem(t0, means, closes=None):
    n = len(means)
    m = np.asarray(means, float)
    return {"t": t0 + H * np.arange(n, dtype=np.int64), "mean": m,
            "close": m.copy() if closes is None else np.asarray(closes, float)}


def fund(ts, rates):
    r = np.asarray(rates, float)
    return np.asarray(ts, np.int64), r, np.concatenate([[0.0], np.cumsum(r)])


def binance_rate(P, m):
    return (P + float(np.clip(0.0001 - P, -0.0005, 0.0005))) * m / 8


class TestPredictedRate(unittest.TestCase):
    def test_constant_premium_gives_binance_formula(self):
        T = D0 + 16 * H
        p = prem(D0, np.full(16, 0.003))
        self.assertAlmostEqual(sp.predicted_rate(p, T, 8), 0.0025)          # 0.3% - 0.05% clamp, 8 h
        self.assertAlmostEqual(sp.predicted_rate(p, T, 4), 0.00125)         # a 4 h interval pays half
        q = prem(D0, np.full(16, 0.00012))
        self.assertAlmostEqual(sp.predicted_rate(q, T, 8), 0.0001)          # inside the clamp: the interest rate
        n = prem(D0, np.full(16, -0.004))
        self.assertAlmostEqual(sp.predicted_rate(n, T, 8), -0.0035)

    def test_linear_weights_and_the_last_hour_at_the_last_close(self):
        T = D0 + 8 * H                                   # 8 h interval: hours open at D0 .. D0 + 7 h
        means = [0.001 * (k + 1) for k in range(8)]       # hour h has mean h * 0.1%
        closes = list(means)
        closes[6] = 0.02                                  # hour 7 (opening T - 2 h) closes at 2%
        p = prem(D0, means, closes)
        known = sum((2 * h - 1) * 0.001 * h for h in range(1, 8))
        P = (known + 15 * 0.02) / 64                      # hour 8 is unknown at T - 1 h: it counts at hour 7's close
        self.assertAlmostEqual(sp.predicted_rate(p, T, 8), binance_rate(P, 8))

    def test_nothing_after_the_entry_is_read(self):
        T = D0 + 8 * H
        p = prem(D0, np.linspace(0.001, 0.004, 12))
        a = sp.predicted_rate(p, T, 8)
        q = {k: v.copy() for k, v in p.items()}
        q["mean"][7:] = 9.0                               # the bar opening at T - 1 h and everything after
        q["close"][7:] = 9.0
        self.assertEqual(sp.predicted_rate(q, T, 8), a)

    def test_missing_hours(self):
        T = D0 + 8 * H
        p = prem(D0, np.full(8, 0.002))
        gap = {k: np.delete(v, 6) for k, v in p.items()}  # no bar opening at T - 2 h: no prediction
        self.assertTrue(np.isnan(sp.predicted_rate(gap, T, 8)))
        hole = {k: np.delete(v, 2) for k, v in p.items()}  # an earlier hour missing: renormalized
        self.assertAlmostEqual(sp.predicted_rate(hole, T, 8), binance_rate(0.002, 8))


class TestPredSignals(unittest.TestCase):
    def test_intervals_live_rule_and_spread(self):
        T = D0 + 24 * H
        ts = [T - 14 * H, T - 8 * H, T - 4 * H, T]        # gaps 6 h, 4 h, 4 h
        fs = fund(ts, [0.0, 0.0, 0.0, 0.0])               # the settled S rates are never used as the signal
        fh = fund(D0 + H * np.arange(30), np.full(30, 0.0002))
        p = prem(D0 - 8 * H, np.full(40, 0.003))
        t, fhat, hp, es, m = sp.pred_signals(fs, fh, p)
        self.assertEqual(t.tolist(), [T - 4 * H, T])       # the 6 h gap is not a 4 or 8 h interval
        self.assertEqual(m.tolist(), [4, 4])
        np.testing.assert_allclose(fhat, [0.00125, 0.00125])
        np.testing.assert_allclose(es, [0.00125 - 0.0004] * 2)
        late = fund(D0 + H * np.arange(10), np.full(10, 0.0002))   # H stops settling at D0 + 9 h
        self.assertEqual(len(sp.pred_signals(fs, late, p)[0]), 0)


class TestReadersAndManifest(unittest.TestCase):
    def test_premium_rows_outside_the_lane_are_never_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / sp.PREM).mkdir()
            t = np.array([sh.T0 - H, sh.T0, sh.T0 + H, sh.T1 - H, sh.T1], np.int64)
            v = np.arange(5.0) / 1000
            pd.DataFrame({"t": t, "open": v, "high": v + 0.004, "low": v, "close": v + 0.002}).to_parquet(
                root / sp.PREM / "XUSDT.parquet")
            with mock.patch.object(sp.base, "DATA", root):           # the runner's own copy of R353's module
                p = sp.load_premium("XUSDT")
            self.assertEqual(p["t"].tolist(), [sh.T0, sh.T0 + H, sh.T1 - H])     # no 2020 row, no row from T1
            np.testing.assert_allclose(p["mean"], v[1:4] + 0.0015)
            np.testing.assert_allclose(p["close"], v[1:4] + 0.002)

    def test_data_paths_include_the_premium_files(self):
        rows = sh.read_symbols(sp.SYMBOLS)
        paths = sp.data_paths(rows)
        self.assertTrue(any(p.startswith("data/premiumIndexKlines_1h/") for p in paths) or not
                        (sh.DATA / sp.PREM).exists())
        self.assertFalse(any("/reserved/" in p for p in paths))
        self.assertFalse(any("dydx" in p for p in paths))


if __name__ == "__main__":
    unittest.main()
