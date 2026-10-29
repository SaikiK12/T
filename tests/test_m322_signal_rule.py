import unittest
from dataclasses import replace

import pandas as pd

from scripts import m322_signal_rule as rule


class SignalRuleTests(unittest.TestCase):
    def setUp(self):
        self.day = 1_000 * rule.DAY
        self.sha = "a" * 64
        self.prior = [rule.PriorBreadth(self.day - i * rule.DAY, .20,
                                         self.day - i * rule.DAY + rule.MINUTE, 100, self.sha)
                      for i in range(1, 181)]
        closes = tuple(rule.Close(self.day - i * rule.DAY, 100.0 if i else 50.0)
                       for i in reversed(range(25)))
        self.coins = [rule.Contract(f"C{i:02d}USDT", i + 1, closes, self.day + rule.MINUTE, 100,
                                    self.sha, None if i < 5 else f"C{i:02d}_USDT")
                      for i in range(35)]

    def test_ticket_uses_original_breadth_and_keeps_unmapped_cash(self):
        t = rule.ticket(self.day, self.coins, self.prior)
        self.assertEqual((t.breadth, t.threshold), (1.0, .20))
        self.assertEqual(len(t.legs), 35)
        self.assertAlmostEqual(sum(x.initial_capital_fraction for x in t.legs), .20)
        self.assertAlmostEqual(sum(x.initial_capital_fraction for x in t.legs if x.mexc_contract is None), .20 * 5 / 35)
        self.assertEqual((t.decision_ms, t.entry_ms, t.exit_ms),
                         (self.day + 2 * rule.MINUTE, self.day + 3 * rule.MINUTE,
                          self.day + 3 * rule.MINUTE + 5 * rule.DAY))

    def test_insufficient_warmup_or_basket_produces_no_ticket(self):
        self.assertIsNone(rule.ticket(self.day, self.coins, self.prior[:-1]))
        self.assertIsNone(rule.ticket(self.day, self.coins[:29], self.prior))

    def test_late_data_duplicate_rows_and_occupied_slot_fail_closed(self):
        late = replace(self.coins[0], available_ms=self.day + 2 * rule.MINUTE)
        with self.assertRaisesRegex(ValueError, "available"):
            rule.ticket(self.day, [late, *self.coins[1:]], self.prior)
        early = replace(self.coins[0], available_ms=self.day - 1)
        with self.assertRaisesRegex(ValueError, "before its bar"):
            rule.ticket(self.day, [early, *self.coins[1:]], self.prior)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rule.ticket(self.day, self.coins + [self.coins[0]], self.prior)
        with self.assertRaisesRegex(ValueError, "occupied"):
            rule.ticket(self.day, self.coins, self.prior, occupied_slots=[(self.day // rule.DAY) % 5])

    def test_missing_close_history_is_excluded_and_gaps_are_rejected(self):
        short = replace(self.coins[0], closes=self.coins[0].closes[-1:])
        t = rule.ticket(self.day, [short, *self.coins[1:]], self.prior)
        self.assertEqual(len(t.legs), 35)  # still a basket member, not in breadth
        bad = replace(self.coins[0], closes=self.coins[0].closes[:-2] + self.coins[0].closes[-1:])
        with self.assertRaisesRegex(ValueError, "gap"):
            rule.ticket(self.day, [bad, *self.coins[1:]], self.prior)

    def test_linear_percentile_matches_source_implementation(self):
        values = [.1, .8, .2, .4, .3, .1, 1.0]
        self.assertAlmostEqual(rule.quantile95(values), pd.Series(values).quantile(.95))


if __name__ == "__main__":
    unittest.main()
