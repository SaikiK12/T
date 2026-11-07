import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_settlehop_exit as ex

H, MIN = ex.H, ex.MIN
T0 = 1_740_067_200_000                          # 2025-02-20 16:00 UTC, an invented settlement


def bars(closes, vols=None, start=None):
    """Minute bars opening at start, start + 1 min, ... (start T0 - 2 h): closes, volume 1 unless given."""
    start = T0 - 2 * H if start is None else start
    c = np.asarray(closes, float)
    v = np.ones(len(c)) if vols is None else np.asarray(vols, float)
    return {"t": start + MIN * np.arange(len(c), dtype=np.int64), "close": c, "traded": (c > 0) & (v > 0)}


def flat(n=180, price=100.0):
    return np.full(n, price)


class TestBars(unittest.TestCase):
    def test_last_traded(self):
        b = bars([1, 2, 3, 4, 5], vols=[1, 1, 0, 0, 1])
        t = b["t"]
        self.assertEqual(ex.last_traded(b, t[3], t[0]), 1)          # bars 2 and 3 untraded
        self.assertEqual(ex.last_traded(b, t[4], t[0]), 4)
        self.assertEqual(ex.last_traded(b, t[3], t[2]), -1)         # none traded in [t2, t3]
        self.assertEqual(ex.last_traded(b, t[0] - MIN, t[0] - 5 * MIN), -1)

    def test_entry_is_the_last_close_before_T_minus_1h(self):
        s, h = bars(flat()), bars(flat())
        self.assertEqual(ex.entries(s, h, T0), (59, 59))             # the bar opening T - 61 min
        v = np.ones(180)
        v[55:60] = 0
        self.assertEqual(ex.entries(bars(flat(), v), h, T0), (54, 59))
        v[:60] = 0                                                   # nothing traded in [T - 2 h, T - 61 min]
        self.assertEqual(ex.entries(bars(flat(), v), h, T0)[0], -1)
        self.assertIsNone(ex.hop_path(bars(flat(), v), h, T0, 1, (5,)))


class TestHopPath(unittest.TestCase):
    def setUp(self):
        self.cs, self.ch = flat(), flat()
        self.cs[120:] = 101.0              # Binance from T: +1%
        self.cs[124:] = 100.5              # from the bar opening T + 4 min: +0.5%
        self.ch[120:] = 99.0               # Lighter from T: -1%

    def test_long_s_short_h(self):
        p = ex.hop_path(bars(self.cs), bars(self.ch), T0, -1, (0, 1, 5, 60))
        self.assertEqual(p[0][0], 0.0)                               # the last close before T is the entry's level
        self.assertAlmostEqual(p[1][0], 0.02)                        # d = -1: ret_S - ret_H = 1% + 1%
        self.assertAlmostEqual(p[5][0], 0.015)                       # the close of the bar opening T + 4 min
        self.assertAlmostEqual(p[60][0], 0.015)
        self.assertAlmostEqual(p[5][1], 0.005)                       # Binance's part, signed for the hop
        self.assertAlmostEqual(p[5][2], 0.01)                        # Lighter's part
        self.assertFalse(p[5][3] or p[5][4])

    def test_short_s_long_h_mirrors(self):
        p = ex.hop_path(bars(self.cs), bars(self.ch), T0, 1, (5,))
        self.assertAlmostEqual(p[5][0], -0.015)

    def test_untraded_exit_minute_takes_the_last_trade_and_is_stale(self):
        v = np.ones(180)
        v[124] = 0                                                   # Binance did not trade in T + 4 .. T + 5 min
        p = ex.hop_path(bars(self.cs, v), bars(self.ch), T0, -1, (5,))
        self.assertAlmostEqual(p[5][0], 0.02)                        # Binance's close of the bar opening T + 3 min
        self.assertTrue(p[5][3])
        self.assertFalse(p[5][4])

    def test_nothing_after_the_exit_minute_is_read(self):
        a = ex.hop_path(bars(self.cs), bars(self.ch), T0, -1, (5,))
        cs, ch = self.cs.copy(), self.ch.copy()
        cs[125:], ch[125:] = 500.0, 1.0                              # every bar opening at or after T + 5 min
        b = ex.hop_path(bars(cs), bars(ch), T0, -1, (5,))
        self.assertEqual(a[5][0], b[5][0])

    def test_the_path_starts_at_zero(self):
        p = ex.hop_path(bars(self.cs), bars(self.ch), T0, -1, ex.PATH)
        self.assertEqual(p[-60][0], 0.0)
        self.assertEqual(len(p), 121)


def hops_frame():
    return pd.DataFrame({"coin": ["AAAUSDT", "BBBUSDT"], "T": [T0, T0 + 4 * H], "d": [-1, -1], "e": [0.01, 0.006],
                         "cost_s_bp": [8.5, 8.5], "cost_h_bp": [1.09, 4.17], "price": [-0.002, 0.001],
                         "fund": [0.010, 0.006], "price0": [0.004, 0.003], "fund0": [0.013, 0.008]})


