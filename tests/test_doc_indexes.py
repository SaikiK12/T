"""The two maintained indexes stay complete: every document is listed where a reader looks for it.

- README.md#docs lists every Markdown file under docs/ (supporting files of a dated review's own folder excepted).
- research/intake/README.md lists every entry of research/intake/.
Both checks read tracked paths and index text only; no document body or result is opened.
"""
from pathlib import Path, PurePosixPath
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def tracked(pattern):
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", pattern],
                         check=True, capture_output=True).stdout.decode("utf-8")
    return sorted(p for p in out.split("\0") if p)


class DocIndexTests(unittest.TestCase):
    def test_root_index_lists_every_doc(self):
        index = (ROOT / "README.md").read_text(encoding="utf-8")
        missing = []
        for path in tracked("docs/*.md"):
            parts = PurePosixPath(path).parts
            # docs/reviews/<review>/<file>.md are a dated review's supporting files, linked from that review.
            if len(parts) == 4 and parts[1] == "reviews":
                continue
            if f"({path}" not in index:
                missing.append(path)
        self.assertEqual(missing, [], "add these to the grouped index in README.md#docs")

    def test_intake_index_lists_every_entry(self):
        index = (ROOT / "research/intake/README.md").read_text(encoding="utf-8")
        entries = {PurePosixPath(p).parts[2] for p in tracked("research/intake/*")}
        entries.discard("README.md")
        missing = sorted(e for e in entries if f"({e}" not in index)
        self.assertEqual(missing, [], "add these to the index in research/intake/README.md")


if __name__ == "__main__":
    unittest.main()
