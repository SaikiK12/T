"""Binance COIN-M hourly klines from data.binance.vision for every contract in the archive (272: perpetuals and
dated quarterlies of about 10 coins, 2020 onward): the dated-futures basis term structure (M170, C09). Raw zips are
cached under data/raw/ (CRC-checked by lab.data.fetch); one parquet per contract in data/coinm_1h/, t in epoch ms.
Monthly files through data.END. Resumable. Data collection only.

usage: python scripts/fetch_coinm.py [--workers 16]
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

CM = "data/futures/cm/monthly/klines/"
OUT = data.ROOT / "coinm_1h"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def one(contract):
    path = OUT / f"{contract}.parquet"
    if path.exists():
        return contract, "skip"
    keys = [k for k in data.list_zips(f"{CM}{contract}/1h/") if data._DATE.search(k).group(1) <= data.END[:7]]
    frames = [data.parse(p, "klines") for p in (data.fetch(k, data.ROOT / "raw") for k in keys) if p is not None]
    if not frames:
        return contract, "none"
    df = pd.concat(frames).drop_duplicates("t").sort_values("t").reset_index(drop=True)
    df.to_parquet(path, index=False)
    return contract, f"{len(df)} bars"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    _, prefixes = data._list(CM)
    contracts = sorted(p.rstrip("/").rsplit("/", 1)[1] for p in prefixes)
    log(f"{len(contracts)} COIN-M contracts")
    status = {}
    with ThreadPoolExecutor(a.workers) as ex:
        for c, msg in ex.map(one, contracts):
            status[c] = msg
    (OUT / "manifest.json").write_text(json.dumps({"source": data.BASE + "/" + CM, "end": data.END,
                                                   "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                                   "contracts": status}, indent=1))
    log(f"done: {sum(v != 'none' for v in status.values())} of {len(contracts)} with data")


if __name__ == "__main__":
    main()
