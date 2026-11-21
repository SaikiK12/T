import unittest

import pandas as pd

from scripts import run_dmake as m


def frame(rows):
    return pd.DataFrame(rows, columns=["timestamp", "price", "direction", "index_price"])


class Dmake(unittest.TestCase):
    def test_fill_through_the_bid_and_edge(self):
        t0 = m.WARM + 1_000
        rows = [(1_000, 100.0, "buy", 100.0), (t0, 100.0, "buy", 100.0),
                (t0 + 5_000, 99.70, "sell", 100.0)]                 # a taker sells 30 bp under the index
        f = m.simulate(frame(rows), 0.0015)
        real = f[f.side != 0]
        self.assertEqual(len(real), 1)
        bid = 100.0 * (1 - 0.0015)
        expect = ((100.0 * (1 - m.H) - bid) / bid - m.MAKER) * 1e4
        self.assertAlmostEqual(real.edge_bp.iloc[0], expect, places=9)
        self.assertEqual(f[f.side == 0].edge_bp.iloc[0], -(m.TAKER + m.H) * 1e4)   # one unit left: closed at the end

    def test_no_fill_at_the_quote_and_latency(self):
        t0 = m.WARM + 1_000
        rows = [(1_000, 100.0, "buy", 100.0), (t0, 99.86, "sell", 100.0)]      # above the bid: no fill
        self.assertEqual(len(m.simulate(frame(rows), 0.0015)), 0)
        rows = [(t0, 100.0, "buy", 100.0), (t0 + 500, 99.0, "sell", 99.0)]       # no reference older than LAT
        self.assertEqual(len(m.simulate(frame(rows), 0.0015)), 0)

    def test_cooldown_and_cap(self):
        t0 = m.WARM + 1_000
        rows = [(1_000, 100.0, "buy", 100.0)] + [(t0 + i * 10_000, 99.0, "sell", 100.0) for i in range(20)]
        f = m.simulate(frame(rows), 0.0015)
        self.assertEqual(int((f.side == 1).sum()), 4)                 # 190 s of sells, one fill a minute

    def test_decide(self):
        p = {"days": 40, "nw_t_daily_usd": 3.5, "l2co_usd_per_day": 1.0, "halves_usd_per_day": [1.0, 2.0]}
        self.assertEqual(m.decide(p, {"usd_per_day": 0.5})[0], "PASS")
        self.assertEqual(m.decide(p, {"usd_per_day": -0.5})[0], "FAIL")
        self.assertEqual(m.decide({"days": 5}, {})[0], "UNREADABLE")


if __name__ == "__main__":
    unittest.main()
