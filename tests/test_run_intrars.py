import unittest

import numpy as np
import pandas as pd

from scripts import run_intrars as ir


def day_index(d):
    return int((pd.Timestamp(d, tz="UTC").value // 10**6 - ir.T0) // ir.DAY)


def grid(C, G=None, R=None):
    n, S = C.shape
    return ir.Grid([f"S{j:02d}" for j in range(S)], C, np.zeros((n, S)) if G is None else G,
                   np.ones((n, S), np.float32) if R is None else R)


def drift_grid(nd, S=40, drift=0.0, seed=0):
    """Hourly closes with a fixed drift per coin (-drift .. +drift per hour) and noise: the morning's leaders tend to
    be the coins with the highest drift, so they keep leading."""
    rng = np.random.default_rng(seed)
    mu = drift * np.linspace(-1, 1, S)
    r = rng.normal(mu, 0.004, (24 * nd, S))
    return grid(100 * np.exp(np.cumsum(r, axis=0)))


class RowsTest(unittest.TestCase):
    def test_rows_and_us_hours(self):
        sp, e, x = ir.rows_for(3, 0, 4)
        self.assertEqual(list(sp), [-1, 23, 47])
        self.assertEqual(list(e), [3, 27, 51])
        self.assertEqual(list(x), [23, 47, 71])
        sp, e, x = ir.rows_for(2, 5, np.array([1, 2]))
        self.assertEqual(list(sp), [4, 28])
        self.assertEqual(list(e), [5, 30])
        us = ir.us_hours(200)
        self.assertEqual(us[day_index("2021-01-04")], 15)       # Monday, EST: 10:00 New York = 15:00 UTC
        self.assertEqual(us[day_index("2021-07-06")], 14)       # Tuesday, EDT
        self.assertEqual(us[day_index("2021-01-02")], 0)        # Saturday
        self.assertEqual(us[day_index("2021-07-05")], 0)        # Independence Day observed

    def test_windows(self):
        d = np.array([day_index("2023-12-31"), day_index("2024-01-01")])
        self.assertEqual(list(ir.in_window(d, 0, "disc")), [True, False])
        self.assertEqual(list(ir.in_window(d, 0, "valid")), [False, True])
        self.assertEqual(list(ir.in_window(d, 5, "disc")), [False, False])


class BookTest(unittest.TestCase):
    def setUp(self):
        S, k = 33, 4
        C = np.full((96, S), 100.0)
        s = np.arange(S) / 1000.0                                # the morning move rises with the coin index
        r = np.zeros(S)
        r[[29, 30, 31]] = 0.02                                   # the strongest eligible three keep rising
        r[[0, 1, 2]] = 0.01                                      # the weakest three rise too (the short loses)
        C[24:28] = 100 * (1 + s)
        C[28:] = 100 * (1 + s) * (1 + r)
        C[47, 31] = np.nan                                       # S31 has no last bar: exit at the close of row 46
        G = np.zeros_like(C)
        G[40:, [29, 30, 31]] = 0.001                             # a settlement inside the hold
        R = np.ones_like(C, dtype=np.float32)
        R[:, 32] = 60                                            # the biggest mover is outside the top 50
        R[72:, :10] = 60                                         # day 3: 23 names, skipped
        self.g, self.k = grid(C, G, R), k

    def books(self, n=3, seed=1):
        sp, e, x = ir.rows_for(4, 0, self.k)
        return ir.day_books(self.g, sp, e, x, np.ones(4, bool), n, seed)

    def test_legs_exit_funding(self):
        df = self.books()
        self.assertEqual(list(df.day), [1, 2])                   # day 0 has no start close, day 3 too few names
        d1 = df.iloc[0]
        self.assertEqual(d1.names, 32)
        self.assertAlmostEqual(d1.long, 0.02 - 0.001)
        self.assertAlmostEqual(d1.short, -0.01)
        self.assertAlmostEqual(d1.gross, 0.02 - 0.001 - 0.01)
        self.assertAlmostEqual(d1.price, 0.01)
        basket = (3 * (0.02 - 0.001) + 3 * 0.01) / 32
        self.assertAlmostEqual(d1.basket, basket)
        self.assertAlmostEqual(df.iloc[1].gross, 0.0)            # day 2 is flat
        fade = ir.flip(df)
        self.assertAlmostEqual(fade.iloc[0].gross, -d1.gross)
        self.assertAlmostEqual(fade.iloc[0].long, 0.01)
        self.assertAlmostEqual(fade.iloc[0].short, -(0.02 - 0.001))
        self.assertEqual(d1.top, "S29|S30|S31")
        self.assertEqual(d1.bot, "S00|S01|S02")
        self.assertEqual(fade.iloc[0].top, "S00|S01|S02")

    def test_ties_are_random(self):
        g = grid(np.full((24 * 6, 40), 100.0))
        sp, e, x = ir.rows_for(6, 0, 4)
        df = ir.day_books(g, sp, e, x, np.ones(6, bool), 3, 1)
        self.assertTrue(np.allclose(df.gross, 0.0))
        self.assertEqual(len(df), 5)
        self.assertGreater(len(set(df.top)), 1)                  # not the same coins every flat day
        self.assertNotIn("S39|S38|S37", set(df.top))             # nor the alphabetically last
        df2 = ir.day_books(g, sp, e, x, np.ones(6, bool), 3, 1)
        self.assertEqual(list(df.top), list(df2.top))           # seeded


class EndToEndTest(unittest.TestCase):
    def test_planted_continuation_is_found_and_null_is_not(self):
        nd = day_index("2024-06-30") + 1
        g = drift_grid(nd, drift=0.0006, seed=3)
        res = ir.family(g, 0, ir.ANCHORS)
        out = ir.analyze(g, res)
        self.assertTrue(out["pick"].endswith("follow"))
        p = out["strategies"][out["pick"]]
        self.assertGreater(p["valid"]["gross"]["mean_bp"], 0)
        self.assertGreater(p["valid"]["long_excess_bp"], 0)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertEqual(len(out["clocks"]), 1 + ir.PLACEBOS)
        self.assertEqual(out["strategies"]["us10 n3 fade"]["disc"]["gross"]["mean_bp"],
                         -out["strategies"]["us10 n3 follow"]["disc"]["gross"]["mean_bp"])
        null = ir.family(drift_grid(nd, seed=4), 0, (4,))
        r = ir.report(null[(4, 5, "follow")])
        self.assertLess(abs(r["valid"]["gross"]["mean_bp"]), 15)
        self.assertLess(abs(r["valid"]["gross"]["t"]), 3)

    def test_plumbing_reads_no_return(self):
        g = drift_grid(40)
        out = ir.plumbing(g)
        self.assertEqual(out["k4"]["days"], 39)                 # day 0 has no start close
        self.assertEqual(out["k4"]["median_names"], 40.0)
        self.assertEqual(out["us10"]["days"], 26)               # NYSE days in 2021-01-02 .. 2021-02-09
        self.assertEqual(len(out["placebo_offsets"]), ir.PLACEBOS)


if __name__ == "__main__":
    unittest.main()
