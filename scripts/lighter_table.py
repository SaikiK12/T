"""qx spread symbol table with a Lighter column, for the Lighter carry lane (docs/VENUE_STRUCTURE.md, plan item 4).

lab/venues.py and scripts/venue_table.py are pinned by frozen lanes (R277, R282), so Lighter is added here, not there.
One row per Binance perp that Lighter lists (route open, hourly candles and funding fetched), columns `key`, `binance`,
one per other venue asked for (from lab.venues, '' where it has none) and `lighter`, the Lighter symbol. When two
Lighter symbols map to one perp, the shorter name wins. Reads file names and contract lists only (no prices). Sorted by
key, so a rebuild is byte for byte.

usage: python scripts/lighter_table.py --venues gate,hyperliquid,kucoin,dydx --out experiments/<lane>/symbols.csv
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, venues  # noqa: E402


def lighter_symbols(root):
    """{Binance perp: Lighter symbol} for open Lighter contracts whose hourly candles and funding are on disk."""
    hist = root / "lighter_hist"
    have = ({p.stem for p in (hist / "open" / "candles_1h").glob("*.parquet")}
            & {p.stem for p in (hist / "open" / "funding").glob("*.parquet")})
    out = {}
    with open(hist / "contracts.csv", newline="") as f:
        for r in csv.DictReader(f):
            sym, perp = r["symbol"], r["binance_perp"]
            if r["route"] == "open" and sym in have and (perp not in out or len(sym) < len(out[perp])):
                out[perp] = sym
    return out


def build(names, root=None):
    root = Path(root or data.ROOT)
    t, _ = venues.table(root)
    lt, perps = lighter_symbols(root), venues.binance_perps(root)
    return [{"key": p, "binance": p, **{v: t.get(p, {}).get(v, ("", ""))[0] for v in names}, "lighter": lt[p]}
            for p in sorted(lt) if p in perps]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venues", default="", help="comma-separated, from: " + ", ".join(venues.SOURCES))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    names = [v for v in a.venues.split(",") if v]
    bad = set(names) - set(venues.SOURCES)
    if bad:
        raise SystemExit(f"unknown venues {sorted(bad)}")
    rows = build(names)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, ["key", "binance", *names, "lighter"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} perps on Lighter; " + ", ".join(f"with {v} {sum(bool(r[v]) for r in rows)}" for v in names))


if __name__ == "__main__":
    main()
