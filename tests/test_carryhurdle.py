"""carryhurdle_v1 (R483): conversion, alignment, missing-day drop, NW t sign, decision rule and input refusals, on
synthetic data in a temporary directory."""
import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_carryhurdle as fc  # noqa: E402
import run_carryhurdle as rc  # noqa: E402
from lab import prereg  # noqa: E402

POOL_S = "00000000-0000-0000-0000-00000000000a"
POOL_A = "00000000-0000-0000-0000-00000000000b"


def chart(dates, apys, hour=23):
    return {"status": "success", "data": [
        {"timestamp": f"{d}T{hour:02d}:01:19.228Z", "tvlUsd": 1.0, "apy": a, "apyBase": a, "apyReward": None,
         "il7d": None, "apyBase7d": None, "pricePerShare": None} for d, a in zip(dates, apys)]}


class Conversion(unittest.TestCase):
    def test_apr(self):
        self.assertAlmostEqual(float(rc.daily_rate([3.65], "apr")[0]), 0.0001, places=15)

    def test_weekly_inverse(self):
        apr = 0.10
        apy = ((1 + apr / 52) ** 52 - 1) * 100
        self.assertAlmostEqual(float(rc.daily_rate([apy], "weekly")[0]), apr / 365, places=15)
        # differs from the daily-compounding approximation, so a swap is caught
        approx = (1 + apy / 100) ** (1 / 365) - 1
        self.assertGreater(abs(float(rc.daily_rate([apy], "weekly")[0]) - approx), 1e-7)

    def test_unknown_kind(self):
        with self.assertRaises(ValueError):
            rc.daily_rate([1.0], "apy")


class Alignment(unittest.TestCase):
    def test_row_d_minus_1_serves_d(self):
        r = rc.chart_rates(chart(["2025-01-01", "2025-01-02"], [3.65, 7.30]), "apr")
        self.assertEqual(list(r.index.strftime("%Y-%m-%d")), ["2025-01-02", "2025-01-03"])
        self.assertAlmostEqual(r.loc["2025-01-02"], 0.0001, places=15)
        self.assertAlmostEqual(r.loc["2025-01-03"], 0.0002, places=15)

    def test_early_hour_stamp_same_date(self):
        r = rc.chart_rates(chart(["2025-01-01"], [3.65], hour=11), "apr")
        self.assertEqual(str(r.index[0].date()), "2025-01-02")

    def test_duplicate_dates_refused(self):
        with self.assertRaises(rc.InputError):
            rc.chart_rates(chart(["2025-01-01", "2025-01-01"], [1.0, 2.0]), "apr")

    def test_missing_day_dropped_not_filled(self):
        dates = pd.date_range("2025-01-01", periods=10, freq="D")
        net = pd.Series(0.0002, index=dates)
        rate_dates = [d for d in dates if d != pd.Timestamp("2025-01-05")]
        rate = pd.Series(0.0001, index=pd.DatetimeIndex(rate_dates))
        st = rc.excess_stats(net, rate)
        self.assertEqual(st["days"], 9)
        self.assertEqual(st["dropped_days"], 1)
        self.assertAlmostEqual(st["excess_ann_pct"], 0.0001 * 365 * 100, places=9)

    def test_null_apy_row_dropped(self):
        body = chart(["2025-01-01", "2025-01-02"], [None, 3.65])
        r = rc.chart_rates(body, "apr")
        self.assertEqual(list(r.index.strftime("%Y-%m-%d")), ["2025-01-03"])


class Statistic(unittest.TestCase):
    def test_nw_sign_and_share(self):
        rng = np.random.default_rng(0)
        dates = pd.date_range("2024-01-01", periods=400, freq="D")
        net = pd.Series(0.0003 + rng.normal(0, 1e-4, 400), index=dates)
        rate = pd.Series(0.0001, index=dates)
        st = rc.excess_stats(net, rate)
        self.assertGreater(st["nw_t"], 2)
        self.assertAlmostEqual(st["excess_ann_pct"], (net.mean() - 0.0001) * 36500, places=9)
        st2 = rc.excess_stats(net, pd.Series(0.0005, index=dates))
        self.assertLess(st2["nw_t"], -2)
        top = np.sort(net.to_numpy())[::-1][:10].sum() / net.sum()
        self.assertAlmostEqual(st["book_top10_share"], top, places=12)

    def test_max_dd(self):
        self.assertAlmostEqual(rc.max_dd(np.array([0.01, -0.03, 0.01])), -0.03)


