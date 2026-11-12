"""Inputs for R475 hip3stock_v1 (short trade.xyz US-stock perps with high trailing funding, long the stock).

universe -> <out>/universe.csv: every xyz market in Hyperliquid's meta (delisted ones included) whose ticker is, on
            Yahoo's chart metadata, an EQUITY quoted in USD on a US exchange; with its growth-mode flag, maximum
            leverage and first funding print. ETFs, indices, commodities and non-US names are left out (a French
            retail account cannot buy US-listed ETFs, and the other underlyings are not reachable as a stock).
xyz      -> <out>/xyz/<TICKER>_funding.csv (every hourly print: time ms, fundingRate, premium) and
            <out>/xyz/<TICKER>_4h.csv (4-hour candles: open_ms, open, high, low, close, volume in units).
yahoo    -> <out>/yahoo/<TICKER>.json (raw) and .parquet (date, close, adjclose) through R471's frozen parser, plus
            IRX (the 13-week bill, percent).
<out>/manifest.json lists every file's sha256. Keyless, paced, generic client name, retries on HTTP 429.

usage: python scripts/fetch_hip3stock.py --start 2025-10-01 --end 2026-11-12 --out data/hip3stock
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from fetch_cryptomon import CHART, UA, epoch, parse_chart  # noqa: E402  (frozen in R471)

INFO = "https://api.hyperliquid.xyz/info"
DEX = "xyz"
META = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=5d&interval=1d"
US = {"NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS"}


def ms(day):
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def request(url, body=None):
    head = {"User-Agent": UA}
    data = None
    if body is not None:
        head["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    for k in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=head), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code != 429 or k == 5:
                raise
            time.sleep(20 * (k + 1))


def post(body):
    return json.loads(request(INFO, body))


def funding(coin, start_ms, end_ms):
    rows, t = [], start_ms
    while t < end_ms:
        page = post({"type": "fundingHistory", "coin": coin, "startTime": t, "endTime": end_ms})
        if not page:
            break
        rows += page
        t = int(page[-1]["time"]) + 1
        if len(page) < 500:
            break
        time.sleep(1.5)
    df = pd.DataFrame(rows, columns=["time", "fundingRate", "premium"]).drop_duplicates("time")
    return df.sort_values("time").reset_index(drop=True)


def candles(coin, start_ms, end_ms):
    """4-hour candles (the venue keeps the latest 5,000 per interval, back past every xyz listing); paged."""
    rows, t = [], start_ms
    while t < end_ms:
        page = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "4h", "startTime": t,
                                                       "endTime": end_ms}}) or []
        rows += page
        if len(page) < 5000:
            break
        t = int(page[-1]["t"]) + 1
        time.sleep(1.5)
    cols = ["open_ms", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(rows)
    if not len(df):
        return pd.DataFrame(columns=cols)
    df = df.rename(columns={"t": "open_ms", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[cols].drop_duplicates("open_ms").sort_values("open_ms")


def yahoo_meta(ticker):
    raw = request(META.format(t=ticker))
    res = (json.loads(raw).get("chart", {}).get("result") or [None])[0] if raw else None
    return (res or {}).get("meta", {})


def universe():
    meta = post({"type": "meta", "dex": DEX})
    rows = []
    for u in meta["universe"]:
        coin = u["name"]
        tick = coin.split(":", 1)[1]
        m = yahoo_meta(tick)
        time.sleep(1.0)
        ok = m.get("instrumentType") == "EQUITY" and m.get("currency") == "USD" and m.get("exchangeName") in US
        rows.append({"coin": coin, "ticker": tick, "equity": int(ok), "delisted": int(bool(u.get("isDelisted"))),
                     "growth": u.get("growthMode") or "", "max_lev": u.get("maxLeverage"),
                     "y_type": m.get("instrumentType") or "", "y_exchange": m.get("exchangeName") or "",
                     "y_name": (m.get("longName") or m.get("shortName") or "").replace(",", " ")})
    return pd.DataFrame(rows)


def fetch(start, end, out):
    out = Path(out)
    for sub in ("xyz", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (meta, fundingHistory, candleSnapshot 4h; dex xyz) and "
                     "query1.finance.yahoo.com/v8/finance/chart (public, no key)",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a, b = ms(start), ms(end)
    uni = universe()
    first = []
    for _, r in uni.iterrows():
        if not r["equity"]:
            first.append("")
            continue
        f = funding(r["coin"], a, b)
        f.to_csv(out / "xyz" / f"{r['ticker']}_funding.csv", index=False)
        candles(r["coin"], a, b).to_csv(out / "xyz" / f"{r['ticker']}_4h.csv", index=False)
        first.append(pd.to_datetime(int(f["time"].iloc[0]), unit="ms").strftime("%Y-%m-%d") if len(f) else "")
        time.sleep(1.5)
    uni["first_funding"] = first
    uni.to_csv(out / "universe.csv", index=False)
    for t in [*uni.loc[uni["equity"] == 1, "ticker"], "IRX"]:
        sym = "%5EIRX" if t == "IRX" else t
        raw = request(CHART.format(t=sym, a=epoch(start), b=epoch(end)))
        (out / "yahoo" / f"{t}.json").write_bytes(raw)
        parse_chart(json.loads(raw))[["date", "close", "adjclose"]].to_parquet(out / "yahoo" / f"{t}.parquet",
                                                                               index=False)
        time.sleep(2)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print("markets", len(uni), "US equities", int(uni["equity"].sum()), "files", len(man["files"]), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "hip3stock"))
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
