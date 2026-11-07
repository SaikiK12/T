import datetime as dt
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import record_lighter_index as rec
from scripts import score_lighter_roll as roll


def synth(out, days, step=0.2, drift=0.05, spread=0.02, rate_pct=0.0004):
    """One row a second from 23:00 to 01:00 UTC around each step day; the index steps up at 23:59 UTC and the book's
    mid follows it 31 minutes later (at 00:30, just before the exit stamp)."""
    for i, day in enumerate(days):
        t0 = roll.us(day, 23, 0)
        t = t0 + np.arange(0, 7200) * 1_000_000
        step_t = roll.us(day, 23, 59)
        index = 100 + step * (t >= step_t)
        mid = 100 + drift + step * (t >= step_t + 31 * roll.MINUTE - 30_000_000)
        nxt = day + dt.timedelta(days=1)
        fts = np.where(t >= roll.us(nxt, 0, 0), roll.us(nxt, 0, 0) // 1000 + 1, roll.us(day, 23, 0) // 1000 + 1)
        df = pd.DataFrame(dict(t=t, ts=t // 1000, index=index, mark=index, mid=mid, bid=mid - spread / 2,
                               ask=mid + spread / 2, last=mid, funding_rate=rate_pct, current_funding_rate=rate_pct,
                               funding_ts=fts, oi=1.0, kind=1))
        rows = {"BRENTOIL": list(df.itertuples(index=False, name=None))}
        rec.write_parts(rows, t0 / 1e6 + i, out)   # distinct part names


class LighterRollTest(unittest.TestCase):
    def test_calendar(self):
        self.assertEqual([str(d) for d in roll.step_days(2026, 11)],
                         ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"])
        self.assertEqual(str(roll.step_days(2027, 1)[0]), "2027-01-08")   # 1 Jan is a bank holiday

    def test_trades_follow_step_one_direction(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            synth(out, roll.step_days(2026, 11))
            steps, missing, months = roll.score(dt.date(2026, 11, 13), out)
            self.assertEqual(months[0]["d"], 1)
            self.assertEqual(len(steps), 4)
            self.assertEqual(missing, [])
            s = steps[0]
            self.assertAlmostEqual(s["gross_bp"], 20.0, delta=0.5)    # 0.2 on 100.05
            self.assertAlmostEqual(s["cost_side_bp"], 1.0, delta=0.05)
            self.assertAlmostEqual(s["funding_bp"], -0.04, delta=1e-6)
            self.assertTrue(s["funding_known"])
            self.assertAlmostEqual(s["pre_bp"], 0.0, delta=1e-9)
            verdict, _ = roll.decide(steps, months)
            self.assertEqual(verdict, "PENDING")

    def test_gap_is_missing_not_filled(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            days = roll.step_days(2026, 11)
            synth(out, days[:2])     # steps 3-5 never recorded
            steps, missing, _ = roll.score(dt.date(2026, 11, 13), out)
            self.assertEqual(len(steps), 1)
            self.assertEqual(len(missing), 3)

    def test_mixed_jump_signs_stop_null(self):
        months = [dict(jumps=[0.2, -0.2, 0.2, 0.2, 0.2])]
        self.assertEqual(roll.decide([], months)[0], "NULL")


if __name__ == "__main__":
    unittest.main()
