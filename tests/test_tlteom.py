"""R473 tlteom_v1: month ends, windows, costs and verdict on synthetic prices (no market data)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_tlteom as te  # noqa: E402


def dates(lo="2002-07-30", hi="2026-11-11"):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(lo, hi)]


def prices(effect_bp=0.0, seed=0, sd=0.009):
    """Daily closes with effect_bp / 3 added to each of the last three trading days of every month."""
    rng = np.random.default_rng(seed)
    ds = dates()
    m = pd.to_datetime(pd.Series(ds)).dt.to_period("M").values
    left = np.zeros(len(ds), int)
    for i in range(len(ds) - 1, -1, -1):
        left[i] = left[i + 1] + 1 if i + 1 < len(ds) and m[i + 1] == m[i] else 1
    r = rng.normal(0.0, sd, len(ds)) + np.where(left <= 3, effect_bp / 3 / 1e4, 0.0)
    r[0] = 0.0
    px = 100 * np.cumprod(1 + r)
    return pd.DataFrame({"date": ds, "close": px, "adjclose": px})


class WindowTest(unittest.TestCase):
    def test_month_ends_skip_the_unfinished_month(self):
        ds = dates("2026-09-28", "2026-11-11")
        idx = te.month_ends(ds)
        self.assertEqual([ds[i] for i in idx], ["2026-09-30", "2026-10-30"])

    def test_events_hold_the_last_three_returns(self):
        px = pd.DataFrame({"date": dates("2026-09-21", "2026-11-11")})
        px["close"] = np.arange(len(px), dtype=float) + 100
        px["adjclose"] = px["close"]
        ev = te.events(px)
        row = ev[ev.month == "2026-10"].iloc[0]
        self.assertEqual((row.entry, row.exit), ("2026-10-27", "2026-10-30"))
        c = px.set_index("date")["close"]
        self.assertAlmostEqual(row.gross, c["2026-10-30"] / c["2026-10-27"] - 1, places=12)
        self.assertEqual(row.cal_days, 3)
        sep = ev[ev.month == "2026-09"].iloc[0]
        self.assertEqual((sep.entry, sep.exit, sep.cal_days), ("2026-09-25", "2026-09-30", 5))

    def test_costs_and_funding(self):
        ev = pd.DataFrame({"gross": [0.004], "cal_days": [5.0]})
        self.assertAlmostEqual(te.net(ev).iloc[0], 0.004 - 5.8e-4 - 0.055 * 5 / 365, places=12)
        self.assertAlmostEqual(te.net(ev, 3, 0.0).iloc[0], 0.004 - 3 * 5.8e-4, places=12)


class VerdictTest(unittest.TestCase):
    def _st(self, **kw):
        px = prices(**kw)
        return {k: te.sample_stats(px, prices(seed=99), k) for k in te.SPANS}

    def test_planted_effect_passes(self):
        st = self._st(effect_bp=60.0, seed=1)
        self.assertEqual(te.verdict(st)[0], "PASS")
        self.assertEqual(st["U"]["events"], 94)
        self.assertEqual(st["R"]["events"], 197)

    def test_no_effect_is_null(self):
        self.assertEqual(te.verdict(self._st(seed=2))[0], "NULL")


class RunTest(unittest.TestCase):
    def test_run_writes_results(self):
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "yahoo").mkdir(parents=True)
            prices(effect_bp=40.0, seed=3).to_parquet(data / "yahoo" / "TLT.parquet")
            prices(seed=4).to_parquet(data / "yahoo" / "IEF.parquet")
            state = te.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["state"], state)
            self.assertIn("2026", s["samples"]["U"]["by_year_gross_bp"])
            self.assertTrue((lane / "results" / "events.csv").exists())


if __name__ == "__main__":
    unittest.main()
