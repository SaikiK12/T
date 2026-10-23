"""Build qx from the locked dependency graph and bind binary/source/toolchain.

Default prints a plan. --execute builds only, never runs a market lane. A new
external run directory preserves each attempt; the target receipt is derived.
Compiler flags/host ABI are not a fully hermetic build environment.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import runtime
from lab.operations import Task


def build(root, state_dir, run_id):
    root, state_dir = Path(root).resolve(), Path(state_dir).resolve()
    if state_dir.is_relative_to(root) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("external state directory and unique safe run ID required")
    directory = state_dir / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {"status": "RUNNING", "sources": runtime.engine_sources(root),
              "started_at": datetime.now(timezone.utc).isoformat(),
              "command": ["cargo", "build", "--locked", "--release", "--manifest-path", "engine/Cargo.toml",
                          "--target-dir", "engine/target"],
              "scope": "build source/binary identity, not historical result reproduction or hermetic compilation"}
    runtime.atomic_json(directory / "status.json", report)
    try:
        for tool in ("cargo", "rustc"):
            report[tool] = subprocess.check_output((tool, "--version"), text=True).strip()
        # Match the engine location used by the frozen qx_run.py, with one build writer.
        import fcntl
        fd = os.open(root / ".engine-build.lock", os.O_CREAT |
                                   os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = runtime.run_process(Task("ENGINE", tuple(report["command"]), timeout=900), root,
                                         directory / "build.log")
            if result["status"] != "SUCCESS":
                raise subprocess.CalledProcessError(result.get("returncode") or 1, report["command"])
            if runtime.engine_sources(root) != report["sources"]:
                raise ValueError("engine source changed during build")
            report.update(status="SUCCESS", binary_sha256=runtime.digest(root / "engine/target/release/qx"),
                          finished_at=datetime.now(timezone.utc).isoformat())
            runtime.atomic_json(root / "engine/target/build-receipt.json", report)
        finally:
            os.close(fd)
    except BaseException as error:
        report.update(status="FAILED", reason=type(error).__name__)
        raise
    finally:
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        runtime.atomic_json(directory / "status.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args(argv)
    if not args.execute:
        print(json.dumps({"action": "locked qx build only", "execute": False, "sources": runtime.engine_sources(ROOT)}))
        return 0
    if args.state_dir is None or args.run_id is None:
        parser.error("--execute requires --state-dir and --run-id")
    try:
        report = build(ROOT, args.state_dir, args.run_id)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(2, f"Build failed ({type(error).__name__}); inspect its external run receipt/log.\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
