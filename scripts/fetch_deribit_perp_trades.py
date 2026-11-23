"""Inputs for R522 dmake_v1: every trade of Deribit's linear USDC perps created 2026-08-01..10-31 whose base is on
Hyperliquid, from each instrument's creation to --end. Keyless, public Deribit history server; run once after the
freeze.

Source: https://history.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time (full history; the main
server keeps only the last few days). Each trade: timestamp, price, amount, direction (the taker's side),
index_price, mark_price.

Writes data/deribit_trades/<BASE>.parquet and data/deribit_trades/manifest.json (sha256 of every file).

usage: python scripts/fetch_deribit_trades.py --end 2026-11-20
"""
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
API = "https://history.deribit.com/api/v2/public/get_last_trades_by_instrument_and_time"
COLS = ["timestamp", "trade_seq", "price", "amount", "direction", "index_price", "mark_price"]


def universe(root=ROOT):
    inst = json.loads((root / "data" / "deribit_perps" / "instruments.json").read_text())
    sym = pd.read_csv(root / "experiments" / "deribitgap_v1" / "results" / "symbols.csv")
    lo, hi = pd.Timestamp("2026-08-01", tz="UTC"), pd.Timestamp("2026-11-01", tz="UTC")
    out = []
    for x in inst:
        if x.get("settlement_period") != "perpetual" or x.get("instrument_type") != "linear":
            continue
        b = x["instrument_name"].split("_USDC")[0]
        c = pd.Timestamp(x["creation_timestamp"], unit="ms", tz="UTC")
        if b in set(sym.deribit) and lo <= c < hi:
            out.append((b, int(x["creation_timestamp"])))
    return sorted(out)


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["result"]
        except Exception:
            time.sleep(2 * (k + 1))
    raise SystemExit(f"failed: {params}")


def trades(base, start, end):
    rows, t = [], start
    while t < end:
        r = get({"instrument_name": f"{base}_USDC-PERPETUAL", "start_timestamp": t, "end_timestamp": end,
                 "count": 1000, "sorting": "asc"})
        tr = r.get("trades", [])
        rows += [{c: x.get(c) for c in COLS} for x in tr]
        if not r.get("has_more") or not tr:
            break
        t = int(tr[-1]["timestamp"])               # same-millisecond trades: dedupe on trade_seq below
        time.sleep(0.1)
    df = pd.DataFrame(rows, columns=COLS)
    return df.drop_duplicates("trade_seq").sort_values(["timestamp", "trade_seq"], ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    out = ROOT / "data" / "deribit_trades"
    out.mkdir(parents=True, exist_ok=True)
    end = int(pd.Timestamp(a.end, tz="UTC").value // 10**6)
    for base, created in universe():
        trades(base, created, end).to_parquet(out / f"{base}.parquet", index=False)
    man = {"source": API, "end": a.end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.parquet"))}}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({"files": len(man["files"])}))


if __name__ == "__main__":
    main()
