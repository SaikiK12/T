"""Symbol table for the KuCoin / dYdX venue replication of R275 and R276: one row per Binance USD-M perp with the
file stem of the same coin on Gate, KuCoin and dYdX (empty where it is not listed or has no history file). Built
from file names and the fetchers' contract lists only (`gate_hist/contracts.csv`, `<venue>_hist/contracts.csv`, open
route); no price or funding value is read. `scripts/venue_symbols.py` stays as R275 / R276 froze it.

When two contracts of one venue map to the same Binance perp, the one with the longer history (Gate: candle months)
or the shorter name is kept, and both are printed. Rows on fewer than 2 venues are dropped.

usage: python scripts/venue_symbols_kd.py OUT.csv
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

D = data.ROOT
VENUES = ("binance", "gate", "kucoin", "dydx")
FILES = {"gate": ("gate_hist", "candlesticks_1h", "funding_applies", "name", "candlesticks_1h_months"),
         "kucoin": ("kucoin_hist", "candles_1d", "funding", "symbol", None),
         "dydx": ("dydx_hist", "candles_1h", "funding", "symbol", None)}


def stems(folder):
    return {p.stem for p in (D / folder).glob("*.parquet")}


def table():
    perps = {s for s in stems("klines_1h") if s.endswith("USDT")} & stems("fundingRate")
    rows = {p: {"key": p, "binance": p} for p in sorted(perps)}
    rank, notes = {}, []
    for venue, (folder, candles, funding, col, months) in FILES.items():
        have = stems(f"{folder}/open/{candles}") & stems(f"{folder}/open/{funding}")
        path = D / folder / "contracts.csv"
        if not path.exists():
            continue
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                perp, stem = r["binance_perp"], r[col]
                if r["route"] != "open" or stem not in have or perp not in rows:
                    continue
                k = (float(r[months] or 0) if months else 0, -len(stem))
                old = rows[perp].get(venue)
                if old is None or k > rank[(venue, perp)]:
                    if old is not None:
                        notes.append(f"{venue}: {perp} keeps {stem} over {old}")
                    rows[perp][venue], rank[(venue, perp)] = stem, k
                else:
                    notes.append(f"{venue}: {perp} keeps {old} over {stem}")
    out = [{k: r.get(k, "") for k in ("key",) + VENUES} for r in rows.values()]
    return [r for r in out if sum(bool(r[v]) for v in VENUES) >= 2], notes


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rows, notes = table()
    with open(sys.argv[1], "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=("key",) + VENUES, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for n in notes:
        print(n)
    print(f"{len(rows)} coins on 2+ venues; " + ", ".join(f"{v} {sum(bool(r[v]) for r in rows)}" for v in VENUES))


if __name__ == "__main__":
    main()
