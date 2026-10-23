"""Small public histories for lanes outside the Binance archive: Deribit's hourly implied-volatility index (DVOL, BTC
and ETH, from 2021-03), Coinbase hourly spot candles (BTC-USD, ETH-USD, USDT-USD) and Binance hourly spot klines
(BTCUSDT, ETHUSDT). Cached in data/deribit/, data/coinbase/ and data/binance_spot/ (gitignored) and merged on each
run. Data collection only.

usage: python scripts/fetch_extra.py [--start 2021-01-01]
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

HOUR = 3_600_000
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


def merge(path, df):
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df])
    df = df.drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def dvol(currency, start_ms, end_ms):
    """Deribit returns the newest 1,000 rows of the range and a continuation (an end timestamp) to page backwards."""
    rows, end = [], end_ms
    while True:
        d = get("https://www.deribit.com/api/v2/public/get_volatility_index_data?"
                f"currency={currency}&start_timestamp={start_ms}&end_timestamp={end}&resolution=3600")["result"]
        rows += d["data"]
        nxt = d.get("continuation")
        if not d["data"] or not nxt or nxt <= start_ms:
            break
        end = nxt
        time.sleep(0.2)
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close"])
    return df.assign(t=df.t.astype(np.int64))


def coinbase(product, start_ms, end_ms):
    """300 hourly candles per call: [time s, low, high, open, close, volume]; time is the bar's open."""
    rows, s = [], start_ms // 1000
    step = 300 * 3600
    while s * 1000 < end_ms:
        e = min(s + step, end_ms // 1000)
        iso = lambda x: pd.Timestamp(x, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
        rows += get(f"https://api.exchange.coinbase.com/products/{product}/candles?granularity=3600"
                    f"&start={iso(s)}&end={iso(e)}")
        s = e
        time.sleep(0.25)
    df = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "volume"])
    return df.assign(t=df.t.astype(np.int64) * 1000)


def binance_spot(symbol, start_ms, end_ms):
    """1,000 hourly klines per call from www.binance.com (api.binance.com is not used); t is the bar's open."""
    rows, s = [], start_ms
    while s < end_ms:
        d = get(f"https://www.binance.com/api/v3/klines?symbol={symbol}&interval=1h&startTime={s}&limit=1000")
        if not d:
            break
        rows += d
        s = int(d[-1][0]) + HOUR
        time.sleep(0.2)
    df = pd.DataFrame([r[:6] for r in rows], columns=["t", "open", "high", "low", "close", "volume"])
    return df.astype({"t": np.int64, "open": float, "high": float, "low": float, "close": float, "volume": float})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-01-01")
    a = ap.parse_args()
    start = int(pd.Timestamp(a.start, tz="UTC").value // 10**6)
    now = int(time.time() * 1000) // HOUR * HOUR
    for cur in ("BTC", "ETH"):
        path = data.ROOT / "deribit" / f"dvol_{cur}.parquet"
        s0 = int(pd.read_parquet(path).t.max()) if path.exists() else start
        df = merge(path, dvol(cur, s0, now))
        log(f"DVOL {cur}: {len(df)} rows, {pd.Timestamp(df.t.min(), unit='ms').date()} .. "
            f"{pd.Timestamp(df.t.max(), unit='ms')}")
    for prod in ("BTC-USD", "ETH-USD", "USDT-USD"):
        path = data.ROOT / "coinbase" / f"{prod}.parquet"
        s0 = int(pd.read_parquet(path).t.max()) if path.exists() else start
        df = merge(path, coinbase(prod, s0, now))
        log(f"Coinbase {prod}: {len(df)} rows, {pd.Timestamp(df.t.min(), unit='ms').date()} .. "
            f"{pd.Timestamp(df.t.max(), unit='ms')}")
    for sym in ("BTCUSDT", "ETHUSDT"):
        path = data.ROOT / "binance_spot" / f"{sym}.parquet"
        s0 = int(pd.read_parquet(path).t.max()) if path.exists() else start
        df = merge(path, binance_spot(sym, s0, now))
        log(f"Binance spot {sym}: {len(df)} rows, {pd.Timestamp(df.t.min(), unit='ms').date()} .. "
            f"{pd.Timestamp(df.t.max(), unit='ms')}")


if __name__ == "__main__":
    main()
