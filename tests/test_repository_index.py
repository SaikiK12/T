import csv
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.repository_index import build_index, main, render


class RepositoryIndexTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def write(self, path, content):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content, encoding="utf-8")
        return file

    def registry(self, rows):
        path = self.write("registry/rounds.csv", "")
        with path.open("w", newline="", encoding="utf-8") as target:
            writer = csv.DictWriter(target, fieldnames=["id", "lane", "status", "verdict"])
            writer.writeheader()
            writer.writerows(rows)

    def test_unknown_document_is_visible_and_output_does_not_index_itself(self):
        self.write("docs/FUTURE.md", "# New family\n")
        self.write("docs/README.md", "# Generated index\n")
        entries = build_index(self.root, ["docs/README.md", "docs/FUTURE.md"])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["group"], "New / unclassified documents")
        self.assertIn("New family", render(entries))

    def test_registry_is_authority_missing_imports_and_unregistered_folders_visible(self):
        self.registry([
            dict(id="R1", lane="local", status="DONE", verdict="NULL"),
            dict(id="R2", lane="imported", status="DONE", verdict="PARTIAL"),
        ])
        self.write("experiments/local/PREREG.md", "# Specification\n")
        self.write("experiments/local/FINDINGS.md", "# Claims success\n")
        self.write("experiments/draft/PREREG.md", "# Not registered\n")
        entries = build_index(self.root, [
            "registry/rounds.csv", "experiments/local/PREREG.md",
            "experiments/local/FINDINGS.md", "experiments/draft/PREREG.md",
        ])
        lanes = {e["title"]: e for e in entries}
        self.assertEqual(lanes["local"]["registry"][0]["verdict"], "NULL")
        self.assertFalse(lanes["imported"]["local"])
        self.assertEqual(lanes["draft"]["registry"], [])
        text = render(entries)
        self.assertIn("Registered folder absent", text)
        self.assertNotIn("](../experiments/imported)", text)
        self.assertIn("No registry row in this checkout", text)

    def test_deterministic_and_never_reads_or_changes_result_journal_or_runner(self):
        paths = ["scripts/run_demo.py", "experiments/demo/results/outcome.json",
                 "experiments/demo/journal/tickets.csv", "docs/GATES.md"]
        for path in paths:
            self.write(path, "# Heading\n" if path.endswith(".md") else "DO NOT PARSE OR RUN\n")
        # The catalog only needs the paths for results/journals, not their contents.
        self.root.joinpath("experiments/demo/results/outcome.json").unlink()
        self.root.joinpath("experiments/demo/journal/tickets.csv").unlink()
        before = self.root.joinpath("scripts/run_demo.py").read_bytes()
        a = build_index(self.root, paths)
        b = build_index(self.root, reversed(paths))
        self.assertEqual(a, b)
        self.assertEqual(render(a), render(b))
        self.assertEqual(self.root.joinpath("scripts/run_demo.py").read_bytes(), before)

    def test_unsafe_paths_and_external_symlinks_fail_before_reading(self):
        self.write("outside.md", "# Outside\n")
        self.root.joinpath("docs").mkdir()
        self.root.joinpath("docs/LINK.md").symlink_to(self.root / "outside.md")
        with self.assertRaises(ValueError):
            build_index(self.root, ["docs/LINK.md"])
        with self.assertRaises(ValueError):
            build_index(self.root, ["docs/../outside.md"])
        self.registry([dict(id="R1", lane="../escape", status="DONE", verdict="NULL")])
        with self.assertRaises(ValueError):
            build_index(self.root, ["registry/rounds.csv"])

    def test_markdown_special_characters_and_spaces(self):
        self.write("docs/a b.md", "# Text | [example]\n")
        text = render(build_index(self.root, ["docs/a b.md"]))
        self.assertIn("Text &#124; &#91;example&#93;", text)
        self.assertIn("../docs/a%20b.md", text)

    def test_cli_search_write_and_stale_check_ignore_untracked_cache(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.write("docs/GATES.md", "# Decision gates\n")
        self.write("data/ignored.md", "# Not a source\n")
        subprocess.run(["git", "-C", str(self.root), "add", "docs/GATES.md"], check=True)
        argv = ["--root", str(self.root)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(argv + ["--check"]), 1)
            self.assertEqual(main(argv + ["--write"]), 0)
            self.assertEqual(main(argv + ["--check"]), 0)
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(main(argv + ["--find", "DECISION", "--json"]), 0)
        matches = json.loads(stream.getvalue())
        self.assertEqual([e["path"] for e in matches], ["docs/GATES.md"])
        self.write("docs/GATES.md", "# Different heading\n")
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(argv + ["--check"]), 1)

    def test_output_symlink_is_not_overwritten(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        target = self.write("important.txt", "unchanged")
        self.root.joinpath("docs").mkdir()
        self.root.joinpath("docs/README.md").symlink_to(target)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root), "--write"]), 2)
        self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
