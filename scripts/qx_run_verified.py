"""Run a qx lane only with a source-matched build, then retain an immutable run receipt.

This is the versioned runner for new qx lanes. Existing frozen preregistrations that hash
``scripts/qx_run.py`` keep using their original runner. A new lane hashes both runners,
this wrapper, ``scripts/build_engine.py``, and every Rust build input in its PREREG.
The build receipt ties the copied executable to Cargo inputs/toolchain; the run receipt
ties that exact executable to frozen lane inputs, report, summary, and any registry note.
It does not make compilation hermetic or upgrade a historical result.

usage: python scripts/qx_run_verified.py experiments/<lane> [--register]
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import tomllib
import uuid

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, runtime  # noqa: E402
from scripts import qx_run  # noqa: E402

REQUIRED_INPUTS = {
    "scripts/qx_run.py",
    "scripts/qx_run_verified.py",
    "scripts/build_engine.py",
}
LOCKED_BUILD_COMMAND = ["cargo", "build", "--locked", "--release", "--manifest-path", "engine/Cargo.toml",
                        "--target-dir", "engine/target"]


def verify_build(root):
    """Fail closed unless a current receipt binds the exact engine sources to qx bytes."""
    root = Path(root).resolve()
    binary = root / "engine/target/release/qx"
    receipt_path = root / "engine/target/build-receipt.json"
    if binary.is_symlink() or receipt_path.is_symlink() or not binary.is_file() or not receipt_path.is_file():
        raise ValueError("verified qx binary and build receipt are required; build with scripts/build_engine.py")
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("qx build receipt is unreadable") from exc
    sources = runtime.engine_sources(root)
    if receipt.get("status") != "SUCCESS" or receipt.get("sources") != sources:
        raise ValueError("qx build receipt is stale or unsuccessful; rebuild with scripts/build_engine.py")
    if receipt.get("command") != LOCKED_BUILD_COMMAND or not receipt.get("cargo") or not receipt.get("rustc"):
        raise ValueError("qx build receipt does not describe the locked Cargo build")
    binary_sha = runtime.digest(binary)
    if receipt.get("binary_sha256") != binary_sha:
        raise ValueError("qx binary does not match its build receipt; rebuild with scripts/build_engine.py")
    return {"receipt": receipt, "receipt_sha256": runtime.digest(receipt_path),
            "binary": binary, "binary_sha256": binary_sha, "sources": sources}


def _input_snapshot(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return None
    st = path.stat()
    return st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns, runtime.digest(path)


def _snapshot_changed(path, before):
    after = _input_snapshot(path)
    return after is not None and after != before


def _write_receipt(lane, run_id, value):
    directory = Path(lane) / "results" / "run_receipts"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run_id}.json"
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    runtime.atomic_json(path, value)
    return path


def _assert_no_symlink(root, path):
    root, path = Path(root).resolve(), Path(path)
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path leaves repository: {path}")
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError(f"symlink in qx lane path: {cursor}")
        cursor = cursor.parent


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lane")
    parser.add_argument("--register", action="store_true")
    args = parser.parse_args(argv)

    root = Path(ROOT).resolve()
    lane_arg = root / args.lane
    try:
        _assert_no_symlink(root, lane_arg)
    except ValueError as exc:
        parser.error(str(exc))
    lane = lane_arg.resolve()
    if not lane.is_dir():
        parser.error("lane must be an ordinary directory inside the repository")
    prereg_path = lane / "PREREG.md"
    prereg_sha = prereg.verify(prereg_path)
    prereg_text = prereg_path.read_text()
    frozen_inputs, _ = qx_run.inputs(prereg_text)
    missing = REQUIRED_INPUTS - frozen_inputs.keys()
    if missing:
        raise SystemExit("new verified qx lanes must freeze inputs: " + ", ".join(sorted(missing)))
    spec_rel = str((lane / "spec.toml").relative_to(root))
    if spec_rel not in frozen_inputs:
        raise SystemExit("new verified qx lanes must freeze spec.toml")
    spec = tomllib.loads((lane / "spec.toml").read_text())
    kind = "spread" if "sets" in spec else "factors" if "factors" in spec else "events"

    build = verify_build(root)
    for path, digest in build["sources"].items():
        if frozen_inputs.get(path) != digest:
            raise SystemExit(f"PREREG must freeze current qx build input {path} {digest}")

    # Copy the receipt-matched binary to a private temporary path. If another build
    # replaces engine/target after preflight, the run still executes these exact bytes.
    with tempfile.TemporaryDirectory(prefix="qx-verified-") as temporary:
        executable = Path(temporary) / "qx"
        shutil.copyfile(build["binary"], executable)
        os.chmod(executable, stat.S_IMODE(build["binary"].stat().st_mode))
        if runtime.digest(executable) != build["binary_sha256"]:
            raise ValueError("private qx execution copy differs from the verified binary")
        if runtime.engine_sources(root) != build["sources"]:
            raise ValueError("qx source changed after build verification")

        out = lane / "results"
        _assert_no_symlink(root, out)
        _assert_no_symlink(root, lane / "run.log")
        report_path, summary_path = out / "report.json", out / "SUMMARY.md"
        before_report, before_summary = _input_snapshot(report_path), _input_snapshot(summary_path)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
        started_at = datetime.now(timezone.utc).isoformat()
        receipt_path = None

        def make_receipt(status, error=None):
            if status == "SUCCESS":
                if not _snapshot_changed(report_path, before_report):
                    raise ValueError("qx report was not freshly written by this run")
                if not _snapshot_changed(summary_path, before_summary):
                    raise ValueError("qx summary was not freshly written by this run")
            return {
                "receipt_version": 1,
                "run_id": run_id,
                "status": status,
                "error": error,
                "started_at": started_at,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "lane": str(lane.relative_to(root)),
                "prereg_sha256": prereg_sha,
                "frozen_inputs": frozen_inputs,
                "engine_sources": build["sources"],
                "build_receipt": build["receipt"],
                "build_receipt_sha256": build["receipt_sha256"],
                "binary_sha256": build["binary_sha256"],
                "execution_binary_sha256": runtime.digest(executable),
                "engine_command": [str(executable), kind, str(lane / "spec.toml")],
                "report_sha256": runtime.digest(report_path) if report_path.is_file() else None,
                "summary_sha256": runtime.digest(summary_path) if summary_path.is_file() else None,
                "register_requested": args.register,
                "scope": "source/build/output identity; compilation host flags and ABI are not hermetic",
            }

        original_append = qx_run.registry.append
        append_called = False

        def append_with_receipt(path, /, id=None, **fields):
            nonlocal append_called, receipt_path
            value = make_receipt("SUCCESS")
            _assert_no_symlink(root, out / "run_receipts")
            receipt_path = _write_receipt(lane, run_id, value)
            receipt_sha = runtime.digest(receipt_path)
            note = fields.get("notes", "")
            fields["notes"] = f"{note}; verified run receipt {receipt_path.relative_to(root)} sha256={receipt_sha}"
            result = original_append(path, id=id, **fields)
            append_called = True
            return result

        old_root, old_binary, old_argv = qx_run.ROOT, qx_run.QX, sys.argv
        old_append = qx_run.registry.append
        try:
            qx_run.ROOT = root
            qx_run.QX = executable
            if args.register:
                qx_run.registry.append = append_with_receipt
            sys.argv = ["qx_run.py", str(lane.relative_to(root))] + (["--register"] if args.register else [])
            qx_run.main()
            if not append_called:
                _assert_no_symlink(root, out / "run_receipts")
                receipt_path = _write_receipt(lane, run_id, make_receipt("SUCCESS"))
        except BaseException as exc:
            if receipt_path is None:
                try:
                    _assert_no_symlink(root, out / "run_receipts")
                    receipt_path = _write_receipt(lane, run_id, make_receipt("FAILED", f"{type(exc).__name__}: {exc}"))
                except (OSError, ValueError):
                    pass
            raise
        finally:
            sys.argv = old_argv
            qx_run.ROOT, qx_run.QX, qx_run.registry.append = old_root, old_binary, old_append

    print(f"verified qx run receipt {receipt_path.relative_to(root)} sha256={runtime.digest(receipt_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