class TestExits(unittest.TestCase):
    def test_at_exit_keeps_the_lump_at_T_only(self):
        h = hops_frame()
        px = pd.DataFrame({("price", 5): [0.003, 0.002], ("price", 60): [-0.002, 0.001],
                           ("stale_s", 5): [False, False], ("stale_h", 5): [False, True],
                           ("stale_s", 60): [False, False], ("stale_h", 60): [False, False]})
        h5 = ex.at_exit(h, px, 5)
        self.assertEqual(h5.price.tolist(), [0.003, 0.002])
        self.assertEqual(h5.fund.tolist(), [0.013, 0.008])           # R354's fund0
        self.assertEqual(h5.stale.tolist(), [False, True])
        h60 = ex.at_exit(h, px, ex.CONTROL)
        self.assertEqual(h60.price.tolist(), h.price.tolist())      # R354's own hop
        self.assertEqual(h60.fund.tolist(), h.fund.tolist())
        g = ex.gain(h5, h)
        self.assertAlmostEqual(g[0], (0.003 + 0.013) - (-0.002 + 0.010))
        self.assertAlmostEqual(g[1], (0.002 + 0.008) - (0.001 + 0.006))

    def test_parity(self):
        h = hops_frame()
        px = pd.DataFrame({("price", 0): [0.004, 0.003], ("price", 60): [-0.002, 0.001 + 2e-6]})
        self.assertEqual(ex.parity(h, px), (1, 2))

    def test_decide_needs_the_four_checks_and_the_gain(self):
        ok = {"t1": 2.5, "day2_bp": 0.3, "half1_day1_bp": 0.5, "half2_day1_bp": 0.4, "wo_best_day1_bp": 0.2,
              "gain_t": 2.1}
        self.assertEqual(ex.decide(ok)["verdict"], "PASS")
        self.assertEqual(ex.decide({**ok, "gain_t": 1.9})["verdict"], "NULL")
        self.assertEqual(ex.decide({**ok, "gain_t": float("nan")})["verdict"], "NULL")
        self.assertEqual(ex.decide({**ok, "half2_day1_bp": -0.1})["verdict"], "NULL")
        self.assertEqual(ex.decide({**ok, "t1": 1.99})["verdict"], "NULL")

    def test_family_bound(self):
        self.assertEqual(ex.TRIALS, 5)
        self.assertEqual(ex.BONF_T, 2.33)
        self.assertEqual(ex.KS, (1, 2, 5, 15, 30))
        self.assertIn(0, ex.PATH)
        self.assertIn(ex.CONTROL, ex.PATH)


class TestFiles(unittest.TestCase):
    def write_minutes(self, root):
        folder = root / "data" / "settlehop_1m"
        T = 1_740_099_600_000                        # 2025-02-21 01:00 UTC: the window starts the day before
        t = np.arange(T - 3 * H, T + 2 * H, MIN, dtype=np.int64)
        df = pd.DataFrame({"t": t, "close": 100.0 + np.arange(len(t)), "volume": 1.0})
        day = pd.to_datetime(df.t, unit="ms").dt.strftime("%Y-%m-%d")
        for d, g in df.groupby(day):
            p = folder / "binance" / "AAAUSDT" / f"{d}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            g.to_parquet(p, index=False)
        p = folder / "lighter" / "AAA" / f"{T}.parquet"
        p.parent.mkdir(parents=True)
        df[(df.t >= T - 2 * H) & (df.t < T + H + MIN)].to_parquet(p, index=False)
        return folder, T

    def test_minute_bars_join_the_days_and_keep_the_window(self):
        with tempfile.TemporaryDirectory() as d:
            folder, T = self.write_minutes(Path(d))
            for venue, sym in (("binance", "AAAUSDT"), ("lighter", "AAA")):
                b = ex.minute_bars(venue, sym, T, folder)
                self.assertEqual(len(b["t"]), 180)
                self.assertEqual((int(b["t"][0]), int(b["t"][-1])), (T - 2 * H, T + H - MIN))
                self.assertTrue(b["traded"].all())

    def test_check_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder, _ = self.write_minutes(root)
            prov = root / "prov.json"
            files = sorted(p for p in folder.rglob("*") if p.is_file())
            prov.write_text(json.dumps({"file_hashes": [{"path": p.relative_to(root).as_posix(),
                                                         "sha256": prereg.sha256_file(p)} for p in files]}))
            self.assertEqual(ex.check_data(prov, folder, root), 3)
            extra = folder / "lighter" / "AAA" / "1.parquet"
            extra.write_bytes(b"x")
            with self.assertRaises(prereg.PreregError):
                ex.check_data(prov, folder, root)
            extra.unlink()
            files[0].write_bytes(files[0].read_bytes() + b"x")
            with self.assertRaises(prereg.PreregError):
                ex.check_data(prov, folder, root)
            files[0].unlink()
            with self.assertRaises(prereg.PreregError):
                ex.check_data(prov, folder, root)

    def test_load_hops_reads_the_primary_book_and_its_calendar(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            h = hops_frame()
            pd.concat([h.assign(book=ex.BOOK), h.assign(book="mexc+lighter th0.5%")]).to_csv(
                src / "hops.csv.gz", index=False)
            pd.DataFrame({"book": [ex.BOOK, ex.BOOK, "other"], "day": ["2025-02-20", "2025-02-21", "2025-02-22"],
                          "net1_bp": 0.0}).to_csv(src / "daily.csv.gz", index=False)
            (src / "symbols.csv").write_text("key,mexc,gate,dydx,lighter\nAAAUSDT,,,,AAA\nBBBUSDT,,,,1000BBB\n")
            got, days = ex.load_hops(src, src / "symbols.csv")
            self.assertEqual(len(got), 2)
            self.assertEqual(got.lighter.tolist(), ["AAA", "1000BBB"])
            self.assertEqual(days.tolist(), [1_740_009_600_000, 1_740_096_000_000])


if __name__ == "__main__":
    unittest.main()
