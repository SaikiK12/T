"""Registry/navigation fixtures only: no market data, outcome reads or journal changes."""
import csv
from pathlib import Path
import tempfile
import unittest

from scripts import catalog


class ExperimentCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "registry").mkdir()
        (self.root / "experiments").mkdir()

    def registry(self, rows):
        with (self.root / "registry/rounds.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "path", "status", "verdict", "trials", "title"])
            w.writeheader()
            for rid, lane, status in rows:
                w.writerow(dict(id=rid, path="experiments/" + lane, status=status, verdict="PENDING",
                                trials="1", title="Fixture " + rid))

    def folder(self, lane):
        p = self.root / "experiments" / lane
        p.mkdir()
        return p

    def test_absent_import_remains_visible_without_a_dangling_link(self):
        self.registry([("R143", "imported", "DONE"), ("R308", "local", "DONE")])
        p = self.folder("local")
        (p / "PREREG.md").write_text("fixture only")
        text, counts = catalog.experiment_catalog(self.root)
        self.assertEqual(counts, (1, 0))
        self.assertIn("Registered rounds with no local folder (1)", text)
        self.assertIn("**R143** `experiments/imported`: DONE PENDING", text)
        self.assertNotIn("](imported", text)
        self.assertIn("[PREREG](local/PREREG.md)", text)
        self.assertFalse((self.root / "experiments/README.md").exists())

    def test_unregistered_study_is_not_presented_as_collected_data(self):
        self.registry([])
        self.folder("recorders")
        self.folder("unregistered_study")
        text, counts = catalog.experiment_catalog(self.root)
        self.assertEqual(counts, (0, 2))
        collection = text.split("## Collection and loop folders (1)", 1)[1].split("## Unregistered folders", 1)[0]
        self.assertIn("[recorders]", collection)
        self.assertNotIn("unregistered_study", collection)
        self.assertIn("[unregistered_study](unregistered_study/)", text.split("## Unregistered folders (1)", 1)[1])

    def test_running_batch_and_planned_round_do_not_acquire_paper_or_done_labels(self):
        self.registry([("R286", "reserved", "RUNNING"), ("R184", "draft", "PLANNED")])
        self.folder("reserved")
        self.folder("draft")
        text, _ = catalog.experiment_catalog(self.root)
        active, rest = text.split("## Other registered rounds", 1)
        self.assertIn("**[reserved]", active)
        self.assertNotIn("**[draft]", active)
        self.assertIn("**[draft]", rest)
        self.assertNotIn("Forward paper lanes (running)", text)
        self.assertNotIn("Finished and registered rounds", text)

    def test_multiple_registry_rows_are_preserved_and_results_are_never_read(self):
        self.registry([("R200", "shared", "REGISTERED"), ("R199", "shared", "DONE")])
        p = self.folder("shared")
        # Evidence links need existence only. Deliberately invalid text must never be parsed.
        (p / "FINDINGS.md").write_bytes(b"\xff\x00")
        (p / "journal").mkdir()
        (p / "journal/days.csv").write_bytes(b"\xff\x00")
        before = {q: q.read_bytes() for q in p.rglob("*") if q.is_file()}
        first = catalog.experiment_catalog(self.root)
        self.assertEqual(first, catalog.experiment_catalog(self.root))
        text, counts = first
        self.assertEqual(counts, (1, 0))
        self.assertEqual(text.count("Fixture R200"), 1)
        self.assertEqual(text.count("Fixture R199"), 1)
        self.assertLess(text.index("Fixture R200"), text.index("Fixture R199"))
        self.assertIn("[journal](shared/journal/)", text)
        self.assertEqual(before, {q: q.read_bytes() for q in p.rglob("*") if q.is_file()})


if __name__ == "__main__":
    unittest.main()
