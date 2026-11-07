import unittest

import numpy as np
import pandas as pd

from scripts import run_auction as ra

M, D = ra.MIN, ra.DAY


def synthetic():
    """Four days of 1-minute bars (session = UTC day, t0 = 0) with known auction setups."""
    n = 4 * 1440
    C = np.full(n, 101.0)
    V = np.ones(n)
    V[:1440] = 10.0                                   # day 0: value around 101
    C[0:200] = 100.0
    V[0:200] = 1.0
    C[1430:1440] = 99.0                               # day 0 closes below value
    V[1430:1440] = 0.1
    d1 = 1440
    C[d1:d1 + 30] = 99.0                              # day 1 opens below value ...
    C[d1 + 30:d1 + 200] = 101.0                       # ... re-enters at 30 min, accepted at 60 and 90
    C[d1 + 200:2 * 1440] = 103.0                      # breaks the initial balance up at minute 200
    d2 = 2 * 1440
    C[d2:3 * 1440] = 105.0                            # day 2 never trades back to day 1's POC
    H, L = C + 0.01, C - 0.01
    return H, L, C, V


class RunAuctionTest(unittest.TestCase):
    def setUp(self):
        H, L, C, V = synthetic()
        self.C = C
        self.A = np.arange(5, dtype=np.int64) * D
        self.tau, self.side = ra.session_signals(H, L, C, V, self.A, t0=0)

    def test_value_area_reentry_fires_after_two_accepted_half_hours(self):
        self.assertEqual(self.tau["VA80"][1], D + 90 * M)
        self.assertEqual(self.side["VA80"][1], 1)          # opened below value: toward the top
        self.assertEqual(self.tau["VA80"][2], -1)          # day 2 opens above value and never comes back

    def test_breaks_of_the_opening_range_and_initial_balance_follow_the_first_close_beyond(self):
        self.assertEqual((self.tau["OR15"][1], self.side["OR15"][1]), (D + 31 * M, 1))
        self.assertEqual((self.tau["IB60"][1], self.side["IB60"][1]), (D + 201 * M, 1))

    def test_vwap_band_fades_the_first_close_beyond_two_sd(self):
        self.assertEqual((self.tau["VWAP2"][1], self.side["VWAP2"][1]), (D + 201 * M, -1))

    def test_naked_poc_trades_toward_an_untouched_prior_poc(self):
        self.assertEqual(self.tau["NPOC"][1], -1)          # day 1 touched day 0's POC in its first hour
        self.assertEqual((self.tau["NPOC"][2], self.side["NPOC"][2]), (2 * D + 60 * M, -1))

    def test_trades_enter_a_minute_after_the_decision_and_charge_funding(self):
        F, rate = np.array([D + 120 * M], np.int64), np.array([1e-4])
        t = ra.rule_trades(self.C, F, rate, self.tau["VA80"], self.side["VA80"], -1, 60, t0=0)
        self.assertEqual(len(t), 1)
        r = t.iloc[0]
        self.assertEqual((r.entry, r.side, r.E, r.X), (D + 91 * M, -1.0, 101.0, 101.0))
        self.assertAlmostEqual(r.funding, -1e-4)            # a short receives a positive rate

    def test_anchor_test_is_exact_over_all_three_anchor_sets(self):
        anchors = list(ra.REAL) + list(ra.PLACEBO)
        T = {f"c{i}": {a: (100.0 - j if a in ra.REAL else float(j)) for j, a in enumerate(anchors)} for i in range(4)}
        at = ra.anchor_test(T, anchors=anchors)
        self.assertEqual(at["sets"], 165)
        self.assertAlmostEqual(at["p"], 1 / 165)            # the real set ranks highest in every combo
        flat = {f"c{i}": {a: 1.0 for a in anchors} for i in range(4)}
        self.assertEqual(ra.anchor_test(flat, anchors=anchors)["p"], 1.0)


if __name__ == "__main__":
    unittest.main()
