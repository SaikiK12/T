import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_litpoolsel", ROOT / "scripts" / "run_litpoolsel.py")
lp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lp)
DAY = lp.DAY


def pools_frame(specs):
    """specs: (index, master, type, created 'YYYY-MM-DD', fee %)."""
    return pd.DataFrame([{"account_index": i, "name": f"p{i}", "account_type": t, "master_account_index": m,
                          "created_at": lp.ms(c) // 1000, "status": 0, "operator_fee": fee,
                          "min_operator_share_rate": 5, "total_asset_value": 1e5, "operator_shares": 1,
                          "total_shares": 10} for i, m, t, c, fee in specs])


def series(start, end, daily, noise=0.0, seed=0, stop=None):
    """Daily share prices at 20:00 UTC from start to end (or stop), growing by `daily` a day plus noise."""
    days = pd.date_range(start, stop or end, freq="D")
    rng = np.random.default_rng(seed)
    r = daily + rng.normal(0, noise, len(days))
    ts = np.array([lp.ms(str(d.date())) + 20 * 3_600_000 for d in days], np.int64)
    return ts, np.cumprod(1 + r)


class LitPoolSel(unittest.TestCase):
    def test_universe_drops_auto_and_protocol_pools(self):
        p = pools_frame([(1, 4, 2, "2025-09-01", 0), (2, 1, 3, "2025-01-17", 0), (3, 77, 2, "2025-09-01", 20)])
        self.assertEqual(list(lp.universe(p).account_index), [3])

    def test_score_uses_only_past_points(self):
        h = series("2025-09-01", "2026-03-01", 0.001, 0.002)
        t = lp.ms("2026-01-31") + DAY - 1
        s = lp.score(h, t)
        h2 = (h[0], np.where(h[0] > t, h[1] * 3, h[1]))               # later prices changed: same score
        self.assertEqual(s, lp.score(h2, t))
        self.assertIsNone(lp.score(series("2026-01-01", "2026-03-01", 0.001, 0.002), t))   # too few points

    def test_score_needs_60_prices_in_the_window(self):
        t = lp.ms("2026-03-31") + DAY - 1
        for n, ok in ((59, False), (60, True)):
            ts = np.array([t - k * DAY for k in range(n)][::-1], np.int64)
            px = np.linspace(1, 1.1, n) + np.random.default_rng(0).normal(0, 0.001, n)
            self.assertEqual(lp.score((ts, px), t) is not None, ok)

    def test_held_return_and_fee(self):
        h = series("2025-09-01", "2026-06-01", 0.001)
        t0, t1, _ = lp.bounds("2026-01-31")
        self.assertAlmostEqual(lp.held_return(h, t0, t1), 1.001 ** 28 - 1)
        p = pools_frame([(10, 77, 2, "2025-09-01", 20)])
        book = lp.run(p, {10: h}, "2026-01-31", "2026-01-31")
        g = 1.001 ** 28 - 1
        idle = lp.HURDLE_ANN * 28 / 365 * (lp.TOP_N - 1)
        self.assertAlmostEqual(book.net_fee.iloc[0], (g * 0.8 + idle) / lp.TOP_N)
        self.assertAlmostEqual(book.cost_1x.iloc[0], lp.SWITCH_COST / lp.TOP_N)

    def test_picks_the_steadiest_and_skips_young_dead_or_losing_pools(self):
        specs = [(1, 77, 2, "2025-09-01", 10), (2, 77, 2, "2025-09-01", 10), (3, 77, 2, "2026-01-15", 10),
                 (4, 77, 2, "2025-09-01", 10), (5, 77, 2, "2025-09-01", 10)]
        hist = {1: series("2025-09-01", "2026-04-01", 0.002, 0.001, 1),     # steady gain
                2: series("2025-09-01", "2026-04-01", 0.002, 0.03, 2),      # noisy gain
                3: series("2026-01-15", "2026-04-01", 0.01, 0.0001, 3),     # too young at 01-31
                4: series("2025-09-01", "2026-04-01", 0.002, 0.001, 4, stop="2026-01-20"),   # stopped pricing
                5: series("2025-09-01", "2026-04-01", -0.002, 0.001, 5)}    # losing
        book = lp.run(pools_frame(specs), hist, "2026-01-31", "2026-01-31")
        self.assertEqual(book.eligible.iloc[0], 3)
        self.assertEqual(book.pools.iloc[0].split()[0], "1")
        self.assertNotIn("5", book.pools.iloc[0].split())

    def test_switch_cost_counts_changes(self):
        specs = [(1, 77, 2, "2025-09-01", 0)]
        hist = {1: series("2025-09-01", "2026-06-01", 0.001, 0.0005, 1)}
        book = lp.run(pools_frame(specs), hist, "2026-01-31", "2026-03-31")
        self.assertEqual(list(book.new), [1, 0, 0])
        self.assertEqual(list(book.cost_1x), [lp.SWITCH_COST / lp.TOP_N, 0.0, 0.0])

    def test_summary_and_decision(self):
        book = pd.DataFrame({"formation": [f"m{i}" for i in range(12)], "days": [30.0] * 12,
                             "net_1x": np.linspace(0.009, 0.011, 12), "net_2x": np.linspace(0.008, 0.01, 12),
                             "net_3x": np.linspace(0.007, 0.009, 12), "gross": [0.012] * 12, "net_fee": [0.01] * 12,
                             "picks": [5] * 12, "new": [1] * 12})
        s = lp.summary(book)
        self.assertAlmostEqual(s["1x"]["net_ann"], 0.12 * 365 / 360)
        self.assertEqual(lp.decide_gate0(s), "EARNED (forward continues)")
        s["1x"]["excess_ann"] = 0.02
        self.assertEqual(lp.decide_gate0(s), "NULL (stop)")


if __name__ == "__main__":
    unittest.main()
