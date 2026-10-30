import unittest
from dataclasses import replace

from scripts import m322_calendar_rule as rule
from scripts.m322_signal_rule import DAY, ENTRY_DELAY


class CalendarRuleTests(unittest.TestCase):
    def row(self, index, status="trigger"):
        day = (1000 + index) * DAY
        if status == "missing":
            return rule.Day(day, status, None, None, None, None, None, None, None, None, "a" * 64)
        return rule.Day(day, status, 100, 100, 100, 100, 100, 100, day + 120_000, 100, "a" * 64)

    def test_one_look_requires_30_triggers_and_keeps_no_trade_days(self):
        self.assertFalse(rule.ready([self.row(i) for i in range(29)]))
        days = [self.row(i) for i in range(30)] + [self.row(30, "no_trigger")]
        self.assertTrue(rule.ready(days))

    def test_missing_day_blocks_without_zero_fill_and_holes_fail(self):
        days = [self.row(i) for i in range(30)] + [self.row(30, "missing")]
        self.assertFalse(rule.ready(days))
        with self.assertRaisesRegex(ValueError, "calendar day"):
            rule.ready([self.row(0), self.row(2)])
        with self.assertRaisesRegex(ValueError, "fabricated"):
            rule.ready([replace(self.row(0, "missing"), strategy_end=0)])

    def test_late_ticket_and_discontinuous_or_insolvent_accounts_fail(self):
        row = self.row(0)
        with self.assertRaisesRegex(ValueError, "late"):
            rule.ready([replace(row, ticket_published_ms=row.day_ms + ENTRY_DELAY)])
        with self.assertRaisesRegex(ValueError, "insolvent"):
            rule.ready([replace(row, strategy_end=0)])
        with self.assertRaisesRegex(ValueError, "discontinuous"):
            rule.ready([row, replace(self.row(1), baseline_start=101)])


if __name__ == "__main__":
    unittest.main()
