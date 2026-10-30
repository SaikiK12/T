"""R335 locked_carry_v1 on invented numbers: the locked-dollar identity, the clocks and the engine's bookkeeping."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_locked_carry as lc

H, DAY = lc.H, lc.DAY


def flat_market(hours, f_over_s, expiry_hours, t0=0):
    """One contract expiring `expiry_hours` after t0, futures at f_over_s x spot, spot 100."""
    grid = np.arange(t0, t0 + hours * H, H, dtype=np.int64)
    spot = np.full(hours, 100.0)
    fut = {"X_1": (t0 + expiry_hours * H, np.full(hours, 100.0 * f_over_s))}
    return grid, fut, spot


class LockedDollar(unittest.TestCase):
    def test_value_is_b_times_f0_at_any_settlement(self):
        rng = np.random.default_rng(0)
        for _ in range(200):
            b, f0, ft = rng.uniform(0.1, 5), rng.uniform(1e3, 1e5), rng.uniform(10, 1e6)
            self.assertAlmostEqual(lc.locked_value_usd(b, f0, ft) / (b * f0), 1.0, places=9)

    def test_equity_equals_notional_so_one_x_never_liquidates(self):
        b, f0 = 2.0, 50_000.0
        for mark in (5_000.0, 50_000.0, 500_000.0):
            equity_coins = b + lc.inverse_short_coins(b * f0, f0, mark)
            notional_coins = b * f0 / mark
            self.assertAlmostEqual(equity_coins / notional_coins, 1.0, places=12)

    def test_short_gains_coins_when_price_falls(self):
        self.assertGreater(lc.inverse_short_coins(1000.0, 100.0, 50.0), 0)
        self.assertLess(lc.inverse_short_coins(1000.0, 100.0, 200.0), 0)


class Clocks(unittest.TestCase):
    def test_expiry_is_0800_utc_on_the_suffix_date(self):
        self.assertEqual(lc.expiry_ms("BTCUSD_210326"), int(pd.Timestamp("2021-03-26 08:00", tz="UTC").timestamp() * 1000))

    def test_tbill_observation_waits_two_days(self):
        d = int(pd.Timestamp("2024-01-10", tz="UTC").timestamp() * 1000)
        grid = np.array([d + 2 * DAY - 2 * H, d + 2 * DAY - H], dtype=np.int64)  # closes at d+2d-1h and d+2d
        r = lc.tbill_asof(grid, np.array([d - DAY * 5, d]), np.array([1.0, 5.0]))
        self.assertAlmostEqual(r[0], 0.01)
        self.assertAlmostEqual(r[1], 0.05)

    def test_no_row_before_t0_is_returned(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = np.arange(-5, 5, dtype=np.int64) * H + 10 * H
            path = Path(tmp) / "x.parquet"
            pd.DataFrame({"t": t, "close": 1.0 + np.arange(10), "volume": 1.0}).to_parquet(path)
            out = lc.load_close(path, t0=10 * H, t1=15 * H)
            np.testing.assert_array_equal(out, [6.0, 7.0, 8.0, 9.0, 10.0])

    def test_untraded_or_thin_bar_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.parquet"
            pd.DataFrame({"t": np.arange(4, dtype=np.int64) * H, "close": [1.0, 2.0, 3.0, 4.0],
                          "volume": [5.0, 0.0, 1.0, 9.0], "count": [10, 0, 9, 40]}).to_parquet(path)
            out = lc.load_close(path, t0=0, t1=4 * H)
            np.testing.assert_array_equal(np.isnan(out), [False, True, True, False])


class Engine(unittest.TestCase):
    def test_locks_at_first_close_and_holds_to_expiry(self):
        hours, exp = 60 * 24, 30 * 24
        grid, fut, spot = flat_market(hours, 1.02, exp)
        r = np.zeros(hours)
        locks, logs, locked = lc.engine(grid, fut, spot, r, hurdle=0.0)
        self.assertEqual(locks[0]["i"], 0)
        self.assertEqual(locks[0]["slots"], exp - 1)
        self.assertFalse(locked[0])
        self.assertTrue(locked[1:exp].all())
        self.assertFalse(locked[exp])
        self.assertAlmostEqual(float(np.expm1(logs[1][1:exp].sum())), 0.02 - lc.COST, places=12)
        self.assertAlmostEqual(float(np.expm1(logs[2][1:exp].sum())), 0.02 - 2 * lc.COST, places=12)

    def test_hurdle_keeps_cash_at_the_tbill(self):
        hours = 60 * 24
        grid, fut, spot = flat_market(hours, 1.001, 30 * 24)
        r = np.full(hours, 0.05)
        locks, logs, locked = lc.engine(grid, fut, spot, r, hurdle=0.03)
        self.assertEqual(locks, [])
        self.assertFalse(locked.any())
        np.testing.assert_allclose(logs[1], np.log1p(0.05) / 8760.0)

    def test_short_tau_is_not_eligible(self):
        hours = 30 * 24
        grid, fut, spot = flat_market(hours, 1.05, 10 * 24)
        locks, _, _ = lc.engine(grid, fut, spot, np.zeros(hours), hurdle=0.0)
        self.assertEqual(locks, [])

    def test_lock_past_window_is_cut(self):
        hours, exp = 20 * 24, 40 * 24
        grid, fut, spot = flat_market(hours, 1.02, exp)
        locks, logs, locked = lc.engine(grid, fut, spot, np.zeros(hours), hurdle=0.0)
        self.assertEqual(locks[0]["in_window"], hours - 1)
        share = (hours - 1) / (exp - 1)
        self.assertAlmostEqual(float(logs[1].sum()), np.log1p(0.02 - lc.COST) * share, places=12)

    def test_relocks_after_expiry(self):
        hours = 100 * 24
        grid = np.arange(0, hours * H, H, dtype=np.int64)
        spot = np.full(hours, 100.0)
        fut = {"A": (30 * 24 * H, np.full(hours, 102.0)), "B": (80 * 24 * H, np.full(hours, 101.0))}
        locks, _, locked = lc.engine(grid, fut, spot, np.zeros(hours), hurdle=0.0)
        self.assertEqual([b["contract"] for b in locks], ["A", "B"])
        self.assertEqual(locks[1]["i"], 30 * 24)

    def test_picks_the_higher_annual_excess(self):
        hours = 10 * 24
        grid = np.arange(0, hours * H, H, dtype=np.int64)
        spot = np.full(hours, 100.0)
        fut = {"near": (30 * 24 * H, np.full(hours, 101.0)), "far": (150 * 24 * H, np.full(hours, 103.0))}
        b = lc.best_lock(0, grid, fut, spot, np.zeros(hours))
        self.assertEqual(b["contract"], "near")  # 0.75% over ~30 d beats 2.75% over ~150 d per year

    def test_lock_vs_realized_tbill(self):
        hours, exp = 60 * 24, 30 * 24
        grid, fut, spot = flat_market(hours, 1.02, exp)
        r = np.zeros(hours)
        locks, _, _ = lc.engine(grid, fut, spot, r, hurdle=0.0)
        r_path = np.full(hours, 0.5)  # the T-bill jumps after entry
        vs = lc.lock_vs_tbill(locks, r_path, grid, 1)
        paid = np.expm1(np.log1p(0.5) / 8760.0 * (exp - 1))
        self.assertAlmostEqual(float(vs[0]), 0.02 - lc.COST - paid, places=12)


if __name__ == "__main__":
    unittest.main()
