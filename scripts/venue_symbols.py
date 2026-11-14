"""Cross-venue symbol table: one row per Binance USD-M perp, with the file stem of the same coin on Gate, Hyperliquid
and MEXC (empty where it is not listed or has no history file). Built from file names and contract lists only; no
price or funding value is read. The same ticker is not proof of the same coin, so a lane checks identity on prices
after its PREREG is frozen (qx spread's correlation guard).

Coins with no Binance perp are left out on purpose: on Gate and MEXC they are reserved samples (docs/GATES.md).
Hyperliquid's "k" coins are its 1000x contracts (kPEPE = 1000PEPE). When two contracts of one venue map to the same
Binance perp, the one with the longer history (Gate: candle months) or the plain name is kept, and both are printed.

usage: python scripts/venue_symbols.py OUT.csv
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402
from scripts.record_funding_board import base_of  # noqa: E402
from scripts.squeeze_events import binance_perp  # noqa: E402

D = data.ROOT
VENUES = ("binance", "gate", "hyperliquid", "mexc")


def stems(folder):
    return {p.stem for p in (D / folder).glob("*.parquet")}


def table():
    perps = {s for s in stems("klines_1h") if s.endswith("USDT")} & stems("fundingRate")
    rows = {p: {"key": p, "binance": p} for p in sorted(perps)}
    notes = []

    def put(venue, perp, stem, rank):
        if perp not in rows:
            return
        old = rows[perp].get(venue)
        if old is None or rank > rows[perp][f"_{venue}_rank"]:
            if old is not None:
                notes.append(f"{venue}: {perp} keeps {stem} over {old}")
            rows[perp][venue], rows[perp][f"_{venue}_rank"] = stem, rank
        else:
            notes.append(f"{venue}: {perp} keeps {old} over {stem}")

    gc, gf = stems("gate_hist/open/candlesticks_1h"), stems("gate_hist/open/funding_applies")
    with open(D / "gate_hist" / "contracts.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["route"] == "open" and r["name"] in gc and r["name"] in gf:
                put("gate", r["binance_perp"], r["name"], (float(r["candlesticks_1h_months"] or 0), -len(r["name"])))
    hc, hf = stems("hyperliquid/candles_1d"), stems("hyperliquid/funding")
    for coin in sorted(hc & hf):
        hit = binance_perp(base_of(coin), perps)
        if hit:
            put("hyperliquid", hit[0], coin, (0, -len(coin)))
    mk, mf = stems("mexc_hist/klines_1h"), stems("mexc_hist/funding")
    for c in json.loads((D / "mexc_hist" / "contracts.json").read_text()):
        if c.get("settle") == "USDT" and c.get("type") == 1 and c["symbol"] in mk and c["symbol"] in mf:
            hit = binance_perp(c["base"], perps)
            if hit:
                put("mexc", hit[0], c["symbol"], (0, -len(c["symbol"])))
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
