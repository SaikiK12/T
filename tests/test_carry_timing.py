import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts import carry_timing as ct


class CarryTimingTest(unittest.TestCase):
    def test_allowed_late_is_twenty_percent_floor(self):
        self.assertEqual(ct.allowed_late(90), 18)
        self.assertEqual(ct.allowed_late(180), 36)
        self.assertEqual(ct.allowed_late(10), 2)

    def test_counts_skip_replay_and_duplicate_days(self):
        rows = [
            {"run": "r0", "day": "2026-11-01", "book": "A", "kind": "replay"},
            {"run": "r1", "day": "2026-11-02", "book": "A", "kind": "late"},
            {"run": "r1", "day": "2026-11-02", "book": "A", "kind": "late"},
            {"run": "r2", "day": "2026-11-04", "book": "A", "kind": "ontime"},
        ]
        c = ct.book_counts(rows)["A"]
        self.assertEqual((c["live"], c["late"], c["last_run"]), (2, 1, "r2"))
        self.assertEqual(ct.missing_days(c["days"]), 1)

    def test_table_reads_only_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            j = root / "experiments" / "xfund_bg_fwd" / "journal"
            j.mkdir(parents=True)
            with (j / "decisions.csv").open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["run", "day", "book", "kind", "exits", "entries", "held", "ready"])
                w.writerow(["t1", "2026-11-04", "A", "late", "", "", "", ""])
                w.writerow(["t2", "2026-11-05", "A", "ontime", "", "", "", ""])
            # A days.csv with results must not be needed or read.
            (j / "days.csv").write_text("not,a,valid,file\n")
            out = ct.table(root=root, today=date(2026, 11, 17))
        self.assertIn("| xfund_bg_fwd | R390 | A | 2 | 1 | 50% | 17 (look 1, 2027-02-02) | 35 (look 2, 2027-05-03) |", out)
        self.assertIn("| xfund_fwd | R278 | - | no journal |", out)


if __name__ == "__main__":
    unittest.main()
