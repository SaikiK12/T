"""Inputs for R474 tltcarry_fwd (short xyz:TLT, long iShares $ Treasury Bond 20+yr UCITS ETF). Public and keyless.

xyz   -> <out>/xyz/funding.csv (Hyperliquid fundingHistory of xyz:TLT: time ms, fundingRate per hour, premium;
         positive when longs pay) and <out>/xyz/candles_1h.csv (candleSnapshot 1h: open time ms, open, close).
yahoo -> <out>/yahoo/<NAME>.json (raw chart response) and <NAME>.parquet (date, close, adjclose) for DTLA.L (the ETF,
         USD, accumulating, London) and ^IRX (the 13-week Treasury bill rate, percent), through R471's frozen parser.
<out>/manifest.json lists every file's sha256. Paced, generic client name.

usage: python scripts/fetch_tltcarry.py --start 2026-09-17 --end 2026-11-14 --out data/tltcarry/held
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
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_cryptomon import CHART, UA, epoch, parse_chart  # noqa: E402  (frozen in R471)

INFO = "https://api.hyperliquid.xyz/info"
COIN = "xyz:TLT"
YAHOO = {"DTLA": "DTLA.L", "IRX": "%5EIRX"}


def ms(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def post(body):
    req = urllib.request.Request(INFO, data=json.dumps(body).encode(), headers={"User-Agent": UA,
                                                                                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def funding(start_ms, end_ms):
    rows, t = [], start_ms
    while t < end_ms:
        page = post({"type": "fundingHistory", "coin": COIN, "startTime": t, "endTime": end_ms})
        if not page:
            break
        rows += page
        t = int(page[-1]["time"]) + 1
        if len(page) < 500:
            break
        time.sleep(1)
    df = pd.DataFrame(rows, columns=["time", "fundingRate", "premium"]).drop_duplicates("time")
    return df.sort_values("time").reset_index(drop=True)


def candles(start_ms, end_ms):
    page = post({"type": "candleSnapshot", "req": {"coin": COIN, "interval": "1h", "startTime": start_ms,
                                                   "endTime": end_ms}})
    df = pd.DataFrame(page)
    df = df.rename(columns={"t": "open_ms", "o": "open", "c": "close"})[["open_ms", "open", "close"]] if len(df) \
        else pd.DataFrame(columns=["open_ms", "open", "close"])
    return df.drop_duplicates("open_ms").sort_values("open_ms").reset_index(drop=True)


def fetch(start, end, out):
    out = Path(out)
    (out / "xyz").mkdir(parents=True, exist_ok=True)
    (out / "yahoo").mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (fundingHistory, candleSnapshot) and "
                     "query1.finance.yahoo.com/v8/finance/chart (public, no key)",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a, b = ms(start), ms(end)
    funding(a, b).to_csv(out / "xyz" / "funding.csv", index=False)
    candles(a, b).to_csv(out / "xyz" / "candles_1h.csv", index=False)
    for name, sym in YAHOO.items():
        req = urllib.request.Request(CHART.format(t=sym, a=epoch(start), b=epoch(end)), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
        (out / "yahoo" / f"{name}.json").write_bytes(raw)
        parse_chart(json.loads(raw))[["date", "close", "adjclose"]].to_parquet(out / "yahoo" / f"{name}.parquet",
                                                                               index=False)
        time.sleep(3)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
