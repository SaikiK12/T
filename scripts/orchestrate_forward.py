#!/usr/bin/env python3
"""Plan or run the existing paper collectors with explicit dependencies.

The default is an offline JSON plan: no collector, lock, status file or journal
is opened. To execute, supply --execute, an external --state-dir, and a unique
--run-id. For example, a scheduler can use::

    python scripts/orchestrate_forward.py --execute \
        --state-dir /workspace/paper-run-status --run-id 20261020T001200Z

Each run gets a new directory, process logs and an atomic status.json. Reusing
an ID is refused, including after failure or interruption; inspect the old run
and use a new ID for a new attempt. The legacy .forward.lock is shared. Existing
runners and their journals retain their own semantics and idempotency rules.
Notice collection and its three paper readers also share .notices.lock with
the five-minute notice loop. Each may wait up to 300 seconds before starting;
its process timeout starts only after acquisition. R278, R279 and R294 use
their respective nonblocking .xfund*.lock, matching the shell wrapper. A busy
lock reports BLOCKED, never a successful skipped task. The graph records these
lock requirements.
Unlike forward_all.sh, an upstream failure blocks mandatory descendants instead
of running every remaining command. Independent branches still run. The default
interpreter is the repository's .venv/bin/python; there is no system fallback.

SUCCESS means that a process exited zero, not that new, complete, executable or
on-time observations exist. This wrapper cannot strengthen a frozen verdict.
It does not place orders or add a new statistical decision.
"""

import argparse
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


# Compatibility imports keep existing callers on the same task types and graph.
sys.path.insert(0, str(ROOT))
from lab.operations import Requirement, Task, forward_tasks, SEED_SHA256  # noqa: E402
from lab import runtime  # noqa: E402


def interpreter(root, override=None):
    """Keep the venv invocation path: resolving its symlink can lose venv identity."""
    if override is None:
        path = Path(root).resolve() / ".venv/bin/python"
    elif os.sep in override:
        path = Path(override)
        if not path.is_absolute():
            path = Path(root).resolve() / path
    else:
        found = shutil.which(override)
        if found is None:
            raise ValueError(f"explicit interpreter is unavailable: {override}")
        path = Path(found)
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError(f"interpreter is missing or not executable: {path}; pass --python explicitly")
    return os.path.abspath(path)


def ordered_tasks(tasks, selected=None):
    """Validate the whole graph, then include selected mandatory ancestors."""
    tasks = tuple(tasks)
    by_name = {t.name: t for t in tasks}
    if len(by_name) != len(tasks) or not tasks:
        raise ValueError("task names must be unique and the graph nonempty")
    for t in tasks:
        if not _RUN_ID.fullmatch(t.name) or not t.argv or any(not isinstance(a, str) or not a for a in t.argv):
            raise ValueError("invalid task name or argv")
        if not math.isfinite(t.timeout) or t.timeout <= 0:
            raise ValueError("timeouts must be finite and positive")
        if not math.isfinite(t.lock_wait) or t.lock_wait < 0:
            raise ValueError("shared-lock waits must be finite and nonnegative")
        if any(c not in runtime.CHECKS for c in t.checks):
            raise ValueError("unknown observation check")
        if t.shared_lock is not None and not re.fullmatch(r"\.[A-Za-z0-9_-]+\.lock", t.shared_lock):
            raise ValueError("shared lock must be a root-local dot lock filename")
        if set(t.needs) & set(t.optional) or any(n not in by_name for n in t.needs + t.optional):
            raise ValueError("unknown or conflicting dependency")
        for f in t.files:
            if Path(f.path).is_absolute() or ".." in Path(f.path).parts:
                raise ValueError("required files must have root-relative paths")
            if f.sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}", f.sha256):
                raise ValueError("invalid required file digest")
    wanted = set(by_name if selected is None else selected)
    if not wanted or wanted - set(by_name):
        raise ValueError("selection must contain known tasks")

    def include(name):
        for dep in by_name[name].needs:
            if dep not in wanted:
                wanted.add(dep)
                include(dep)
    for name in tuple(wanted):
        include(name)
    order, visiting, done = [], set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError("dependency cycle")
        if name in done:
            return
        visiting.add(name)
        for dep in by_name[name].needs + by_name[name].optional:
            visit(dep)
        visiting.remove(name)
        done.add(name)
        if name in wanted:
            order.append(by_name[name])
    for t in tasks:
        visit(t.name)
    return tuple(order)


