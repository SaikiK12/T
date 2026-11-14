import unittest

import numpy as np
import pandas as pd

from scripts import run_weekend_reopen as wr

MIN = 60_000


def utc_ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


class WeekendReopenTest(unittest.TestCase):
    def test_new_york_clock_follows_dst(self):
        self.assertEqual(wr.ny_ms("2026-03-08", 18), utc_ms("2026-03-08 22:00"))   # first EDT Sunday
        self.assertEqual(wr.ny_ms("2026-03-01", 18), utc_ms("2026-03-01 23:00"))   # EST
        self.assertEqual(wr.ny_ms("2026-10-26", 9, 30), utc_ms("2026-10-26 13:30"))

    def test_weekend_anchors_and_holidays(self):
        wk = wr.weekends("2026-05-15", "2026-07-10").set_index("friday")
        self.assertTrue(wk.loc["2026-05-22", "holiday"])      # Memorial Day Monday
        self.assertTrue(wk.loc["2026-06-19", "holiday"])      # Juneteenth Friday
        self.assertTrue(wk.loc["2026-07-03", "holiday"])      # Independence Day observed
        self.assertFalse(wk.loc["2026-05-29", "holiday"])
        r = wk.loc["2026-05-29"]
        self.assertEqual(r.F, utc_ms("2026-05-29 21:00"))
        self.assertEqual(r.S, utc_ms("2026-05-31 22:00"))
        self.assertEqual((r.E_pre, r.E_post, r.x15, r.x60), (r.S - 5 * MIN, r.S + MIN, r.S + 15 * MIN, r.S + 60 * MIN))
        self.assertEqual(r.cash, utc_ms("2026-06-01 13:30"))

    def test_price_is_the_last_traded_close_before_the_instant(self):
        t = np.array([0, MIN, 2 * MIN, 10 * MIN], np.int64)
        c = np.array([1.0, 2.0, 3.0, 4.0])
        p, age = wr.price_at(t, c, np.array([2 * MIN, 3 * MIN, 9 * MIN, 11 * MIN]), stale_min=5)
        self.assertEqual(p[0], 2.0)            # the bar opening at 1 min ends at 2 min
        self.assertEqual(p[1], 3.0)
        self.assertTrue(np.isnan(p[2]))        # 3.0 is 6 minutes old: stale
        self.assertEqual(p[3], 4.0)
        self.assertEqual(age[1], 0.0)

    def test_fade_earns_the_giveback_at_the_reopen(self):
        wk = wr.weekends("2026-05-29", "2026-05-29")
        r = wk.iloc[0]
        t = np.arange(r.F - 120 * MIN, r.cash + 10 * MIN, MIN, dtype=np.int64)
        c = np.full(len(t), 100.0)
        c[t >= r.F + 60 * MIN] = 101.0         # weekend move +1% after the Friday close
        c[t >= r.S] = 100.7                    # the reopen gives back 0.3 points
        rows = wr.legs(t, c, wk, "CLUSDT")
        self.assertTrue(rows.valid.iloc[0])
        self.assertAlmostEqual(rows.W_pre.iloc[0], 1e4 * np.log(1.01), places=6)
        g, w, grp, sym = wr.trades(rows, "pre", "x15", 50.0, "all", "fade")
        self.assertAlmostEqual(g[0], -1e4 * np.log(100.7 / 101.0), places=6)
        self.assertEqual((w[0], grp[0], sym[0]), ("2026-05-29", "energy", "CLUSDT"))
        g2, *_ = wr.trades(rows, "pre", "x15", 50.0, "all", "follow")
        self.assertAlmostEqual(g2[0], -g[0])
        self.assertEqual(len(wr.trades(rows, "pre", "x15", 150.0, "all", "fade")[0]), 0)   # |W| ~ 99.5 bp < 150
        g3, *_ = wr.trades(rows, "post", "x15", 0.0, "all", "fade")
        self.assertAlmostEqual(g3[0], 0.0)     # after the reopen nothing moves in this tape
        self.assertEqual(len(wr.trades(rows, "pre", "x15", 0.0, "metals", "fade")[0]), 0)

    def test_holiday_and_unlisted_weekends_are_invalid(self):
        wk = wr.weekends("2026-06-19", "2026-06-26")
        r = wk.iloc[-1]
        t = np.arange(r.F - 10 * MIN, r.cash + 10 * MIN, MIN, dtype=np.int64)
        rows = wr.legs(t, np.full(len(t), 50.0), wk, "XAUUSDT")
        self.assertEqual(rows.valid.tolist(), [False, True])   # 06-19 is a holiday Friday

    def test_block_bootstrap_and_slope(self):
        rng = np.random.default_rng(0)
        ci = wr.block_boot(np.ones(40), np.repeat(np.arange(20), 2), rng)
        self.assertEqual((ci["mean"], ci["lo"], ci["hi"], ci["p_le0"], ci["blocks"]), (1.0, 1.0, 1.0, 0.0, 20))
        x = np.linspace(-100, 100, 60)
        s = wr.slope_boot(x, -0.2 * x, np.repeat(np.arange(20), 3), rng)
        self.assertAlmostEqual(s["b"], -0.2)
        self.assertAlmostEqual(s["lo"], -0.2)

    def test_verdict(self):
        wks = np.repeat(np.arange(20), 2)
        grp = np.array(["energy", "metals"] * 20)
        good = dict(lo=1.0, p_le0=0.0)
        self.assertEqual(wr.verdict(np.full(40, 30.0), wks, grp, good), "PASS")
        self.assertEqual(wr.verdict(np.full(40, 20.0), wks, grp, good), "PARTIAL")      # 2x net negative
        self.assertEqual(wr.verdict(np.full(40, 5.0), wks, grp, dict(lo=-8.0, p_le0=1.0)), "NULL")
        self.assertEqual(wr.verdict(np.full(20, 30.0), wks[:20], grp[:20], good), "INCONCLUSIVE")
        bad_group = np.r_[np.full(20, 80.0), np.full(20, -1.0)]
        self.assertEqual(wr.verdict(bad_group, wks, np.array(["energy"] * 20 + ["metals"] * 20), good), "PARTIAL")

    def test_trial_count(self):
        self.assertEqual(wr.TRIALS, 2 * 3 * 3 * 4 * 2 + 4 + 2 * 3 * 4 + 2)


if __name__ == "__main__":
    unittest.main()
