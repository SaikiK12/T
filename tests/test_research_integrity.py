import tempfile
import unittest
from pathlib import Path

from lab import prereg, registry
from scripts.check_research_integrity import audit


class PreregMetadataTests(unittest.TestCase):
    def check_metadata(self, metadata):
        """Audit a frozen fixture and check that every byte stays intact."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lane = root / "experiments" / "fixture"
            lane.mkdir(parents=True)
            spec = lane / "PREREG.md"
            spec.write_text("# Frozen test specification\n\n" + metadata + "\n", encoding="utf-8")
            digest = prereg.freeze(spec)
            register = root / "registry" / "rounds.csv"
            register.parent.mkdir()
            registry.append(register, id="R233", lane="fixture", title="fixture",
                            status="REGISTERED", verdict="PENDING", trials=0,
                            prereg_sha=digest, path="experiments/fixture")
            before = {path.relative_to(root): path.read_bytes()
                      for path in root.rglob("*") if path.is_file()}
            report = audit(root)
            after = {path.relative_to(root): path.read_bytes()
                     for path in root.rglob("*") if path.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(prereg.verify(spec), digest)
            self.assertEqual(report["summary"]["verified_frozen"], 1)
            return report

    def codes(self, metadata):
        return [issue["code"] for issue in self.check_metadata(metadata)["issues"]]

    def test_supported_id_formats_and_annotations(self):
        for metadata in (
            "Registry id: R233",
            "- **Registry id:** R233 (claimed on issue #7)",
            "* **Registry id:** `R233` (claimed on issue #7)",
            "+ Registry id: `R233`",
            "\tregistry ID:\tR233\t(note)\t",
            "Registry id: R233 (related evidence in R217)",
        ):
            with self.subTest(metadata=metadata):
                self.assertEqual(self.codes(metadata), [])

    def test_malformed_values_still_fail(self):
        for value in (
            "", "R", "r233", "R233x", "R233 or R234", "R233 (note) R234",
            "R233 claimed on issue #7", "R233(note)", "R233 (unclosed",
            "R233 extra)", "R233 (note) (second)", "R233 ((nested))",
            "R233 (first\nsecond)", "`R233", "R233`", "``R233``",
        ):
            with self.subTest(value=value):
                self.assertEqual(self.codes("Registry id: " + value), ["REGISTRY_ID_INVALID"])

    def test_duplicate_and_conflicting_declarations_still_fail(self):
        for second in ("R233", "R233 (again)", "R234 (different)"):
            with self.subTest(second=second):
                metadata = "Registry id: R233 (claimed on issue #7)\nRegistry id: " + second
                self.assertEqual(self.codes(metadata), ["REGISTRY_ID_INVALID"])

    def test_mismatching_id_is_not_an_invalid_format(self):
        report = self.check_metadata("Registry id: `R234` (claimed on issue #7)")
        self.assertEqual([issue["code"] for issue in report["issues"]], ["REGISTRY_ID_MISMATCH"])
        self.assertEqual(report["issues"][0]["round_id"], "R233")

    def test_missing_metadata_remains_a_warning(self):
        report = self.check_metadata("No explicit metadata in this legacy specification.")
        self.assertEqual(report["summary"]["errors"], 0)
        self.assertEqual(self.codes("No explicit metadata."), ["REGISTRY_ID_MISSING"])

    def test_empty_declaration_cannot_consume_next_line(self):
        self.assertEqual(self.codes("Registry id:\nR233"), ["REGISTRY_ID_INVALID"])
        self.assertEqual(self.codes("Registry id:\nRegistry id: R233"), ["REGISTRY_ID_INVALID"])


if __name__ == "__main__":
    unittest.main()
