"""Gate.io USDT-perp hourly contract stats (top-trader and all-account long/short ratios, taker sizes, liquidations,
open interest) for the coins of the Binance research universe. Gate keeps 180 days, so this is refetchable until each
hour ages out; it is cached in data/gate_1h/ (gitignored) and merged on each run. Data collection only.

usage: python scripts/fetch_gate.py [--days 179]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "gate_1h"
API = "https://api.gateio.ws/api/v4/futures/usdt"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=4):
    delay = 2.0
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab/1"}), timeout=30) as r:
                return json.loads(r.read())
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url}: {err}")


def gate_name(binance_symbol):
    base = binance_symbol[:-4]
    return f"{base}_USDT"


def fetch(contract, start, end):
    rows, s = [], start
    while s < end:
        d = get(f"{API}/contract_stats?contract={urllib.parse.quote(contract)}&interval=1h&from={s}&limit=1000")
        if not d:
            break
        rows += d
        last = int(d[-1]["time"])
        if last <= s or len(d) < 1000:
            break
        s = last + 3600
        time.sleep(0.2)
    if not rows:
        return None
    df = pd.DataFrame(rows).drop_duplicates("time")
    df["t"] = df["time"].astype(np.int64) * 1000
    num = [c for c in df.columns if c not in ("time", "t")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")
    return df.drop(columns=["time"]).sort_values("t")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=179)
    a = ap.parse_args()
    contracts = {c["name"] for c in get(f"{API}/contracts")}
    rd = data.ROOT / "research"
    meta = json.loads((rd / "meta.json").read_text())
    elig = np.load(rd / "elig.npy", mmap_mode="r")
    now = int(time.time())
    start = now - a.days * 86400
    t = np.load(rd / "t.npy")
    recent = t >= (start * 1000)
    syms = [s for j, s in enumerate(meta["symbols"]) if np.asarray(elig[recent, j]).any()]
    OUT.mkdir(parents=True, exist_ok=True)
    have = 0
    for i, s in enumerate(syms):
        g = gate_name(s)
        if g not in contracts:
            continue
        path = OUT / f"{s}.parquet"
        s0 = start
        old = pd.read_parquet(path) if path.exists() else None
        if old is not None and len(old):
            s0 = max(start, int(old["t"].max()) // 1000)
        df = fetch(g, s0, now)
        if df is not None:
            if old is not None:
                df = pd.concat([old, df]).drop_duplicates("t", keep="last").sort_values("t")
            df.to_parquet(path, index=False)
            have += 1
        if i % 20 == 0:
            log(f"{i + 1}/{len(syms)} {s}")
    log(f"{have} contracts written of {len(syms)} Binance symbols eligible in the window")


if __name__ == "__main__":
    main()