class Decision(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(rc.classify({"excess_ann_pct": 1.0, "nw_t": 2.0}), "BEATS")
        self.assertEqual(rc.classify({"excess_ann_pct": 1.0, "nw_t": 1.99}), "TIES")
        self.assertEqual(rc.classify({"excess_ann_pct": -1.0, "nw_t": -2.0}), "LOSES")
        self.assertEqual(rc.classify({"excess_ann_pct": -1.0, "nw_t": -1.99}), "TIES")
        self.assertEqual(rc.classify({"excess_ann_pct": 1.0, "nw_t": math.nan}), "TIES")
        self.assertEqual(rc.classify({"days": 1}), "TIES")

    def test_lane(self):
        B, L, T = "BEATS", "LOSES", "TIES"
        self.assertEqual(rc.lane_verdict([B, B, B, T, T, T]), "PASS")
        self.assertEqual(rc.lane_verdict([B, B, B, B, B, L]), "PARTIAL")
        self.assertEqual(rc.lane_verdict([B, B, T, T, T, T]), "PARTIAL")
        self.assertEqual(rc.lane_verdict([L, L, L, T, T, B]), "NULL")
        self.assertEqual(rc.lane_verdict([L, L, T, T, T, T]), "PARTIAL")

    def test_deciders_and_trials(self):
        self.assertEqual(sorted(rc.DECIDERS.values()), ["R278 A", "R278 B", "R278 C", "R279 A", "R279 B", "R390 A"])
        self.assertEqual((rc.DECIDE_BENCH, rc.DECIDE_ENGINE, rc.DECIDE_COST), ("susde", "v2", 2))
        self.assertEqual(rc.NW_LAG, 10)


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.root = Path(self.tmp.name)
        dates = pd.date_range("2024-02-16", "2024-10-31", freq="D")
        src = t / "sealed"
        src.mkdir()
        for pool, apy in ((POOL_S, 20.0), (POOL_A, 3.65)):
            (src / f"{pool}.json").write_text(json.dumps(chart([d.strftime("%Y-%m-%d") for d in dates],
                                                               [apy] * len(dates))))
            (src / f"{pool}.hdr").write_text("HTTP/2 200\n")
        (src / "receipt.txt").write_text("synthetic\n")
        sha = {p: hashlib.sha256((src / f"{p}.json").read_bytes()).hexdigest() for p in (POOL_S, POOL_A)}
        size = {p: (src / f"{p}.json").stat().st_size for p in (POOL_S, POOL_A)}
        self.intake = t / "intake.md"
        self.intake.write_text("\n".join(
            f"| x | https://yields.llama.fi/chart/{p} | 200 | {size[p]:,} | {sha[p]} |" for p in (POOL_S, POOL_A)))
        self.src, self.sha = src, sha
        self.pools = {POOL_S: ("susde", "weekly", sha[POOL_S]), POOL_A: ("aave_usdc", "apr", sha[POOL_A])}
        rng = np.random.default_rng(1)
        bdates = pd.date_range("2024-01-01", "2024-09-30", freq="D")
        rows = []
        for i, b in enumerate(rc.DECIDERS):
            for eng in ("v1", "v2"):
                mu = (0.0010 if i < 3 else 0.0002)
                x = mu + rng.normal(0, 5e-5, len(bdates))
                for d, v in zip(bdates, x):
                    rows.append({"book": b, "engine": eng, "date": d.strftime("%Y-%m-%d"), "net_1x": v + 1e-5,
                                 "net_2x": v, "net_3x": v - 1e-5})
        self.books = t / "daily.csv"
        pd.DataFrame(rows).to_csv(self.books, index=False)
        self.lane = t / "lane"
        self.lane.mkdir()
        self.raw = self.lane / "raw"

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        h = prereg.sha256_file(self.books)
        (self.lane / "PREREG.md").write_text(f"# fake\n\n```inputs\n{h} daily.csv\n```\n")
        prereg.freeze(self.lane / "PREREG.md")

    def test_import_refuses_mismatch(self):
        bad = self.intake.read_text().replace(self.sha[POOL_S], "0" * 64)
        self.intake.write_text(bad)
        with self.assertRaises(SystemExit):
            fc.run(self.src, self.raw, self.intake)
        self.assertFalse(self.raw.exists())

    def test_refuses_unfrozen_and_changed(self):
        fc.run(self.src, self.raw, self.intake)
        with self.assertRaises(prereg.PreregError):
            rc.run(self.lane, self.raw, [self.books], self.pools, self.root)
        self.freeze()
        with open(self.books, "a") as f:
            f.write("\n")
        with self.assertRaises(prereg.PreregError):
            rc.run(self.lane, self.raw, [self.books], self.pools, self.root)

    def test_refuses_tampered_body(self):
        fc.run(self.src, self.raw, self.intake)
        self.freeze()
        p = self.raw / f"{POOL_S}.json"
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaises(rc.InputError):
            rc.run(self.lane, self.raw, [self.books], self.pools, self.root)

    def test_refuses_without_import(self):
        self.freeze()
        with self.assertRaises(rc.InputError):
            rc.run(self.lane, self.raw, [self.books], self.pools, self.root)

    def test_end_to_end(self):
        fc.run(self.src, self.raw, self.intake)
        rec = json.loads((self.raw / "import_receipt.json").read_text())
        self.assertEqual(set(rec["files"]), {f"{p}{e}" for p in (POOL_S, POOL_A) for e in (".json", ".hdr")}
                         | {"receipt.txt"})
        self.freeze()
        summ, tab = rc.run(self.lane, self.raw, [self.books], self.pools, self.root)
        # sUSDe at 20%/yr is about 5.0 bp/day; books 0-2 earn 10 bp/day (BEAT), books 3-5 2 bp/day (LOSE)
        calls = [summ["deciders"][b]["call"] for b in rc.DECIDERS]
        self.assertEqual(calls, ["BEATS"] * 3 + ["LOSES"] * 3)
        self.assertEqual(summ["verdict"], "NULL")
        d = tab[(tab.bench == "susde") & (tab.engine == "v2") & (tab.cost == 2) & (tab.window == "full")].iloc[0]
        self.assertEqual(d["first"], "2024-02-17")          # row dated 02-16 serves 02-17
        self.assertEqual(d["last"], "2024-09-30")
        self.assertAlmostEqual(d["bench_ann_pct"], 52 * (1.2 ** (1 / 52) - 1) * 100, places=6)
        a = tab[(tab.bench == "aave_usdc") & (tab.window == "full")].iloc[0]
        self.assertAlmostEqual(a["bench_ann_pct"], 3.65, places=9)
        self.assertTrue((self.lane / "run.log").is_file())
        self.assertTrue((self.lane / "results" / "summary.json").is_file())
        self.assertEqual(set(tab.bench), {"susde", "aave_usdc", "bill"})
        self.assertEqual(set(tab.window), {"full", "2025+", "2025-04-09+"})


if __name__ == "__main__":
    unittest.main()
