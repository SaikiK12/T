"""Inputs for R465 ltwknd_v1 (R462's trade.xyz weekend fade replicated on Lighter's US-stock perps). Public and
keyless, through lab/carrylane.py's paced Lighter client (60 requests a minute):

universe  -> experiments/ltwknd_v1/universe.csv (run before the freeze; names, ids and fees only, no price)
    - the 76 rows of R462's frozen experiments/xyzwknd_v1/universe.csv whose coin is also a Lighter perp symbol
      (orderBookDetails), with Lighter's market id, listing time (created_at), taker and maker fee and status. The
      `etf` and `ipo_424b4` columns are R462's.
bars      -> data/lighter_wknd/ (run after the freeze; gitignored, recorded with scripts/data_provenance.py)
    - klines_1h/<COIN>.parquet: Lighter 1 h candles (t open ms, close, volume) over [--start, --end)
    - funding/<COIN>.parquet: Lighter hourly funding (t ms, rate signed + when longs pay)
    - manifest.json (per-file sha256)

usage: python scripts/fetch_lighter_wknd.py universe
       python scripts/fetch_lighter_wknd.py bars --start 2026-02-13T00:00:00Z --end 2026-11-10T00:00:00Z
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carrylane  # noqa: E402

LANE = ROOT / "experiments" / "ltwknd_v1"
PARENT = ROOT / "experiments" / "xyzwknd_v1" / "universe.csv"
OUT = ROOT / "data" / "lighter_wknd"
COLS = ["coin", "market_id", "created_at", "status", "taker_fee", "maker_fee", "etf", "ipo_424b4"]


def universe():
    with open(PARENT, newline="") as f:
        parent = list(csv.DictReader(f))
    lt = {d["symbol"]: d for d in carrylane._lighter_details()}
    out = []
    for r in parent:
        d = lt.get(r["coin"])
        if d is None:
            continue
        out.append({"coin": r["coin"], "market_id": int(d["market_id"]), "created_at": int(d["created_at"]),
                    "status": d.get("status", ""), "taker_fee": d.get("taker_fee", ""),
                    "maker_fee": d.get("maker_fee", ""), "etf": r["etf"], "ipo_424b4": r["ipo_424b4"]})
    LANE.mkdir(parents=True, exist_ok=True)
    with open(LANE / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print(len(out), "of", len(parent), "R462 markets are Lighter perps")


def epoch_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


def bars(start, end):
    with open(LANE / "universe.csv", newline="") as f:
        coins = [r["coin"] for r in csv.DictReader(f)]
    s0, s1 = epoch_ms(start), epoch_ms(end)
    (OUT / "klines_1h").mkdir(parents=True, exist_ok=True)
    (OUT / "funding").mkdir(parents=True, exist_ok=True)
    man = {"kind": "lighter_1h_and_funding", "start": start, "end_exclusive": end, "files": {},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for coin in coins:
        k = carrylane.lighter_prices(coin, s0, s1)
        k = k[(k.t >= s0) & (k.t < s1)].reset_index(drop=True)
        f = carrylane.lighter_funding(coin, s0, s1)
        f = f[(f.t > s0) & (f.t <= s1)].drop_duplicates("t").sort_values("t").reset_index(drop=True)
        for sub, df in (("klines_1h", k), ("funding", f)):
            p = OUT / sub / f"{coin}.parquet"
            df.to_parquet(p, index=False)
            man["files"][f"{sub}/{coin}.parquet"] = {"rows": len(df),
                                                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        print(coin, len(k), "candles", len(f), "funding", flush=True)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(coins), "markets")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("universe")
    b = sub.add_parser("bars")
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    a = ap.parse_args()
    if a.cmd == "universe":
        universe()
    else:
        bars(a.start, a.end)


if __name__ == "__main__":
    main()
