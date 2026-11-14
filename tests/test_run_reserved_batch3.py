"""Synthetic tests for scripts/run_reserved_batch3.py (R392). No archive or reserved file is read."""
import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_reserved_batch3 as rb3
from scripts.run_intrars import COST, TURN, Grid

H, DAY = rb3.H, rb3.DAY


def write_bars(root, sym, t, close, qv, rate_t=(), rate=()):
    (root / "klines_1h").mkdir(parents=True, exist_ok=True)
    (root / "fundingRate").mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"t": np.asarray(t, np.int64), "close": close, "volume": np.ones(len(t)), "quote_volume": qv}) \
        .to_parquet(root / "klines_1h" / f"{sym}.parquet")
    pd.DataFrame({"t": np.asarray(rate_t, np.int64), "interval_h": 8, "rate": np.asarray(rate, float)}) \
        .to_parquet(root / "fundingRate" / f"{sym}.parquet")


def frozen(path, text):
    path.write_text(text)
    prereg.freeze(path)
    return str(path)


class Guard(unittest.TestCase):
    def test_2020_needs_a_frozen_prereg_with_the_token(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            t0 = rb3.ms("2019-12-30")
            t = t0 + np.arange(24 * 16) * H                         # 2019-12-30 .. 2020-01-14
            write_bars(d / "data", "AUSDT", t, np.linspace(1, 2, len(t)), np.ones(len(t)), [t[30], t[60], t[300]],
                       [1e-4, 2e-4, 4e-4])
            with self.assertRaises(PermissionError):
                rb3.load_grid(d / "data", "2020-01-01", "2020-01-10", None)
            (d / "a").mkdir()
            no_token = frozen(d / "a" / "PREREG.md", "no token\n")
            with self.assertRaises(PermissionError):
                rb3.load_grid(d / "data", "2020-01-01", "2020-01-10", no_token)
            ok = frozen(d / "PREREG.md", "batch: RESERVED-2020-READ\n")
            g = rb3.load_grid(d / "data", "2020-01-01", "2020-01-10", ok)
            self.assertEqual(g.C.shape, (240, 1))                    # rows outside the window are not loaded
            self.assertTrue(np.isnan(g.R[178, 0]) and g.R[179, 0] == 1)   # the rank's 180-bar warm-up
            self.assertEqual(g.t0, rb3.ms("2020-01-01"))
            self.assertAlmostEqual(g.C[0, 0], np.linspace(1, 2, len(t))[48])
            self.assertEqual(g.G[-1, 0], 2e-4)                        # only the funding inside the window
            self.assertEqual(g.G[0, 0], 0.0)

    def test_edited_prereg_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "PREREG.md"
            frozen(p, "batch: RESERVED-2020-READ\n")
            p.write_text("batch: RESERVED-2020-READ edited\n")
            with self.assertRaises(prereg.PreregError):
                rb3.load_grid(Path(d) / "data", "2020-01-01", "2020-01-02", str(p))

    def test_dry_specs_never_name_reserved_paths(self):
        spec = {"start": "2021-01-01", "end": "2026-09-30", "symbols": "experiments/reserved_batch3/symbols.csv",
                "reserved_prereg": "experiments/reserved_batch3/RESERVED.md", "seed": 392,
                "venues": [{"name": "gate", "prices": "gate_hist/reserved/candlesticks_1h",
                            "funding": "gate_hist/reserved/funding_applies"},
                           {"name": "mexc", "prices": "mexc_hist/klines_1h", "funding": "mexc_hist/funding"}]}
        s = rb3.dry_carry_spec(spec, "/tmp/x")
        self.assertNotIn("reserved_prereg", s)
        self.assertTrue(all("reserved" not in v["prices"] + v["funding"] for v in s["venues"]))
        self.assertEqual(spec["venues"][0]["prices"], "gate_hist/reserved/candlesticks_1h")   # the input is untouched
        with self.assertRaises(AssertionError):
            rb3.no_reserved_paths(spec)


class Books(unittest.TestCase):
    def grid(self, t0, nd=3, S=32, seed=1):
        rng = np.random.default_rng(seed)
        C = np.exp(np.cumsum(rng.normal(0, 0.01, (24 * nd, S)), axis=0))
        G = np.cumsum(rng.normal(0, 1e-5, (24 * nd, S)), axis=0)
        R = np.tile(np.arange(1, S + 1, dtype=np.float32), (24 * nd, 1))
        g = Grid([f"S{j}" for j in range(S)], C, G, R)
        g.t0 = t0
        return g

    def brute(self, g, sp, e, x, n=3):
        sig = g.C[e] / g.C[sp] - 1
        o = np.argsort(sig)
        lr = g.C[x] / g.C[e] - 1 - (g.G[x] - g.G[e])
        return lr[o[-n:]].mean() - lr[o[:n]].mean()

    def test_m319_follow_book_matches_brute_force(self):
        g = self.grid(rb3.ms("2020-01-06"))
        df, shares = rb3.intraday_book(g, "M319")
        self.assertEqual(df.day.tolist(), [0, 1])                     # day 2 ends past the grid
        for i in (0, 1):
            sp = 24 * i + 7
            self.assertAlmostEqual(df.gross.iloc[i], self.brute(g, sp, sp + 8, sp + 24), places=12)
        self.assertEqual(df.start.iloc[0], rb3.ms("2020-01-06") + 8 * H)
        self.assertEqual(len(shares), 2 * 6)

    def test_c17_decides_at_10_new_york(self):
        g = self.grid(rb3.ms("2020-01-06"))                          # Mon-Wed in EST: 15:00 UTC
        df, _ = rb3.intraday_book(g, "C17")
        self.assertEqual(df.day.tolist(), [1, 2])                      # day 0 has no 00:00 close before the grid
        self.assertAlmostEqual(df.gross.iloc[0], self.brute(g, 23, 23 + 15, 47), places=12)

    def test_us_hours(self):
        k = rb3.us_hours(rb3.ms("2020-07-02"), 5)                     # Thu, Fri (holiday), Sat, Sun, Mon
        self.assertEqual(k.tolist(), [14, 0, 0, 0, 14])
        self.assertEqual(rb3.us_hours(rb3.ms("2020-03-06"), 4).tolist(), [15, 0, 0, 14])   # DST from 03-08

    def test_too_few_names_means_no_book(self):
        g = self.grid(rb3.ms("2020-01-06"), S=20)
        df, _ = rb3.intraday_book(g, "M319")
        self.assertEqual(len(df), 0)


class Stats(unittest.TestCase):
    def book(self, nd=80, seed=2):
        rng = np.random.default_rng(seed)
        t0 = rb3.ms("2020-01-01")
        days = np.arange(nd)
        gross = rng.normal(COST * TURN + 5e-4, 1e-2, nd)
        df = pd.DataFrame({"day": days, "gross": gross, "price": gross, "long": gross / 2, "short": gross / 2,
                           "basket": 0.0, "names": 40, "start": t0 + days * DAY})
        rows = []
        for d, gr in zip(days, gross):
            net = gr - COST * TURN
            rows += [(d, "A", net * 0.5), (d, "B", net * 0.3), (d, "C", net * 0.2)]
        return df, pd.DataFrame(rows, columns=["day", "coin", "net"])

    def test_stats(self):
        df, sh = self.book()
        r = rb3.intraday_stats(df, sh, "2020-01-01", "2020-12-31")
        x = df.gross.to_numpy() - COST * TURN
        self.assertEqual(r["n"], 80)
        self.assertAlmostEqual(r["mean_1x_bp"], x.mean() * 1e4)
        self.assertAlmostEqual(r["mean_2x_bp"], (x - COST * TURN).mean() * 1e4)
        top2 = sh.groupby("coin").net.sum().sort_values().index[::-1][:2]
        self.assertEqual(sorted(r["l2co_dropped"]), sorted(top2))
        self.assertAlmostEqual(r["l2co_mean_bp"], x.mean() * 0.2 * 1e4)
        self.assertGreater(r["t"], 0) if x.mean() > 0 else self.assertLessEqual(r["t"], 0)
        r2 = rb3.intraday_stats(df, sh, "2020-02-01", "2020-02-10")
        self.assertEqual(r2["n"], 10)

    def test_decide_reallocates_and_checks(self):
        alpha = {"C17": 0.002, "M319": 0.001, "GLT": 0.047}
        good = {"n": 300, "p_one_sided": 0.01, "t": 2.3, "mean_2x_bp": 1.0, "trimmed_mean_bp": 1.0, "l2co_mean_bp": 1.0}
        res = {"C17": {"n": 40}, "M319": dict(good, p_one_sided=0.0009), "GLT": dict(good, l2co_mean_bp=-1.0)}
        d = rb3.decide(res, alpha)
        self.assertEqual(d["C17"]["verdict"], "UNREADABLE")
        self.assertAlmostEqual(d["M319"]["alpha"] + d["GLT"]["alpha"], 0.05)
        self.assertAlmostEqual(d["M319"]["alpha"], 0.001 * 0.05 / 0.048)
        self.assertEqual(d["M319"]["verdict"], "PASS")
        self.assertEqual(d["GLT"]["verdict"], "FAIL")

    def test_alpha_block(self):
        text = "x\n```alpha\nC17 0.002  # a\nM319 0.001\nGLT 0.047\n```\n"
        self.assertEqual(rb3.alpha_from_prereg(text), {"C17": 0.002, "M319": 0.001, "GLT": 0.047})
        with self.assertRaises(SystemExit):
            rb3.alpha_from_prereg(text.replace("0.047", "0.04"))


class Symbols(unittest.TestCase):
    def test_long_tail_table(self):
        with tempfile.TemporaryDirectory() as d:
            data, repo = Path(d) / "data", Path(d) / "repo"
            gr = data / "gate_hist" / "reserved"
            for sub in ("candlesticks_1h", "funding_applies"):
                (gr / sub).mkdir(parents=True)
                for s in ("AAA_USDT", "BBB_USDT", "CCC_USDT"):
                    (gr / sub / f"{s}.parquet").touch()
            with open(data / "gate_hist" / "contracts.csv", "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["name", "route", "binance_perp"])
                w.writerows([["AAA_USDT", "reserved", ""], ["BBB_USDT", "reserved", ""], ["CCC_USDT", "reserved", ""],
                             ["DDD_USDT", "open", "DDDUSDT"]])
            for sub in ("klines_1h", "funding"):
                (data / "mexc_hist" / sub).mkdir(parents=True)
                for s in ("AAA_USDT", "BBB_USDT", "DDD_USDT"):
                    (data / "mexc_hist" / sub / f"{s}.parquet").touch()
            for v in ("kucoin", "dydx", "lighter"):
                (data / f"{v}_hist").mkdir()
                (data / f"{v}_hist" / "contracts.csv").write_text("symbol,route,base\n")
            (repo / "experiments" / "unlocks_v1").mkdir(parents=True)
            (repo / "experiments" / "unlocks_v1" / "events.csv").write_text("perp,window\nBBB_USDT,reserved_mexc\n")
            rows, ov = rb3.glt_symbols(data, repo)
            self.assertEqual(rows, [{"key": "AAA", "gate": "AAA_USDT", "mexc": "AAA_USDT"}])
            self.assertEqual(ov["mexc_only_excluded"], ["BBB"])
            self.assertEqual(ov["gate_long_tail"], 3)
            self.assertEqual(ov["with_binance_perp"], 0)


if __name__ == "__main__":
    unittest.main()
