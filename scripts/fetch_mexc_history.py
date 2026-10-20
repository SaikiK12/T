"""Download MEXC public history for every crypto USDT perpetual listed today: hourly contract klines, hourly index
klines and settled funding, from 2025-04-01 (funding history starts 2025-04-27 on every contract) to the last closed
hour. Writes data/mexc_hist/ only (the forward lanes' caches under data/mexc/ are left alone). Resumable: a symbol
whose three files exist is skipped. Public endpoints, no keys.

usage: python scripts/fetch_mexc_history.py [--workers 4]
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
from lab import data, mexc, panel  # noqa: E402

OUT = data.ROOT / "mexc_hist"
START = panel.ms("2025-04-01")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def one(sym, end):
    paths = {k: OUT / k / f"{sym}.parquet" for k in ("klines_1h", "index_price_1h", "funding")}
    if all(p.exists() for p in paths.values()):
        return sym, "skip"
    try:
        got = {"klines_1h": mexc.fetch_klines(sym, START, end),
               "index_price_1h": mexc.fetch_klines(sym, START, end, kind="index_price"),
               "funding": mexc.funding_history(sym, START, end)}
    except mexc.MexcError as e:
        return sym, f"error {e}"
    for k, df in got.items():
        paths[k].parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(paths[k], index=False)
    return sym, f"{len(got['klines_1h'])} bars, {len(got['funding'])} settlements"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    table = mexc.contracts(refresh=True)
    crypto = table[table.type == 1]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "contracts.json").write_text(crypto.to_json(orient="records"))
    end = int(time.time() * 1000) // mexc.HOUR * mexc.HOUR - mexc.HOUR    # open time of the last closed bar + 1 h
    log(f"{len(crypto)} crypto contracts; history {pd.Timestamp(START, unit='ms')} .. {pd.Timestamp(end, unit='ms')}")
    errors = []
    with ThreadPoolExecutor(a.workers) as ex:
        for i, (sym, msg) in enumerate(ex.map(lambda s: one(s, end), sorted(crypto.symbol)), 1):
            if msg.startswith("error"):
                errors.append(sym)
            if i % 25 == 0 or msg.startswith("error"):
                log(f"{i}/{len(crypto)} {sym}: {msg}")
    (OUT / "manifest.json").write_text(json.dumps({"start": START, "end": end, "contracts": len(crypto),
                                                   "errors": errors, "fetched_at": time.strftime("%Y-%m-%dT%H:%MZ")}))
    log(f"done; {len(errors)} errors: {errors[:20]}")


if __name__ == "__main__":
    main()
