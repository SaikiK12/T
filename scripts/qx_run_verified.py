"""Run a qx lane only with a source-matched build, then retain an immutable run receipt.

This is the versioned runner for new qx lanes. Existing frozen preregistrations that hash
``scripts/qx_run.py`` keep using their original runner. A new lane hashes both runners,
this wrapper, ``scripts/build_engine.py``, every Rust build input, direct spec files, and
the provenance manifests for every data folder named by the spec. The runner verifies
those folder manifests before and after the run and permits only one writer per lane.
The build receipt ties the copied executable to Cargo inputs/toolchain; the run receipt
ties that executable identity to frozen lane inputs, report, summary, and any registry note.
The executable is not archived, and compilation is not hermetic.

usage: python scripts/qx_run_verified.py experiments/<lane> [--register]
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
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
SPEC_FILE_INPUTS = ("events", "factors", "symbols", "reserved_prereg")
SPEC_DATA_DIRS = ("prices", "klines", "funding")


def verify_build(root):
    """Fail closed unless a current receipt binds the exact engine sources to qx bytes."""
    root = Path(root).resolve()
    binary = root / "engine/target/release/qx"
    receipt_path = root / "engine/target/build-receipt.json"
    for path in (binary, receipt_path):
        _assert_no_symlink(root, path)
    if not binary.is_file() or not receipt_path.is_file():
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


def _safe_spec_path(value, label):
    if not isinstance(value, str) or not value.strip() or "\\" in value:
        raise ValueError(f"spec {label} must be a nonempty repository-relative path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"spec {label} leaves the repository or data root")
    return path.as_posix()


def _spec_inputs(spec):
    """List the direct files and data folders that qx can read from its TOML spec."""
    files, folders = set(), set()
    for key in SPEC_FILE_INPUTS:
        value = spec.get(key)
        if value is not None:
            files.add(_safe_spec_path(value, key))
    for key in SPEC_DATA_DIRS:
        value = spec.get(key)
        if value is not None:
            folders.add(_safe_spec_path(value, key))
    venues = spec.get("venues", [])
    if not isinstance(venues, list):
        raise ValueError("spec venues must be an array of tables")
    for i, venue in enumerate(venues):
        if not isinstance(venue, dict):
            raise ValueError(f"spec venues[{i}] must be a table")
        for key in SPEC_DATA_DIRS:
            value = venue.get(key)
            if value is not None:
                folders.add(_safe_spec_path(value, f"venues[{i}].{key}"))
    if not files and not folders:
        raise ValueError("spec declares no frozen data inputs")
    return sorted(files), sorted(folders)


def _manifest_snapshot(root, manifest_path, manifest):
    """Verify a frozen data-provenance document against every current file in its folder."""
    folder_text = manifest.get("folder")
    if not isinstance(folder_text, str):
        raise ValueError(f"data manifest has no folder: {manifest_path}")
    folder_rel = _safe_spec_path(folder_text, "data manifest folder")
    if not folder_rel.startswith("data/"):
        raise ValueError(f"data manifest folder must be inside data/: {folder_rel}")
    folder = root / folder_rel
    _assert_no_symlink(root, folder)
    if not folder.is_dir():
        raise ValueError(f"data folder is missing: {folder_rel}")

    excluded = manifest.get("excluded", [])
    if not isinstance(excluded, list) or any(not isinstance(x, str) for x in excluded):
        raise ValueError(f"invalid data manifest exclusions: {manifest_path}")
    skip = tuple(x.rstrip("/") + "/" for x in excluded)
    paths = []
    for path in folder.rglob("*"):
        rel = path.relative_to(folder).as_posix()
        if rel.startswith(skip):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in frozen data folder: {folder_rel}/{rel}")
        if path.is_file():
            paths.append(path)

    records, total, combined, stat_combined = [], 0, hashlib.sha256(), hashlib.sha256()
    for path in sorted(paths):
        rel = path.relative_to(folder).as_posix()
        before = path.stat()
        sha = runtime.digest(path)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != \
                (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f"data input changed while hashing: {folder_rel}/{rel}")
        records.append({"path": rel, "bytes": after.st_size, "sha256": sha})
        total += after.st_size
        combined.update(f"{rel}\t{sha}\n".encode())
        stat_combined.update(f"{rel}\t{after.st_ino}\t{after.st_size}\t{after.st_mtime_ns}\t{after.st_ctime_ns}\n".encode())

    if records != manifest.get("file_hashes") or len(records) != manifest.get("files") or \
            total != manifest.get("bytes") or combined.hexdigest() != manifest.get("combined_sha256"):
        raise ValueError(f"data folder differs from its frozen provenance: {folder_rel}")
    return {"manifest": str(manifest_path.relative_to(root)),
            "manifest_sha256": runtime.digest(manifest_path), "folder": folder_rel,
            "files": len(records), "bytes": total, "combined_sha256": combined.hexdigest(),
            "file_state_sha256": stat_combined.hexdigest()}


def verify_spec_inputs(root, spec, frozen_inputs):
    """Require every direct spec file and each referenced dataset folder to be frozen and source-matched."""
    root = Path(root).resolve()
    files, folders = _spec_inputs(spec)
    for rel in files:
        path = root / rel
        _assert_no_symlink(root, path)
        if not path.is_file() or rel not in frozen_inputs:
            raise ValueError(f"spec file input must exist and be frozen in PREREG: {rel}")
        actual = runtime.digest(path)
        if actual != frozen_inputs[rel]:
            raise ValueError(f"spec file input differs from frozen PREREG: {rel}")

    provenance = {}
    for rel in frozen_inputs:
        if not rel.startswith("docs/provenance/") or not rel.endswith(".json"):
            continue
        path = root / rel
        _assert_no_symlink(root, path)
        if not path.is_file() or runtime.digest(path) != frozen_inputs[rel]:
            raise ValueError(f"data provenance file differs from frozen PREREG: {rel}")
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"data provenance file is unreadable: {rel}") from exc
        folder = record.get("folder") if isinstance(record, dict) else None
        if isinstance(folder, str):
            folder = _safe_spec_path(folder, f"{rel} folder")
            if not folder.startswith("data/"):
                raise ValueError(f"data provenance folder must be inside data/: {folder}")
            provenance[folder] = (path, record)

    snapshots = {}
    for ref in folders:
        data_path = root / "data" / ref
        _assert_no_symlink(root, data_path)
        if not data_path.is_dir():
            raise ValueError(f"spec data folder is missing: data/{ref}")
        matches = [(folder, path, record) for folder, (path, record) in provenance.items()
                   if (root / folder).is_dir() and data_path.is_relative_to(root / folder)]
        if not matches:
            raise ValueError(f"spec data folder has no frozen docs/provenance record: data/{ref}")
        folder, manifest_path, record = max(matches, key=lambda item: len(item[0]))
        if folder in snapshots:
            continue
        digest_path = manifest_path.relative_to(root).as_posix()
        if digest_path not in frozen_inputs:
            raise ValueError(f"data provenance file must be frozen in PREREG: {digest_path}")
        snapshots[folder] = _manifest_snapshot(root, manifest_path, record)
    return {key: snapshots[key] for key in sorted(snapshots)}


def verify_frozen_files(root, frozen_inputs):
    """Check every file named in the prereg block, including once more after execution."""
    root = Path(root).resolve()
    for rel, expected in frozen_inputs.items():
        path = root / rel
        _assert_no_symlink(root, path)
        if not path.is_file() or runtime.digest(path) != expected:
            raise ValueError(f"frozen input changed during qx run: {rel}")


def _git_directory(root):
    dotgit = Path(root) / ".git"
    if dotgit.is_symlink():
        raise ValueError("refusing symlinked .git metadata")
    if dotgit.is_dir():
        return dotgit.resolve()
    if not dotgit.is_file():
        raise ValueError("verified qx lane lock requires a Git worktree")
    text = dotgit.read_text().strip()
    if not text.startswith("gitdir: "):
        raise ValueError("unrecognized Git worktree metadata")
    target = Path(text[len("gitdir: "):])
    if not target.is_absolute():
        target = dotgit.parent / target
    target = target.resolve()
    if not target.is_dir():
        raise ValueError("Git worktree metadata points to a missing git directory")
    return target


@contextmanager
def lane_lock(root, lane):
    """Fail fast when another verified runner is mutating this lane's output paths."""
    root, lane = Path(root).resolve(), Path(lane).resolve()
    git_dir = _git_directory(root)
    lock_dir = git_dir / "qx-run-locks"
    if lock_dir.is_symlink():
        raise ValueError("refusing symlinked qx lock directory")
    lock_dir.mkdir(mode=0o700, exist_ok=True)
    key = hashlib.sha256(str(lane.relative_to(root)).encode()).hexdigest()
    lock_path = lock_dir / f"{key}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"verified qx lane is already running: {lane.relative_to(root)}") from exc
        yield
    finally:
        os.close(fd)


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
    with lane_lock(root, lane):
        return _run_lane(root, lane, args)


def _run_lane(root, lane, args):
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
    if runtime.digest(lane / "spec.toml") != frozen_inputs[spec_rel]:
        raise SystemExit("spec.toml differs from its frozen PREREG input")
    spec = tomllib.loads((lane / "spec.toml").read_text())
    kind = "spread" if "sets" in spec else "factors" if "factors" in spec else "events"
    data_sources = verify_spec_inputs(root, spec, frozen_inputs)

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
                verify_frozen_files(root, frozen_inputs)
                if runtime.digest(lane / "spec.toml") != frozen_inputs[spec_rel]:
                    raise ValueError("spec.toml changed during qx run")
                if verify_spec_inputs(root, spec, frozen_inputs) != data_sources:
                    raise ValueError("data source snapshot changed during qx run")
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
                "engine_invocation": ["qx", kind, spec_rel],
                "binary_archived": False,
                "data_sources": data_sources,
                "report_sha256": runtime.digest(report_path) if report_path.is_file() else None,
                "summary_sha256": runtime.digest(summary_path) if summary_path.is_file() else None,
                "register_requested": args.register,
                "scope": "Source and data identity; the binary itself is not archived, and compilation host flags and ABI are not hermetic.",
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
