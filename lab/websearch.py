"""Append-only web search ledger (registry/web_searches.csv): validate, append, and look up prior searches.

Metadata only. Nothing here touches the network. ``append`` adds exactly one row and never rewrites earlier bytes.
List-valued fields (urls_fetched, routed_to, queue_ids) separate items with ``;`` or whitespace as noted below.
"""
import csv
from datetime import date
import io
from pathlib import Path
import re

LEDGER = Path("registry") / "web_searches.csv"
COLUMNS = ("search_id", "date", "agent", "lens", "query", "tool", "urls_fetched", "fetch_status", "source_tier",
           "verification", "routed_to", "queue_ids", "note")
STATUS = ("FETCHED_FULL", "FETCHED_PARTIAL", "SEARCH_SUMMARY_ONLY", "BLOCKED", "NOT_FOUND")
TIER = ("primary", "secondary", "practitioner", "search_summary")
VERIFICATION = ("VERIFIED", "CONTRADICTED", "UNVERIFIED")
_ID = re.compile(r"WS[0-9]{4,}\Z")
_URL = re.compile(r"https?://[^\s/$.?#][^\s]*\Z")
_REQUIRED = ("search_id", "date", "agent", "query", "fetch_status", "source_tier", "verification")


def _items(value, sep=r"[;\s]+"):
    return [part for part in re.split(sep, value or "") if part]


def load(root):
    """Return ledger rows as dicts; an absent ledger is an empty list."""
    path = Path(root) / LEDGER
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _queue_ids(root):
    ids = set()
    for name, columns in (("methods.csv", ("id",)), ("methods_aliases.csv", ("rec_id", "queue_id"))):
        path = Path(root) / "registry" / name
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    ids.update(row[c] for c in columns if row.get(c))
    return ids


def validate(rows, root=None):
    """Return a list of problem strings (empty when valid). With ``root`` also check paths and queue ids."""
    problems = []
    seen_ids = set()
    known = _queue_ids(root) if root is not None else None
    for number, row in enumerate(rows, 1):
        tag = row.get("search_id") or f"row {number}"
        for column in _REQUIRED:
            if not (row.get(column) or "").strip():
                problems.append(f"{tag}: {column} is empty")
        if row.get("search_id"):
            if not _ID.match(row["search_id"]):
                problems.append(f"{tag}: search_id must look like WS0001")
            if row["search_id"] in seen_ids:
                problems.append(f"{tag}: duplicate search_id")
            seen_ids.add(row["search_id"])
        try:
            date.fromisoformat(row.get("date") or "")
        except ValueError:
            problems.append(f"{tag}: date is not ISO YYYY-MM-DD")
        for column, allowed in (("fetch_status", STATUS), ("source_tier", TIER), ("verification", VERIFICATION)):
            if row.get(column) and row[column] not in allowed:
                problems.append(f"{tag}: {column} {row[column]!r} not in {', '.join(allowed)}")
        for url in _items(row.get("urls_fetched")):
            if not _URL.match(url):
                problems.append(f"{tag}: bad URL {url!r}")
        if root is not None:
            for target in _items(row.get("routed_to"), r"[;]+"):
                target = target.strip()
                if "/" in target and not (Path(root) / target.split("#")[0]).exists():
                    problems.append(f"{tag}: routed_to path does not exist: {target}")
            for queue_id in _items(row.get("queue_ids")):
                if queue_id not in known:
                    problems.append(f"{tag}: queue id {queue_id} not in registry/methods.csv or aliases")
    return problems


def append(root, **fields):
    """Assign the next WSnnnn id, validate the whole ledger plus the new row, append one line. Return the row."""
    unknown = set(fields) - set(COLUMNS)
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    rows = load(root)
    number = 1 + max((int(r["search_id"][2:]) for r in rows if _ID.match(r.get("search_id") or "")), default=0)
    row = {column: str(fields.get(column, "") or "") for column in COLUMNS}
    row["search_id"] = f"WS{number:04d}"
    row["date"] = row["date"] or date.today().isoformat()
    problems = validate([*rows, row], root)
    if problems:
        raise ValueError("; ".join(problems))
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow([row[c] for c in COLUMNS])
    path = Path(root) / LEDGER
    with path.open("ab") as handle:
        if path.stat().st_size and not _ends_with_newline(path):
            handle.write(b"\n")
        handle.write(buffer.getvalue().encode("utf-8"))
    return row


def _ends_with_newline(path):
    with path.open("rb") as handle:
        handle.seek(-1, 2)
        return handle.read(1) == b"\n"


def seen(root, text):
    """Case-insensitive substring hits in the ledger and research/intake/source_catalog_*.csv."""
    needle = (text or "").strip().lower()
    hits = []
    if not needle:
        return hits
    for row in load(root):
        if any(needle in (row.get(c) or "").lower() for c in ("query", "urls_fetched", "lens", "note")):
            hits.append(dict(source=str(LEDGER), id=row["search_id"], match=row["query"] or row["urls_fetched"]))
    for path in sorted((Path(root) / "research" / "intake").glob("source_catalog_*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if any(needle in (row.get(c) or "").lower() for c in ("url", "provider", "research_gap", "id")):
                    hits.append(dict(source=str(path.relative_to(root)), id=row.get("id", ""), match=row.get("url", "")))
    return hits
