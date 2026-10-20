"""Read-only operational job metadata for the control room.

Use the existing orchestrator's report schema when an explicit external state
directory is supplied. Legacy log modification times prove only that bytes were
written: they never imply successful execution. No command lines, environment
values, log contents, journal rows or market data are inspected.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

try:
    from scripts.orchestrate_forward import forward_tasks
except ModuleNotFoundError:  # dashboard_data.py invoked directly from scripts/
    from orchestrate_forward import forward_tasks


# Stable identifiers and paths remain intact; these are presentation labels.
LABELS = {
    "REC_TICKER": ("Market data collection", "MEXC funding and ticker snapshots", "recorders"),
    "REC_NOTICES": ("Market data collection", "Exchange announcement snapshots", "recorders"),
    "REC_UNLOCKS": ("Market data collection", "Token unlock calendar snapshots", "recorders"),
    "REC_DIGEST": ("Data integrity", "Recorder provenance digests", "recorders"),
    "R200": ("Prospective paper", "Binance positioning books", "flow72_fwd2"),
    "R214": ("Prospective paper", "Binance delayed-entry control", "flow72_fwd3"),
    "R215": ("Prospective paper", "MEXC positioning books", "mexc_fwd"),
    "R218": ("Prospective paper", "MEXC agreement-weighted book", "mexc_fwd_sq"),
    "R220": ("Prospective paper", "Funding carry books", "carry_fwd"),
    "R221": ("Evidence decisions", "MEXC sequential evidence review", "mexc_seq"),
    "R224": ("Execution measurement", "MEXC order-book execution costs", "mexc_costs"),
    "R225": ("Prospective paper", "MEXC volatility-targeted books", "vt_fwd"),
    "R266": ("Prospective paper", "MEXC token unlock events", "unlocks_fwd"),
    "R268": ("Prospective paper", "MEXC delisting announcement events", "delist_fwd"),
    "R270": ("Prospective paper", "MEXC monitoring-tag events", "montag_fwd"),
    "R272": ("Prospective paper", "MEXC funding-change and prelisting events", "announce_fwd"),
    # These share vt_fwd/tick.log in the shell; it cannot identify their outcomes.
    "LAG": ("Data integrity", "Forward processing-lag report", "vt_fwd"),
    "PANEL": ("Reporting", "Canonical research panel refresh", "vt_fwd"),
    "DASH": ("Reporting", "Control room dataset export", "vt_fwd"),
}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")
STATES = {"SUCCESS", "FAILED", "TIMED_OUT", "BLOCKED", "RUNNING", "PENDING"}
MAX_REPORT_BYTES = 2_000_000
MAX_REPORTS = 200


def _iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _stamp(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.timestamp()


def _safe_file(path, boundary):
    """Never follow a symlink through an explicitly supplied directory."""
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        return False
    try:
        path.resolve().relative_to(boundary)
        return path.is_file()
    except (ValueError, OSError):
        return False


def _reports(root, state_dir):
    """Return bounded validated reports; do not open task logs or other files."""
    if state_dir is None:
        return [], False
    raw = Path(state_dir).absolute()
    if raw.is_symlink() or any(p.is_symlink() for p in raw.parents):
        return [], True
    boundary = raw.resolve()
    if boundary == root or root in boundary.parents:
        return [], True  # Existing orchestrator requires external run storage.
    if not boundary.is_dir():
        return [], True
    reports, rejected = [], False
    try:
        candidates = list(boundary.glob("*/status.json"))
        candidates.sort(key=lambda p: p.lstat().st_mtime, reverse=True)
    except OSError:
        return [], True
    for path in candidates[:MAX_REPORTS]:
        try:
            if not _safe_file(path, boundary) or path.stat().st_size > MAX_REPORT_BYTES:
                raise ValueError("unsafe/oversize report")
            payload = json.loads(path.read_text())
            if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                raise ValueError("unsupported schema")
            if payload.get("root") != str(root):
                continue  # A shared external directory may contain another checkout's runs.
            rid = payload.get("run_id")
            if not isinstance(rid, str) or not NAME.fullmatch(rid) or rid != path.parent.name:
                raise ValueError("invalid run identity")
            started = _stamp(payload.get("started_at"))
            nodes = payload.get("tasks")
            if not isinstance(nodes, list) or len(nodes) > 200:
                raise ValueError("invalid tasks")
            seen = set()
            for node in nodes:
                if not isinstance(node, dict):
                    raise ValueError("invalid task")
                name = node.get("name")
                if not isinstance(name, str) or not NAME.fullmatch(name) or name in seen:
                    raise ValueError("invalid task identity")
                seen.add(name)
                if node.get("status") not in STATES:
                    raise ValueError("invalid task state")
                code = node.get("returncode")
                if code is not None and (isinstance(code, bool) or not isinstance(code, int)):
                    raise ValueError("invalid exit code")
                if node["status"] == "SUCCESS" and code != 0:
                    raise ValueError("success requires recorded zero exit code")
                for field in ("started_at", "finished_at"):
                    if node.get(field) is not None:
                        _stamp(node[field])
            reports.append((started, payload, path))
        except (OSError, ValueError, TypeError, OverflowError):
            rejected = True
    return sorted(reports, key=lambda item: item[0], reverse=True), rejected


def build_jobs(root, *, now=None, state_dir=None):
    """Categorize jobs without executing them or treating observations as evidence.

    ``ok`` is tri-state: True = recorded process exit zero; False = a recorded
    failure/timeout/block; None = unknown/pending/running. Staleness is separate
    from that recorded outcome. It never certifies paper-data quality.
    """
    root = Path(root).resolve()
    now = time.time() if now is None else float(now)
    tasks = list(forward_tasks())
    reports, rejected = _reports(root, state_dir)
    latest = {}
    for _, report, report_path in reports:
        for node in report["tasks"]:
            latest.setdefault(node["name"], (report, node, report_path))
    catalog = {t.name: t for t in tasks}
    for name in latest.keys() - catalog.keys():
        catalog[name] = None  # Preserve explicit custom orchestrator tasks, without guessing their role.
    rows = []
    for name, task in catalog.items():
        category, label, lane = LABELS.get(name, ("Unclassified operation", name, None))
        row = {"key": name, "task_id": name, "job": label, "display_name": label,
               "category": category, "kind": category, "lane": lane, "run_id": None,
               "state": "UNKNOWN", "status_source": "not_recorded", "returncode": None,
               "at": None, "age_h": None, "stale": None, "ok": None, "log_path": None,
               "note": "No structured execution report. Process/data success is unverified."}
        if name in latest:
            report, node, path = latest[name]
            stamp = _stamp(node.get("finished_at") or node.get("started_at") or report["started_at"])
            age = round(max(0, now - stamp) / 3600, 2)
            status = node["status"]
            row.update(run_id=report["run_id"], state=status, status_source="orchestrator",
                       returncode=node.get("returncode"), at=_iso(stamp), age_h=age, stale=age > 2,
                       ok=True if status == "SUCCESS" else False if status in {"FAILED", "TIMED_OUT", "BLOCKED"} else None,
                       note="Recorded process state; data freshness, completeness and evidence validity are separate.")
            log = node.get("log")
            if isinstance(log, str) and log == name + ".log":
                row["log_path"] = str(path.parent / log)  # Metadata only; file content is never read.
        elif lane:
            log = root / "experiments" / lane / "tick.log"
            if _safe_file(log, root):
                stamp = log.stat().st_mtime
                age = round(max(0, now - stamp) / 3600, 2)
                row.update(status_source="legacy_log", at=_iso(stamp), age_h=age, stale=age > 2,
                           log_path=str(log.relative_to(root)),
                           note="Legacy log changed; exit status is unknown. This file may be shared by several tasks.")
        rows.append(row)
    if state_dir is not None and (rejected or not reports):
        rows.append({"key": "REPORT_INPUT", "task_id": "REPORT_INPUT", "job": "Execution-report input",
                     "display_name": "Execution-report input", "category": "Data integrity", "kind": "Data integrity",
                     "lane": None, "run_id": None, "state": "UNAVAILABLE", "status_source": "report_validation",
                     "returncode": None, "at": None, "age_h": None, "stale": None, "ok": None, "log_path": None,
                     "note": "Some configured reports are unavailable, invalid or for another checkout; no success inferred."})
    return rows
