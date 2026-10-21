import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_clockflow as rc

MIN = rc.MIN


def bars(t0, closes):
    t = t0 + np.arange(len(closes)) * MIN
    return pd.DataFrame({"t": t, "close": closes, "count": np.where(np.isnan(closes), 0, 1)})


class ClockflowTest(unittest.TestCase):
    def test_price_is_the_close_of_the_bar_before_the_instant(self):
        t0 = 0
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "X.parquet"
            closes = np.array([10.0, 11.0, np.nan, 13.0])
            bars(t0, closes).to_parquet(p)
            P = rc.load_prices(p, t0=t0, t1=t0 + 4 * MIN)
        self.assertTrue(np.isnan(rc.price(P, t0, t0=t0)))               # no bar ends at the first instant
        self.assertEqual(rc.price(P, t0 + MIN, t0=t0), 10.0)            # bar [0, 1) closes at 10
        self.assertTrue(np.isnan(rc.price(P, t0 + 3 * MIN, t0=t0)))     # an empty bar is not carried forward
        self.assertEqual(rc.price(P, t0 + 4 * MIN, t0=t0), 13.0)

    def test_sigma_needs_40_defined_values_among_the_last_60(self):
        m = np.r_[np.full(30, np.nan), np.arange(50, dtype=float)]
        s = rc.sigma(m)
        self.assertTrue(np.isnan(s[69]))                                # only 39 defined before index 69
        self.assertAlmostEqual(s[70], np.arange(40).std(ddof=1))
        self.assertAlmostEqual(s[79], np.arange(49).std(ddof=1))         # look-back of 60 still holds 30 NaNs

    def test_trades_fade_enter_a_minute_late_and_pay_funding_inside_the_hold(self):
        P = np.full(400, 100.0)
        P[10] = 98.0                                                    # window 0..10 moves -2%
        P[11] = 98.5                                                    # entry, one minute after the window
        P[11 + 60] = 99.0                                               # exit after h = 60
        F = np.array([11 * MIN, 30 * MIN, 71 * MIN, 72 * MIN], np.int64)
        rate = np.array([1.0, 2.0, 4.0, 8.0]) * 1e-4
        starts = np.array([0], np.int64)
        t = rc.trades(P, F, rate, starts, 10, np.array([0.01]), 1, "fade", 60, t0=0)
        self.assertEqual(len(t), 1)
        self.assertEqual(t.side[0], 1.0)                                # fade a fall: long
        self.assertAlmostEqual(t.gross[0], 99.0 / 98.5 - 1)
        self.assertAlmostEqual(t.funding[0], 6e-4)                      # settlements at 30 and 71, not 11 or 72
        none = rc.trades(P, F, rate, starts, 10, np.array([0.03]), 1, "fade", 60, t0=0)
        self.assertEqual(len(none), 0)                                  # |m| = 2% < 1 x 3%
        follow = rc.trades(P, F, rate, starts, 10, np.array([0.01]), 1, "follow", 60, t0=0)
        self.assertAlmostEqual(follow.gross[0], -(99.0 / 98.5 - 1))
        self.assertAlmostEqual(follow.funding[0], -6e-4)                # a short receives positive rates

    def test_clocks_follow_daylight_saving_holidays_and_expiry_fridays(self):
        c = rc.clocks()
        days, starts, _ = c["OPEN"]
        at = dict(zip(days.strftime("%Y-%m-%d"), starts))
        self.assertEqual(pd.to_datetime(at["2024-03-08"], unit="ms").strftime("%H:%M"), "14:30")   # EST
        self.assertEqual(pd.to_datetime(at["2024-03-11"], unit="ms").strftime("%H:%M"), "13:30")   # EDT
        self.assertNotIn("2024-07-04", at)                              # Independence Day
        self.assertNotIn("2024-03-09", at)                              # Saturday
        off_days = set(c["OPEN_OFF"][0].strftime("%Y-%m-%d"))
        self.assertIn("2024-07-04", off_days)
        days, starts, mask = c["SETTLE_monthly"]
        monthly = set(days[mask].strftime("%Y-%m-%d"))
        self.assertIn("2024-03-29", monthly)                            # last Friday of March 2024
        self.assertNotIn("2024-03-22", monthly)
        self.assertEqual(pd.to_datetime(starts[0], unit="ms").strftime("%H:%M"), "07:30")
        self.assertEqual(len(rc.variants()), rc.TRIALS)

    def test_inputs_must_match_their_frozen_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.bin").write_bytes(b"one")
            good = prereg.sha256_file(root / "a.bin")
            spec = root / "PREREG.md"
            spec.write_text(f"x\n```inputs\n{good}  a.bin\n```\n")
            self.assertEqual(rc.check_inputs(spec, root=root), {"a.bin": good})
            (root / "a.bin").write_bytes(b"two")
            with self.assertRaises(prereg.PreregError):
                rc.check_inputs(spec, root=root)

    def test_a_planted_open_reversal_is_booked_by_the_fade_and_lost_by_the_follow(self):
        t0, n_days = rc.T0, 150
        t1 = t0 + n_days * rc.DAY
        clk = rc.clocks(t0, t1)
        cal = pd.date_range(pd.to_datetime(t0, unit="ms"), pd.to_datetime(t1 - rc.DAY, unit="ms"), freq="D")
        rng = np.random.default_rng(0)
        coins = {}
        for sym in rc.COINS:
            r = rng.normal(0, 2e-4, (t1 - t0) // MIN + 1)
            for st in clk["OPEN"][1]:                                   # a 5-minute flush, half reverts in 60 min
                i = (st - t0) // MIN
                drop = rng.uniform(0.004, 0.012) * rng.choice([-1, 1])
                r[i + 1:i + 6] += drop / 5
                r[i + 7:i + 47] -= drop / 2 / 40
            P = 100 * np.exp(np.cumsum(r))
            coins[sym] = (P, np.array([t1 + rc.DAY], np.int64), np.array([0.0]))
        v = {"family": "OPEN", "clock": "OPEN", "w": 5, "k": 1, "side": "fade", "h": 60}
        book, tr = rc.run_variant(v, coins, clk, cal, t0=t0)
        self.assertEqual(len(book), n_days)
        self.assertGreater(len(tr), 30)
        self.assertTrue((tr.day.dt.weekday < 5).all())
        self.assertGreater(rc.net(book, rc.COST).sum(), 0)
        follow, _ = rc.run_variant(dict(v, side="follow"), coins, clk, cal, t0=t0)
        self.assertLess(rc.net(follow, rc.COST).sum(), 0)
        self.assertAlmostEqual(book.gross.sum(), -follow.gross.sum())


if __name__ == "__main__":
    unittest.main()
