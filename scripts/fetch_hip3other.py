"""Inputs for R476 hip3other_v1: R475's frozen rule on the US-stock perps of every other HIP-3 deployer. Keyless.

Every HIP-3 dex in Hyperliquid's perpDexs except xyz (Felix, Ventuals, HyENA, Kinetiq, Dreamcash, Paragon, mkts,
EntropyIO and any other at fetch time), delisted markets included. A market stays if Yahoo's chart metadata calls its
ticker an EQUITY quoted in USD on a US exchange (R475's filter, `fetch_hip3stock.US`).

The files mirror R475's layout so that `run_hip3stock.load` reads them unchanged, with names <DEX>_<TICKER> because
two deployers can list the same stock:
universe -> <out>/universe.csv (coin, ticker = <DEX>_<TICKER>, dex, stock, equity, delisted, growth, max_lev, ...).
xyz      -> <out>/xyz/<DEX>_<TICKER>_funding.csv and _4h.csv (the folder keeps R475's name; it holds every dex).
yahoo    -> <out>/yahoo/<TICKER>.json (raw), <out>/yahoo/<DEX>_<TICKER>.parquet (one copy per listing) and IRX.
<out>/manifest.json lists every file's sha256. Paced, generic client name, retries on HTTP 429 (R475's client).

usage: python scripts/fetch_hip3other.py --start 2025-10-01 --end 2026-11-12 --out data/hip3other
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)
from fetch_cryptomon import CHART, epoch, parse_chart  # noqa: E402  (frozen in R471)

SKIP = {"xyz"}


def universe():
    dexes = [d["name"] for d in fs.post({"type": "perpDexs"}) if d and d["name"] not in SKIP]
    seen, rows = {}, []
    for dex in dexes:
        time.sleep(1.5)
        for u in fs.post({"type": "meta", "dex": dex})["universe"]:
            coin = u["name"]
            stock = coin.split(":", 1)[1]
            if stock not in seen:
                seen[stock] = fs.yahoo_meta(stock)
                time.sleep(1.0)
            m = seen[stock]
            ok = m.get("instrumentType") == "EQUITY" and m.get("currency") == "USD" and m.get("exchangeName") in fs.US
            rows.append({"coin": coin, "ticker": f"{dex}_{stock}", "dex": dex, "stock": stock, "equity": int(ok),
                         "delisted": int(bool(u.get("isDelisted"))), "growth": u.get("growthMode") or "",
                         "max_lev": u.get("maxLeverage"), "y_type": m.get("instrumentType") or "",
                         "y_exchange": m.get("exchangeName") or "",
                         "y_name": (m.get("longName") or m.get("shortName") or "").replace(",", " ")})
    return pd.DataFrame(rows)


def fetch(start, end, out):
    out = Path(out)
    for sub in ("xyz", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (perpDexs, meta, fundingHistory, candleSnapshot 4h; every HIP-3 dex "
                     "but xyz) and query1.finance.yahoo.com/v8/finance/chart (public, no key)",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a, b = fs.ms(start), fs.ms(end)
    uni = universe()
    first = []
    for _, r in uni.iterrows():
        if not r["equity"]:
            first.append("")
            continue
        f = fs.funding(r["coin"], a, b)
        f.to_csv(out / "xyz" / f"{r['ticker']}_funding.csv", index=False)
        fs.candles(r["coin"], a, b).to_csv(out / "xyz" / f"{r['ticker']}_4h.csv", index=False)
        first.append(pd.to_datetime(int(f["time"].iloc[0]), unit="ms").strftime("%Y-%m-%d") if len(f) else "")
        time.sleep(1.5)
    uni["first_funding"] = first
    uni.to_csv(out / "universe.csv", index=False)
    eq = uni[uni["equity"] == 1]
    for stock in [*sorted(eq["stock"].unique()), "IRX"]:
        sym = "%5EIRX" if stock == "IRX" else stock
        raw = fs.request(CHART.format(t=sym, a=epoch(start), b=epoch(end)))
        (out / "yahoo" / f"{stock}.json").write_bytes(raw)
        px = parse_chart(json.loads(raw))[["date", "close", "adjclose"]]
        for name in (["IRX"] if stock == "IRX" else eq.loc[eq["stock"] == stock, "ticker"]):
            px.to_parquet(out / "yahoo" / f"{name}.parquet", index=False)
        time.sleep(2)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print("markets", len(uni), "US-equity listings", len(eq), "files", len(man["files"]), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "hip3other"))
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
