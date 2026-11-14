"""Inputs for R477 xyztwin_v1: xyz index, ETF and metal perps against a USD UCITS ETF or ETC twin on the LSE. Keyless.

PAIRS (frozen in the PREREG) maps each xyz market to the twin a French retail account can hold. For each pair:
xyz   -> <out>/xyz/<PERP>_funding.csv and _4h.csv (R475's fetchers, `fetch_hip3stock.funding` and `.candles`).
yahoo -> <out>/yahoo/<TWIN>.json (raw chart) and <out>/yahoo/<PERP>.parquet (the twin's date, close, adjclose, named
         by the perp so R475's loader finds it), plus IRX.
<out>/universe.csv: coin, ticker (= PERP), twin, twin currency and exchange, equity (1 if the twin is quoted in USD),
delisted, growth, max_lev, first_funding. <out>/manifest.json lists every file's sha256.

usage: python scripts/fetch_xyztwin.py --start 2025-10-01 --end 2026-11-12 --out data/xyztwin
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

PAIRS = [("SMH", "SMH.L"), ("URNM", "URNM.L"), ("EWY", "CSKR.L"), ("KR200", "CSKR.L"), ("EWJ", "IJPA.L"),
         ("JP225", "IJPA.L"), ("NIFTY", "NDIA.L"), ("SP500", "CSPX.L"), ("XYZ100", "CNDX.L"), ("XLE", "XLES.L"),
         ("GOLD", "IGLN.L"), ("SILVER", "PHAG.L"), ("TLT", "DTLA.L")]


def fetch(start, end, out):
    out = Path(out)
    for sub in ("xyz", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (meta, fundingHistory, candleSnapshot 4h; dex xyz) and "
                     "query1.finance.yahoo.com/v8/finance/chart (public, no key)",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a, b = fs.ms(start), fs.ms(end)
    meta = {u["name"]: u for u in fs.post({"type": "meta", "dex": "xyz"})["universe"]}
    raw, rows = {}, []
    for perp, twin in PAIRS:
        coin = f"xyz:{perp}"
        u = meta.get(coin, {})
        f = fs.funding(coin, a, b) if u else pd.DataFrame(columns=["time", "fundingRate", "premium"])
        f.to_csv(out / "xyz" / f"{perp}_funding.csv", index=False)
        fs.candles(coin, a, b).to_csv(out / "xyz" / f"{perp}_4h.csv", index=False) if u else None
        time.sleep(1.5)
        if twin not in raw:
            raw[twin] = fs.request(CHART.format(t=twin, a=epoch(start), b=epoch(end)))
            (out / "yahoo" / f"{twin}.json").write_bytes(raw[twin])
            time.sleep(2)
        js = json.loads(raw[twin])
        m = js["chart"]["result"][0]["meta"]
        parse_chart(js)[["date", "close", "adjclose"]].to_parquet(out / "yahoo" / f"{perp}.parquet", index=False)
        rows.append({"coin": coin, "ticker": perp, "twin": twin, "twin_currency": m.get("currency") or "",
                     "twin_exchange": m.get("exchangeName") or "",
                     "equity": int(m.get("currency") == "USD" and bool(u)),
                     "delisted": int(bool(u.get("isDelisted"))), "growth": u.get("growthMode") or "",
                     "max_lev": u.get("maxLeverage"),
                     "first_funding": pd.to_datetime(int(f["time"].iloc[0]), unit="ms").strftime("%Y-%m-%d")
                     if len(f) else ""})
    pd.DataFrame(rows).to_csv(out / "universe.csv", index=False)
    irx = fs.request(CHART.format(t="%5EIRX", a=epoch(start), b=epoch(end)))
    (out / "yahoo" / "IRX.json").write_bytes(irx)
    parse_chart(json.loads(irx))[["date", "close", "adjclose"]].to_parquet(out / "yahoo" / "IRX.parquet", index=False)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print("pairs", len(rows), "files", len(man["files"]), flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-10-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(ROOT / "data" / "xyztwin"))
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
