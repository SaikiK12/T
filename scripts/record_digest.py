"""Append a SHA-256 digest of every recorder file under data/recorders/ to experiments/recorders/journal/digests.csv
(committed). The recorder data itself is gitignored; the committed digest proves what each file held when it was
recorded, so a later lane can show its point-in-time inputs were not edited. A file is digested again only when its
content changes (the notice journals grow). Append-only.

usage: python scripts/record_digest.py
"""
import csv
import hashlib
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

SRC = data.ROOT / "recorders"
JOURNAL = ROOT / "experiments" / "recorders" / "journal" / "digests.csv"
COLS = ("path", "bytes", "sha256", "digested_utc")


def digest(src=SRC, journal=JOURNAL, now=None):
    seen = set()
    if journal.exists():
        with journal.open(newline="") as f:
            seen = {(r["path"], r["sha256"]) for r in csv.DictReader(f)}
    now = now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = []
    for p in sorted(Path(src).rglob("*")):
        if not p.is_file() or p.name.endswith(".part"):
            continue
        rel = p.relative_to(src).as_posix()
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if (rel, sha) not in seen:
            rows.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha, "digested_utc": now})
    journal.parent.mkdir(parents=True, exist_ok=True)
    new_file = not journal.exists()
    with journal.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


if __name__ == "__main__":
    print(time.strftime("%H:%M:%S"), f"recorder digests: +{digest()}")
