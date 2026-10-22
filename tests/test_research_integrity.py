import json
import tempfile
import unittest
from pathlib import Path

from lab import prereg, registry
from scripts.check_research_integrity import audit


class Fixture:
    def check_metadata(self, metadata, extra=None):
        """Audit a frozen fixture and check that every byte stays intact. `extra` maps file names to contents
        written beside the spec."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lane = root / "experiments" / "fixture"
            lane.mkdir(parents=True)
            spec = lane / "PREREG.md"
            spec.write_text("# Frozen test specification\n\n" + metadata + "\n", encoding="utf-8")
            digest = prereg.freeze(spec)
            for name, content in (extra or {}).items():
                (lane / name).write_text(content, encoding="utf-8")
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

    def codes(self, metadata, extra=None):
        return [issue["code"] for issue in self.check_metadata(metadata, extra)["issues"]]


class PreregMetadataTests(Fixture, unittest.TestCase):
    def test_plural_typed_method_ids_cannot_hide_another_round(self):
        self.assertEqual(self.codes("Registry id: R233 (claim). **Methods:** M301, M303."), [])
        for tail in ("**Methods:** M301, R234.", "**Methods:** M301, M303. R234",
                     "**Methods:** M301, M303. **Methods:** M304", "**Method:** M301, M303."):
            with self.subTest(tail=tail):
                self.assertEqual(self.codes("Registry id: R233. " + tail), ["REGISTRY_ID_INVALID"])
        self.assertEqual(self.codes("Registry id: R234. **Methods:** M301, M303."),
                         ["REGISTRY_ID_MISMATCH"])

    def test_exact_block_opening_annotation_preserves_primary_id_validation(self):
        note = ". It opens the Claude block R220-R239, claimed on issue #7 before this freeze."
        self.assertEqual(self.codes("Registry id: R233" + note), [])
        self.assertEqual(self.codes("Registry id: R234" + note), ["REGISTRY_ID_MISMATCH"])
        self.assertEqual(self.codes("Registry id: R233" + note + " R234"), ["REGISTRY_ID_INVALID"])

    def test_exact_reserved_round_note_is_context_not_a_second_declaration(self):
        note = " (Claude block R220-R239, claimed on issue #7 before the freeze). R232 stays reserved for"
        self.assertEqual(self.codes("Registry id: R233" + note + "\n  `other_lane`, frozen separately."), [])
        self.assertEqual(self.codes("Registry id: R234" + note), ["REGISTRY_ID_MISMATCH"])
        for tail in (note + " R231", note + "\nRegistry id: R232", ". R232"):
            with self.subTest(tail=tail):
                self.assertEqual(self.codes("Registry id: R233" + tail), ["REGISTRY_ID_INVALID"])

    def test_typed_comma_claim_annotation_is_not_an_arbitrary_trailing_id(self):
        claim = ", in the Claude block R220-R239 claimed on issue #7 on 2026-10-22"
        for text in ("R233" + claim, "R233" + claim + ".", "`R233`" + claim + "."):
            with self.subTest(text=text):
                self.assertEqual(self.codes("- **Registry id:** " + text), [])
        for text in ("R233, R234", "R233" + claim + ". R234", "R233" + claim + ", R234",
                     "R233" + claim + "\nRegistry id: R233", "R233, in a free text note R234"):
            with self.subTest(text=text):
                self.assertEqual(self.codes("Registry id: " + text), ["REGISTRY_ID_INVALID"])
        self.assertEqual(self.codes("Registry id: R234" + claim + "."), ["REGISTRY_ID_MISMATCH"])

    def test_typed_inline_method_field_preserves_round_validation(self):
        for text in ("R233. **Method:** M281.", "`R233`. **Method:** M281"):
            with self.subTest(text=text):
                self.assertEqual(self.codes("- **Registry id:** " + text), [])
        for text in ("R233. **Method:** R234.", "R233. **Method:** M281. R234",
                     "R233. **Method:** M281; R234",
                     "R233. **Method:** M281. **Method:** M282"):
            with self.subTest(text=text):
                self.assertEqual(self.codes("Registry id: " + text), ["REGISTRY_ID_INVALID"])
        self.assertEqual(self.codes("Registry id: R234. **Method:** M281."),
                         ["REGISTRY_ID_MISMATCH"])

    def test_sentence_period_preserves_full_value_and_id_checks(self):
        for text in ("R233.", "`R233`.", "R233 (Claude block R220-R239, claimed on issue #7)."):
            with self.subTest(text=text):
                self.assertEqual(self.codes("- **Registry id:** " + text), [])
        for text in ("R233..", "R233. R234", "R233 (note). R234", "R233 (note). (second)"):
            with self.subTest(text=text):
                self.assertEqual(self.codes("Registry id: " + text), ["REGISTRY_ID_INVALID"])
        self.assertEqual(self.codes("Registry id: R234 (claim)."), ["REGISTRY_ID_MISMATCH"])

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


class ReassignmentTests(Fixture, unittest.TestCase):
    """The fixture's registry row is R233; these specs declare another id."""

    def moved(self, **fields):
        data = {"declared": "R230", "registered": "R233", "reason": "R230 was claimed first on issue #7"}
        data.update(fields)
        return {"REGISTRY_REASSIGNMENT.json": json.dumps({k: v for k, v in data.items() if v is not None})}

    def test_documented_reassignment_is_info_not_error(self):
        report = self.check_metadata("Registry id: R230", self.moved())
        self.assertEqual([issue["code"] for issue in report["issues"]], ["REGISTRY_ID_REASSIGNED"])
        self.assertEqual(report["summary"]["errors"], 0)

    def test_reassignment_must_match_both_ids(self):
        for fields in ({"declared": "R231"}, {"registered": "R234"}):
            with self.subTest(fields=fields):
                self.assertEqual(self.codes("Registry id: R230", self.moved(**fields)), ["REGISTRY_ID_MISMATCH"])

    def test_malformed_reassignment_fails(self):
        for extra in (self.moved(reason=" "), self.moved(reason=None), self.moved(declared="r230"),
                      self.moved(declared="R233"), self.moved(extra="x"),
                      {"REGISTRY_REASSIGNMENT.json": "not json"}):
            with self.subTest(extra=extra):
                self.assertEqual(self.codes("Registry id: R230", extra),
                                 ["REASSIGNMENT_INVALID", "REGISTRY_ID_MISMATCH"])

    def test_unneeded_reassignment_is_a_warning(self):
        self.assertEqual(self.codes("Registry id: R233", self.moved()), ["REASSIGNMENT_UNUSED"])


if __name__ == "__main__":
    unittest.main()
