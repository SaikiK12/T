"""R337 levels_lighter_v1 on invented numbers: the venue map, the book costs, Lighter pricing and the halves."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_levels_lighter as ll

H, DAY, GRID0 = ll.H, ll.DAY, ll.GRID0


def candles(n, t0=GRID0, close=None, vol=None):
    close = np.full(n, 100.0) if close is None else np.asarray(close, float)
    vol = np.ones(n) if vol is None else np.asarray(vol, float)
    return pd.DataFrame({"t": t0 + np.arange(n) * H, "close": close, "quote_volume": vol})


class VenueMap(unittest.TestCase):
    def test_open_route_only(self):
        c = pd.DataFrame({"symbol": ["APT", "CRO", "1000NOT"], "route": ["open", "reserved", "open"],
                          "binance_perp": ["APTUSDT", None, "NOTUSDT"]})
        self.assertEqual(ll.lighter_map(c), {"APTUSDT": "APT", "NOTUSDT": "1000NOT"})

    def test_book_cost_is_the_median_of_both_sides_with_a_floor(self):
        rows = pd.DataFrame({"symbol": ["A", "A", "A", "B", "R"], "buy_1k_bp": [2.0, 4.0, 9.0, 0.2, 1.0],
                             "sell_1k_bp": [4.0, 6.0, 11.0, 0.4, 1.0]})
        out = ll.book_costs(rows, {"A", "B"})
        self.assertAlmostEqual(out["A"], 5e-4)            # sides 3, 5, 10 bp: median 5
        self.assertAlmostEqual(out["B"], 1e-4)            # 0.3 bp floored to 1 bp
        self.assertNotIn("R", out)                        # a symbol outside the map is never read


class Pricing(unittest.TestCase):
    def test_return_from_decision_close_to_exit_close_net_of_funding(self):
        close = np.full(80, 100.0)
        close[75], close[76] = 102.0, 103.02                       # +2% then +1%
        cd = candles(80, close=close)
        fd = pd.DataFrame({"t": [GRID0 + 75 * H + 5, GRID0 + 76 * H], "rate": [0.001, 0.002]})
        grid = ll.coin_grid(cd, fd)
        # decision bar 74 (its close is the entry), exit row 76 on R333's grid: two bars held
        g, st = ll.price(GRID0 + 74 * H, 76, 1, *grid)
        self.assertEqual(st, 0)
        self.assertAlmostEqual(g, (0.02 - 0.001) + (0.01 - 0.002))
        g, st = ll.price(GRID0 + 74 * H, 76, -1, *grid)
        self.assertAlmostEqual(g, -((0.02 - 0.001) + (0.01 - 0.002)))

    def test_needs_72_traded_hours_to_the_decision(self):
        vol = np.ones(150)
        vol[40] = 0.0
        grid = ll.coin_grid(candles(150, vol=vol), pd.DataFrame(columns=["t", "rate"]))
        self.assertEqual(ll.price(GRID0 + 111 * H, 115, 1, *grid)[1], 1)   # hours 40..111: hour 40 untraded
        self.assertEqual(ll.price(GRID0 + 112 * H, 115, 1, *grid)[1], 0)   # hours 41..112 all traded
        self.assertEqual(ll.price(GRID0 + 30 * H, 35, 1, *grid)[1], 1)     # fewer than 72 hours of bars

    def test_a_missing_close_or_bar_drops_the_event(self):
        grid = ll.coin_grid(candles(100).drop(index=[80]), pd.DataFrame(columns=["t", "rate"]))
        self.assertEqual(ll.price(GRID0 + 79 * H, 82, 1, *grid)[1], 2)    # no close at bar 80, inside the hold
        self.assertEqual(ll.price(GRID0 + 85 * H, 88, 1, *grid)[1], 1)    # bar 80 untraded, within 72 h of bar 85
        self.assertEqual(ll.price(GRID0 + 90 * H, 120, 1, *grid)[1], 3)   # the exit is past the last bar


class Stats(unittest.TestCase):
    def test_halves_split_on_the_lanes_date(self):
        net = np.array([0.01, -0.02, 0.03])
        day = np.array([ll.D0, ll.HALF - 1, ll.HALF])
        s = ll.sum_stats(net, day, np.array(["A", "B", "A"]))
        n_first, n_second = ll.HALF - ll.D0, ll.D1 - ll.HALF
        self.assertAlmostEqual(s["bp_per_day_first_half"], round(1e4 * -0.01 / n_first, 2))
        self.assertAlmostEqual(s["bp_per_day_second_half"], round(1e4 * 0.03 / n_second, 2))
        self.assertEqual(s["best_coin"], "A")
        self.assertEqual(sorted(s["bp_per_trade_by_quarter"]), ["2025Q1", "2025Q4"])

    def test_only_frozen_book_files_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "PREREG.md"
            p.write_text("x\n```inputs\n" + "a" * 64 + "  data/recorders/lighter_book/2026-10-21/16.parquet\n"
                         + "b" * 64 + "  data/recorders/mexc_ticker/2026-10-20/12.parquet\n```\n")
            self.assertEqual(ll.frozen_files(p, ll.BOOKS), ["data/recorders/lighter_book/2026-10-21/16.parquet"])


if __name__ == "__main__":
    unittest.main()
