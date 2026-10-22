"""Offline orchestration tests: invented subprocesses only, never collectors."""

import ast
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import fcntl
import hashlib
import io
import json
from pathlib import Path
import subprocess
import shlex
import shutil
import sys
import tempfile
import threading
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
        (self.root / ".venv/bin").mkdir(parents=True)
        (self.root / ".venv/bin/python").symlink_to(sys.executable)

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
        self.assertEqual(len(report["code"]["code_sha256"]), 64)

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

    def test_busy_notice_lock_prevents_start_and_blocks_only_mandatory_dependents(self):
        task = orchestration.Task("NOTICE", (sys.executable, "-c",
            "from pathlib import Path; Path('NOTICE.ran').write_text('should not run')"),
            shared_lock=".notices.lock", lock_wait=.05)
        with (self.root / ".notices.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = self.run_tasks((task, self.task("DEP", needs=("NOTICE",)), self.task("OTHER")))
        nodes = self.nodes(report)
        self.assertEqual(nodes["NOTICE"]["status"], "BLOCKED")
        self.assertIsNone(nodes["NOTICE"]["returncode"])
        self.assertIn("shared lock .notices.lock", nodes["NOTICE"]["reason"])
        self.assertGreaterEqual(nodes["NOTICE"]["lock_wait_seconds"], .05)
        self.assertFalse((self.root / "NOTICE.ran").exists())
        self.assertEqual(nodes["DEP"]["status"], "BLOCKED")
        self.assertEqual(nodes["OTHER"]["status"], "SUCCESS")

    @unittest.skipUnless(shutil.which("flock"), "requires shell-compatible flock")
    def test_lock_is_held_for_child_lifetime_and_released_after_failure(self):
        # The child must not inherit the parent descriptor, yet a separate flock command must observe the lock.
        check = "import subprocess; raise SystemExit(0 if subprocess.run(['flock','-n','.notices.lock','true']).returncode == 1 else 9)"
        held = orchestration.Task("HELD", (sys.executable, "-c", check), shared_lock=".notices.lock")
        fail = orchestration.Task("FAIL", (sys.executable, "-c", "raise SystemExit(7)"), shared_lock=".notices.lock")
        again = orchestration.Task("AGAIN", (sys.executable, "-c", check), shared_lock=".notices.lock")
        nodes = self.nodes(self.run_tasks((held, fail, again)))
        self.assertEqual([nodes[n]["status"] for n in ("HELD", "FAIL", "AGAIN")],
                         ["SUCCESS", "FAILED", "SUCCESS"])
        subprocess.run(("flock", "-n", str(self.root / ".notices.lock"), "true"), check=True)

    def test_notice_lock_released_after_timeout_and_interruption(self):
        slow = orchestration.Task("SLOW", (sys.executable, "-c", "import time; time.sleep(10)"),
                                  timeout=.05, shared_lock=".notices.lock")
        self.assertEqual(self.nodes(self.run_tasks((slow,)))["SLOW"]["status"], "TIMED_OUT")
        with (self.root / ".notices.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with patch.object(orchestration, "_run_process", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            self.run_tasks((slow,), "interrupt_lock")
        with (self.root / ".notices.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_lock_wait_does_not_consume_process_timeout(self):
        task = orchestration.Task("NOTICE", (sys.executable, "-c", "print('lock released')"),
                                  timeout=.3, shared_lock=".notices.lock", lock_wait=2)
        with (self.root / ".notices.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = threading.Timer(.4, lambda: fcntl.flock(lock, fcntl.LOCK_UN))
            release.start()
            try:
                node = self.nodes(self.run_tasks((task,)))["NOTICE"]
            finally:
                release.cancel()
                release.join()
        self.assertEqual(node["status"], "SUCCESS")
        self.assertGreater(node["lock_wait_seconds"], .3)

    def test_notice_lock_symlink_is_refused_before_child_start(self):
        target = self.base / "outside-lock"
        target.write_bytes(b"preserve")
        (self.root / ".notices.lock").symlink_to(target)
        task = orchestration.Task("NOTICE", self.task("NOTICE").argv, shared_lock=".notices.lock")
        node = self.nodes(self.run_tasks((task,)))["NOTICE"]
        self.assertEqual(node["status"], "FAILED")
        self.assertFalse((self.root / "NOTICE.ran").exists())
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_shared_lock_metadata_is_explicit_but_plan_does_not_open_it(self):
        tasks = orchestration.forward_tasks()
        locked = {t.name for t in tasks if t.shared_lock}
        expected = {name: {"path": ".notices.lock", "wait_seconds": 300}
                    for name in ("REC_NOTICES", "R268", "R270", "R272")}
        expected.update({name: {"path": path, "wait_seconds": 0}
                         for name, path in (("R278", ".xfund.lock"), ("R279", ".xfund_kc.lock"),
                                            ("R294", ".xfund_lt.lock"))})
        self.assertEqual(locked, set(expected))
        plan = orchestration.plan(tasks, self.root)
        for node in plan["tasks"]:
            if node["name"] in locked:
                self.assertEqual(node["shared_lock"], expected[node["name"]])
        self.assertFalse((self.root / ".notices.lock").exists())
        self.assertEqual(list(self.root.glob(".xfund*.lock")), [])

    def test_busy_carry_lock_blocks_only_that_lane_and_is_reported_to_cross_family_book(self):
        actual = {t.name: t for t in orchestration.forward_tasks()}
        carry = [replace(actual[name], argv=self.task(name).argv) for name in ("R278", "R279", "R294")]
        # Use invented children, preserving the real carry lock settings and the book's carry edges.
        book_code = ("from pathlib import Path; "
                     "assert not Path('R278.ran').exists(); assert Path('R279.ran').exists(); "
                     "Path('BOOK.ran').write_text('invented')")
        book = replace(actual["R285"], argv=self.task("BOOK", book_code).argv,
                       optional=tuple(name for name in actual["R285"].optional if name in {t.name for t in carry}))
        with (self.root / actual["R278"].shared_lock).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report = self.run_tasks((book, *carry))
        nodes = self.nodes(report)
        self.assertEqual(nodes["R278"]["status"], "BLOCKED")
        self.assertIsNone(nodes["R278"]["returncode"])
        self.assertIn(".xfund.lock", nodes["R278"]["reason"])
        self.assertEqual(nodes["R279"]["status"], "SUCCESS")
        self.assertEqual(nodes["R294"]["status"], "SUCCESS")
        self.assertEqual(nodes["R285"]["status"], "SUCCESS")
        self.assertEqual(nodes["R285"]["optional_unavailable"], ["R278"])
        self.assertTrue((self.root / "BOOK.ran").exists())
        self.assertFalse((self.root / "R278.ran").exists())
        self.assertEqual(report["status"], "FAILED")
        self.assertIn(".xfund.lock", (self.state / "tick_1/R278.log").read_text())

    @unittest.skipUnless(shutil.which("flock"), "requires shell-compatible flock")
    def test_each_carry_lock_is_held_for_child_and_released_after_failure(self):
        actual = {t.name: t for t in orchestration.forward_tasks()}
        for name in ("R278", "R279", "R294"):
            with self.subTest(name=name):
                task = actual[name]
                check = ("import subprocess; "
                         f"assert subprocess.run(['flock','-n',{task.shared_lock!r},'true']).returncode == 1; "
                         "raise SystemExit(7)")
                child = replace(task, argv=self.task(name, check).argv)
                node = self.nodes(self.run_tasks((child,), run_id=name))[name]
                self.assertEqual((node["status"], node["returncode"]), ("FAILED", 7))
                with (self.root / task.shared_lock).open("a") as lock:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_invalid_lock_paths_and_waits_rejected_before_outputs(self):
        for path, wait in (("../outside.lock", 1), ("/tmp/lock", 1), (".notices.lock", -1),
                           (".notices.lock", float("inf"))):
            with self.subTest(path=path, wait=wait), self.assertRaises(ValueError):
                self.run_tasks((orchestration.Task("A", self.task("A").argv, shared_lock=path, lock_wait=wait),))
        self.assertFalse(self.state.exists())

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

    def test_untracked_code_bytes_are_fingerprinted(self):
        first = orchestration.code_version(self.root)
        extra = self.root / "scripts/untracked.py"
        extra.write_text("# first untracked version\n")
        second = orchestration.code_version(self.root)
        self.assertNotEqual(first["code_sha256"], second["code_sha256"])
        extra.write_text("# changed without changing git status\n")
        third = orchestration.code_version(self.root)
        self.assertEqual(second["dirty_code"], third["dirty_code"])
        self.assertNotEqual(second["code_sha256"], third["code_sha256"])

    def test_new_untracked_code_during_task_blocks_the_next_task(self):
        report = self.run_tasks((self.task("CREATE", "from pathlib import Path; Path('scripts/new.py').write_text('# new')"),
                                 self.task("LATER")))
        nodes = self.nodes(report)
        self.assertEqual(nodes["CREATE"]["status"], "FAILED")
        self.assertEqual(nodes["LATER"]["status"], "BLOCKED")
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

    def test_interrupt_before_first_task_persists_interrupted_status(self):
        version = orchestration.code_version(self.root)
        with patch.object(orchestration, "code_version", side_effect=[version, KeyboardInterrupt]), \
                self.assertRaises(KeyboardInterrupt):
            self.run_tasks((self.task("A"), self.task("B")))
        report = json.loads((self.state / "tick_1/status.json").read_text())
        self.assertEqual(report["status"], "INTERRUPTED")
        self.assertTrue(all(n["status"] == "BLOCKED" for n in report["tasks"]))
        self.assertFalse((self.root / "A.ran").exists())

    def test_interrupt_during_initial_status_write_is_recovered(self):
        original = orchestration.write_status
        calls = 0
        def interrupt_once(*args, **kwargs):
            nonlocal calls
            calls += 1
            original(*args, **kwargs)
            if calls == 1:
                raise KeyboardInterrupt
        with patch.object(orchestration, "write_status", side_effect=interrupt_once), \
                self.assertRaises(KeyboardInterrupt):
            self.run_tasks((self.task("A"),))
        report = json.loads((self.state / "tick_1/status.json").read_text())
        self.assertEqual(report["status"], "INTERRUPTED")
        self.assertEqual(self.nodes(report)["A"]["status"], "BLOCKED")

    def test_interrupt_while_acquiring_lock_is_recovered(self):
        with patch.object(orchestration.fcntl, "flock", side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            self.run_tasks((self.task("A"),))
        report = json.loads((self.state / "tick_1/status.json").read_text())
        self.assertEqual(report["status"], "INTERRUPTED")
        self.assertEqual(self.nodes(report)["A"]["status"], "BLOCKED")

    def test_interrupted_atomic_replace_preserves_previous_status_and_allows_recovery(self):
        self.state.mkdir()
        path = self.state / "status.json"
        orchestration.write_status(path, {"status": "RUNNING"})
        with patch.object(orchestration.os, "replace", side_effect=KeyboardInterrupt), \
                self.assertRaises(KeyboardInterrupt):
            orchestration.write_status(path, {"status": "SUCCESS"})
        self.assertEqual(json.loads(path.read_text())["status"], "RUNNING")
        self.assertEqual(list(self.state.glob("*.tmp")), [])
        orchestration.write_status(path, {"status": "INTERRUPTED"})
        self.assertEqual(json.loads(path.read_text())["status"], "INTERRUPTED")

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
        self.assertEqual(plan["tasks"][0]["argv"][0], str(self.root / ".venv/bin/python"))

    def test_default_cli_refuses_missing_venv_without_system_fallback(self):
        (self.root / ".venv/bin/python").unlink()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            orchestration.main(["--root", str(self.root), "--task", "R225"])
        self.assertEqual(raised.exception.code, 2)
        self.assertFalse((self.root / ".forward.lock").exists())
        self.assertFalse(self.state.exists())

    def test_explicit_interpreter_override_is_recorded(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(orchestration.main(["--root", str(self.root), "--python", sys.executable]), 0)
        self.assertEqual(json.loads(output.getvalue())["tasks"][0]["argv"][0], sys.executable)

    def test_main_handles_interrupt_outside_task_execution(self):
        with patch.object(orchestration, "run_tasks", side_effect=KeyboardInterrupt), \
                redirect_stderr(io.StringIO()):
            result = orchestration.main(["--root", str(self.root), "--execute",
                                         "--state-dir", str(self.state), "--run-id", "outer_interrupt"])
        self.assertEqual(result, 130)

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
        self.assertEqual(tasks["LAG"].needs, ("R200", "R214", "R215", "R218", "R220", "R225"))
        self.assertEqual(tasks["PANEL"].needs, ("LAG",))
        static = "experiments/venue_gap_v1/results/tradfi_symbols.json"
        self.assertEqual(tasks["R215"].files[0].path, static)
        self.assertEqual(tasks["R224"].files[0].path, static)
        # Compare with the actual frozen runner's carry mapping without importing/running it.
        parsed = ast.parse((orchestration.ROOT / "scripts/forward_xbook.py").read_text())
        assignment, = [node for node in parsed.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "CARRY" for target in node.targets)]
        carry_names = {name.split()[0] for name in ast.literal_eval(assignment.value)}
        self.assertEqual(carry_names, {"R278", "R279"})
        self.assertEqual(set(tasks["R285"].optional),
                         carry_names | {"R215", "R218", "R266", "R268", "R270", "R272"})
        order = [t.name for t in orchestration.ordered_tasks(tasks.values())]
        self.assertTrue(all(order.index(name) < order.index("R285") for name in carry_names))
        self.assertNotIn("R294", tasks["R285"].needs + tasks["R285"].optional)

    def test_graph_commands_order_and_timeouts_match_the_actual_shell_wrapper(self):
        shell = orchestration.ROOT / "scripts/forward_all.sh"
        actual = []
        locks = {}
        for line in shell.read_text().splitlines():
            words = shlex.split(line, comments=True)
            lock = None
            if words[:2] == ["flock", "-w"]:                  # lanes that read the notice catalogs hold its lock
                lock = {"path": words[3], "wait_seconds": float(words[2])}
                words = words[4:]
            elif words[:2] == ["flock", "-n"]:                # independent carry lanes use nonblocking locks
                lock = {"path": words[2], "wait_seconds": 0}
                words = words[3:]
            elif words and words[0] == "flock":
                self.fail(f"unparsed shell lock command: {line}")
            if words and words[0] == "timeout":
                self.assertGreaterEqual(len(words), 4)
                self.assertEqual(words[2], "$PY")
                actual.append((words[3], float(words[1])))
                locks[words[3]] = lock
        self.assertTrue(actual)
        proposed = [(t.argv[1], t.timeout) for t in orchestration.ordered_tasks(orchestration.forward_tasks())]
        self.assertEqual(proposed, actual)
        for task in orchestration.forward_tasks():
            expected = {"path": task.shared_lock, "wait_seconds": task.lock_wait} if task.shared_lock else None
            self.assertEqual(expected, locks[task.argv[1]])


if __name__ == "__main__":
    unittest.main()
