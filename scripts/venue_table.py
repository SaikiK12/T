"""Write a qx spread symbol table from lab.venues: one row per Binance perp found on at least one of the venues asked
for, columns `key`, `binance` and one per venue (the venue's symbol, '' where it has none).

Reads file names and contract lists only (no prices). Reserved samples are never listed (lab.venues reads `open/`
folders only). The output is sorted by key, so a rebuild is byte for byte.

usage: python scripts/venue_table.py --venues gate,kucoin,dydx --out experiments/<lane>/symbols.csv
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import venues  # noqa: E402


def build(names, root=None):
    t, notes = venues.table(root)
    rows = []
    for perp in sorted(t):
        r = {"key": perp, "binance": perp, **{v: t[perp].get(v, ("", ""))[0] for v in names}}
        if any(r[v] for v in names):
            rows.append(r)
    return rows, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", required=True, help="comma-separated, from: " + ", ".join(venues.SOURCES))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    names = a.venues.split(",")
    bad = set(names) - set(venues.SOURCES)
    if bad:
        raise SystemExit(f"unknown venues {sorted(bad)}")
    rows, notes = build(names)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, ["key", "binance", *names], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} perps; " + ", ".join(f"{v} {sum(bool(r[v]) for r in rows)}" for v in names)
          + f"; {len(notes)} duplicate-key notes")


if __name__ == "__main__":
    main()
