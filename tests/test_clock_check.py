import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import clock_check  # noqa: E402


def fake_clock(*stamps):
    it = iter(stamps)
    return lambda: next(it)


class VenueOffsetTests(unittest.TestCase):
    def test_lowest_round_trip_sample_wins(self):
        # sample 1: round trip 800 ms, midpoint 5,400, server 7,300 (offset 1,900); sample 2: round trip 200 ms,
        # midpoint 6,100, server 7,600 (offset 1,500). The shorter round trip is the better estimate.
        replies = iter([7_300, 7_600])
        clock = fake_clock(5_000, 5_800, 6_000, 6_200)
        off, rtt = clock_check.venue_offset("u", lambda j: j, samples=2, get=lambda url: next(replies), clock_ms=clock)
        self.assertEqual((off, rtt), (1_500, 200))

    def test_failed_samples_are_skipped_and_all_failed_raises(self):
        def bad(url):
            raise ValueError("down")
        with self.assertRaises(RuntimeError):
            clock_check.venue_offset("u", lambda j: j, samples=3, get=bad, clock_ms=fake_clock(*range(10)))


class ConsensusTests(unittest.TestCase):
    def test_median_and_agreement(self):
        med, ok = clock_check.consensus({"a": (1_700, 300), "b": (1_780, 400), "c": (1_680, 320)})
        self.assertEqual((med, ok), (1_700, True))

    def test_disagreeing_or_single_venue_is_not_ok(self):
        self.assertFalse(clock_check.consensus({"a": (1_700, 300), "b": (-200, 400)})[1])
        self.assertFalse(clock_check.consensus({"a": (1_700, 300)})[1])
        self.assertFalse(clock_check.consensus({})[1])


class MainTests(unittest.TestCase):
    def run_main(self, res, args, pending=0):
        applied = []
        with tempfile.TemporaryDirectory() as d:
            old = clock_check.LOG
            clock_check.LOG = Path(d) / "clock.csv"
            try:
                clock_check.main(args, measure_fn=lambda: res, adjust=applied.append, pending_fn=lambda: pending)
                rows = clock_check.LOG.read_text().splitlines()
            finally:
                clock_check.LOG = old
        return applied, rows

    def test_slew_applies_the_median_when_venues_agree(self):
        applied, rows = self.run_main({"mexc": (1_760, 300), "deribit": (1_780, 400), "okx": (1_680, 320)}, ["slew"])
        self.assertEqual(applied, [1_760])
        self.assertEqual(len(rows), 2)
        self.assertTrue(rows[1].split(",")[3] == "1760")

    def test_slew_refuses_small_large_and_disagreeing_offsets(self):
        agree = lambda o: {"mexc": (o, 300), "deribit": (o + 10, 400), "okx": (o - 10, 320)}
        self.assertEqual(self.run_main(agree(100), ["slew"])[0], [])
        self.assertEqual(self.run_main(agree(20_000), ["slew"])[0], [])
        self.assertEqual(self.run_main({"mexc": (1_700, 300), "okx": (-300, 320)}, ["slew"])[0], [])

    def test_noisy_round_trips_are_not_used(self):
        # the 2026-10-29 10:30 reading under CPU load: round trips of 640 to 1,050 ms
        noisy = {"mexc": (1_649, 641), "deribit": (1_829, 928), "okx": (1_853, 1_054)}
        self.assertFalse(clock_check.consensus(noisy)[1])
        self.assertEqual(self.run_main(noisy, ["slew"])[0], [])
        mixed = {"mexc": (1_650, 300), "deribit": (1_700, 350), "okx": (1_900, 1_000)}
        self.assertEqual(clock_check.consensus(mixed), (1_675, True))      # the slow one is dropped, two remain

    def test_offset_far_from_the_pending_slew_is_a_bad_measurement(self):
        res = {"mexc": (1_800, 300), "deribit": (1_820, 350), "okx": (1_790, 320)}
        self.assertEqual(self.run_main(res, ["slew"], pending=1_450)[0], [1_800])    # 350 ms away: within 400
        self.assertEqual(self.run_main(res, ["slew"], pending=0)[0], [1_800])        # nothing pending: no guard
        applied, rows = self.run_main(res, ["slew"], pending=1_000)                  # 800 ms away: refused
        self.assertEqual(applied, [])
        self.assertEqual(rows[1].split(",")[4], "1000")                              # the pending slew is logged

    def test_status_never_adjusts(self):
        applied, rows = self.run_main({"mexc": (1_760, 300), "deribit": (1_780, 400)}, ["status"])
        self.assertEqual(applied, [])
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
