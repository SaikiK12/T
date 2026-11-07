"""Edge map: structural checks on the registry files and the generator."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import edge_map  # noqa: E402

FAM_FIELDS = ["id", "group", "family", "payer", "equation", "binding_constraint", "fake_edge_checks", "reading",
              "gaps", "next"]


def write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fam(fid):
    return {k: f"{k} of {fid}" for k in FAM_FIELDS} | {"id": fid}


class RepoTests(unittest.TestCase):
    def test_registry_files_are_consistent(self):
        self.assertEqual(edge_map.problems(*edge_map.load(ROOT)), [])

    def test_every_family_has_its_fields(self):
        families = edge_map.load(ROOT)[0]
        self.assertEqual(len({f["id"] for f in families}), len(families))
        for f in families:
            self.assertEqual(list(f), FAM_FIELDS)
            self.assertTrue(all(f[k] for k in ("id", "family", "payer", "equation")), f["id"])


class GeneratorTests(unittest.TestCase):
    def test_rounds_come_from_method_rid_and_unplaced_items_are_listed(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            write(root / "registry/edge_families.csv", FAM_FIELDS, [fam("P1"), fam("X0")])
            write(root / "registry/edge_map_links.csv", ["item", "family"],
                  [{"item": "M001", "family": "P1"}, {"item": "R003", "family": "X0"}])
            write(root / "registry/methods.csv", ["id", "method", "status", "rid"],
                  [{"id": "M001", "method": "a", "status": "TESTED", "rid": "R001 NULL; R002"},
                   {"id": "M002", "method": "b", "status": "UNTESTED", "rid": "-"}])
            write(root / "registry/rounds.csv", ["id", "status", "verdict"],
                  [{"id": "R001", "status": "DONE", "verdict": "NULL"},
                   {"id": "R002", "status": "RUNNING", "verdict": "PENDING"},
                   {"id": "R003", "status": "DONE", "verdict": "CONFIRMED"},
                   {"id": "R004", "status": "DONE", "verdict": "PARTIAL"}])
            text = edge_map.render(root)
        self.assertIn("null R001; running R002", text)
        self.assertIn("confirmed R003", text)
        self.assertIn("- **Methods:** M002", text)
        self.assertIn("- **Rounds:** R004", text)

    def test_an_item_placed_twice_or_in_an_unknown_family_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            write(root / "registry/edge_families.csv", FAM_FIELDS, [fam("P1")])
            write(root / "registry/edge_map_links.csv", ["item", "family"],
                  [{"item": "M001", "family": "P1"}, {"item": "M001", "family": "Q9"}])
            write(root / "registry/methods.csv", ["id", "method", "status", "rid"],
                  [{"id": "M001", "method": "a", "status": "TESTED", "rid": "-"}])
            write(root / "registry/rounds.csv", ["id", "status", "verdict"], [])
            with self.assertRaises(ValueError) as e:
                edge_map.render(root)
        self.assertIn("placed 2 times", str(e.exception))
        self.assertIn("unknown family Q9", str(e.exception))


if __name__ == "__main__":
    unittest.main()
