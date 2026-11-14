"""qx spread symbol table for reserved batch 2 (R391): the long-tail contracts in the KuCoin, dYdX and Lighter
`reserved/` folders (docs/GATES.md), matched with each other and with MEXC by base name.

A row is a base listed by at least two of: KuCoin reserved, dYdX reserved, Lighter reserved, MEXC. At least one of
those must be a reserved venue. The columns are `key` (the base), `kucoin`, `dydx`, `lighter` and `mexc` ('' where the
venue has none). Each entry needs the venue's price and funding files on disk.

Excluded:
- **The MEXC-only reserved set:** the contracts of R265's `reserved_mexc` unlock events (batch 1, R286). Those MEXC
  bars are a different reserved sample, and this batch does not read them.
- **Gate:** its long tail is reserved and on its own cadence. It is reported as an overlap and never read.

A base with two contracts on one venue keeps the shorter symbol. The output is sorted by key, so a rebuild is byte for
byte. The script reads contract lists and file names only: no price, funding or timestamp row.

usage: python scripts/reserved_venue_table.py --out experiments/reserved_batch2/symbols.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESERVED = {"kucoin": "candles_1d", "dydx": "candles_1h", "lighter": "candles_1h"}   # venue -> price folder
VENUES = ("kucoin", "dydx", "lighter", "mexc")


def stems(folder):
    return {p.stem for p in Path(folder).glob("*.parquet")}


def reserved_venue(name, data=DATA):
    """{BASE: symbol} for a venue's reserved contracts that have price and funding files."""
    hist = data / f"{name}_hist"
    have = stems(hist / "reserved" / RESERVED[name]) & stems(hist / "reserved" / "funding")
    out = {}
    with open(hist / "contracts.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["route"] != "reserved" or r["symbol"] not in have:
                continue
            b = r["base"].upper()
            if b not in out or len(r["symbol"]) < len(out[b]):
                out[b] = r["symbol"]
    return out


def mexc_only(root=ROOT):
    """The MEXC-only reserved contracts fixed by batch 1: the perps of R265's reserved_mexc events."""
    with open(root / "experiments" / "unlocks_v1" / "events.csv", newline="") as f:
        return {r["perp"] for r in csv.DictReader(f) if r["window"] == "reserved_mexc"}


def mexc(data=DATA, root=ROOT):
    """{BASE: symbol} for MEXC contracts with hourly bars and funding, minus the MEXC-only reserved set."""
    hist = data / "mexc_hist"
    skip = mexc_only(root)
    out = {}
    for s in sorted(stems(hist / "klines_1h") & stems(hist / "funding")):
        if s in skip or not s.endswith("_USDT"):
            continue
        b = s[: -len("_USDT")].upper()
        if b not in out or len(s) < len(out[b]):
            out[b] = s
    return out


def gate_reserved(data=DATA):
    with open(data / "gate_hist" / "contracts.csv", newline="") as f:
        return {r["name"].rsplit("_", 1)[0].upper() for r in csv.DictReader(f) if r["route"] == "reserved"}


def build(data=DATA, root=ROOT):
    by = {v: reserved_venue(v, data) for v in RESERVED}
    by["mexc"] = mexc(data, root)
    rows = []
    for b in sorted(set().union(*by.values())):
        on = [v for v in VENUES if b in by[v]]
        if len(on) >= 2 and any(v in RESERVED for v in on):
            rows.append({"key": b, **{v: by[v].get(b, "") for v in VENUES}})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = build()
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, ["key", *VENUES], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    gate = gate_reserved()
    print(json.dumps({"rows": len(rows), **{v: sum(bool(r[v]) for r in rows) for v in VENUES},
                      "gate_reserved_overlap": sorted(r["key"] for r in rows if r["key"] in gate),
                      "mexc_only_excluded": sorted(mexc_only())}))


if __name__ == "__main__":
    sys.exit(main())
