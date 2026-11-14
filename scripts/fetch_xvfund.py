"""Inputs for R470 xvfund_v1 (cross-venue funding carry on the same US stock perp, trade.xyz against Lighter). Public
and keyless, through lab/carrylane.py (Hyperliquid info API; Lighter's paced client, 60 requests a minute).

bars -> data/xvfund/ (run after the freeze; gitignored, recorded with scripts/data_provenance.py)
    - xyz/funding/<COIN>.parquet       Hyperliquid fundingHistory of xyz:<COIN> (t ms, rate per hour, + when longs pay)
    - xyz/klines_1d/<COIN>.parquet     xyz:<COIN> 1d candles (t open ms, close, volume in base units)
    - lighter/funding/<COIN>.parquet   Lighter hourly funding (t ms, rate signed + when longs pay)
    - lighter/klines_1h/<COIN>.parquet Lighter 1 h candles (t open ms, close, volume in base units)
    - manifest.json (per-file sha256)

The pairs are R465's frozen experiments/ltwknd_v1/universe.csv: the 50 of R462's US-stock xyz markets that Lighter
lists under the same symbol.

usage: python scripts/fetch_xvfund.py bars --start 2025-11-01T00:00:00Z --end 2026-11-11T00:00:00Z
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

PAIRS = ROOT / "experiments" / "ltwknd_v1" / "universe.csv"
OUT = ROOT / "data" / "xvfund"


def coins():
    with open(PAIRS, newline="") as f:
        return [r["coin"] for r in csv.DictReader(f)]


def epoch_ms(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)


def bars(start, end):
    s0, s1 = epoch_ms(start), epoch_ms(end)
    man = {"kind": "xyz_and_lighter_funding_and_prices", "start": start, "end_exclusive": end, "files": {},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for coin in coins():
        got = {("xyz", "funding"): carrylane.hl_funding("xyz:" + coin, s0, s1),
               ("xyz", "klines_1d"): carrylane.hl_prices("xyz:" + coin, s0, s1),
               ("lighter", "funding"): carrylane.lighter_funding(coin, s0, s1),
               ("lighter", "klines_1h"): carrylane.lighter_prices(coin, s0, s1)}
        for (venue, sub), df in got.items():
            df = df[(df["t"] >= s0) & (df["t"] < s1)].drop_duplicates("t").sort_values("t", ignore_index=True)
            p = OUT / venue / sub / f"{coin}.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(p, index=False)
            man["files"][f"{venue}/{sub}/{coin}.parquet"] = {"rows": len(df),
                                                             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        print(coin, {f"{v}/{s}": len(d) for (v, s), d in got.items()}, flush=True)
        time.sleep(0.5)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(man["files"]), "files")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["bars"])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    bars(a.start, a.end)


if __name__ == "__main__":
    main()
