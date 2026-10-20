"""Synthetic operational metadata fixtures only; no running processes are read."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.dashboard_jobs import build_jobs, MAX_REPORT_BYTES


class DashboardJobs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.state = Path(self.tmp.name) / "runs"
        self.root.mkdir()
        self.now = 1_700_000_000

    def report(self, rid="tick1", task="R215", status="SUCCESS", code=0, started="2023-11-14T22:00:00Z", **extra):
        directory = self.state / rid
        directory.mkdir(parents=True)
        value = {"schema_version": 1, "root": str(self.root), "run_id": rid, "started_at": started,
                 "tasks": [{"name": task, "status": status, "returncode": code,
                            "log": task + ".log", "finished_at": started}], **extra}
        (directory / "status.json").write_text(json.dumps(value))
        return directory / "status.json"

    def row(self, **kwargs):
        return next(r for r in build_jobs(self.root, now=self.now, **kwargs) if r["task_id"] == "R215")

    def test_missing_logs_are_unknown_not_hidden_or_green(self):
        row = self.row()
        self.assertEqual(row["state"], "UNKNOWN")
        self.assertIsNone(row["ok"])
        self.assertEqual(row["display_name"], "MEXC positioning books")
        self.assertEqual(row["category"], "Prospective paper")

    def test_fresh_marker_or_error_log_is_not_read_and_never_success(self):
        log = self.root / "experiments/mexc_fwd/tick.log"
        log.parent.mkdir(parents=True)
        log.write_text("== tick freshly started\nError old failure\n")
        # With no structured input, no file contents should be opened at all.
        with patch.object(Path, "read_text", side_effect=AssertionError("no log reading")):
            row = self.row()
        self.assertEqual(row["state"], "UNKNOWN")
        self.assertEqual(row["status_source"], "legacy_log")
        self.assertIsNone(row["ok"])

    def test_structured_status_preserves_id_run_exit_and_category(self):
        self.report()
        row = self.row(state_dir=self.state)
        self.assertEqual((row["state"], row["run_id"], row["returncode"]), ("SUCCESS", "tick1", 0))
        self.assertTrue(row["ok"])
        self.assertEqual(row["status_source"], "orchestrator")
        self.assertTrue(row["log_path"].endswith("tick1/R215.log"))

    def test_failures_timeouts_blocking_and_running_are_distinct(self):
        for status, code, ok in (("FAILED", 1, False), ("TIMED_OUT", -9, False),
                                 ("BLOCKED", None, False), ("RUNNING", None, None), ("PENDING", None, None)):
            with self.subTest(status=status):
                path = self.report(rid=status, status=status, code=code)
                row = self.row(state_dir=self.state)
                self.assertEqual(row["state"], status)
                self.assertIs(row["ok"], ok)
                path.unlink()
                path.parent.rmdir()

    def test_stale_success_is_not_recent_success(self):
        self.report(started="2023-11-13T00:00:00Z")
        row = self.row(state_dir=self.state)
        self.assertTrue(row["ok"])
        self.assertTrue(row["stale"])
        self.assertGreater(row["age_h"], 2)

    def test_latest_run_is_chosen_by_recorded_time_not_file_touch(self):
        old = self.report(rid="old", status="FAILED", code=1, started="2023-11-13T00:00:00Z")
        self.report(rid="new")
        old.touch()
        self.assertEqual(self.row(state_dir=self.state)["run_id"], "new")

    def test_report_from_other_checkout_does_not_change_local_status(self):
        self.report(root="/other/repo")
        row = self.row(state_dir=self.state)
        self.assertEqual(row["state"], "UNKNOWN")
        self.assertIsNone(row["ok"])

    def test_untrusted_reports_cannot_assert_success(self):
        for value in ([], {"schema_version": 99}, {"schema_version": 1, "root": str(self.root),
                        "run_id": "bad", "started_at": "2023-11-14T22:00:00Z",
                        "tasks": [{"name": "R215", "status": "SUCCESS", "returncode": 7}]}):
            with self.subTest(value=value):
                path = self.state / "bad/status.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value))
                self.assertIsNone(self.row(state_dir=self.state)["ok"])

    def test_symlink_report_and_oversize_report_rejected(self):
        outside = Path(self.tmp.name) / "outside.json"
        outside.write_text("not a report")
        run = self.state / "linked"
        run.mkdir(parents=True)
        (run / "status.json").symlink_to(outside)
        self.assertEqual(self.row(state_dir=self.state)["state"], "UNKNOWN")
        (run / "status.json").unlink()
        (run / "status.json").write_bytes(b" " * (MAX_REPORT_BYTES + 1))
        self.assertEqual(self.row(state_dir=self.state)["state"], "UNKNOWN")

    def test_external_status_directory_required_and_no_commandline_inspection(self):
        with patch("os.listdir", side_effect=AssertionError("no proc inspection")):
            rows = build_jobs(self.root, now=self.now, state_dir=self.root)
        self.assertTrue(any(r["state"] == "UNAVAILABLE" for r in rows))


if __name__ == "__main__":
    unittest.main()
