"""lab/freshness.py on an invented checkout: states from file ages, and R200's newest hour from its ticks."""
import os
import tempfile
import unittest
from pathlib import Path

from lab import freshness

NOW = 1_793_030_400.0                     # 2026-10-26T16:00:00Z


class FreshnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, minutes_ago, text="x"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        t = NOW - 60 * minutes_ago
        os.utime(p, (t, t))
        return p

    def rows(self, lanes=()):
        return {r["stream"]: r for r in freshness.rows(self.root, NOW, lane_specs=lanes)}

    def test_states_follow_age_against_cadence(self):
        self.assertEqual(freshness.state(None, 60), "MISSING")
        self.assertEqual(freshness.state(90, 60), "FRESH")
        self.assertEqual(freshness.state(91, 60), "LATE")
        self.assertEqual(freshness.state(270, 60), "LATE")
        self.assertEqual(freshness.state(271, 60), "STALE")

    def test_newest_file_of_a_stream_decides(self):
        self.write("data/recorders/funding_board/2026-10-26/14.parquet", 130)
        self.write("data/recorders/funding_board/2026-10-26/15.parquet", 50)
        self.write("data/tape/status.json", 80)                  # every 10 minutes: far too old
        r = self.rows()
        self.assertEqual((r["funding_board"]["state"], r["funding_board"]["age_min"]), ("FRESH", 50.0))
        self.assertTrue(r["funding_board"]["path"].endswith("15.parquet"))
        self.assertEqual(r["tape"]["state"], "STALE")
        self.assertEqual(r["wallets"]["state"], "MISSING")
        order = [x["state"] for x in freshness.rows(self.root, NOW, lane_specs=())]
        self.assertEqual(order, sorted(order, key=["STALE", "MISSING", "LATE", "FRESH"].index))

    def test_r200_row_reads_the_newest_hour_and_its_compute_lag(self):
        self.write("experiments/flow72_fwd2/journal/status.json", 5)
        hour = int(NOW * 1000) - 2 * 3_600_000                  # the 14:00 bar, closed 15:00
        self.write(freshness.R200_TICKS, 5, "t,utc,run_at\n"
                   f"{hour - 3_600_000},2026-10-26 13:00,2026-10-26T14:20:00Z\n"
                   f"{hour},2026-10-26 14:00,2026-10-26T16:05:00Z\n")
        r = self.rows(lanes=(("R200", "flow books", "experiments/flow72_fwd2/journal/status.json"),))["R200"]
        self.assertEqual(r["state"], "FRESH")
        self.assertEqual(r["data_at"], "2026-10-26T15:00:00Z")
        self.assertEqual(r["data_age_min"], 60.0)
        self.assertEqual(r["lag_at_compute_min"], 65.0)          # computed 16:05 for a 15:00 close: late
        self.assertFalse(r["on_time"])

    def test_every_lane_in_the_catalog_has_a_row(self):
        from lab.operations import LANES
        names = {r["stream"] for r in freshness.rows(self.root, NOW)}
        self.assertTrue({lane.rid for lane in LANES} <= names)


if __name__ == "__main__":
    unittest.main()
