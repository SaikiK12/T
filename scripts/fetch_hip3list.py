"""Inputs for R517 hip3list_v1: funding and 4-hour candles of every HIP-3 market whose ticker is listed on two or more
HIP-3 dexes. Keyless, public Hyperliquid info API; run once after the freeze.

- **Universe.** Every dex in perpDexs (the main dex excluded) and every market in its meta, delisted ones included.
  A base is the market name after "dex:". Bases listed on at least two dexes are kept. Names are not merged across
  spellings: US500 and USA500 stay apart.
- **Files:**
  - <out>/universe.csv: dex, coin, base, delisted, first_funding (UTC day);
  - <out>/funding/<dex>_<base>.parquet (t ms, rate per hour);
  - <out>/prices/<dex>_<base>.parquet (t = 4 h bar open ms, close, volume);
  - <out>/manifest.json: every file's sha256.
- **Client.** R475's frozen client (`fetch_hip3stock.post/funding/candles`): paced, with retries.

usage: python scripts/fetch_hip3list.py --end 2026-11-20 --out data/hip3list
"""
import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)

START = "2025-10-01"


def shared(markets):
    """Rows of `markets` (dicts with dex, coin) whose base is listed on two or more dexes."""
    by = defaultdict(set)
    for m in markets:
        by[m["coin"].split(":", 1)[-1]].add(m["dex"])
    return [dict(m, base=m["coin"].split(":", 1)[-1]) for m in markets
            if len(by[m["coin"].split(":", 1)[-1]]) >= 2]


def universe():
    out = []
    for d in fs.post({"type": "perpDexs"}):
        if not d:
            continue
        time.sleep(1.0)
        for u in fs.post({"type": "meta", "dex": d["name"]})["universe"]:
            out.append({"dex": d["name"], "coin": u["name"], "delisted": int(bool(u.get("isDelisted")))})
    return shared(out)


def fetch(end, out):
    out = Path(out)
    for sub in ("funding", "prices"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    a, b = fs.ms(START), fs.ms(end)
    rows = universe()
    for r in rows:
        name = f"{r['dex']}_{r['base']}"
        f = fs.funding(r["coin"], a, b)
        pd.DataFrame({"t": f["time"].astype("int64"), "rate": f["fundingRate"].astype(float)}).to_parquet(
            out / "funding" / f"{name}.parquet", index=False)
        c = fs.candles(r["coin"], a, b)
        pd.DataFrame({"t": c["open_ms"].astype("int64"), "close": c["close"].astype(float),
                      "volume": c["volume"].astype(float)}).to_parquet(out / "prices" / f"{name}.parquet", index=False)
        r["first_funding"] = pd.to_datetime(int(f["time"].iloc[0]), unit="ms").strftime("%Y-%m-%d") if len(f) else ""
        time.sleep(1.0)
    pd.DataFrame(rows).to_csv(out / "universe.csv", index=False)
    man = {"source": "api.hyperliquid.xyz/info (perpDexs, meta, fundingHistory, candleSnapshot 4h)", "start": START,
           "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({"markets": len(rows), "files": len(man["files"])}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "hip3list"))
    a = ap.parse_args()
    fetch(a.end, a.out)


if __name__ == "__main__":
    main()
