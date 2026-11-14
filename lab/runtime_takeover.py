"""Durable operational state and honest task health for the Codex paper-lab takeover."""
from datetime import datetime, timezone
from contextlib import contextmanager
import fcntl
import csv
import io
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys


@contextmanager
def single_writer(root):
    """Share the legacy forward lock before restoring or touching live journals."""
    with (Path(root)/".forward.lock").open("a") as f:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def admitted(path, prefixes):
    p = PurePosixPath(path)
    return (not p.is_absolute() and ".." not in p.parts and "\\" not in path
            and any(path.startswith(s+"/") for s in prefixes))


def safe(root, name):
    p = Path(root)/name
    if not p.resolve().is_relative_to(Path(root).resolve()) or any(x.is_symlink() for x in (p, *p.parents)):
        raise ValueError("unsafe operational path: "+name)
    return p


def restore(root, state, config, frozen):
    """Only a manifested canonical snapshot; missing/corrupt state never resets budgets."""
    root, state = Path(root), Path(state)
    manifest = json.loads((state/"manifest.json").read_text())
    if manifest["schema"] != 1 or manifest["owner"] != "github-actions":
        raise ValueError("unrecognized canonical writer state")
    checked = []
    for name, record in manifest["files"].items():
        wanted = record["sha256"]
        if not admitted(name, config["state_prefixes"]) or name in frozen:
            raise ValueError("state cannot replace code/frozen inputs: "+name)
        source, dest = safe(state/"state", name), safe(root, name)
        if not source.is_file() or digest(source) != wanted:
            raise ValueError("canonical state hash mismatch: "+name)
        raw = source.read_bytes()
        if name.endswith((".csv", ".jsonl")) and raw:
            if not raw.endswith(b"\n"):
                raise ValueError("cut journal requires reconciliation: "+name)
            if name.endswith(".jsonl"):
                for line in raw.decode().splitlines():
                    json.loads(line)
            else:
                rows = list(csv.reader(io.StringIO(raw.decode(), newline=""), strict=True))
                if any(row and len(row) != len(rows[0]) for row in rows[1:]):
                    raise ValueError("cut CSV row requires reconciliation: "+name)
        if type(record["mtime_ns"]) is not int or record["mtime_ns"] < 0:
            raise ValueError("invalid source mtime")
        if dest.exists() and dest.read_bytes() != source.read_bytes():
            immutable = name.startswith("data/recorders/") and not name.endswith(("requests.jsonl", "denials.jsonl", "budget.lock"))
            append_only = name.endswith(".jsonl") or (name.endswith(".csv") and not name.endswith(("statement.csv", "book_days.csv")))
            if immutable or (append_only and not source.read_bytes().startswith(dest.read_bytes())):
                raise ValueError("journal/raw state diverged; manual reconciliation required: "+name)
        checked.append((source, dest, record))
    for source, dest, record in checked:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        import os
        os.utime(dest, ns=(record["mtime_ns"], record["mtime_ns"]))
    return manifest


def snapshot(root, state, config, *, report):
    """Copy without deleting earlier files. Market journals are never generated here."""
    root, state = Path(root), Path(state)
    previous = json.loads((state/"manifest.json").read_text())
    files = dict(previous["files"])
    total = 0
    for prefix in config["state_prefixes"]:
        base = safe(root, prefix)
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.is_symlink():
                raise ValueError("state symlink refused")
            if not p.is_file() or p.name.endswith(".lock"):
                continue
            name = p.relative_to(root).as_posix()
            total += p.stat().st_size
            if total > config["max_stored_bytes"]:
                raise ValueError("operational state cap exceeded; data retained locally")
            dest = safe(state/"state", name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            files[name] = dict(sha256=digest(p), mtime_ns=p.stat().st_mtime_ns)
    previous.update(files=files, bootstrap=False, updated_utc=datetime.now(timezone.utc).isoformat(), last_report=report)
    (state/"manifest.json").write_text(json.dumps(previous, indent=2, sort_keys=True)+"\n")
    return previous


def health(root, lanes, now=None):
    now = now or datetime.now(timezone.utc)
    rows = []
    for rid, lane in lanes.items():
        p = Path(root)/"experiments"/lane/"journal/status.json"
        row = dict(rid=rid, path=str(p.relative_to(root)), status="MISSING", hours_old=None)
        if p.exists():
            obj = json.loads(p.read_text())
            stamp = obj.get("updated") or obj.get("updated_at")
            row["source_updated"] = stamp
            if isinstance(stamp, str):
                try:
                    age = (now-datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds()/3600
                    row.update(hours_old=round(age, 2), status="FRESH" if 0 <= age <= 3 else "STALE_OR_CLOCK")
                except (TypeError, ValueError):
                    row["status"] = "UNKNOWN_CLOCK"
            else:
                row["status"] = "UNKNOWN_CLOCK"
        rows.append(row)
    return rows


def run_child(root, script, args, policy_name, log, timeout, invoke):
    cmd = [sys.executable, str(Path(root)/"scripts/quant_runtime.py"), "child", script, policy_name, "--", *args]
    with Path(log).open("x") as out:
        try:
            result = invoke(cmd, cwd=root, stdout=out, stderr=subprocess.STDOUT, timeout=timeout, check=False)
            return dict(state="PROCESS_OK" if result.returncode == 0 else "FAILED", returncode=result.returncode)
        except subprocess.TimeoutExpired:
            # subprocess.run kills only the child it started; no foreign process is touched.
            return dict(state="FAILED_TIMEOUT")