def code_version(root):
    """Hash tracked and non-ignored untracked code files, without environment values."""
    def git(*args):
        return subprocess.check_output(("git", "-C", str(root), *args), stderr=subprocess.PIPE)
    head = git("rev-parse", "HEAD").decode().strip()
    scope = ("lab", "scripts", "engine/src", "engine/Cargo.toml", "engine/Cargo.lock",
             "dashboard/index.html", "requirements-test.in", "requirements-test.lock", ".python-version", "rust-toolchain.toml")
    dirty = git("status", "--porcelain", "--untracked-files=all", "--", *scope).decode()
    paths = sorted(set(p for p in git("ls-files", "--cached", "--others", "--exclude-standard",
                                    "-z", "--", *scope).split(b"\0") if p))
    h = hashlib.sha256()
    for raw in paths:
        path = root / os.fsdecode(raw)
        if not path.resolve().is_relative_to(root):
            raise ValueError("tracked code resolves outside repository")
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"
        h.update(raw + b"\0" + digest.encode() + b"\0")
    wrapper_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {"commit": head, "code_sha256": h.hexdigest(), "code_files": len(paths),
            "dirty_code": dirty.splitlines(),
            "orchestrator_sha256": wrapper_sha}


def plan(tasks, root):
    nodes = []
    for t in tasks:
        nodes.append({"name": t.name, "argv": list(t.argv), "needs": list(t.needs),
                      "optional": list(t.optional), "timeout_seconds": t.timeout,
                      "shared_lock": {"path": t.shared_lock, "wait_seconds": t.lock_wait}
                                     if t.shared_lock else None,
                      "required_files": [{"path": f.path, "sha256": f.sha256} for f in t.files],
                      "checks": list(t.checks)})
    encoded = json.dumps(nodes, sort_keys=True, separators=(",", ":")).encode()
    return {"schema_version": 1, "root": str(root), "code": code_version(root),
            "graph_sha256": hashlib.sha256(encoded).hexdigest(), "tasks": nodes,
            "success_meaning": "process exit zero plus declared checks only; statistical eligibility unverified"}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_status(path, data, first=False):
    payload = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if first and path.exists():
        raise FileExistsError(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="."+path.name+".", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            f.write(payload)
        os.replace(temporary, path)
    finally:
        # This is our unfinished status snapshot, never a research journal.
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class SharedLockTimeout(TimeoutError):
    pass


@contextmanager
def shared_task_lock(task, root):
    """Match shared shell locks; wait time is separate from process timeout."""
    if task.shared_lock is None:
        yield 0.0
        return
    # Refuse symlinks: shared locks must identify the same root-local inode as the shell.
    fd = os.open(Path(root) / task.shared_lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    start = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = task.lock_wait - (time.monotonic() - start)
                if remaining <= 0:
                    raise SharedLockTimeout(f"shared lock {task.shared_lock} wait expired")
                time.sleep(min(.05, remaining))
        yield time.monotonic() - start
    finally:
        os.close(fd)


def run_process(task, root, log_path):
    """Never start a shared-lock task without acquiring its lock."""
    start = time.monotonic()
    try:
        with shared_task_lock(task, root) as waited:
            result = _run_process(task, root, log_path)
            if task.shared_lock:
                result["lock_wait_seconds"] = waited
            return result
    except SharedLockTimeout as exc:
        reason = str(exc)
        with log_path.open("xb") as log:
            log.write(f"Task not started: {reason}.\n".encode())
        return {"status": "BLOCKED", "returncode": None, "reason": reason,
                "lock_wait_seconds": time.monotonic() - start}


def _run_process(task, root, log_path):
    return runtime.run_process(task, root, log_path)


def run_tasks(tasks, root, state_dir, run_id, selected=None):
    """Execute a validated DAG sequentially; failures block only mandatory descendants."""
    root, state_dir = Path(root).resolve(), Path(state_dir).resolve()
    # The existing views consume this same run store, including our RUNNING
    # report. No second daemon or hand-maintained status inventory is needed.
    tasks = tuple(replace(t, argv=(*t.argv, "--jobs-state-dir", str(state_dir)))
                  if len(t.argv) > 1 and t.argv[1] in ("scripts/dashboard_data.py", "scripts/panel.py")
                  else t for t in tasks)
    tasks = ordered_tasks(tasks, selected)
    if not _RUN_ID.fullmatch(run_id):
        raise ValueError("run ID must be 1-80 letters, numbers, underscores or hyphens")
    if state_dir.is_relative_to(root):
        raise ValueError("status directory must be outside the repository")
    report = plan(tasks, root)
    report.update(run_id=run_id, started_at=utc_now(), finished_at=None, status="RUNNING")
    report["environment"] = runtime.environment(root)
    report["environment_scope"] = "orchestrator process; child package environments not independently verified"
    for node in report["tasks"]:
        node["status"] = "PENDING"
    by_name = {n["name"]: n for n in report["tasks"]}
    state_dir.mkdir(parents=True, exist_ok=True)
    run_dir = state_dir / run_id
    run_dir.mkdir()  # Never retry a run ID: processes may already have appended journals.
    status_path = run_dir / "status.json"
    try:
        write_status(status_path, report, first=True)
        with (root / ".forward.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                report["status"] = "BLOCKED"
                report["finished_at"] = utc_now()
                for node in report["tasks"]:
                    node.update(status="BLOCKED", reason="another forward tick holds .forward.lock")
                write_status(status_path, report)
                return report
            for task in tasks:
                node = by_name[task.name]
                blocked = [n for n in task.needs if by_name[n]["status"] != "SUCCESS"]
                node["optional_unavailable"] = [n for n in task.optional
                                                  if n not in by_name or by_name[n]["status"] != "SUCCESS"]
                try:
                    unchanged = code_version(root) == report["code"]
                    code_error = None
                except (OSError, ValueError, subprocess.CalledProcessError) as exc:
                    unchanged, code_error = False, type(exc).__name__
                if blocked:
                    node.update(status="BLOCKED", reason="mandatory upstream task failed", blocked_by=blocked)
                elif not unchanged:
                    node.update(status="BLOCKED", reason="code snapshot unavailable" if code_error
                                else "code changed since run snapshot")
                else:
                    invalid = []
                    for f in task.files:
                        path = root / f.path
                        if not path.resolve().is_relative_to(root) or not path.is_file():
                            invalid.append(f.path + ": missing or outside repository")
                        elif f.sha256 and hashlib.sha256(path.read_bytes()).hexdigest() != f.sha256:
                            invalid.append(f.path + ": SHA-256 mismatch")
                    if invalid:
                        node.update(status="BLOCKED", reason="required input unavailable", invalid_files=invalid)
                    else:
                        node["preflight"] = [runtime.check(c, root, phase="before") for c in task.checks]
                        if any(not r["usable"] for r in node["preflight"]):
                            node.update(status="BLOCKED", data_state="INCOMPLETE", reason="journal preflight failed; no writer started")
                            write_status(status_path, report)
                            continue
                        node.update(status="RUNNING", started_at=utc_now(), log=task.name + ".log")
                        write_status(status_path, report)
                        start = time.monotonic()
                        try:
                            node.update(run_process(task, root, run_dir / node["log"]))
                            node["observations"] = [runtime.check(c, root) for c in task.checks]
                            node["data_state"] = ("COMPLETE" if task.checks and
                                                  all(r["usable"] for r in node["observations"])
                                                  else "UNVERIFIED" if not task.checks else "INCOMPLETE")
                            if node["status"] == "SUCCESS" and node["data_state"] == "INCOMPLETE":
                                node.update(status="FAILED", reason="process exited zero but observation check failed")
                            after = code_version(root)
                            if after != report["code"]:
                                node.update(status="FAILED", reason="code changed during task", code_at_finish=after)
                        except OSError as exc:
                            node.update(status="FAILED", returncode=None, reason="process start or log error: " + str(exc))
                        except (ValueError, subprocess.CalledProcessError) as exc:
                            node.update(status="FAILED", reason="code snapshot unavailable after task: " + type(exc).__name__)
                        node.update(finished_at=utc_now(), elapsed_seconds=time.monotonic() - start)
                write_status(status_path, report)
        report.update(status="SUCCESS" if all(n["status"] == "SUCCESS" for n in by_name.values()) else "FAILED",
                      finished_at=utc_now())
        write_status(status_path, report)
        return report
    except KeyboardInterrupt:
        for node in report["tasks"]:
            if node["status"] == "RUNNING":
                node.update(status="FAILED", returncode=None, reason="orchestrator interrupted", finished_at=utc_now())
            elif node["status"] == "PENDING":
                node.update(status="BLOCKED", reason="orchestrator interrupted")
        report.update(status="INTERRUPTED", finished_at=utc_now())
        write_status(status_path, report)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--python", help="explicit interpreter override; default ROOT/.venv/bin/python must exist")
    parser.add_argument("--task", action="append", help="task ID; repeatable; includes mandatory ancestors")
    parser.add_argument("--execute", action="store_true", help="run collectors; default only prints an offline plan")
    parser.add_argument("--state-dir", type=Path, help="new run directories outside the repository")
    parser.add_argument("--run-id", help="unique scheduler tick ID; an existing ID is never rerun")
    args = parser.parse_args(argv)
    try:
        python = interpreter(args.root, args.python)
        tasks = ordered_tasks(forward_tasks(python), args.task)
        if args.execute:
            if args.state_dir is None or args.run_id is None:
                parser.error("--execute requires --state-dir and --run-id")
            # Scheduler termination must kill our child group and release the shared lock.
            def terminate(_signum, _frame):
                raise KeyboardInterrupt
            previous = signal.signal(signal.SIGTERM, terminate)
            try:
                report = run_tasks(forward_tasks(python), args.root, args.state_dir, args.run_id, args.task)
            finally:
                signal.signal(signal.SIGTERM, previous)
        else:
            report = plan(tasks, args.root.resolve())
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0 if report.get("status", "SUCCESS") == "SUCCESS" else 1
    except KeyboardInterrupt:
        print("Orchestration interrupted; inspect the run's status before starting a new ID.", file=sys.stderr)
        return 130
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
