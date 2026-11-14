"""Synthetic checks for R306's Malaysian SnR rules: no market data is read."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts import run_msnr as m

H = m.HOUR


def path(closes4):
    """Hourly o, h, l, c whose 4-hour candles open at the previous candle's close and close at `closes4`, with wicks
    of 0.1 around each hour's body."""
    o, h, l, c = [], [], [], []
    prev = closes4[0]
    for x in closes4:
        steps = np.linspace(prev, x, 5)
        for a, b in zip(steps[:-1], steps[1:]):
            o.append(a)
            c.append(b)
            h.append(max(a, b) + 0.1)
            l.append(min(a, b) - 0.1)
        prev = x
    return [np.array(v, float) for v in (o, h, l, c)]


class LevelTest(unittest.TestCase):
    def test_candles_do_not_touch_inputs(self):
        o, h, l, c = path([10, 11, 12])
        c[5] = np.nan
        O, H_, L, C = m.candles(o, h, l, c)
        self.assertEqual(len(C), 3)
        self.assertTrue(np.isnan(C[1]) and np.isnan(O[1]))
        self.assertAlmostEqual(C[2], 12.0)
        self.assertAlmostEqual(H_[2], 12.1)
        self.assertTrue(np.isfinite(o[4]))                 # the input row is left alone

    def test_a_and_v_levels_from_bodies(self):
        closes = [10 + 0.01 * i for i in range(16)] + [11, 12, 11, 10, 11]
        o, h, l, c = path(closes)
        O, H_, L, C = m.candles(o, h, l, c)
        lv = m.levels(O, H_, L, C)
        a = [x for x in lv if x[0] == 1]
        v = [x for x in lv if x[0] == -1]
        self.assertEqual(a[-1][1], 12.0)                   # the bullish candle's close before the bearish one
        self.assertEqual(a[-1][2], 4 * (17 + 2))           # live once the next candle has closed
        self.assertEqual(v[-1][1], 10.0)
        self.assertGreater(a[-1][3], 0)

    def test_first_touch_needs_penetration(self):
        h = np.array([9.0, 10.0, 10.0019, 10.003])
        l = h - 1
        self.assertEqual(m.first_touch(h, l, 1, 10.0, 0, 4), 3)
        self.assertEqual(m.first_touch(h, l, 1, 10.0, 0, 3), -1)
        self.assertEqual(m.first_touch(h, l - 9.0, -1, 0.5, 0, 4), 0)


class TradeTest(unittest.TestCase):
    def setUp(self):
        # an A-level at 12 forms at candles 17-18; price comes back up through it at candle 21
        closes = [10 + 0.01 * i for i in range(16)] + [11, 12, 11, 10.5, 11.5, 12.5, 12.6, 12.7] + [12.7] * 30
        self.o, self.h, self.l, self.c = path(closes)
        O, H_, L, C = m.candles(self.o, self.h, self.l, self.c)
        self.lv = [x for x in m.levels(O, H_, L, C) if x[0] == 1 and x[1] == 12.0]
        self.T = len(self.c)
        self.t = np.arange(self.T, dtype=np.int64) * H

    def test_fade_fills_at_the_level_and_breaks_enter_at_the_close(self):
        fade = m.events(self.lv, self.o, self.h, self.l, self.c, "fade", 30)
        self.assertEqual(len(fade), 1)
        row, side, entry, atr, level = fade[0]
        self.assertEqual((side, entry), (-1, 12.0))
        self.assertGreaterEqual(self.h[row], 12.0 * (1 + m.PEN))
        brk = m.events(self.lv, self.o, self.h, self.l, self.c, "break", 30)
        self.assertEqual(brk[0][1], 1)
        self.assertEqual(brk[0][0] % 4, 3)                 # the touch candle's last hour
        self.assertGreater(brk[0][2], 12.0)
        self.assertEqual(m.events(self.lv, self.o, self.h, self.l, self.c, "fade", 1), [])   # expired first

    def test_trades_funding_cost_and_overlap(self):
        fund = np.zeros(self.T)
        fund[100] = 0.001                                  # a long pays it
        cost = np.full(self.T, 5e-4)
        ok = np.ones(self.T, bool)
        tr = m.trades(self.lv, self.t, self.o, self.h, self.l, self.c, fund, cost, ok, ("break", 30, "t24"))
        self.assertEqual(len(tr), 1)
        x = tr[0]
        self.assertEqual(x["side"], 1)
        self.assertEqual(x["kind"], "A")
        self.assertEqual(x["t_exit"] - x["t"], 24 * H)
        self.assertAlmostEqual(x["funding"], -0.001 if x["t"] < 100 * H <= x["t_exit"] else 0.0)
        self.assertAlmostEqual(m.net(x, 2) - m.net(x, 1), -2 * 5e-4)
        none = m.trades(self.lv, self.t, self.o, self.h, self.l, self.c, fund, cost, np.zeros(self.T, bool),
                        ("break", 30, "t24"))
        self.assertEqual(none, [])

    def test_bracket_stop_comes_first(self):
        h = np.array([10.0, 10.5, 12.0, 10.0])
        l = np.array([10.0, 9.5, 8.0, 10.0])
        c = np.array([10.0, 10.0, 10.0, 10.0])
        self.assertEqual(m.bracket_exit(1, 0, 10.0, 0.1, h, l, c, fade=False, cap=3), (2, 9.0))
        # a fade entry's own bar can stop out but not take profit
        h2 = np.array([12.5, 10.0, 10.0, 10.0])
        l2 = np.array([8.0, 10.0, 10.0, 10.0])
        self.assertEqual(m.bracket_exit(-1, 0, 10.0, 0.2, h2, l2, c, fade=True, cap=3), (0, 12.0))
        self.assertEqual(m.bracket_exit(-1, 0, 10.0, 0.3, h2, l2, c, fade=True, cap=3), (3, 10.0))


class TreeTest(unittest.TestCase):
    def test_tree_sha_is_order_free_and_content_bound(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a, b = root / "a.parquet", root / "b.parquet"
            a.write_bytes(b"one")
            b.write_bytes(b"two")
            s1 = m.tree_sha([a, b], root)
            self.assertEqual(s1, m.tree_sha([b, a], root))
            b.write_bytes(b"three")
            self.assertNotEqual(s1, m.tree_sha([a, b], root))
            self.assertNotEqual(m.tree_sha([a], root), m.tree_sha([a, b], root))


class StatsTest(unittest.TestCase):
    def test_cohort_window_and_trials(self):
        day = 24 * H
        tr = [{"t": d * day, "t_exit": d * day + 3 * H, "gross": 0.01 * (1 if d % 2 else -0.5), "funding": 0.0,
               "cost": 0.0} for d in range(40)]
        s = m.cohort_stats(tr, 0, 30 * day, 1)
        self.assertEqual(s["trades"], 30)
        self.assertEqual(s["days"], 30)
        self.assertAlmostEqual(s["per_trade_bp"], 25.0)
        self.assertEqual(m.TRIALS, 24)
        self.assertEqual(len(m.BOOKS), 12)


if __name__ == "__main__":
    unittest.main()
