"""Append-only register of research rounds (the machine-readable ROADMAP). IDs are allocated under a file lock."""
import csv
import os
import re
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path

FIELDS = ("id", "date", "lane", "title", "status", "verdict", "trials", "prereg_sha", "path", "notes")
STATUS = ("PLANNED", "REGISTERED", "RUNNING", "DONE", "ARMED", "ABANDONED")
VERDICT = ("PENDING", "NULL", "PARTIAL", "CONFIRMED", "DATA_PASS")
_ID = re.compile(r"R(\d+)$")
_SHA = re.compile(r"[0-9a-f]{8,64}$")


class RegistryError(Exception):
    pass


@contextmanager
def _lock(path, timeout=10.0):
    lock = f"{path}.lock"
    start = time.monotonic()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.monotonic() - start > timeout:
                raise RegistryError(f"{lock} held for over {timeout}s; if no writer is alive, delete it by hand")
            time.sleep(0.02)
    try:
        yield
    finally:
        os.close(fd)
        os.unlink(lock)


def rows(path):
    if not Path(path).exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _check(row):
    if row["status"] not in STATUS:
        raise RegistryError(f"status {row['status']!r} not in {STATUS}")
    if row["verdict"] not in VERDICT:
        raise RegistryError(f"verdict {row['verdict']!r} not in {VERDICT}")
    if row["date"]:
        date.fromisoformat(row["date"])
    if row["trials"]:
        int(row["trials"])
    if row["prereg_sha"] and not _SHA.match(row["prereg_sha"]):
        raise RegistryError(f"prereg_sha {row['prereg_sha']!r} is not 8-64 lowercase hex characters")


def append(path, /, id=None, **fields) -> str:
    """Add one row and return its id. Pass id only to import an existing round; otherwise the next free one is used.
    `path` is positional-only so the row's own "path" field can be passed by name."""
    unknown = set(fields) - set(FIELDS)
    if unknown:
        raise RegistryError(f"unknown fields {sorted(unknown)}")
    row = {k: str(fields.get(k, "")) for k in FIELDS}
    with _lock(path):
        existing = rows(path)
        used = {r["id"] for r in existing}
        if id is None:
            top = max((int(m.group(1)) for r in existing if (m := _ID.match(r["id"]))), default=0)
            id = f"R{top + 1}"
        if not _ID.match(id) or id in used:
            raise RegistryError(f"id {id!r} is malformed or already used")
        row["id"] = id
        _check(row)
        new_file = not Path(path).exists() or Path(path).stat().st_size == 0
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, FIELDS, lineterminator="\n")
            if new_file:
                w.writeheader()
            w.writerow(row)
    return id


def validate(path):
    """Raise if any row breaks the schema or an id repeats."""
    seen = set()
    for r in rows(path):
        if tuple(r) != FIELDS:
            raise RegistryError(f"columns {tuple(r)} differ from {FIELDS}")
        if not _ID.match(r["id"]) or r["id"] in seen:
            raise RegistryError(f"id {r['id']!r} is malformed or repeated")
        seen.add(r["id"])
        _check(r)


def program_trials(path) -> int:
    """Total trials across all rounds: the denominator any 'significant' lane has to be read against."""
    return sum(int(r["trials"]) for r in rows(path) if r["trials"])
