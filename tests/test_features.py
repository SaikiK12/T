import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import features, panel
from lab.panel import HOUR, Panel


def synthetic(T=24 * 220, S=10, seed=3):
    """Random-walk hourly panel with symbols that list late and delist early, starting on a UTC day boundary."""
    rng = np.random.default_rng(seed)
    t0 = panel.ms("2021-01-01")
    t = np.arange(t0, t0 + T * HOUR, HOUR)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.006, (T, S)), 0))
    o = np.vstack([c[:1], c[:-1]]) * (1 + rng.normal(0, 0.001, (T, S)))
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.004, (T, S)))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.004, (T, S)))
    v = rng.uniform(50, 150, (T, S))
    f = {"open": o, "high": h, "low": l, "close": c, "volume": v, "quote_volume": v * c,
         "count": rng.integers(100, 900, (T, S)).astype(float), "taker_buy_volume": v * rng.uniform(0.3, 0.7, (T, S)),
         "taker_buy_quote_volume": v * c * 0.5, "premium": rng.normal(0, 5e-4, (T, S)),
         "funding": np.repeat(rng.normal(1e-4, 5e-5, (T // 8 + 1, S)), 8, axis=0)[:T]}
    f["fund_event"] = np.where(np.arange(T)[:, None] % 8 == 0, f["funding"], np.nan)
    f = {k: x.astype(np.float32) for k, x in f.items()}
    syms = ["BTCUSDT"] + [f"S{i}USDT" for i in range(S - 1)]
    for j in range(2, S, 3):                       # late listing
        for x in f.values():
            x[: 700 + 37 * j, j] = np.nan
    for j in range(3, S, 4):                       # early delisting
        for x in f.values():
            x[T - 500 - 11 * j:, j] = np.nan
    return Panel(t, syms, f)


class PanelTests(unittest.TestCase):
    def test_ffill_keeps_leading_gaps(self):
        x = np.array([[np.nan], [1.0], [np.nan], [np.nan], [4.0], [np.nan]], dtype=np.float32)
        out = panel.ffill(x)[:, 0]
        np.testing.assert_array_equal(out, [np.nan, 1, 1, 1, 4, 4])

    def test_resample_aggregates_each_bar(self):
        p = synthetic()
        b = panel.resample(p, 4)
        j, n = 1, 5
        win = slice(n * 4, n * 4 + 4)
        self.assertAlmostEqual(float(b["high"][n, j]), float(p["high"][win, j].max()), places=4)
        self.assertAlmostEqual(float(b["low"][n, j]), float(p["low"][win, j].min()), places=4)
        self.assertAlmostEqual(float(b["open"][n, j]), float(p["open"][win.start, j]), places=4)
        self.assertAlmostEqual(float(b["close"][n, j]), float(p["close"][win.stop - 1, j]), places=4)
        self.assertAlmostEqual(float(b["volume"][n, j]), float(p["volume"][win, j].sum()), places=2)

    def test_resample_marks_partial_price_blocks_missing(self):
        p = synthetic(T=24 * 12, S=4)
        j, n = 1, 3
        p["close"][n * 4 + 2, j] = np.nan
        b = panel.resample(p, 4)
        self.assertEqual(int(b["coverage"][n, j]), 3)
        self.assertTrue(np.isnan(b["close"][n, j]))

    def test_align_shows_a_bar_only_after_it_closes(self):
        p = synthetic()
        daily = panel.resample(p, 24)["close"]
        a = panel.align(daily, 24)
        j, d = 1, 20
        for h in range(23):                              # before the day's last hour: the previous day's close
            self.assertAlmostEqual(float(a[d * 24 + h, j]), float(daily[d - 1, j]), places=4)
        self.assertAlmostEqual(float(a[d * 24 + 23, j]), float(daily[d, j]), places=4)   # final once the day has closed

    def test_alignment_and_smoothed_features_do_not_extend_past_missing_bar(self):
        x = np.array([[1.0], [np.nan], [3.0]], np.float32)
        np.testing.assert_array_equal(panel.align(x, 4)[:, 0],
                                      [np.nan] * 3 + [1.0] * 4 + [np.nan] * 4 + [3.0])
        p = synthetic(T=24 * 40, S=2)
        p["close"][600, 1] = np.nan
        f = features.Bank(p).get("ema_cross", 4, (3, 5))
        self.assertTrue(np.isfinite(f[602, 1]))
        self.assertTrue(np.isnan(f[603:607, 1]).all())

    def test_prev_bar_hides_the_current_bar(self):
        x = np.arange(5, dtype=np.float32).reshape(-1, 1)
        out = features.prev_bar(x, 3)[:, 0]
        np.testing.assert_array_equal(out, [np.nan] * 3 + [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3])

    def test_liquidity_rank_orders_by_trailing_volume(self):
        p = synthetic(T=24 * 40)
        live = {k: np.nan_to_num(v, nan=1.0) for k, v in p.f.items()}
        live["quote_volume"] = np.tile(np.arange(1, p.S + 1, dtype=np.float32) * 1000, (p.T, 1))   # last symbol most liquid
        r = panel.liquidity_rank(Panel(p.t, p.symbols, live))
        self.assertEqual(float(r[-1, p.S - 1]), 1.0)
        self.assertEqual(float(r[-1, 0]), float(p.S))

    def test_load_panel_places_rows_on_the_clock(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "klines_1h").mkdir()
            t0 = panel.ms("2021-01-01")
            df = pd.DataFrame({"t": [t0 + 5 * HOUR, t0 + 6 * HOUR], "open": 1.0, "high": 2.0, "low": 0.5, "close": [1.5, 1.7],
                               "volume": 10.0, "quote_volume": 15.0, "count": 3, "taker_buy_volume": 4.0, "taker_buy_quote_volume": 6.0})
            df.to_parquet(root / "klines_1h" / "AAAUSDT.parquet", index=False)
            p = panel.load_panel(root=root, end="2021-01-02")
        self.assertEqual(p.T, 48)
        self.assertTrue(np.isnan(p["close"][4, 0]))
        self.assertAlmostEqual(float(p["close"][5, 0]), 1.5, places=5)
        self.assertAlmostEqual(float(p["close"][6, 0]), 1.7, places=5)


class FeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = synthetic()
        cls.bank = features.Bank(cls.p)

    def test_ema_ratio_matches_a_manual_ema(self):
        c = self.p["close"][:, 1].astype(np.float64)
        alpha = 2 / (21 + 1)
        e = np.empty_like(c)
        e[0] = c[0]
        for i in range(1, len(c)):
            e[i] = alpha * c[i] + (1 - alpha) * e[i - 1]
        got = self.bank.get("ema_ratio", 1, (21,))[:, 1]
        np.testing.assert_allclose(got[100:], (c / e - 1)[100:], rtol=2e-3, atol=2e-4)

    def test_bounded_features_stay_in_range(self):
        rsi = self.bank.get("rsi", 1, (14,))
        self.assertTrue(np.nanmin(rsi) >= 0 and np.nanmax(rsi) <= 100)
        d = self.bank.get("donch", 4, (20,))
        self.assertTrue(np.nanmin(d) >= -1e-6 and np.nanmax(d) <= 1 + 1e-6)

    def test_calendar_features(self):
        h = self.bank.get("hour", 1, ())
        self.assertEqual(float(h[0, 0]), 0.0)
        self.assertEqual(float(h[25, 3]), 1.0)
        self.assertEqual(float(self.bank.get("dow", 1, ())[0, 0]), 4.0)   # 2021-01-01 was a Friday (Monday = 0)

    def test_bins_have_expected_shape_and_missing_marker(self):
        elig = ~np.isnan(self.p["close"])
        specs = [s for s in features.default_specs() if s.family in ("ret", "rsi", "hour")][:12]
        v, names = features.views(self.bank, specs, elig)
        self.assertEqual(v.shape, (12, self.p.T, self.p.S))
        self.assertEqual(v.dtype, np.int8)
        xs_rows = [i for i, sp in enumerate(specs) if sp.norm[0] == "xs"]
        self.assertTrue(xs_rows)
        for i in xs_rows:
            self.assertTrue((v[i][~elig] == -1).all())          # a symbol that is not trading never gets a bucket
        self.assertGreaterEqual(int(v.min()), -1)
        xs = features.bins_xs(self.bank.get("ret", 1, (24,)), elig, 8)
        used = np.unique(xs[xs >= 0])
        self.assertEqual(list(used), list(range(8)))                         # every bucket, including 0, gets used

    def test_fixed_bins_reject_infinities(self):
        got = features.bins_fixed(np.array([[-np.inf, -1.0, 0.0, 1.0, np.inf, np.nan]]), (-0.5, 0.5))
        np.testing.assert_array_equal(got, [[-1, 0, 1, 2, -1, -1]])

    def test_default_spec_names_are_unique(self):
        names = [s.name for s in features.default_specs()]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreater(len(names), 200)


class CausalityCanary(unittest.TestCase):
    def test_no_default_feature_reads_the_future(self):
        p = synthetic(T=24 * 200, S=8)
        bad = features.check_causal(p, features.default_specs(), cuts=(24 * 90 + 5, 24 * 140 + 17, 24 * 170 + 11))
        self.assertEqual(bad, [])

    def test_canary_catches_a_deliberate_leak(self):
        features.FAMILIES["leaky"] = lambda B, k: np.vstack([B.bars(1)["close"][1:], B.bars(1)["close"][-1:]])
        try:
            p = synthetic(T=24 * 60, S=4)
            spec = features.Spec("leaky", 1, (), ("fix", (1.0,)))
            self.assertEqual(features.check_causal(p, [spec], cuts=(500,)), [spec.name])
        finally:
            del features.FAMILIES["leaky"]


if __name__ == "__main__":
    unittest.main()
