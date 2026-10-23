import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import forward_lag as fl

H = fl.H


def ticks(start, runs):
    """One row per hour from start; runs[i] is the run_at string of hour i."""
    t0 = int(pd.Timestamp(start, tz="UTC").value // 1_000_000)
    return pd.DataFrame({"t": [t0 + i * H for i in range(len(runs))], "run_at": runs})


class TestForwardLag(unittest.TestCase):
    def test_hour_lag_is_minutes_after_bar_close(self):
        tk = ticks("2026-10-20 00:00", ["2026-10-20T01:12:00Z", "2026-10-20T04:00:00Z"])
        self.assertEqual(list(fl.hour_lags(tk)), [12.0, 120.0])

    def test_strict_ontime_needs_every_hour_prompt(self):
        prompt = [(pd.Timestamp("2026-10-20 01:12", tz="UTC") + pd.Timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
                  for i in range(24)]
        backfill = prompt[:20] + ["2026-10-21T03:00:00Z"] * 4
        d1 = fl.by_day(ticks("2026-10-20", prompt))
        d2 = fl.by_day(ticks("2026-10-20", backfill))
        self.assertTrue(bool(d1.strict_ontime.iloc[0]))
        self.assertFalse(bool(d2.strict_ontime.iloc[0]))
        self.assertEqual(int(d2.hours_late.iloc[0]), 4)
        replay = fl.by_day(ticks("2026-10-19", prompt))
        self.assertEqual(replay.kind.iloc[0], "replay")

    def test_order_check_flags_gaps_and_reordering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.csv"
            pd.DataFrame({"day": ["2026-10-01", "2026-10-02", "2026-10-04", "2026-10-03"],
                          "book": ["A"] * 4}).to_csv(p, index=False)
            self.assertEqual(fl.order_check(p)["problems"], {"A": {"out_of_order": 1, "gaps": 1}})
            pd.DataFrame({"day": ["2026-10-01", "2026-10-02"], "book": ["A", "A"]}).to_csv(p, index=False)
            self.assertEqual(fl.order_check(p)["problems"], {})


if __name__ == "__main__":
    unittest.main()
