"""Legs for the Monitoring Tag short (R269) from Binance's news and delisting catalogs
(data/recorders/notices/binance_{news,delisting}.csv, scripts/record_notices.py; one tag notice was filed under
Delisting). Parses titles only; no price is read.

- tag:   "Binance Will Extend the Monitoring Tag to (Include) A, B and C ... on YYYY-MM-DD". The names end at
         ", (and) Remove ..." or " on <date>".
- untag: "... Remove the Monitoring Tag for A & B ..." (descriptive only in R269).
A leg is one ticker of one notice, mapped to its USD-M perp as in scripts/delist_events.py (perp_for). t0 is the
notice's release time. Notices released at or after --until are left out, so a rebuild is byte-identical.

usage: python scripts/montag_events.py [--out experiments/montag_v1] [--until 2026-10-20T17:00:00Z]
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data  # noqa: E402
from delist_events import names, perp_for  # noqa: E402

SRC = [data.ROOT / "recorders" / "notices" / f"binance_{c}.csv" for c in ("news", "delisting")]
UNTIL = "2026-10-20T17:00:00Z"
END = r"(?=,? and Remove|, Remove|,? and the Seed Tag| on \d{4}-\d{2}-\d{2}|\s*$)"
TAG = re.compile(r"Extend the Monitoring Tag to (?:Include )?(?P<names>.+?)" + END, re.I)
UNTAG = re.compile(r"Remove the Monitoring Tag for (?P<names>.+?)" + END, re.I)


def parse(title):
    """[(kind, [tickers])] for the tag and untag lists in a title."""
    out = []
    for kind, rx in (("tag", TAG), ("untag", UNTAG)):
        m = rx.search(title)
        if m and names(m.group("names")):
            out.append((kind, names(m.group("names"))))
    return out


def legs(src=SRC, root=None, until=UNTIL):
    root = Path(root or data.ROOT)
    perps = {f.stem for f in (root / "klines_1h").glob("*.parquet")}     # names only; no price is read
    end_ms = int(pd.Timestamp(data.END, tz="UTC").value // 10**6) + 86_400_000
    d = pd.concat([pd.read_csv(p) for p in src]).drop_duplicates("id").sort_values("id")
    d = d[d.release_ms < int(pd.Timestamp(until).value // 10**6)]
    rows = []
    for r in d.itertuples():
        for kind, ticks in parse(r.title):
            for t in ticks:
                perp, in_archive = perp_for(t, perps)
                rows.append({"notice": int(r.id), "kind": kind, "ticker": t, "perp": perp, "in_archive": in_archive,
                             "window": "archive" if int(r.release_ms) < end_ms else "post_archive",
                             "release_ms": int(r.release_ms), "title": r.title})
    out = pd.DataFrame(rows).drop_duplicates(["notice", "kind", "perp"])
    return out.sort_values(["release_ms", "notice", "kind", "perp"]).reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "experiments" / "montag_v1"))
    ap.add_argument("--until", default=UNTIL)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = legs(until=a.until)
    L.to_csv(out / "legs.csv", index=False)
    print(f"{L.notice.nunique()} notices -> {len(L)} legs")
    print(L.groupby(["window", "kind", "in_archive"]).agg(notices=("notice", "nunique"), legs=("perp", "size")).to_string())


if __name__ == "__main__":
    main()
