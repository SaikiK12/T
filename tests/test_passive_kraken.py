import unittest

import pandas as pd

from scripts import run_passive_kraken as r

H, M5 = r.H_MS, r.M5_MS
T0 = 1_790_000_000_000 - 1_790_000_000_000 % r.DAY


def candles(prices, vol=1.0, start=T0):
    """5-minute trade candles from (low, high) pairs."""
    return pd.DataFrame({"t": [start + i * M5 for i in range(len(prices))], "open": [p[0] for p in prices],
                         "high": [p[1] for p in prices], "low": [p[0] for p in prices],
                         "close": [p[1] for p in prices], "volume": vol})


def marks(values, start=T0):
    return pd.DataFrame({"t": [start + i * H for i in range(len(values))], "open": values})


class Simulate(unittest.TestCase):
    def test_fill_rules_and_costs(self):
        hs, walk = 10.0, 15.0                                          # bp
        mk = marks([100.0] * 25)
        # buy limit = 99.9; sell limit = 100.1
        through = candles([(99.8, 100.0)] + [(100.0, 100.0)] * 80)     # prints below 99.9: buy fills
        rows = r.simulate(through, mk, hs, walk, [T0], horizons=(6,))
        b = rows[rows.side == "buy"].iloc[0]
        self.assertTrue(b.fill_cons)
        self.assertAlmostEqual(b.passive_bp, -hs + r.MAKER_BP)
        self.assertAlmostEqual(b.saving_bp, walk + r.TAKER_BP - (-hs + r.MAKER_BP))
        s = rows[rows.side == "sell"].iloc[0]
        self.assertFalse(s.fill_cons)                                  # never above 100.1
        self.assertAlmostEqual(s.passive_bp, 0 + walk + r.TAKER_BP)   # mark unchanged: no drift

    def test_touch_is_optimistic_only_and_drift_is_charged(self):
        mk = marks([100.0] * 6 + [101.0] * 20)                         # the price rises 1% by t + 6 h
        touch = candles([(99.9, 100.0)] * 80)                          # touches 99.9, never below
        b = r.simulate(touch, mk, 10.0, 15.0, [T0], horizons=(6,))
        b = b[b.side == "buy"].iloc[0]
        self.assertFalse(b.fill_cons)
        self.assertTrue(b.fill_opt)
        self.assertAlmostEqual(b.passive_bp, 100.0 + 15.0 + r.TAKER_BP)   # +1% drift, then the taker walk

    def test_zero_volume_candles_are_not_trades(self):
        mk = marks([100.0] * 25)
        filler = candles([(99.0, 99.0)] * 80, vol=0.0)
        rows = r.simulate(filler, mk, 10.0, 15.0, [T0], horizons=(6,))
        self.assertFalse(rows[rows.side == "buy"].iloc[0].fill_cons)

    def test_coin_table_from_frozen_diagnostics(self):
        t = r.coin_table()
        self.assertGreater(len(t), 100)
        self.assertGreater(t.thin.sum(), 30)
        self.assertTrue((t.hs_bp > 0).all())


if __name__ == "__main__":
    unittest.main()
