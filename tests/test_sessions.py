import unittest

import numpy as np
import pandas as pd

from lab import sessions


def row(stamp_utc):
    """Panel open time whose decision time (bar close) is the given UTC stamp."""
    return np.array([pd.Timestamp(stamp_utc, tz="UTC").value // 10**6 - sessions.HOUR])


class ClockTests(unittest.TestCase):
    def code(self, name, stamp):
        return int(sessions.codes(row(stamp), name)[0])

    def test_us_open_follows_daylight_saving(self):
        self.assertEqual(self.code("us_clock", "2024-07-01 13:00"), 4)   # 09:00 EDT: next bar holds the 09:30 open
        self.assertEqual(self.code("us_clock", "2024-07-01 14:00"), 5)
        self.assertEqual(self.code("us_clock", "2024-01-08 14:00"), 4)   # 09:00 EST
        self.assertEqual(self.code("us_clock", "2024-01-08 20:00"), 10)  # 15:00 EST: next bar ends at the close
        self.assertEqual(self.code("us_clock", "2024-01-08 21:00"), 11)
        self.assertEqual(self.code("us_clock", "2024-07-04 14:00"), 14)  # Independence Day
        self.assertEqual(self.code("us_clock", "2024-03-29 14:00"), 14)  # Good Friday
        self.assertEqual(self.code("us_clock", "2024-07-06 14:00"), 14)  # Saturday

    def test_london_open(self):
        self.assertEqual(self.code("eu_clock", "2024-07-01 07:00"), 3)   # 08:00 BST
        self.assertEqual(self.code("eu_clock", "2024-01-08 08:00"), 3)   # 08:00 GMT
        self.assertEqual(self.code("eu_clock", "2024-01-06 08:00"), 13)

    def test_cme_week(self):
        self.assertEqual(self.code("cme_clock", "2024-07-07 22:00"), 1)  # Sunday 18:00 EDT reopen
        self.assertEqual(self.code("cme_clock", "2024-07-08 01:00"), 2)
        self.assertEqual(self.code("cme_clock", "2024-07-06 12:00"), 0)  # Saturday
        self.assertEqual(self.code("cme_clock", "2024-07-05 20:00"), 5)  # Friday 16:00 EDT
        self.assertEqual(self.code("cme_clock", "2024-07-05 21:00"), 0)  # Friday 17:00 EDT close
        self.assertEqual(self.code("cme_clock", "2024-07-09 21:00"), 3)  # Tuesday maintenance break
        self.assertEqual(self.code("cme_clock", "2024-07-09 15:00"), 4)

    def test_us_days(self):
        self.assertEqual(self.code("us_day", "2024-09-18 18:00"), 3)     # FOMC
        self.assertEqual(self.code("us_day", "2024-09-06 12:00"), 2)     # first Friday
        self.assertEqual(self.code("us_day", "2024-09-05 12:00"), 1)     # Thursday
        self.assertEqual(self.code("us_day", "2024-09-10 12:00"), 0)
        self.assertEqual(self.code("us_day", "2024-09-02 12:00"), 4)     # Labor Day
        self.assertEqual(self.code("us_day", "2024-09-07 12:00"), 5)

    def test_expiry(self):
        self.assertEqual(self.code("expiry_clock", "2024-06-28 07:00"), 5)  # quarterly expiry morning
        self.assertEqual(self.code("expiry_clock", "2024-06-28 09:00"), 6)
        self.assertEqual(self.code("expiry_clock", "2024-07-25 12:00"), 2)
        self.assertEqual(self.code("expiry_clock", "2024-07-02 12:00"), 3)
        self.assertEqual(self.code("expiry_clock", "2024-07-15 12:00"), 4)

    def test_dst_flag(self):
        t = np.arange(pd.Timestamp("2024-01-01", tz="UTC").value // 10**6, pd.Timestamp("2025-01-01", tz="UTC").value // 10**6,
                      sessions.HOUR)
        fast = sessions.codes(t, "us_dst")
        ny = pd.to_datetime(t[::97] + sessions.HOUR, unit="ms", utc=True).tz_convert("America/New_York")
        slow = np.array([bool(x.dst()) for x in ny], np.float32)
        np.testing.assert_array_equal(fast[::97], slow)
        self.assertAlmostEqual(fast.mean(), 238 / 366, delta=0.01)


if __name__ == "__main__":
    unittest.main()
