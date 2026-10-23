import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from lab import live, panel

H = live.HOUR


class LiveTests(unittest.TestCase):
    def test_parse_klines(self):
        rows = [[1792396800000, "82695.00", "82940.90", "82539.30", "82785.90", "6930.892", 1792400399999,
                 "573463300.58560", 105718, "3979.294", "329256956.94700", "0"]]
        df = live.parse_klines(rows)
        self.assertEqual(df["t"].iloc[0], 1792396800000)
        self.assertAlmostEqual(df["close"].iloc[0], 82785.9)
        self.assertAlmostEqual(df["quote_volume"].iloc[0], 573463300.5856)
        self.assertNotIn("ignore", df)

    def test_hourly_metrics_mean_last_and_shifts(self):
        t0 = 1_790_000_000_000 // H * H
        ts = t0 + np.arange(1, 25) * live.FIVE                # live snapshots stamped 5 minutes after the archive
        top = pd.DataFrame({"timestamp": ts, "value": np.r_[np.full(12, 1.0), np.full(12, 3.0)]})
        oi = pd.DataFrame({"timestamp": ts, "oi": np.arange(24.0), "oi_value": np.arange(24.0) * 10})
        tk = pd.DataFrame({"timestamp": ts - live.FIVE, "value": np.r_[np.full(12, 2.0), np.full(12, 4.0)]})
        frames = {"topLongShortPositionRatio": top, live.OI: oi, "takerlongshortRatio": tk}
        out = live.hourly_metrics(frames, live.ARCHIVE_SHIFTS).set_index("t")
        self.assertEqual(list(out.index[:2]), [t0, t0 + H])
        self.assertAlmostEqual(out.loc[t0, "top_ls_sum"], 1.0)
        self.assertAlmostEqual(out.loc[t0 + H, "top_ls_sum"], 3.0)
        self.assertAlmostEqual(out.loc[t0, "oi"], 11.0)                 # last row of the hour
        self.assertAlmostEqual(out.loc[t0, "taker_ls_vol"], 2.0)
        naive = live.hourly_metrics(frames).set_index("t")
        self.assertAlmostEqual(naive.loc[t0, "top_ls_sum"], (11 * 1.0) / 11)
        self.assertIn(t0 + 2 * H, naive.index)                          # unshifted, the last snapshot spills over

    def test_grid_places_rows(self):
        tt = np.arange(0, 5 * H, H)
        g = live.grid({"A": pd.DataFrame({"t": [H, 3 * H], "x": [1.0, 2.0]}), "B": None}, tt, "x")
        self.assertEqual(g.shape, (5, 2))
        self.assertEqual(g[1, 0], 1.0)
        self.assertEqual(g[3, 0], 2.0)
        self.assertTrue(np.isnan(g[:, 1]).all())

    def test_rank_matches_panel_on_a_long_grid(self):
        rng = np.random.default_rng(0)
        T, S, w = 200, 6, 48
        qv = rng.lognormal(10, 1, (T, S)).astype(np.float32)
        close = np.ones((T, S), np.float32)
        qv[:80, 2] = np.nan                                              # a coin listed later
        close[:80, 2] = np.nan
        p = panel.Panel(np.arange(T) * H, list("abcdef"), {"quote_volume": qv, "close": close})
        ref = panel.liquidity_rank(p, w)
        mine = live.liquidity_rank(qv, close, w)
        np.testing.assert_array_equal(ref[w:], mine[w:])                # equal once the window is full

    def test_klines_cache_fetches_only_new_bars(self):
        calls = []

        def fake(symbol, s, e, interval="1h"):
            calls.append((s, e))
            t = np.arange(s, e, H)
            return pd.DataFrame({"t": t, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0,
                                 "quote_volume": 1.0})

        with tempfile.TemporaryDirectory() as d, mock.patch.object(live, "fetch_klines", fake):
            a = live.klines_cached("X", 0, 10 * H, root=d)
            b = live.klines_cached("X", 0, 12 * H, root=d)
            self.assertEqual(len(a), 10)
            self.assertEqual(len(b), 12)
            self.assertEqual(calls[1], (9 * H, 12 * H))                  # refetch from the last cached bar
            self.assertTrue((Path(d) / "klines_1h" / "X.from").exists())


if __name__ == "__main__":
    unittest.main()
