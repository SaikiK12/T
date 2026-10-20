"""Binance spot hourly klines from data.binance.vision for every perp with a USDT spot pair (data/spot_pairs.json,
481 pairs): the spot leg for carry and basis lanes (M047, C09). Monthly files from 2020-01 through data.END. Raw
zips are cached under data/raw/ like the perp archive (CRC-checked by lab.data.fetch); one parquet per perp symbol
in data/spot_1h/ with t in epoch ms (2025+ files use microseconds; lab.data.parse converts). Writes a manifest of
files per symbol. Resumable. Data collection only.

usage: python scripts/fetch_spot.py [--workers 16]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "spot_1h"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def keys_for(spot):
    keys = data.list_zips(f"data/spot/monthly/klines/{spot}/1h/")
    return [k for k in keys if data._DATE.search(k).group(1) <= data.END[:7]]


def one(perp, spot):
    path = OUT / f"{perp}.parquet"
    if path.exists():
        return perp, spot, "skip", 0
    keys = keys_for(spot)
    frames = []
    for k in keys:
        p = data.fetch(k, data.ROOT / "raw")
        if p is not None:
            frames.append(data.parse(p, "klines"))
    if not frames:
        return perp, spot, "none", 0
    df = pd.concat(frames).drop_duplicates("t").sort_values("t").reset_index(drop=True)
    df.to_parquet(path, index=False)
    return perp, spot, f"{len(df)} bars", len(keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = json.loads((data.ROOT / "spot_pairs.json").read_text())
    log(f"{len(pairs)} perp -> spot pairs")
    old = OUT / "manifest.json"
    prev = json.loads(old.read_text())["pairs"] if old.exists() else {}   # a rerun keeps the entries it skips
    manifest, errors = {}, []
    with ThreadPoolExecutor(a.workers) as ex:
        jobs = [(perp, v["spot"]) for perp, v in sorted(pairs.items())]
        futs = [ex.submit(one, perp, spot) for perp, spot in jobs]
        for i, f in enumerate(futs, 1):
            try:
                perp, spot, msg, n = f.result()
                manifest[perp] = prev.get(perp) if msg == "skip" and perp in prev else {"spot": spot, "files": n, "status": msg}
            except Exception as e:  # noqa: BLE001 - logged and listed in the manifest
                errors.append(f"{jobs[i - 1][0]}: {e}")
            if i % 50 == 0:
                log(f"{i}/{len(jobs)}")
    (OUT / "manifest.json").write_text(json.dumps({"source": data.BASE + "/data/spot/monthly/klines", "end": data.END,
                                                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                   "pairs": manifest, "errors": errors}, indent=1))
    log(f"done: {sum(v['status'] != 'none' for v in manifest.values())} with data, {len(errors)} errors")


if __name__ == "__main__":
    main()
