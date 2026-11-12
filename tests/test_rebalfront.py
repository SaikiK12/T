"""R472 rebalfront_v1: signals, calendar, costs and verdict on synthetic markets (no market data)."""
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
import run_rebalfront as rf  # noqa: E402


def dates(lo="2002-07-31", hi="2026-11-11"):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(lo, hi)]


def world(a=0.0, c=0.0, seed=0):
    """Daily stock and bond returns; tomorrow's stock-minus-bond return carries -a x Threshold and
    -c x Calendar on week-4 days, both read from today's close."""
    rng = np.random.default_rng(seed)
    ds = dates()
    left, _ = rf.calendar(ds)
    n = len(ds)
    complete = np.arange(n) + left < n
    sig = rf.Signals()
    rs, rb = np.zeros(n), np.zeros(n)
    thr = cal = 0.0
    week4_prev = False
    for i in range(n):
        x = -a * thr - (c * cal if week4_prev else 0.0)
        rb[i] = rng.normal(0.0001, 0.004)
        rs[i] = rb[i] + x + rng.normal(0.0002, 0.011)
        thr, cal = sig.step(rs[i], rb[i], (left[i] == 1) and complete[i])
        week4_prev = (left[i] <= rf.WEEK4) and complete[i]
    return pd.DataFrame({"date": ds, "rs": rs, "rb": rb, "rf": np.full(n, 0.02 / 252)})


class SignalsTest(unittest.TestCase):
    def test_paper_example(self):
        thr, cal = rf.Signals().step(0.10, 0.0, False)       # equities +10%, bonds flat: 66 / 106
        self.assertAlmostEqual(thr, 66 / 106 - 0.6, places=12)
        self.assertAlmostEqual(cal, 66 / 106 - 0.6, places=12)

    def test_month_end_resets_the_calendar_portfolio(self):
        s = rf.Signals()
        s.step(0.10, 0.0, True)
        self.assertAlmostEqual(s.step(0.0, 0.0, False)[1], 0.0, places=12)
        s = rf.Signals()
        s.step(0.10, 0.0, False)
        self.assertAlmostEqual(s.step(0.0, 0.0, False)[1], 66 / 106 - 0.6, places=12)

    def test_threshold_bands(self):
        s = rf.Signals()
        dev = 0.606 / 1.006 - 0.6                              # +1% equities: 0.24%, so bands 0.0-0.2% reset
        thr0, _ = s.step(0.01, 0.0, False)
        self.assertAlmostEqual(thr0, dev, places=12)
        thr1, _ = s.step(0.0, 0.0, False)
        self.assertAlmostEqual(thr1, dev * 23 / 26, places=12)


class CalendarTest(unittest.TestCase):
    def test_days_left_and_first_days(self):
        ds = dates("2026-01-26", "2026-02-04")
        left, first = rf.calendar(ds)
        self.assertEqual(list(left[:5]), [5, 4, 3, 2, 1])     # 2026-01-26 .. 01-30
        self.assertTrue(first[5] and not first[4])            # 2026-02-02

    def test_calmod_week4_and_first_day(self):
        df = rf.build(world(seed=3))
        jan = df[(df.date >= "2010-01-01") & (df.date <= "2010-02-01")]
        last5 = jan[jan.date <= "2010-01-29"].tail(5)
        self.assertTrue((last5.week4 == 1).all())
        np.testing.assert_array_equal(last5.calmod.values, np.sign(-last5.cal.values))
        m4 = jan[jan.date <= "2010-01-29"].iloc[-4]
        self.assertEqual(df.loc[df.date == "2010-02-01", "calmod"].item(), np.sign(m4.cal))
        mid = df[(df.date >= "2010-01-11") & (df.date <= "2010-01-15")]
        self.assertTrue((mid.calmod == 0).all())

    def test_unfinished_last_month_has_no_week4(self):
        df = rf.build(world(seed=4))
        self.assertTrue((df[df.date >= "2026-11-01"].week4 == 0).all())


class VerdictTest(unittest.TestCase):
    def _stats(self, **kw):
        df = rf.returns(rf.build(world(**kw)))
        return df, {k: rf.sample_stats(rf.span(df, k)) for k in rf.SPANS}

    def test_costs(self):
        df, _ = self._stats(seed=1)
        np.testing.assert_allclose(df["gross"] - df["net_1x"], rf.UNIT_BP / 1e4 * df["turn"], atol=1e-15)
        np.testing.assert_allclose(df["gross"] - df["net_3x"], 3 * rf.UNIT_BP / 1e4 * df["turn"], atol=1e-15)

    def test_planted_rebalancing_passes(self):
        _, st = self._stats(a=0.8, c=0.4, seed=2)
        state, _ = rf.verdict(st)
        self.assertEqual(state, "PASS")
        self.assertLess(st["R"]["threshold_slope"]["b"], 0)

    def test_no_effect_is_null(self):
        _, st = self._stats(seed=5)
        state, text = rf.verdict(st)
        self.assertEqual(state, "NULL")


class RunTest(unittest.TestCase):
    def test_run_writes_results(self):
        w = world(a=0.8, c=0.4, seed=6)
        with tempfile.TemporaryDirectory() as d:
            data, lane = Path(d) / "data", Path(d) / "lane"
            (data / "yahoo").mkdir(parents=True)
            (data / "fred").mkdir(parents=True)
            for t, r in (("SPY", w.rs), ("IEF", w.rb)):
                px = 100 * np.cumprod(np.r_[1.0, 1 + r.values[1:]])
                pd.DataFrame({"date": w.date, "adjclose": px}).to_parquet(data / "yahoo" / f"{t}.parquet")
            pd.DataFrame({"observation_date": w.date, "DTB3": 2.0}).to_csv(data / "fred" / "DTB3.csv", index=False)
            state = rf.run(lane, data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(s["state"], state)
            self.assertIn("U2026", s["samples"])


if __name__ == "__main__":
    unittest.main()
