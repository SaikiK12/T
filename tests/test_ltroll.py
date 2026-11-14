"""ltroll_v1 (R481): marks, cycle arithmetic, costs, bill and the verdict on a synthetic world."""
import math
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_ltroll as lt  # noqa: E402

H = lt.H


def world(rate=3e-5, jump=0.02):
    """Hourly perp and front bars, Feb 1 .. Oct 31 2026. The front is 100. The perp is 100 x (1 + jump) from 00:00 UTC
    on business day 7 of each month to the 25th (the oracle on the next contract, the front not yet switched), else
    100. Longs pay `rate` every hour."""
    t = np.arange(int(pd.Timestamp("2026-02-01", tz="UTC").value // 1_000_000),
                  int(pd.Timestamp("2026-10-31", tz="UTC").value // 1_000_000), H, dtype=np.int64)
    close_t = pd.to_datetime(t + H, unit="ms")
    up = np.zeros(len(t), bool)
    for m in range(2, 11):
        bd7 = pd.Timestamp(lt.rc.bdays(2026, m)[6])
        up |= (close_t >= bd7) & (close_t < pd.Timestamp(f"2026-{m:02d}-25"))
    perp = pd.DataFrame({"t": t, "close": np.where(up, 100 * (1 + jump), 100.0), "volume": 1.0})
    front = pd.DataFrame({"open_ms": t, "close": 100.0})
    funding = pd.DataFrame({"t": t + H, "rate": rate})
    irx = pd.DataFrame({"date": ["2026-01-02"], "close": [3.65]})
    return perp, front, funding, irx


class Marks(unittest.TestCase):
    def test_close_ending_and_fallback(self):
        perp, front, _, _ = world()
        t = lt.mark("2026-03-04")
        self.assertEqual(lt.close_ending(perp, "t", t), 100.0)
        self.assertEqual(lt.r_at(perp, front, t), (0.0, 0))
        gap = front[front["open_ms"] != t - H]
        r, lag = lt.r_at(perp, gap, t)
        self.assertEqual((r, lag), (0.0, 1))
        self.assertTrue(math.isnan(lt.r_at(perp, front.iloc[:0], t)[0]))

    def test_bill_accrues_daily_rate(self):
        irx = pd.DataFrame({"date": ["2026-03-01"], "close": [3.65]})
        a = lt.mark("2026-03-02")
        self.assertAlmostEqual(lt.bill(irx, a, a + 10 * 24 * H), 0.001, places=9)


class Cycles(unittest.TestCase):
    def test_roll_funding_cost_and_excess(self):
        perp, front, funding, irx = world()
        df = lt.cycles("NATGAS", perp, funding, front, irx)
        self.assertEqual(list(df["month"]), [f"2026-{m:02d}" for m in range(2, 11)])
        np.testing.assert_allclose(df["roll"], 0.02)
        np.testing.assert_allclose(df["roll_wide"], 0.02)
        np.testing.assert_allclose(df["fund"], 3e-5 * df["prints"])
        self.assertTrue((df["prints"] == df["hours"]).all())
        self.assertEqual(df["cost_bp"].iloc[0], 8 + 2 + 9)
        self.assertEqual(df["cost_bp"].iloc[1], 10)
        self.assertEqual(df["cost_bp"].iloc[-1], 19)
        row = df.iloc[2]
        want = 0.75 * (row["fund"] - 0.02 - 2 * row["cost_bp"] / 1e4) - 0.25 * row["bill"]
        self.assertAlmostEqual(row["excess_2x"], want, places=12)
        self.assertAlmostEqual(df["max_up"].iloc[0], 0.02, places=12)      # from 100 at the start to 102
        self.assertAlmostEqual(df["max_up"].iloc[1], 0.0, places=12)       # starts at 102 (old front not yet expired)

    def test_copper_hedge_rolls_bimonthly(self):
        perp, front, funding, irx = world()
        df = lt.cycles("XCU", perp, funding, front, irx).set_index("month")
        self.assertEqual(df.loc["2026-04", "hedge_rolls"], 1)
        self.assertEqual(df.loc["2026-05", "hedge_rolls"], 0)
        self.assertEqual(df.loc["2026-05", "cost_bp"], 2)

    def test_stats_and_verdict(self):
        perp, front, funding, irx = world(rate=1e-4, jump=0.0)
        df = lt.cycles("NATGAS", perp, funding, front, irx)
        df["excess_1x"] += np.linspace(-1e-4, 1e-4, len(df))      # some spread for a finite t
        st = lt.stats(df)
        self.assertEqual(st["cycles"], len(df))
        self.assertGreater(st["ann_excess_pct"], 2)
        self.assertEqual(lt.verdict(st), "PASS")
        self.assertEqual(lt.verdict({**st, "t": 1.0}), "PARTIAL")
        self.assertEqual(lt.verdict({**st, "ann_excess_pct": -0.1}), "NULL")
        self.assertEqual(lt.verdict({"cycles": 1}), "NULL")


if __name__ == "__main__":
    unittest.main()
