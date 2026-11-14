"""R470 xvfund_v1: the carry book on synthetic xyz/Lighter pairs (no market data)."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_xvfund as xv  # noqa: E402

H, DAY = 3_600_000, 86_400_000
T0 = int(datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)
T1 = int(datetime(2026, 11, 11, tzinfo=timezone.utc).timestamp() * 1000)
# coin -> (xyz funding per year, Lighter funding per year)
WORLD = {"AAA": (0.60, 0.0), "BBB": (0.05, 0.05), "CCC": (0.0, 0.40)}


def world(root, split_day=None, seed=0):
    rng = np.random.default_rng(seed)
    pairs, xu = root / "pairs.csv", root / "xyz.csv"
    with open(pairs, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["coin", "market_id"])
        w.writerows([[c, i] for i, c in enumerate(WORLD)])
    with open(xu, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["coin", "growth"])
        w.writerows([[c, "enabled"] for c in WORLD])
    data, man = root / "data", {"files": {}}
    hours = np.arange(T0, T1, H)
    for coin, (ax, al) in WORLD.items():
        lp = np.cumsum(rng.normal(0, 0.003, len(hours)))
        close = 100 * np.exp(lp)
        days = hours[hours % DAY == 0]
        # the xyz 1d candle opened at day t closes at the price of the last hour before t + 1 day
        xclose = np.array([close[np.searchsorted(hours, t + DAY) - 1] for t in days])
        if split_day is not None and coin == "AAA":
            xclose[days >= split_day - DAY] *= 1.5
        frames = {("xyz", "funding"): pd.DataFrame({"t": hours, "rate": ax / 8760}),
                  ("xyz", "klines_1d"): pd.DataFrame({"t": days, "close": xclose, "volume": 1e4}),
                  ("lighter", "funding"): pd.DataFrame({"t": hours, "rate": al / 8760}),
                  ("lighter", "klines_1h"): pd.DataFrame({"t": hours, "close": close, "volume": 1e4})}
        for (v, s), df in frames.items():
            p = data / v / s / f"{coin}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)
            man["files"][f"{v}/{s}/{coin}.parquet"] = {"sha256": xv.prereg.sha256_file(p)}
    (data / "manifest.json").write_text(json.dumps(man))
    return pairs, xu, data


class Book(unittest.TestCase):
    def _book(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            pairs, xu, data = world(Path(d), **kw)
            self.assertEqual(xv.verify_bars(data), 12)
            return xv.book(xv.load(data, pairs, xu), last=date(2026, 11, 10))

    def test_sides_funding_and_costs(self):
        daily, trades = self._book()
        self.assertEqual(set(trades["coin"]), {"AAA", "CCC"})
        side = dict(zip(trades["coin"], trades["dir"]))
        self.assertEqual(side["AAA"], 1)        # xyz pays more: short xyz, long Lighter
        self.assertEqual(side["CCC"], -1)       # Lighter pays more: short Lighter, long xyz
        steady = daily.iloc[5:]
        self.assertTrue(np.allclose(steady["funding"], (0.60 + 0.40) / 365 / xv.SLOTS, rtol=1e-6))
        self.assertTrue(np.allclose(steady["price"], 0.0, atol=1e-12))   # same prices on both venues
        entry_cost = daily["cost_1x"].sum()
        self.assertAlmostEqual(entry_cost, 2 * (0.9 + 4.0) / 1e4 / xv.SLOTS)
        self.assertTrue((trades["reason"] == "open").all())

    def test_split_guard(self):
        split = int(datetime(2026, 9, 15, tzinfo=timezone.utc).timestamp() * 1000)
        daily, trades = self._book(split_day=split)
        aaa = trades[trades["coin"] == "AAA"]
        self.assertIn("split_guard", set(aaa["reason"]))
        day = daily[daily["D"] == split]
        self.assertTrue(np.allclose(day["price"], 0.0, atol=1e-12))

    def test_no_entry_without_history(self):
        daily, _ = self._book()
        first = datetime.fromisoformat(daily["date"].iloc[0]).date()
        self.assertEqual(first, date(2026, 6, 9))


class Verdict(unittest.TestCase):
    def s(self, ex, t, ex2, dd=-0.01, days=200):
        return {"days": days, "1x": {"excess_pts": ex, "nw_t": t, "drawdown": dd}, "2x": {"excess_pts": ex2}}

    def test_rules(self):
        self.assertEqual(xv.verdict(self.s(5, 2.5, 2), self.s(1, 1, 0, days=70))[0], "PASS")
        self.assertEqual(xv.verdict(self.s(5, 2.5, 2), self.s(-1, -1, -2, days=70))[0], "PARTIAL")
        self.assertEqual(xv.verdict(self.s(2, 2.5, 1), self.s(1, 1, 0))[0], "NULL")
        self.assertEqual(xv.verdict(self.s(5, 1.5, 2), self.s(1, 1, 0))[0], "NULL")
        self.assertEqual(xv.verdict(self.s(5, 2.5, 2, dd=-0.06), self.s(1, 1, 0))[0], "NULL")
        self.assertEqual(xv.verdict(self.s(5, 2.5, 2, days=30), self.s(1, 1, 0))[0], "INCONCLUSIVE")


class Run(unittest.TestCase):
    def test_run_writes_results(self):
        with tempfile.TemporaryDirectory() as d:
            pairs, xu, data = world(Path(d))
            lane = Path(d) / "lane"
            state = xv.run(lane, data, check=False, pairs=pairs, xyz_universe=xu)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["state"], state)
            self.assertGreater(s["samples"]["A"]["1x"]["excess_pts"], 3.0)


if __name__ == "__main__":
    unittest.main()
