"""R528's daily construction on synthetic hourly bars: New York hours across DST, roll exclusion, signs and costs."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_closing_momentum as cm


def bars(days, inst=None, px=None):
    """Hourly bars (open-time stamps, UTC) from 13:00 to 21:00 UTC on each date; close = px(date, ny_close_hour)."""
    rows = []
    for i, d in enumerate(days):
        for h in range(12, 23):
            ts = pd.Timestamp(f"{d} {h:02d}:00", tz="UTC")
            close_ny = (ts + pd.Timedelta(hours=1)).tz_convert(cm.NY)
            rows.append({"ts": ts, "instrument_id": (inst or {}).get(d, 1),
                         "close": px(i, close_ny.hour) if px else 100.0 + i + close_ny.hour / 100})
    return pd.DataFrame(rows)


class Closing(unittest.TestCase):
    def test_new_york_hours_across_dst(self):
        b = bars(["2024-03-08", "2024-03-11"])              # US DST starts 2024-03-10
        w = cm.closes(b)
        for d in w.index:
            self.assertTrue(np.isfinite(w.loc[d, "close10"]) and np.isfinite(w.loc[d, "close16"]))
        # 16:00 New York is 21:00 UTC in winter and 20:00 UTC in summer; the close value encodes the NY hour
        self.assertAlmostEqual(w.iloc[0].close16 % 1, 0.16, places=6)
        self.assertAlmostEqual(w.iloc[1].close16 % 1, 0.16, places=6)

    def test_signs_targets_and_costs(self):
        # day 1: up from the previous close to 10:00 (A long) and to 15:00 (B long); the last hour rises 1%
        def px(i, hour):
            if i == 0:
                return 100.0
            return {10: 101.0, 15: 99.0, 16: 99.99}.get(hour, 100.5)
        t = cm.trades(cm.closes(bars(["2024-06-03", "2024-06-04"], px=px)), 0.0001)
        self.assertEqual(len(t), 1)
        r = t.iloc[0]
        self.assertAlmostEqual(r.target, np.log(99.99 / 99.0))
        self.assertEqual(r.sA, 1.0)                          # 101 > 100
        self.assertEqual(r.sB, -1.0)                         # 99 < 100
        self.assertAlmostEqual(r.A, r.target - 0.0001)
        self.assertAlmostEqual(r.B, -r.target - 0.0001)

    def test_a_roll_day_is_excluded(self):
        b = bars(["2024-06-03", "2024-06-04", "2024-06-05"], inst={"2024-06-04": 2, "2024-06-05": 2})
        t = cm.trades(cm.closes(b), 0.0001)
        self.assertEqual([d.strftime("%Y-%m-%d") for d in t.index], ["2024-06-05"])

    def test_decide(self):
        ok = cm.decide({"nw_t": 3.1}, {"mean_bp": 0.5}, [1.0, 0.2])
        self.assertEqual(ok[0], "PASS")
        self.assertEqual(cm.decide({"nw_t": 2.5}, {"mean_bp": 0.5}, [1.0, 0.2])[0], "FAIL")
        self.assertEqual(cm.decide({"nw_t": 3.1}, {"mean_bp": 0.5}, [1.0, -0.2])[0], "FAIL")


if __name__ == "__main__":
    unittest.main()
