"""R469 asiaclose_c: the date guard, the one-read guard and the C read on synthetic worlds (no market data)."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_asiaclose as base  # noqa: E402
import run_asiaclose_c as c  # noqa: E402

H = 3_600_000
AFTER = int(datetime(2027, 2, 2, tzinfo=timezone.utc).timestamp() * 1000)


def world(root, rho, seed):
    """Six KRX markets with hourly bars over 2026-10-15 .. 2027-02-01; the open moves rho times the night's move."""
    rng = np.random.default_rng(seed)
    uni = root / "uni"
    uni.mkdir(parents=True)
    rows = [{"venue": v, "coin": f"C{i}", "exchange": "KRX", "local": f"00000{i}"}
            for i, v in enumerate(("xyz", "lighter") * 3)]
    with open(uni / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    data = root / "data"
    hours = np.arange(int(datetime(2026, 10, 15, tzinfo=timezone.utc).timestamp() * 1000),
                      int(datetime(2027, 2, 1, tzinfo=timezone.utc).timestamp() * 1000), H)
    hour = (hours // H) % 24
    man = {"files": {}}
    for u in rows:
        r = rng.normal(0, 0.002, len(hours))
        night = (hour >= 7) & (hour <= 22)
        r[night] += rng.normal(0, 0.004, night.sum())
        lp = np.cumsum(r)
        for ix in np.where(hour == 0)[0]:
            if ix >= 17:
                lp[ix:] += rho * (lp[ix - 1] - lp[ix - 17])
        for sub, df in (("klines_1h", pd.DataFrame({"t": hours, "close": 100 * np.exp(lp), "volume": 1.0})),
                        ("funding", pd.DataFrame({"t": hours[1:], "rate": 0.0}))):
            p = data / u["venue"] / sub / f"{u['coin']}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)
            man["files"][f"{u['venue']}/{sub}/{u['coin']}.parquet"] = {"sha256": base.prereg.sha256_file(p)}
    (data / "manifest.json").write_text(json.dumps(man))
    return uni, data


class Guards(unittest.TestCase):
    def test_refuses_before_february(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            early = int(datetime(2027, 1, 31, 23, tzinfo=timezone.utc).timestamp() * 1000)
            self.assertIsNone(c.run(lane, Path(d) / "data", now_ms=early, check=False, do_fetch=False))
            self.assertFalse((lane / "results").exists())

    def test_reads_once(self):
        with tempfile.TemporaryDirectory() as d:
            lane = Path(d) / "lane"
            (lane / "results").mkdir(parents=True)
            (lane / "results" / "summary.json").write_text(json.dumps({"state": "NULL"}))
            self.assertIsNone(c.run(lane, Path(d) / "data", now_ms=AFTER, check=False, do_fetch=False))

    def test_2027_new_year_is_a_holiday(self):
        import asiaclose_rule as rule
        keep = {x: set(v) for x, v in rule.HOLIDAYS.items()}
        try:
            for x, days in c.HOLIDAYS_2027.items():
                rule.HOLIDAYS[x] = rule.HOLIDAYS[x] | days
            self.assertIsNone(rule.opening("KRX", c.date(2027, 1, 1)))
            self.assertEqual(rule.opening("TSE", c.date(2027, 1, 12))["P"], "2027-01-08")
        finally:
            rule.HOLIDAYS.update(keep)

    def test_verdict_rules(self):
        row = {"n": 300, "days": 50, "mean": 30.0, "median": 20.0, "p_one_sided": 0.01, "unit": 5.0}
        self.assertEqual(c.verdict(row)[0], "PASS")
        self.assertEqual(c.verdict(dict(row, mean=8.0))[0], "NULL")
        self.assertEqual(c.verdict(dict(row, p_one_sided=0.2))[0], "NULL")
        self.assertEqual(c.verdict(dict(row, days=10))[0], "INCONCLUSIVE")


class Read(unittest.TestCase):
    def _run(self, rho, seed):
        with tempfile.TemporaryDirectory() as d:
            uni, data = world(Path(d), rho, seed)
            lane = Path(d) / "lane"
            keep = (c.UNIVERSE_LANE, base.SPANS)
            c.UNIVERSE_LANE = uni
            try:
                state = c.run(lane, data, now_ms=AFTER, check=False, do_fetch=False)
            finally:
                c.UNIVERSE_LANE, base.SPANS = keep
            cells = pd.read_csv(lane / "results" / "cells.csv")
            return state, cells

    def test_overshoot_passes(self):
        state, cells = self._run(-0.5, 1)
        self.assertEqual(state, "PASS")
        self.assertEqual(len(cells), 7)

    def test_underreaction_is_null(self):
        state, cells = self._run(0.5, 2)
        self.assertEqual(state, "NULL")
        self.assertLess(cells.iloc[0]["mean"], 0)


if __name__ == "__main__":
    unittest.main()
