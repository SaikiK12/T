import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lab import prereg, registry, runtime
from scripts import orchestrate_forward, qx_run_verified


class VerifiedQxRunnerTests(unittest.TestCase):
    def fixture(self, root):
        root = Path(root)
        lane = root / "experiments" / "fixture"
        lane.mkdir(parents=True)
        for directory in (root / "engine/src", root / "engine/target/release", root / "scripts", root / "registry"):
            directory.mkdir(parents=True, exist_ok=True)
        for name, contents in (("Cargo.toml", "[package]\nname='qx'\n"), ("Cargo.lock", "# fixture\n"),
                               ("src/main.rs", "fn main() {}\n")):
            (root / "engine" / name).write_text(contents)
        for name in ("qx_run.py", "qx_run_verified.py", "build_engine.py"):
            source = Path(__file__).resolve().parents[1] / "scripts" / name
            (root / "scripts" / name).write_bytes(source.read_bytes())

        report = {
            "name": "synthetic verified run", "verdict": "NULL", "trials": 1,
            "events_in": 0, "priced_legs": 0, "no_market": 0, "clusters": {}, "legs_by_venue": {},
            "rc_null_p95": 0.0, "survivors": [], "spec": {"costs": [0.001, 0.002, 0.003]},
            "strategies": [{"label": "fixture", "p_rc": 1.0, "pass": False, "null": None, "gates": {},
                            "stats": [{"n": 1, "mean_pct": 0.0, "median_pct": 0.0, "hit": 0.0,
                                       "t": 0.0, "half1_pct": 0.0, "half2_pct": 0.0,
                                       "y2025_pct": 0.0, "y2025_n": 0}] * 3}],
        }
        report_path = root / "report-fixture.json"
        report_path.write_text(json.dumps(report))
        binary = root / "engine/target/release/qx"
        binary.write_text(
            f"#!{sys.executable}\n"
            "import pathlib,sys\n"
            f"source=pathlib.Path({str(report_path)!r})\n"
            "spec=pathlib.Path(sys.argv[2])\n"
            "out=spec.parent/'results'/'report.json'\n"
            "out.parent.mkdir(exist_ok=True)\n"
            "out.write_bytes(source.read_bytes())\n"
            f"pathlib.Path({str(root / 'called.txt')!r}).write_text(' '.join(sys.argv[1:]))\n"
        )
        binary.chmod(0o755)

        spec = lane / "spec.toml"
        spec.write_text('events = []\ncosts = [0.001, 0.002, 0.003]\n')
        paths = [spec, root / "scripts/qx_run.py", root / "scripts/qx_run_verified.py",
                 root / "scripts/build_engine.py"]
        paths.extend(root / name for name in runtime.engine_sources(root))
        prereg_path = lane / "PREREG.md"
        hashes = "".join(f"{path.relative_to(root)}  {runtime.digest(path)}\n" for path in paths)
        prereg_path.write_text("# PREREG: fixture (R999999). Verified runner test\n"
                               "- **Registry id:** R999999\n\n```inputs\n" + hashes + "```\n")
        prereg.freeze(prereg_path)
        build_receipt = {"status": "SUCCESS", "sources": runtime.engine_sources(root),
                         "binary_sha256": runtime.digest(binary), "cargo": "cargo fixture",
                         "rustc": "rustc fixture", "command": qx_run_verified.LOCKED_BUILD_COMMAND}
        receipt_path = root / "engine/target/build-receipt.json"
        runtime.atomic_json(receipt_path, build_receipt)
        return lane, binary, report_path, receipt_path

    def test_stale_binary_fails_before_engine_or_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, binary, _, _ = self.fixture(root)
            binary.write_text("replaced after its build receipt\n")
            with mock.patch.object(qx_run_verified, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "does not match its build receipt"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            self.assertFalse((root / "called.txt").exists())
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_changed_engine_source_fails_before_engine_or_registry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            (root / "engine/src/main.rs").write_text("// changed after build receipt\n")
            with mock.patch.object(qx_run_verified, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "build receipt is stale"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            self.assertFalse((root / "called.txt").exists())
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_matching_build_runs_and_links_receipt_to_registered_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, binary, report_fixture, build_receipt = self.fixture(root)
            with mock.patch.object(qx_run_verified, "ROOT", root), \
                    mock.patch.object(orchestrate_forward, "code_version", return_value={}), \
                    mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(qx_run_verified.main([str(lane.relative_to(root)), "--register"]), 0)

            self.assertEqual((root / "called.txt").read_text(), f"events {lane / 'spec.toml'}")
            receipts = list((lane / "results/run_receipts").glob("*.json"))
            self.assertEqual(len(receipts), 1)
            path = receipts[0]
            receipt = json.loads(path.read_text())
            self.assertEqual(receipt["status"], "SUCCESS")
            self.assertEqual(receipt["prereg_sha256"], qx_run_verified.prereg.verify(lane / "PREREG.md"))
            self.assertEqual(receipt["binary_sha256"], runtime.digest(binary))
            self.assertEqual(receipt["execution_binary_sha256"], runtime.digest(binary))
            self.assertEqual(receipt["build_receipt_sha256"], runtime.digest(build_receipt))
            self.assertEqual(receipt["report_sha256"], runtime.digest(lane / "results/report.json"))
            self.assertEqual(receipt["summary_sha256"], runtime.digest(lane / "results/SUMMARY.md"))
            self.assertEqual(receipt["report_sha256"], runtime.digest(report_fixture))
            row = registry.rows(root / "registry/rounds.csv")[0]
            self.assertIn(f"{path.relative_to(root)} sha256={runtime.digest(path)}", row["notes"])


if __name__ == "__main__":
    unittest.main()
