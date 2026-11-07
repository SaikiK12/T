import unittest
from dataclasses import replace

from scripts import m090_event_rule as rule


class EventRuleTests(unittest.TestCase):
    def setUp(self):
        self.T = 100 * rule.DAY
        self.decision = self.T - rule.HOUR
        self.previous = self.T - 8 * rule.HOUR
        self.clock = rule.ClockBound(self.T - rule.DAY, self.T + rule.DAY, 100, "a" * 64)
        self.display = rule.Observation("BTC_USDT", self.T, .001, self.T - 2 * rule.HOUR,
                                        self.T - 2 * rule.HOUR + 1000, self.T - 2 * rule.HOUR + 2000,
                                        "b" * 64, self.clock)
        self.history = rule.Observation("BTC_USDT", self.previous, .0005, self.previous + 1000,
                                        self.previous + 2000, self.previous + 3000, "c" * 64, self.clock)

    def test_ticket_requires_both_inputs_and_exact_prior_event(self):
        t = rule.ticket(self.T, self.previous, [self.display], [self.history])
        self.assertEqual((t.displayed_rate, t.previous_rate), (.001, .0005))
        self.assertIsNone(rule.ticket(self.T, self.previous, [], [self.history]))
        self.assertIsNone(rule.ticket(self.T, self.previous, [self.display],
                                      [replace(self.history, settlement_ms=self.previous - rule.HOUR)]))
        before_settlement = replace(self.history, request_start_ms=self.previous - 1)
        self.assertIsNone(rule.ticket(self.T, self.previous, [self.display], [before_settlement]))

    def test_late_publication_old_capture_and_uncertain_clock_are_not_eligible(self):
        late = replace(self.display, published_ms=self.decision)
        self.assertIsNone(rule.ticket(self.T, self.previous, [late], [self.history]))
        old = replace(self.display, request_start_ms=self.T - 4 * rule.HOUR,
                      received_ms=self.T - 3 * rule.HOUR, published_ms=self.T - 3 * rule.HOUR + 1)
        self.assertIsNone(rule.ticket(self.T, self.previous, [old], [self.history]))
        invalid = replace(self.display, clock=replace(self.clock, max_error_ms=1001))
        with self.assertRaisesRegex(ValueError, "clock"):
            rule.ticket(self.T, self.previous, [invalid], [self.history])

    def test_conflicting_duplicates_are_rejected(self):
        conflicting = replace(self.display, rate=.002)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            rule.ticket(self.T, self.previous, [self.display, conflicting], [self.history])

    def test_label_must_be_for_exact_settlement_and_seen_after_it(self):
        t = rule.ticket(self.T, self.previous, [self.display], [self.history])
        sealed = rule.seal(t, rule.ticket_bytes(t), self.decision - 1000, self.clock)
        with self.assertRaisesRegex(ValueError, "sealed"):
            rule.outcome(t, [self.display])
        self.assertIsNone(rule.outcome(sealed, [self.display]))
        label = replace(self.display, request_start_ms=self.T + 200, received_ms=self.T + 300,
                        published_ms=self.T + 400, rate=.0008)
        self.assertEqual(rule.outcome(sealed, [label]), .0008)
        with self.assertRaisesRegex(ValueError, "conflicting"):
            rule.outcome(sealed, [label, replace(label, rate=.0009)])

    def test_ticket_must_be_durable_after_inputs_and_before_the_decision(self):
        t = rule.ticket(self.T, self.previous, [self.display], [self.history])
        raw = rule.ticket_bytes(t)
        self.assertEqual(rule.seal(t, raw, self.decision - 1000, self.clock).ticket, t)
        with self.assertRaisesRegex(ValueError, "durably available"):
            rule.seal(t, raw, self.decision, self.clock)
        with self.assertRaisesRegex(ValueError, "durably available"):
            rule.seal(t, raw, t.inputs_ready_ms, self.clock)
        with self.assertRaisesRegex(ValueError, "bytes"):
            rule.seal(t, raw + b"x", self.decision - 1000, self.clock)

    def test_final_look_requires_90_unique_events_and_30_dates(self):
        events = [i * 8 * rule.HOUR for i in range(90)]
        self.assertTrue(rule.final_look_ready(events))
        self.assertFalse(rule.final_look_ready(events[:-1]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            rule.final_look_ready(events + [events[0]])


if __name__ == "__main__":
    unittest.main()
