"""Binance announcement catalogs (Delisting, New Cryptocurrency Listing, Latest Binance News) as an append-only journal:
one row per article with its id, title, release time (ms, as published) and the UTC time this recorder first saw it.
The first run pages back through the whole catalog; later runs stop at the first page whose articles are all known,
so an hourly run is cheap and idempotent. Event lanes use first_seen_utc for live tickets and release_ms for history.

Journal: data/recorders/notices/binance_<catalog>.csv (gitignored); scripts/record_digest.py commits its digest.
Data collection only.

usage: python scripts/record_notices.py
"""
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

API = "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId={cat}&pageNo={page}&pageSize=20"
CATALOGS = {161: "delisting", 48: "listing", 49: "news"}   # "news": delistings before 2022-02 were posted here
OUT = data.ROOT / "recorders" / "notices"
COLS = ("id", "code", "title", "release_ms", "first_seen_utc")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=4):
    delay = 2.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def known_ids(path):
    if not path.exists():
        return set()
    with path.open(newline="") as f:
        return {int(r["id"]) for r in csv.DictReader(f)}


def new_articles(cat, known, max_pages=400):
    """Articles not yet in the journal, newest first; stops at the first fully known page."""
    out = []
    for page in range(1, max_pages + 1):
        cats = get(API.format(cat=cat, page=page))["data"]["catalogs"]   # empty past the last page
        arts = cats[0]["articles"] if cats else []
        if not arts:
            break
        fresh = [a for a in arts if int(a["id"]) not in known]
        out += fresh
        if not fresh:
            break
        time.sleep(0.3)
    return out


def record(cat, name, now=None):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"binance_{name}.csv"
    known = known_ids(path)
    arts = new_articles(cat, known)
    seen = now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = sorted(({"id": int(a["id"]), "code": a["code"], "title": a["title"], "release_ms": int(a["releaseDate"]),
                    "first_seen_utc": seen} for a in arts if int(a["id"]) not in known), key=lambda r: r["release_ms"])
    new_file = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows), len(known) + len(rows)


def main():
    for cat, name in CATALOGS.items():
        added, total = record(cat, name)
        log(f"binance {name}: +{added} (total {total})")


if __name__ == "__main__":
    main()
