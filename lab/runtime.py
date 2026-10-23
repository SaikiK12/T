"""Offline execution receipts and fail-closed checks around legacy paper writers.

No repairs, market requests, environment values or statistical decisions. A
complete receipt certifies only its named structural checks at that instant.
"""
import csv
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile

HOUR = 3_600_000
FUNDING_VENUES = ("gate", "hyperliquid", "okx", "bitget", "kucoin", "dydx")
PACKAGES = ("numpy", "pandas", "numba", "scipy", "scikit-learn", "pyarrow", "websockets")
CHECKS = {"flow_signals", "funding_snapshot"}


def atomic_json(path, value):
    """Replace a derived operational snapshot; never use for evidence journals."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def environment(root):
    """Package/binary identity, never credentials or process environment values."""
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    binary = Path(root) / "engine/target/release/qx"
    binding = "UNVERIFIED"
    receipt = Path(root) / "engine/target/build-receipt.json"
    sha = digest(binary) if binary.is_file() and not binary.is_symlink() else None
    if receipt.is_file() and not receipt.is_symlink() and sha:
        try:
            saved = json.loads(receipt.read_text())
            if saved.get("status") == "SUCCESS" and saved.get("binary_sha256") == sha and saved.get("sources") == engine_sources(root):
                binding = "MATCHES_BUILD_RECEIPT"
        except (OSError, ValueError):
            pass
    return {"python": platform.python_version(), "implementation": platform.python_implementation(),
            "executable": sys.executable, "packages": versions,
            "qx_sha256": sha, "qx_source_binding": binding}


def engine_sources(root):
    base = Path(root) / "engine"
    _path(root, "engine/src")
    paths = [base / "Cargo.toml", base / "Cargo.lock", *sorted((base / "src").rglob("*.rs")),
             Path(root) / "rust-toolchain.toml"]
    for path in paths:
        _path(root, path.relative_to(root))
    return {str(path.relative_to(root)): digest(path) for path in paths if path.is_file()}


def _path(root, relative):
    path = Path(root) / relative
    # Refuse symlinks, including internal ones: receipts must identify ordinary files.
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("symlink input")
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError("input outside repository")
    return path


def _csv(path, required):
    if not path.exists():
        return [], None
    before = path.stat()
    # A truncated CSV may still parse as a valid short row. Check cardinality,
    # required values and the terminated final record separately.
    with path.open("rb") as stream:
        if before.st_size:
            stream.seek(-1, 2)
            if stream.read(1) != b"\n":
                raise ValueError("unterminated CSV record")
    with path.open(newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames or []
        if not required.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("missing/duplicate CSV columns")
        rows = []
        for row in reader:
            if None in row or any(v is None for v in row.values()) or any(row[k] == "" for k in required):
                raise ValueError("incomplete CSV record")
            rows.append(row)
    sha = digest(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("input changed during validation")
    return rows, {"rows": len(rows), "bytes": after.st_size, "sha256": sha}


def _integer(value):
    # The legacy writer uses integer text; reject rounding or NaN recovery.
    if not isinstance(value, str) or not value.isdecimal():
        raise ValueError("invalid nonnegative integer")
    return int(value)


def flow_signals(root, *, phase="after", now_ms=None):
    """Every signal hour must have one tick and n_elig distinct symbols.

    Orphan rows block retries instead of silently filling or dropping history.
    This does not prove that the upstream universe or features were correct.
    """
    base = "experiments/flow72_fwd2/journal/"
    signals, sr = _csv(_path(root, base + "signals.csv"), {"t", "symbol"})
    ticks, tr = _csv(_path(root, base + "ticks.csv"), {"t", "n_elig"})
    if sr is None and tr is None and any(_path(root, base + name).exists() for name in ("status.json", "tickets.csv")):
        raise ValueError("journal inputs absent beside prior outputs; not a fresh bootstrap")
    groups, seen = {}, set()
    for row in signals:
        t = _integer(row["t"])
        key = (t, row["symbol"])
        if t % HOUR or key in seen:
            raise ValueError("duplicate or off-grid signal key")
        seen.add(key)
        groups[t] = groups.get(t, 0) + 1
    hours = {}
    for row in ticks:
        t, n = _integer(row["t"]), _integer(row["n_elig"])
        if t % HOUR or t in hours or groups.get(t, 0) != n:
            raise ValueError("tick count/key disagrees with signal batch")
        hours[t] = n
    if set(groups) - set(hours):
        raise ValueError("uncommitted signal hour; inspect interrupted append before retry")
    if hours and max(hours) - min(hours) != (len(hours) - 1) * HOUR:
        raise ValueError("missing tick hour inside journal")
    state = "COMPLETE" if hours else "EMPTY"
    return {"state": state, "usable": bool(hours) or phase == "before", "hours": len(hours),
            "last_observation_ms": max(hours) if hours else None,
            "inputs": {base + "signals.csv": sr, base + "ticks.csv": tr},
            "scope": "signal/tick keys and cardinalities only; freshness/features/tickets unverified"}


def funding_snapshot(root, *, phase="after", now_ms=None):
    """Check the current UTC-hour file, source coverage and reception clock.

    Six nonempty source sets are required for COMPLETE. A missing venue remains
    PARTIAL even when the process returned zero; no discarded data or backfill.
    """
    if phase == "before":
        return {"state": "NOT_CHECKED", "usable": True, "scope": "post-process observation check"}
    import pandas as pd
    now_ms = int(now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000)
    hour = now_ms // HOUR * HOUR
    at = datetime.fromtimestamp(hour / 1000, timezone.utc)
    relative = at.strftime("data/recorders/funding_board/%Y-%m-%d/%H.parquet")
    path = _path(root, relative)
    if not path.is_file():
        return {"state": "MISSING", "usable": False, "expected_sources": list(FUNDING_VENUES),
                "answered_sources": [], "path": relative}
    before = path.stat()
    frame = pd.read_parquet(path, columns=["venue", "symbol", "recv_ms", "rate", "interval_h"])
    recv = pd.to_numeric(frame.recv_ms, errors="coerce")
    rates = pd.to_numeric(frame.rate, errors="coerce")
    intervals = pd.to_numeric(frame.interval_h, errors="coerce")
    import numpy as np
    valid = (np.isfinite(rates) & np.isfinite(intervals) & (intervals > 0) &
             (recv >= hour) & (recv <= now_ms) & frame.symbol.notna() & (frame.symbol.astype(str) != ""))
    answered = sorted(set(frame.loc[valid, "venue"]))
    complete = (set(answered) == set(FUNDING_VENUES) and bool(valid.all()) and
                not frame.duplicated(["venue", "symbol"]).any())
    sha = digest(path)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("snapshot changed during validation")
    return {"state": "COMPLETE" if complete else "PARTIAL", "usable": complete,
            "path": relative, "rows": len(frame), "sha256": sha,
            "expected_sources": list(FUNDING_VENUES), "answered_sources": answered,
            "last_observation_ms": int(recv.max()) if len(frame) and np.isfinite(recv.max()) else None,
            "scope": "current-hour source/rate/reception checks; full venue universe and settlement correctness unverified"}


def check(name, root, *, phase="after", now_ms=None):
    if name not in CHECKS:
        raise ValueError("unknown observation check")
    try:
        result = globals()[name](root, phase=phase, now_ms=now_ms)
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as error:
        result = {"state": "INVALID", "usable": False, "reason": str(error)[:200]}
    return {"check": name, "phase": phase, **result}


def run_process(task, root, log_path):
    """Only terminate the process group created for this task, including on interruption."""
    with log_path.open("xb") as log:
        proc = subprocess.Popen(task.argv, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True, stdin=subprocess.DEVNULL)
        try:
            return {"status": "SUCCESS" if proc.wait(timeout=task.timeout) == 0 else "FAILED",
                    "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            return {"status": "TIMED_OUT", "returncode": proc.returncode,
                    "reason": "task timeout"}
        except BaseException:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            raise

