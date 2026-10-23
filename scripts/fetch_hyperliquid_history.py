"""Hyperliquid public history for every listed perp (POST api.hyperliquid.xyz/info, no keys): hourly funding with
premium since 2023-05 (500 rows per call, paged), daily candles over the full history, and hourly candles for the last
5,000 hours (the API's limit). For the cross-venue funding spread (old E02 hl_carry) and an on-chain venue sample.
Throttled to about one request a second (the API weighs info calls). Saved in data/hyperliquid/{funding,candles_1d,
candles_1h}/<COIN>.parquet; a coin whose file exists is skipped, so it resumes. Data collection only.

usage: python scripts/fetch_hyperliquid_history.py [--pause 1.1]
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

API = "https://api.hyperliquid.xyz/info"
OUT = data.ROOT / "hyperliquid"
START = 1_682_899_200_000          # 2023-05-01, before the first funding record
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def post(body, tries=5):
    delay = 2.0
    for _ in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{body}: {err}")


def funding(coin, now, pause):
    rows, s = [], START
    while s < now:
        d = post({"type": "fundingHistory", "coin": coin, "startTime": s})
        time.sleep(pause)
        if not d:
            break
        rows += d
        last = int(d[-1]["time"])
        if last <= s or len(d) < 500:
            break
        s = last + 1
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.rename(columns={"time": "t", "fundingRate": "rate"}).drop(columns="coin")
    return df.astype({"t": "int64", "rate": float, "premium": float}).drop_duplicates("t").sort_values("t")


def candles(coin, interval, now, pause):
    d = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": 0, "endTime": now}})
    time.sleep(pause)
    df = pd.DataFrame(d)
    if df.empty:
        return df
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume", "n": "trades"})
    return df[["t", "open", "high", "low", "close", "volume", "trades"]].astype(
        {"t": "int64", "open": float, "high": float, "low": float, "close": float, "volume": float})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pause", type=float, default=1.1)
    a = ap.parse_args()
    now = int(time.time() * 1000)
    coins = [u["name"] for u in post({"type": "meta"})["universe"]]
    log(f"{len(coins)} perps")
    status = {}
    for i, coin in enumerate(coins, 1):
        status[coin] = {}
        for kind, fn in (("candles_1d", lambda c: candles(c, "1d", now, a.pause)),
                         ("candles_1h", lambda c: candles(c, "1h", now, a.pause)),
                         ("funding", lambda c: funding(c, now, a.pause))):
            path = OUT / kind / f"{coin}.parquet"
            if path.exists():
                status[coin][kind] = "skip"
                continue
            try:
                df = fn(coin)
            except RuntimeError as e:
                status[coin][kind] = f"error {e}"
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
            status[coin][kind] = len(df)
        if i % 20 == 0:
            log(f"{i}/{len(coins)} {coin}: {status[coin]}")
    (OUT / "manifest.json").write_text(json.dumps({"source": API, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                   time.gmtime()), "coins": status}, indent=1))
    log("done")


if __name__ == "__main__":
    main()
