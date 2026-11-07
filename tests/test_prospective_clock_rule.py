import unittest
from dataclasses import replace

from scripts import prospective_clock_rule as clock


class ClockBoundTests(unittest.TestCase):
    def setUp(self):
        self.a = clock.ClockSample("a", 10_000, 10_200, 200, 10_300, 0, "a" * 64)
        self.b = clock.ClockSample("b", 10_100, 10_300, 200, 10_400, 0, "b" * 64)

    def test_two_sources_bound_offset_under_declared_assumptions(self):
        self.assertEqual(clock.offset_interval([self.a, self.b], 10_300, 200), (99, 301))

    def test_backwards_or_inconsistent_wall_time_is_rejected(self):
        bad = replace(self.a, start_local_ms=10_200, end_local_ms=10_100)
        with self.assertRaisesRegex(ValueError, "duration"):
            clock.offset_interval([bad, self.b], 10_300, 200)
        bad = replace(self.a, monotonic_elapsed_ms=50)
        with self.assertRaisesRegex(ValueError, "duration"):
            clock.offset_interval([bad, self.b], 10_300, 200)

    def test_missing_duplicate_stale_and_disagreeing_sources_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "two"):
            clock.offset_interval([self.a], 10_300, 200)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            clock.offset_interval([self.a, replace(self.b, source="a")], 10_300, 200)
        with self.assertRaisesRegex(ValueError, "stale"):
            clock.offset_interval([self.a, self.b], 80_000, 200)
        with self.assertRaisesRegex(ValueError, "disagree"):
            clock.offset_interval([self.a, replace(self.b, server_ms=20_000)], 10_300, 200)


if __name__ == "__main__":
    unittest.main()
