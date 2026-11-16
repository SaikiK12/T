"""scripts/lane_census.py: word-boundary writer match, owner parsing, classes, and a census on a synthetic repo."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import lane_census as lc  # noqa: E402

TODAY = date(2026, 11, 16)


class Parts(unittest.TestCase):
    def test_writer_match_is_whole_word(self):
        wf = {"a.yml": "run experiments/tltcarry_fwd/x", "b.yml": "python run.py --lane carry_fwd"}
        self.assertEqual(lc.writers("carry_fwd", wf), ["b.yml"])
        self.assertEqual(lc.writers("tltcarry_fwd", wf), ["a.yml"])
        self.assertEqual(lc.writers("xvroll_fwd", wf), [])

    def test_owner_line(self):
        self.assertEqual(lc.owner("- **Owner (single writer):** Codex, isolated branch\n"), "Codex, isolated branch")
        self.assertEqual(lc.owner("no owner here"), "")

    def test_classes(self):
        c = lambda wf, own, last: lc.classify({}, wf, own, last, TODAY, 10)  # noqa: E731
        self.assertEqual(c(["w.yml"], "", date(2026, 11, 15)), "workflow")
        self.assertEqual(c(["w.yml"], "", date(2026, 10, 1)), "workflow-quiet")
        self.assertEqual(c([], "Codex; native journals", date(2026, 11, 7)), "codex")
        self.assertEqual(c([], "Claude", date(2026, 11, 6)), "no-writer-recent")
        self.assertEqual(c([], "Claude", date(2026, 11, 1)), "no-writer")
        self.assertEqual(c([], "Claude", None), "no-writer")
        self.assertEqual(lc.classify({}, ["w.yml"], "", date(2026, 10, 1), TODAY, 10, dated=True), "workflow-dated")
        self.assertEqual(lc.classify({}, [], "Claude", date(2026, 11, 1), TODAY, 10, noted=True), "writer-lost-noted")

    def test_dated_only(self):
        self.assertTrue(lc.dated_only(["on:\n  schedule:\n    - cron: '41 6 13-16 2 *'\n    - cron: '41 6 15-18 5 *'\n"]))
        self.assertFalse(lc.dated_only(["    - cron: '41 6 13-16 2 *'\n    - cron: '29 0-7 * * *'\n"]))
        self.assertFalse(lc.dated_only(["workflow_dispatch only"]))


class Census(unittest.TestCase):
    def test_synthetic_repo(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "registry").mkdir()
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "registry" / "rounds.csv").write_text(
                "id,date,lane,title,status,verdict,trials,prereg_sha,path,notes\n"
                "R1,2026-11-01,live_fwd,t,RUNNING,PENDING,1,,,\n"
                "R2,2026-11-01,dead_fwd,t,RUNNING,PENDING,1,,,\n"
                "R3,2026-11-01,cx_v1,t,REGISTERED,PENDING,1,,,\n"
                "R4,2026-11-01,done_v1,t,DONE,NULL,1,,,\n")
            (root / ".github" / "workflows" / "w.yml").write_text("lane: live_fwd\n")
            (root / "experiments" / "dead_fwd").mkdir(parents=True)
            (root / "experiments" / "dead_fwd" / "README.md").write_text("# dead\n")
            (root / "experiments" / "cx_v1").mkdir(parents=True)
            (root / "experiments" / "cx_v1" / "PREREG.md").write_text("- **Owner (single writer):** Codex\n")
            last = {"experiments/live_fwd": date(2026, 11, 16), "experiments/dead_fwd": date(2026, 11, 6),
                    "experiments/cx_v1": date(2026, 11, 7)}
            rows = lc.census(root, TODAY, 7, last=lambda p: last.get(p))
            got = {r["id"]: r["class"] for r in rows}
            self.assertEqual(got, {"R1": "workflow", "R2": "no-writer", "R3": "codex"})
            (root / "experiments" / "dead_fwd" / "README.md").write_text("# dead\n**Writer lost (2026-11-16).**\n")
            self.assertEqual({r["id"]: r["class"] for r in lc.census(root, TODAY, 7, last=lambda p: last.get(p))}["R2"],
                             "writer-lost-noted")
            text = lc.render(rows, TODAY)
            self.assertIn("3 open rows", text)
            self.assertLess(text.index("| R2 "), text.index("| R1 "))     # lost writers listed first


if __name__ == "__main__":
    unittest.main()
