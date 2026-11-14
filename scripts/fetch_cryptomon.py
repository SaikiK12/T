"""Inputs for R471 cryptomon_v1 (does a Bitcoin-linked US stock keep moving after Monday's open in the direction of
Bitcoin's weekend move?). Public and keyless.

btc    -> data/cryptomon/binance/klines_1h/BTCUSDT.parquet (+ manifest), Binance's public archive through
          lab/data.py (data.binance.vision, USD-M BTCUSDT perp 1 h klines, each file checked against its published
          SHA-256).
stocks -> data/cryptomon/yahoo/<TICKER>.json (raw chart response) and <TICKER>.parquet (date in New York, open,
          high, low, close, adjclose, volume), from Yahoo's public chart endpoint (query1.finance.yahoo.com/v8/finance/
          chart, interval 1d, splits and dividends included), paced 3 s apart with a generic client name.
          data/cryptomon/yahoo/manifest.json lists every file's sha256.

usage: python scripts/fetch_cryptomon.py btc --end 2026-11-11
       python scripts/fetch_cryptomon.py stocks --start 2020-06-01 --end 2026-11-12
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data as bdata  # noqa: E402

OUT = ROOT / "data" / "cryptomon"
TICKERS = ("MSTR", "COIN", "MARA", "RIOT", "HOOD", "IREN", "QQQ")
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={a}&period2={b}&interval=1d&events=div%7Csplit"
UA = "Mozilla/5.0 (research client)"


def epoch(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def parse_chart(js):
    """Yahoo chart JSON -> frame of daily rows (date = New York session date)."""
    r = js["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    adj = r["indicators"].get("adjclose", [{}])[0].get("adjclose")
    tz = r["meta"].get("exchangeTimezoneName", "America/New_York")
    stamps = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz)
    df = pd.DataFrame({"date": stamps.strftime("%Y-%m-%d"), "open": q["open"], "high": q["high"], "low": q["low"],
                       "close": q["close"], "adjclose": adj if adj else q["close"], "volume": q["volume"]})
    return df.dropna(subset=["open", "close"]).drop_duplicates("date", keep="last").reset_index(drop=True)


def stocks(start, end):
    out = OUT / "yahoo"
    out.mkdir(parents=True, exist_ok=True)
    man = {"source": "query1.finance.yahoo.com/v8/finance/chart (public, no key)", "start": start, "end": end,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    for t in TICKERS:
        req = urllib.request.Request(CHART.format(t=t, a=epoch(start), b=epoch(end)), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        js = json.loads(raw)
        (out / f"{t}.json").write_bytes(raw)
        df = parse_chart(js)
        df.to_parquet(out / f"{t}.parquet", index=False)
        for name in (f"{t}.json", f"{t}.parquet"):
            man["files"][name] = {"sha256": hashlib.sha256((out / name).read_bytes()).hexdigest()}
        man["files"][f"{t}.parquet"]["rows"] = len(df)
        print(t, len(df), df["date"].iloc[0] if len(df) else None, df["date"].iloc[-1] if len(df) else None, flush=True)
        time.sleep(3)
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")


def btc(end):
    bdata.build("klines", "1h", symbols=["BTCUSDT"], strict=True, end=end, root=OUT / "binance", workers=8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["btc", "stocks"])
    ap.add_argument("--start", default="2020-06-01")
    ap.add_argument("--end", required=True)
    a = ap.parse_args()
    btc(a.end) if a.cmd == "btc" else stocks(a.start, a.end)


if __name__ == "__main__":
    main()
