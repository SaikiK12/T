import io
import json
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest import mock

from lab import prereg, registry, runtime
from scripts import orchestrate_forward, qx_run_verified


class VerifiedQxRunnerTests(unittest.TestCase):
    def fixture(self, root, mutate_data_during_run=False):
        root = Path(root)
        lane = root / "experiments" / "fixture"
        lane.mkdir(parents=True)
        for directory in (root / "engine/src", root / "engine/target/release", root / "scripts", root / "registry",
                          root / ".git", root / "data/synthetic/quotes", root / "data/synthetic/funds",
                          root / "docs/provenance"):
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
        mutate = (f"pathlib.Path({str(root / 'data/synthetic/quotes/BTCUSDT.parquet')!r})"
                  ".write_bytes(b'changed during execution')\n" if mutate_data_during_run else "")
        binary.write_text(
            f"#!{sys.executable}\n"
            "import pathlib,sys\n"
            f"source=pathlib.Path({str(report_path)!r})\n"
            "spec=pathlib.Path(sys.argv[2])\n"
            "out=spec.parent/'results'/'report.json'\n"
            "out.parent.mkdir(exist_ok=True)\n"
            "out.write_bytes(source.read_bytes())\n"
            f"{mutate}"
            f"pathlib.Path({str(root / 'called.txt')!r}).write_text(' '.join(sys.argv[1:]))\n"
        )
        binary.chmod(0o755)

        events = lane / "legs.csv"
        events.write_text("release_ms,kind,perp\n0,test,BTCUSDT\n")
        (root / "data/synthetic/quotes/BTCUSDT.parquet").write_bytes(b"synthetic quote input")
        (root / "data/synthetic/funds/BTCUSDT.parquet").write_bytes(b"synthetic funding input")
        source_rows, total, combined = [], 0, hashlib.sha256()
        for path in sorted((root / "data/synthetic").rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root / "data/synthetic").as_posix()
            digest = runtime.digest(path)
            size = path.stat().st_size
            source_rows.append({"path": rel, "bytes": size, "sha256": digest})
            total += size
            combined.update(f"{rel}\t{digest}\n".encode())
        manifest_path = root / "docs/provenance/synthetic.json"
        runtime.atomic_json(manifest_path, {"folder": "data/synthetic", "excluded": [], "files": len(source_rows),
                                            "bytes": total, "combined_sha256": combined.hexdigest(),
                                            "file_hashes": source_rows})

        spec = lane / "spec.toml"
        spec.write_text('events = "experiments/fixture/legs.csv"\n'
                        'venues = [{name="perp", col="perp", klines="synthetic/quotes", '
                        'funding="synthetic/funds"}]\n'
                        'costs = [0.001, 0.002, 0.003]\n')
        paths = [events, manifest_path, spec, root / "scripts/qx_run.py", root / "scripts/qx_run_verified.py",
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

    def test_changed_data_file_fails_manifest_check_before_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            (root / "data/synthetic/quotes/BTCUSDT.parquet").write_bytes(b"changed quote input")
            with mock.patch.object(qx_run_verified, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "differs from its frozen provenance"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            self.assertFalse((root / "called.txt").exists())
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_data_change_during_run_cannot_get_success_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root, mutate_data_during_run=True)
            with mock.patch.object(qx_run_verified, "ROOT", root), \
                    mock.patch.object(orchestrate_forward, "code_version", return_value={}), \
                    mock.patch("sys.stdout", new=io.StringIO()):
                with self.assertRaisesRegex(ValueError, "differs from its frozen provenance"):
                    qx_run_verified.main([str(lane.relative_to(root))])
            receipts = list((lane / "results/run_receipts").glob("*.json"))
            self.assertEqual(len(receipts), 1)
            self.assertEqual(json.loads(receipts[0].read_text())["status"], "FAILED")
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_spec_file_must_be_explicitly_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            prereg_path = lane / "PREREG.md"
            text = prereg_path.read_text()
            text = text.replace(f"{lane.relative_to(root)}/legs.csv  {runtime.digest(lane / 'legs.csv')}\n", "")
            prereg_path.write_text(text)
            (lane / "PREREG.sha256").unlink()
            prereg.freeze(prereg_path)
            with mock.patch.object(qx_run_verified, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "must exist and be frozen in PREREG"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            self.assertFalse((root / "called.txt").exists())
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_same_lane_lock_rejects_concurrent_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            with qx_run_verified.lane_lock(root, lane):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with qx_run_verified.lane_lock(root, lane):
                        self.fail("second lane writer acquired the lock")

    def test_build_rejects_symlinked_parent_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            _, _, _, _ = self.fixture(root)
            target = root / "engine/target"
            real_target = root / "engine/target-real"
            target.rename(real_target)
            target.symlink_to(real_target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink in qx lane path"):
                qx_run_verified.verify_build(root)

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
            self.assertIn("calculation and output verification only", receipt["status_meaning"])
            self.assertEqual(receipt["prereg_sha256"], qx_run_verified.prereg.verify(lane / "PREREG.md"))
            self.assertEqual(receipt["binary_sha256"], runtime.digest(binary))
            self.assertEqual(receipt["execution_binary_sha256"], runtime.digest(binary))
            self.assertEqual(receipt["engine_invocation"], ["qx", "events", "experiments/fixture/spec.toml"])
            self.assertFalse(receipt["binary_archived"])
            self.assertEqual(receipt["data_sources"]["data/synthetic"]["combined_sha256"],
                             json.loads((root / "docs/provenance/synthetic.json").read_text())["combined_sha256"])
            self.assertEqual(receipt["build_receipt_sha256"], runtime.digest(build_receipt))
            self.assertEqual(receipt["report_sha256"], runtime.digest(lane / "results/report.json"))
            self.assertEqual(receipt["summary_sha256"], runtime.digest(lane / "results/SUMMARY.md"))
            self.assertEqual(receipt["report_sha256"], runtime.digest(report_fixture))
            row = registry.rows(root / "registry/rounds.csv")[0]
            self.assertIn(f"verified calculation receipt {path.relative_to(root)} sha256={runtime.digest(path)}",
                          row["notes"])
            registration_files = sorted((lane / "results/registration_receipts").glob("*.json"))
            attempts = [json.loads(p.read_text()) for p in registration_files if p.name.endswith(".attempt.json")]
            outcomes = [json.loads(p.read_text()) for p in registration_files if p.name.endswith(".outcome.json")]
            self.assertEqual([r["status"] for r in attempts], ["ATTEMPTED"])
            self.assertEqual([r["status"] for r in outcomes], ["REGISTERED"])
            self.assertEqual(outcomes[0]["calculation_receipt_sha256"], runtime.digest(path))
            self.assertEqual(outcomes[0]["registry_id"], "R999999")
            self.assertEqual(outcomes[0]["registry_row_sha256"], hashlib.sha256(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest())

    def test_duplicate_registry_id_keeps_calculation_and_failed_registration_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            with mock.patch.object(qx_run_verified, "ROOT", root), \
                    mock.patch.object(orchestrate_forward, "code_version", return_value={}), \
                    mock.patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(qx_run_verified.main([str(lane.relative_to(root)), "--register"]), 0)
                with self.assertRaisesRegex(registry.RegistryError, "already used"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])

            calculations = [json.loads(p.read_text()) for p in (lane / "results/run_receipts").glob("*.json")]
            registrations = [json.loads(p.read_text()) for p in (lane / "results/registration_receipts").glob("*.outcome.json")]
            self.assertEqual(len(calculations), 2)
            self.assertEqual([r["status"] for r in calculations], ["SUCCESS", "SUCCESS"])
            self.assertEqual(sorted(r["status"] for r in registrations), ["FAILED", "REGISTERED"])
            failed = next(r for r in registrations if r["status"] == "FAILED")
            self.assertIn("already used", failed["error"])
            self.assertEqual(len(registry.rows(root / "registry/rounds.csv")), 1)

    def test_registry_append_failure_gets_explicit_failed_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            with mock.patch.object(qx_run_verified, "ROOT", root), \
                    mock.patch.object(orchestrate_forward, "code_version", return_value={}), \
                    mock.patch.object(registry, "append", side_effect=registry.RegistryError("injected append failure")), \
                    mock.patch("sys.stdout", new=io.StringIO()):
                with self.assertRaisesRegex(registry.RegistryError, "injected append failure"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            outcomes = [json.loads(p.read_text()) for p in (lane / "results/registration_receipts").glob("*.outcome.json")]
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["status"], "FAILED")
            self.assertIn("injected append failure", outcomes[0]["error"])
            self.assertFalse((root / "registry/rounds.csv").exists())

    def test_append_that_writes_then_raises_is_reconciled_as_registered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            lane, _, _, _ = self.fixture(root)
            real_append = registry.append

            def append_then_raise(path, /, id=None, **fields):
                real_append(path, id=id, **fields)
                raise OSError("post-append cleanup failed")

            with mock.patch.object(qx_run_verified, "ROOT", root), \
                    mock.patch.object(orchestrate_forward, "code_version", return_value={}), \
                    mock.patch.object(registry, "append", side_effect=append_then_raise), \
                    mock.patch("sys.stdout", new=io.StringIO()):
                with self.assertRaisesRegex(OSError, "post-append cleanup failed"):
                    qx_run_verified.main([str(lane.relative_to(root)), "--register"])
            outcomes = [json.loads(p.read_text()) for p in (lane / "results/registration_receipts").glob("*.outcome.json")]
            self.assertEqual(len(outcomes), 1)
            self.assertEqual(outcomes[0]["status"], "REGISTERED")
            self.assertIn("post-append cleanup failed", outcomes[0]["error"])
            row = registry.rows(root / "registry/rounds.csv")[0]
            self.assertIn(outcomes[0]["calculation_receipt_sha256"], row["notes"])


if __name__ == "__main__":
    unittest.main()
