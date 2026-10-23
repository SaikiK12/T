"""Offline execution receipts and fail-closed checks around legacy paper writers.

No repairs, market requests, environment values or statistical decisions. A
complete receipt certifies only its named structural checks at that instant.
"""
import csv
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import math
import re
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
CHECKS = {"flow_signals", "funding_snapshot", "unlock_journal"}


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


def unlock_journal(root, *, phase="after", now_ms=None):
    """R266 structural admission around its unchanged frozen paper writer.

    Checks tickets before their delayed entry, unique append keys, score links/
    arithmetic and retained snapshot bytes. Does not certify calendar eligibility,
    original publication, funding/price completeness, fills or scientific gates.
    """
    from scripts.forward_unlocks import TICKET_COLS, SCORE_COLS, SKIP_COLS, START_MS
    base = "experiments/unlocks_fwd/journal/"
    now_ms = int(now_ms if now_ms is not None else datetime.now(timezone.utc).timestamp() * 1000)
    tickets, tr = _csv(_path(root, base + "tickets.csv"), set(TICKET_COLS))
    scores, sr = _csv(_path(root, base + "scores.csv"), set(SCORE_COLS))
    skips, kr = _csv(_path(root, base + "skipped.csv"), set(SKIP_COLS) - {"detail"})
    if not tickets:
        # The native writer omits tickets.csv when a tick only records skips.
        # A documented zero-ticket status and empty book are legitimate.
        status_path = _path(root, base + "status.json")
        if status_path.exists():
            status = json.loads(status_path.read_text())
            if not isinstance(status, dict) or any(type(status.get(k)) is not int or status[k] != 0 for k in ("tickets", "scored", "open")):
                raise ValueError("ticket journal absent beside nonempty/unknown prior status")
        book, _ = _csv(_path(root, base + "book_days.csv"), {"day", "ret", "equity", "drawdown"})
        if scores or book:
            raise ValueError("ticket journal absent beside prior scores/book")

    def stamp(value):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("journal timestamp requires timezone")
        return int(parsed.timestamp() * 1000)

    def day(value):
        parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if parsed.strftime("%Y-%m-%d") != value:
            raise ValueError("noncanonical day")
        return int(parsed.timestamp() * 1000)

    def number(value, *, positive=False):
        result = float(value)
        if not math.isfinite(result) or (positive and result <= 0):
            raise ValueError("nonfinite or invalid positive journal value")
        return result

    def boolean(value):
        if value not in {"True", "False"}:
            raise ValueError("invalid journal boolean")
        return value == "True"

    indexed, events, contracts, snapshots, missing = {}, set(), set(), {}, []
    for row in tickets:
        d, entry, exit_ = day(row["day"]), _integer(row["entry_ms"]), _integer(row["exit_ms"])
        frozen = stamp(row["frozen_at"])
        if entry != d - 6 * 24 * HOUR or exit_ != d + 24 * HOUR or entry < START_MS:
            raise ValueError("ticket schedule outside frozen R266 rule")
        if not entry - 24 * HOUR <= frozen < entry + HOUR or frozen > now_ms:
            raise ValueError("ticket not frozen in its pre-entry window")
        key, event, contract = row["ticket"], (row["gecko_id"], row["day"]), (row["contract"], row["day"])
        if key != f"U{d // (24 * HOUR)}-{row['contract']}" or key in indexed or event in events or contract in contracts:
            raise ValueError("duplicate or inconsistent ticket identity")
        indexed[key] = (row, exit_)
        events.add(event)
        contracts.add(contract)
        for field in ("mult", "frac_max_supply", "tokens", "last_at_freeze", "index_price", "price_ratio"):
            number(row[field], positive=True)
        if number(row["taker"]) < 0 or not 1 / 3 <= number(row["price_ratio"]) <= 3:
            raise ValueError("invalid fee or ticket identity ratio")
        computed_ratio = number(row["last_at_freeze"]) / (number(row["index_price"]) * number(row["mult"]))
        if not math.isclose(number(row["price_ratio"]), computed_ratio, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("ticket price ratio disagrees with retained values")
        boolean(row["listed_binance"])
        name, expected = row["snapshot"], row["snapshot_sha256"]
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.json\.gz", name) or day(name[:10]) > frozen // (24 * HOUR) * (24 * HOUR):
            raise ValueError("unsafe or future snapshot name")
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("invalid snapshot digest")
        if name in snapshots and snapshots[name]["sha256"] != expected:
            raise ValueError("same daily snapshot has conflicting ticket hashes")
        path = _path(root, "data/recorders/unlocks/" + name)
        if not path.is_file():
            missing.append(name)
        else:
            before = path.stat()
            actual = digest(path)
            after = path.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns) or actual != expected:
                raise ValueError("ticket snapshot changed or digest mismatch")
        snapshots[name] = {"sha256": expected, "present": path.is_file()}
    skipped = set()
    for row in skips:
        key = (row["gecko_id"], row["day"])
        day(row["day"])
        if key in skipped or key in events or stamp(row["noted_at"]) > now_ms:
            raise ValueError("duplicate/conflicting/future skip")
        skipped.add(key)
    scored = set()
    for row in scores:
        key = row["ticket"]
        if key not in indexed or key in scored:
            raise ValueError("orphan or duplicate score")
        scored.add(key)
        ticket, exit_ = indexed[key]
        at = stamp(row["scored_at"])
        if at < exit_ + HOUR + 600_000 or at > now_ms:
            raise ValueError("score before frozen exit cutoff or in future")
        values = {f: number(row[f]) for f in ("entry_price", "exit_price", "gross", "funding", "taker", "spread_entry", "spread_exit", "cost_measured", "net", "net_1x", "net_2x", "net_3x", "mae", "mfe")}
        if min(values[f] for f in ("entry_price", "exit_price")) <= 0 or any(values[f] < 0 for f in ("taker", "spread_entry", "spread_exit", "cost_measured")):
            raise ValueError("invalid price or negative execution cost")
        _integer(row["settlements"])
        for field in ("stopped_trading", "spread_flag", "liq_1x", "liq_2x", "liq_3x"):
            boolean(row[field])
        for leverage in (1, 2, 3):
            if boolean(row[f"liq_{leverage}x"]) != (values["mae"] >= 1 / leverage - .01):
                raise ValueError("liquidation diagnostic flag disagrees with retained MAE")
        expected = {"gross": 1 - values["exit_price"] / values["entry_price"],
                    "taker": number(ticket["taker"]),
                    "cost_measured": 2 * values["taker"] + values["spread_entry"] + values["spread_exit"],
                    "net": values["gross"] - values["cost_measured"] + values["funding"]}
        expected.update({f"net_{k}x": values["gross"] - .002 * k + values["funding"] for k in (1, 2, 3)})
        if any(not math.isclose(values[k], v, rel_tol=1e-10, abs_tol=1e-12) for k, v in expected.items()):
            raise ValueError("score arithmetic disagrees with frozen R266 accounting")
    status_path = _path(root, base + "status.json")
    if tickets and status_path.exists():
        status = json.loads(status_path.read_text())
        if not isinstance(status, dict):
            raise ValueError("invalid prior derived status")
        # Appends may legitimately precede the derived status write. A prior
        # count ABOVE the remaining journal rows instead indicates row loss.
        for field, count in (("tickets", len(tickets)), ("scored", len(scores))):
            previous = status.get(field)
            if type(previous) is not int or not 0 <= previous <= count:
                raise ValueError("prior derived count exceeds retained journal rows")
    derived = {}
    if phase == "after":
        # Both files are written on every successful native tick, even with
        # zero tickets. An interrupted append may recover in preflight but is
        # not a completed execution receipt until derived outputs exist.
        book, br = _csv(_path(root, base + "book_days.csv"), {"day", "ret", "equity", "drawdown"})
        if not status_path.is_file() or br is None:
            raise ValueError("native status/book output missing after paper tick")
        before = status_path.stat()
        status = json.loads(status_path.read_text())
        if not isinstance(status, dict):
            raise ValueError("invalid native status output")
        for field, count in (("tickets", len(tickets)), ("scored", len(scores)), ("open", len(tickets) - len(scores))):
            if type(status.get(field)) is not int or status[field] != count:
                raise ValueError("native status disagrees with completed journal")
        age = now_ms - stamp(status["updated"])
        if not 0 <= age <= 900_000:
            raise ValueError("native status is stale/future after paper tick")
        if bool(book) != bool(scores):
            raise ValueError("book/score presence disagrees")
        days = [day(row["day"]) for row in book]
        if days != sorted(set(days)):
            raise ValueError("duplicate or unordered book day")
        for row in book:
            day(row["day"])
            for field in ("ret", "equity", "drawdown"):
                number(row[field])
        sha = digest(status_path)
        after = status_path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError("native status changed during validation")
        derived = {base + "status.json": {"sha256": sha}, base + "book_days.csv": br}
    inputs = {base + "tickets.csv": tr, base + "scores.csv": sr, base + "skipped.csv": kr, **derived}
    for relative, receipt in inputs.items():
        if receipt is not None and digest(_path(root, relative)) != receipt["sha256"]:
            raise ValueError("journal changed during validation")
    if missing:
        return {"state": "MISSING_SNAPSHOT", "usable": False, "missing_snapshots": sorted(set(missing)), "inputs": inputs}
    has_history = tr is not None or kr is not None
    return {"state": "COMPLETE" if has_history else "EMPTY", "usable": has_history or phase == "before",
            "tickets": len(tickets), "scores": len(scores), "skips": len(skips),
            "open": len(tickets) - len(scores), "snapshots": snapshots, "inputs": inputs,
            "source_validation": "UNVERIFIED", "gate_eligibility": "UNASSESSED",
            "scope": "journal keys/cutoffs/arithmetic/snapshot-byte identity only; raw prices/funding, calendar eligibility and original availability are unverified"}


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
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError, csv.Error) as error:
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
