"""Offline orchestration tests: invented subprocesses only, never collectors."""

from contextlib import redirect_stdout
import fcntl
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import orchestrate_forward as orchestration


class ForwardOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "invented.py").write_text("# invented code\n")
        for argv in (("init", "-q"), ("add", "scripts"),
                     ("-c", "user.name=Offline fixture", "-c", "user.email=offline@example.invalid",
                      "commit", "-qm", "invented fixture")):
            subprocess.run(("git", "-C", str(self.root), *argv), check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.state = self.base / "status"

    def task(self, name, code=None, needs=(), optional=(), timeout=10, files=()):
        if code is None:
            code = f"from pathlib import Path; Path('{name}.ran').write_text('invented'); print('{name} output')"
        return orchestration.Task(name, (sys.executable, "-c", code), needs, optional, timeout, files)

    def run_tasks(self, tasks, run_id="tick_1", selected=None):
        return orchestration.run_tasks(tasks, self.root, self.state, run_id, selected)

    @staticmethod
    def nodes(report):
        return {n["name"]: n for n in report["tasks"]}

    def test_mandatory_failure_blocks_descendants_and_independent_branch_runs(self):
        report = self.run_tasks((self.task("A", "print('failure evidence'); raise SystemExit(7)"),
                                 self.task("B", needs=("A",)), self.task("C"),
                                 self.task("D", needs=("B",))))
        n = self.nodes(report)
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual((n["A"]["status"], n["A"]["returncode"]), ("FAILED", 7))
        self.assertEqual(n["B"]["blocked_by"], ["A"])
        self.assertEqual(n["D"]["blocked_by"], ["B"])
        self.assertEqual(n["C"]["status"], "SUCCESS")
        self.assertFalse((self.root / "B.ran").exists())
        self.assertEqual((self.state / "tick_1" / "A.log").read_text(), "failure evidence\n")
        self.assertEqual(json.loads((self.state / "tick_1" / "status.json").read_text()), report)
        self.assertEqual(len(report["code"]["commit"]), 40)
        self.assertEqual(len(report["code"]["tracked_code_sha256"]), 64)

    def test_optional_failure_does_not_block_and_is_reported(self):
        report = self.run_tasks((self.task("REF", "raise SystemExit(2)"),
                                 self.task("BOOK", optional=("REF",))))
        n = self.nodes(report)
        self.assertEqual(n["BOOK"]["status"], "SUCCESS")
        self.assertEqual(n["BOOK"]["optional_unavailable"], ["REF"])
        self.assertEqual(report["status"], "FAILED")

    def test_selection_includes_mandatory_ancestors_without_optional_ones(self):
        tasks = (self.task("A"), self.task("REF", needs=("A",)),
                 self.task("BOOK", needs=("A",), optional=("REF",)))
        report = self.run_tasks(tasks, selected=["BOOK"])
        n = self.nodes(report)
        self.assertEqual(list(n), ["A", "BOOK"])
        self.assertEqual(n["BOOK"]["optional_unavailable"], ["REF"])
        self.assertFalse((self.root / "REF.ran").exists())

    def test_task_order_does_not_depend_on_input_order(self):
        report = self.run_tasks((self.task("CHILD", needs=("PARENT",)), self.task("PARENT")))
        self.assertEqual(list(self.nodes(report)), ["PARENT", "CHILD"])
        self.assertEqual(report["status"], "SUCCESS")

    def test_duplicate_run_id_refuses_process_reexecution_and_preserves_report(self):
        tasks = (self.task("A", "from pathlib import Path; p=Path('counter'); p.write_text(p.read_text()+'x' if p.exists() else 'x')"),)
        self.run_tasks(tasks)
        original = (self.state / "tick_1" / "status.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_tasks(tasks)
        self.assertEqual((self.root / "counter").read_text(), "x")
        self.assertEqual((self.state / "tick_1" / "status.json").read_bytes(), original)

    def test_timeout_keeps_failure_evidence_and_blocks_only_dependents(self):
        report = self.run_tasks((self.task("SLOW", "import time; print('started', flush=True); time.sleep(10)", timeout=.15),
                                 self.task("DEP", needs=("SLOW",)), self.task("OTHER")))
        n = self.nodes(report)
        self.assertEqual(n["SLOW"]["status"], "TIMED_OUT")
        self.assertLess(n["SLOW"]["returncode"], 0)
        self.assertEqual(n["DEP"]["status"], "BLOCKED")
        self.assertEqual(n["OTHER"]["status"], "SUCCESS")

    def test_missing_executable_fails_but_does_not_abort_independent_task(self):
        missing = orchestration.Task("MISSING", (str(self.base / "absent_executable"),))
        n = self.nodes(self.run_tasks((missing, self.task("OTHER"))))
        self.assertEqual(n["MISSING"]["status"], "FAILED")
        self.assertIsNone(n["MISSING"]["returncode"])
        self.assertEqual(n["OTHER"]["status"], "SUCCESS")

    def test_shared_legacy_lock_blocks_every_process(self):
        with (self.root / ".forward.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = self.run_tasks((self.task("A"),))
        self.assertEqual(report["status"], "BLOCKED")
        self.assertFalse((self.root / "A.ran").exists())

    def test_missing_and_changed_static_input_block_its_task_only(self):
        path = self.root / "seed"
        requirement = orchestration.Requirement("seed", hashlib.sha256(b"correct").hexdigest())
        tasks = (self.task("INPUT", files=(requirement,)), self.task("OTHER"))
        first = self.nodes(self.run_tasks(tasks))
        self.assertEqual(first["INPUT"]["status"], "BLOCKED")
        self.assertEqual(first["OTHER"]["status"], "SUCCESS")
        path.write_bytes(b"wrong")
        second = self.nodes(self.run_tasks(tasks, "tick_2"))
        self.assertIn("SHA-256 mismatch", second["INPUT"]["invalid_files"][0])
        path.write_bytes(b"correct")
        self.assertEqual(self.run_tasks(tasks, "tick_3")["status"], "SUCCESS")

    def test_symlink_input_cannot_escape_repository(self):
        outside = self.base / "outside"
        outside.write_text("not an input")
        (self.root / "seed").symlink_to(outside)
        report = self.run_tasks((self.task("A", files=(orchestration.Requirement("seed"),)),))
        self.assertEqual(self.nodes(report)["A"]["status"], "BLOCKED")

    def test_code_change_blocks_later_tasks(self):
        code = "from pathlib import Path; Path('scripts/invented.py').write_text('# changed during run')"
        report = self.run_tasks((self.task("EDIT", code), self.task("LATER")))
        n = self.nodes(report)
        self.assertEqual(n["EDIT"]["status"], "FAILED")
        self.assertEqual(n["EDIT"]["returncode"], 0)
        self.assertIn("code changed during", n["EDIT"]["reason"])
        later = n["LATER"]
        self.assertEqual(later["status"], "BLOCKED")
        self.assertIn("code changed", later["reason"])
        self.assertFalse((self.root / "LATER.ran").exists())

    def test_last_task_code_change_cannot_report_overall_success(self):
        report = self.run_tasks((self.task("EDIT", "from pathlib import Path; Path('scripts/invented.py').write_text('# changed')"),))
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("code_at_finish", self.nodes(report)["EDIT"])

    def test_interruption_persists_status_blocks_remaining_and_releases_lock(self):
        with patch.object(orchestration, "run_process", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.run_tasks((self.task("A"), self.task("B")))
        report = json.loads((self.state / "tick_1" / "status.json").read_text())
        self.assertEqual(report["status"], "INTERRUPTED")
        self.assertEqual(self.nodes(report)["A"]["status"], "FAILED")
        self.assertEqual(self.nodes(report)["B"]["status"], "BLOCKED")
        with (self.root / ".forward.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_invalid_graphs_fail_before_any_output(self):
        cases = ((self.task("A", needs=("B",)), self.task("B", needs=("A",))),
                 (self.task("A", needs=("UNKNOWN",)),),
                 (self.task("A"), self.task("A")),
                 (self.task("A", timeout=float("inf")),))
        for tasks in cases:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                self.run_tasks(tasks)
        self.assertFalse(self.state.exists())

    def test_output_cannot_enter_repository_and_run_id_cannot_traverse(self):
        with self.assertRaises(ValueError):
            orchestration.run_tasks((self.task("A"),), self.root, self.root / "experiments", "id")
        with self.assertRaises(ValueError):
            self.run_tasks((self.task("A"),), "../unsafe")
        self.assertFalse(self.state.exists())

    def test_default_cli_prints_plan_without_launching_or_writing(self):
        output = io.StringIO()
        with patch.object(orchestration, "run_process", side_effect=AssertionError("must stay offline")), redirect_stdout(output):
            self.assertEqual(orchestration.main(["--root", str(self.root), "--task", "R225"]), 0)
        plan = json.loads(output.getvalue())
        self.assertEqual([t["name"] for t in plan["tasks"]], ["R200", "R215", "R218", "R225"])
        self.assertFalse((self.root / ".forward.lock").exists())
        self.assertFalse(self.state.exists())

    def test_forward_graph_matches_direct_mandatory_and_optional_reads(self):
        tasks = {t.name: t for t in orchestration.forward_tasks()}
        self.assertEqual(tasks["R215"].needs, ("R200",))
        self.assertEqual(tasks["R215"].optional, ("R214",))
        self.assertEqual(tasks["R218"].needs, ("R200", "R215"))
        self.assertEqual(tasks["R220"].needs, ("R200",))
        self.assertEqual(tasks["R224"].needs, ("R200",))
        self.assertEqual(tasks["R221"].needs, ("R215", "R218"))
        self.assertEqual(tasks["R225"].needs, ("R215", "R218"))
        self.assertEqual(tasks["R225"].files[0].sha256, orchestration.SEED_SHA256)


if __name__ == "__main__":
    unittest.main()
