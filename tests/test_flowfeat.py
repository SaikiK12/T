"""Tests for lab.flowfeat: the raw order-flow feature builder that feeds the forward lanes.

These build tiny arrays in memory and check the feature wiring directly (log offsets, NaN lead
edges, quadrant encoding, trailing means, binning dispatch, and the parquet reader on the clock).
No network, no real data folder.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import flowfeat, panel
from lab.panel import HOUR


def metrics(T, S, **over):
    m = {c: np.ones((T, S), np.float32) for c in flowfeat.METRIC_COLS}
    m.update({k: np.asarray(v, np.float32) for k, v in over.items()})
    return m


def book(T, S, **over):
    b = {c: np.ones((T, S), np.float32) for c in flowfeat.BOOK_COLS}
    b.update({k: np.asarray(v, np.float32) for k, v in over.items()})
    return b


class RawFeatureTests(unittest.TestCase):
    def test_oi_chg_is_the_log_change_over_n_hours_with_a_nan_lead(self):
        T, S = 30, 1
        oi = (2.0 ** np.arange(T)).reshape(T, 1).astype(np.float32)
        f = flowfeat.raw_features(metrics(T, S, oi=oi), None, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        x = f["oi_chg[4]"][:, 0]
        self.assertTrue(np.all(np.isnan(x[:4])))
        np.testing.assert_allclose(x[4:], 4 * np.log(2.0), rtol=1e-5)
        np.testing.assert_allclose(f["oi_chg[24]"][24:], 24 * np.log(2.0), rtol=1e-5)

    def test_oi_price_quadrant_encodes_price_and_oi_direction(self):
        T, S = 30, 4
        close = np.ones((T, S), np.float32)
        oi = np.ones((T, S), np.float32)
        close[10] = [2.0, 2.0, 0.5, 0.5]     # up, up, down, down
        oi[10] = [2.0, 0.5, 2.0, 0.5]        # up, down, up, down
        f = flowfeat.raw_features(metrics(T, S, oi=oi), None, close, np.ones((T, S), np.float32))
        np.testing.assert_array_equal(f["oi_price[4]"][10], [3, 2, 1, 0])
        self.assertTrue(np.all(np.isnan(f["oi_price[4]"][:4])))

    def test_top_vs_crowd_is_the_log_ratio_difference(self):
        T, S = 5, 1
        m = metrics(T, S, top_ls_sum=4.0 * np.ones((T, S), np.float32), ls_count=2.0 * np.ones((T, S), np.float32))
        f = flowfeat.raw_features(m, None, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        np.testing.assert_allclose(f["top_vs_crowd"][:, 0], np.log(4.0) - np.log(2.0), rtol=1e-6)
        np.testing.assert_allclose(f["top_ls"][:, 0] - f["crowd_ls"][:, 0], f["top_vs_crowd"][:, 0], rtol=1e-6)

    def test_taker_1_is_the_log_ratio_and_24_is_its_trailing_mean(self):
        T, S = 30, 1
        v = (2.0 ** np.arange(T)).reshape(T, 1).astype(np.float32)
        f = flowfeat.raw_features(metrics(T, S, taker_ls_vol=v), None, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        lt = np.arange(T) * np.log(2.0)
        np.testing.assert_allclose(f["taker[1]"][:, 0], lt, rtol=1e-5)
        self.assertTrue(np.isnan(f["taker[24]"][22, 0]))
        np.testing.assert_allclose(f["taker[24]"][29, 0], lt[29 - 23:30].mean(), rtol=1e-4)

    def test_imb_and_shape_come_from_the_book(self):
        T, S = 5, 1
        b = book(T, S, b1=3.0 * np.ones((T, S), np.float32), a1=1.0 * np.ones((T, S), np.float32),
                 b5=5.0 * np.ones((T, S), np.float32), a5=1.0 * np.ones((T, S), np.float32))
        f = flowfeat.raw_features(metrics(T, S), b, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        np.testing.assert_allclose(f["imb[1]"][:, 0], 0.5, rtol=1e-6)
        np.testing.assert_allclose(f["shape"][:, 0], np.log(3.0 / 5.0) - np.log(1.0 / 1.0), rtol=1e-6)

    def test_no_book_yields_no_book_features(self):
        T, S = 5, 1
        f = flowfeat.raw_features(metrics(T, S), None, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        for name in ("imb[1]", "imb[2]", "imb[5]", "imb_dev", "liq", "shape"):
            self.assertNotIn(name, f)

    def test_oi_turnover_is_defined_only_after_a_full_volume_window(self):
        T, S = 30, 1
        m = metrics(T, S, oi_value=2.0 * np.ones((T, S), np.float32))
        f = flowfeat.raw_features(m, None, np.ones((T, S), np.float32), np.ones((T, S), np.float32))
        x = f["oi_turnover"][:, 0]
        self.assertTrue(np.all(np.isnan(x[:23])))
        np.testing.assert_allclose(x[23:], np.log(2.0 / 24.0), rtol=1e-5)


class BinningTests(unittest.TestCase):
    def test_binned_dispatches_on_the_norm_tag(self):
        x = np.linspace(-3, 3, 40).reshape(20, 2).astype(np.float32)
        elig = np.ones_like(x, bool)
        np.testing.assert_array_equal(flowfeat.binned(x, ("xs", 8), elig), flowfeat.bins_xs(x, elig, 8))
        np.testing.assert_array_equal(flowfeat.binned(x, ("z", 10), elig), flowfeat.bins_z(x, 10))
        np.testing.assert_array_equal(flowfeat.binned(x, ("fix", flowfeat.IMB_EDGES), elig),
                                      flowfeat.bins_fixed(x, flowfeat.IMB_EDGES))

    def test_specs_and_names_are_unique_and_well_formed(self):
        names = [flowfeat.spec_name(n, norm) for n, norm in flowfeat.specs()]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("flow:oi_chg[4]/xs8", names)
        self.assertIn("flow:imb[1]/fix", names)


class LoadTests(unittest.TestCase):
    def test_load_places_rows_on_the_clock_and_ignores_out_of_range(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "metrics_1h").mkdir()
            t0 = panel.ms("2021-01-01")
            t = t0 + np.arange(4) * HOUR
            df = pd.DataFrame({"t": [t0 + 1 * HOUR, t0 + 2 * HOUR], "oi": [7.0, 8.0]})
            df.to_parquet(root / "metrics_1h" / "AAA.parquet", index=False)
            out = flowfeat.load("metrics", t, ["AAA"], ("oi",), root)
        self.assertTrue(np.isnan(out["oi"][0, 0]))
        self.assertAlmostEqual(float(out["oi"][1, 0]), 7.0, places=5)
        self.assertAlmostEqual(float(out["oi"][2, 0]), 8.0, places=5)
        self.assertTrue(np.isnan(out["oi"][3, 0]))


class BuildTests(unittest.TestCase):
    def _write(self, root, t, syms):
        (root / "klines_1h").mkdir()
        (root / "metrics_1h").mkdir()
        for j, s in enumerate(syms):
            k = pd.DataFrame({"t": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0 + j, "volume": 10.0,
                              "quote_volume": 10.0, "count": 5.0, "taker_buy_volume": 4.0,
                              "taker_buy_quote_volume": 6.0})
            k.to_parquet(root / "klines_1h" / f"{s}.parquet", index=False)
            m = pd.DataFrame({"t": t, **{c: 2.0 + j for c in flowfeat.METRIC_COLS}})
            m.to_parquet(root / "metrics_1h" / f"{s}.parquet", index=False)

    def test_build_bins_features_and_flags_a_missing_one(self):
        T = 48
        t0 = panel.ms(panel.START)
        t = t0 + np.arange(T) * HOUR
        syms = ["AAAUSDT", "BBBUSDT"]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._write(root, t, syms)
            elig = np.ones((T, len(syms)), bool)
            specs = [("oi_chg[4]", flowfeat.XS8), ("imb[1]", ("fix", flowfeat.IMB_EDGES)), ("nope", flowfeat.XS8)]
            out = [np.full((T, len(syms)), -9, np.int8) for _ in specs]
            names = flowfeat.build(t, syms, elig, specs, out, log=lambda *a, **k: None, root=root)
        self.assertEqual(names, ["flow:oi_chg[4]/xs8", "flow:imb[1]/fix", "flow:nope/xs8"])
        self.assertTrue(np.all(out[2] == -1))                     # absent feature -> -1
        self.assertTrue(np.all(out[1] == -1))                     # no bookDepth_1h -> imb absent -> -1
        self.assertTrue(np.all((out[0] >= -1) & (out[0] <= 7)))   # xs bin in range or -1


if __name__ == "__main__":
    unittest.main()
