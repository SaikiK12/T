import unittest
from datetime import datetime, timezone

import pandas as pd

from scripts import record_cboe_chain as C


class Cboe(unittest.TestCase):
    def test_sessions_follow_new_york_time(self):
        utc = lambda *a: datetime(*a, tzinfo=timezone.utc)
        self.assertEqual(C.session(utc(2026, 11, 6, 13, 40)), "pre")      # 08:40 New York (EST)
        self.assertIsNone(C.session(utc(2026, 7, 6, 13, 40)))             # 09:40 EDT, after the open
        self.assertEqual(C.session(utc(2026, 7, 6, 12, 40)), "pre")
        self.assertIsNone(C.session(utc(2026, 11, 6, 14, 30)))            # 09:30 New York, the open
        self.assertEqual(C.session(utc(2026, 11, 6, 21, 30)), "post")     # 16:30 New York
        self.assertIsNone(C.session(utc(2026, 11, 7, 13, 40)))            # Saturday

    def test_table_and_gex(self):
        doc = {"timestamp": "2026-11-06 15:42:13", "data": {"current_price": 100.0, "options": [
            {"option": "QQQ261120C00100000", "open_interest": 10, "gamma": 0.05, "iv": 0.2, "delta": 0.5},
            {"option": "QQQ261120P00095000", "open_interest": 20, "gamma": 0.02, "iv": 0.25, "delta": -0.3},
            {"option": "BAD", "open_interest": 1}]}}
        t, bad = C.table(doc, "QQQ")
        self.assertEqual(bad, 1)
        self.assertEqual(list(t.columns), C.COLS)
        self.assertEqual(t.strike.tolist(), [100.0, 95.0])
        self.assertEqual(t.expiry.iloc[0], pd.Timestamp("2026-11-20"))
        g = C.gex(t)
        self.assertAlmostEqual(g[100.0], 0.05 * 10 * 100 * 100 ** 2 * 0.01)
        self.assertAlmostEqual(g[95.0], -0.02 * 20 * 100 * 100 ** 2 * 0.01)
        self.assertAlmostEqual(C.gex(t, sign=-1)[95.0], -g[95.0])


if __name__ == "__main__":
    unittest.main()
