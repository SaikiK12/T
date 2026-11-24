"""Two-account simulation: the accounts' total must equal the engine's book PnL at leverage L, and the rule must move
collateral toward the account that is losing."""
import math
import unittest

import numpy as np

from lab import xfund_v2 as v2
from scripts import rebalance_sim as rs
from tests.test_risk_limits import universe


def book(u):
    rows, trades = v2.replay(u, v2.Book([0, 1], 14, 0.05, 20), v2.window_start(u, [0, 1], 14))
    return rows, trades


class TwoAccounts(unittest.TestCase):
    def test_daily_change_is_the_engine_pnl(self):
        u, _ = universe(n_coins=2)
        rows, trades = book(u)
        self.assertGreater(len(trades), 0)
        L, k = 2.0, 20
        d0, d1 = int(rows.day.iloc[0]), int(rows.day.iloc[-1])
        df, _ = rs.simulate(u, trades, "bitfinex", "gate", L, d0, d1)
        total = (df["eq_bitfinex"] + df["eq_gate"]).to_numpy()
        eng = rows.set_index("day")
        for i in range(1, len(df) - 1):          # the engine's last row also charges the closing of open legs
            d = int(df.day.iloc[i])
            want = L * (eng.gross[d - 1] - rs.COST * eng.legs[d]) / (2 * k)
            self.assertAlmostEqual(total[i] - total[i - 1], want, places=10)

    def test_a_rally_moves_collateral_to_the_short_venue(self):
        u, _ = universe(n_coins=2)
        rows, trades = book(u)
        first = min(t["entry_day"] for t in trades)
        for c in range(2):                       # a 30% rally in both coins on both venues, two days after entry
            for vi in range(2):
                s = u.series[c][vi]
                s.val[first + 2:] = s.val[first + 2:] * 1.3
        df, ev = rs.simulate(u, trades, "bitfinex", "gate", 16.0, int(rows.day.iloc[0]), int(rows.day.iloc[-1]))
        self.assertTrue(ev)
        self.assertEqual(ev[0]["day"], first + 2)
        short = trades[0]["short"]
        self.assertEqual(ev[0]["from"], "bitfinex" if short == "gate" else "gate")
        row = df[df.day == first + 2].iloc[0]
        self.assertGreater(row["dist_after"], min(row["dist_bitfinex"], row["dist_gate"]))

    def test_summary(self):
        u, _ = universe(n_coins=2)
        rows, trades = book(u)
        df, ev = rs.simulate(u, trades, "bitfinex", "gate", 2.0, int(rows.day.iloc[0]), int(rows.day.iloc[-1]))
        s = rs.summarize(df, ev, "bitfinex", "gate", u.t0)
        self.assertEqual(s["days"], len(df))
        self.assertTrue(s["median_distance_pct"] > 0)


if __name__ == "__main__":
    unittest.main()
