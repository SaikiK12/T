"""Hourly MEXC contract klines for a list of TradFi perps over one window, into a separate folder, for R461's sample B
(earnings releases of 2026-10-21 .. 2026-11-09, after data/mexc_tradfi ends). It never writes data/mexc_tradfi, which
earlier frozen lanes hash.

Each symbol: GET https://contract.mexc.com/api/v1/contract/kline/<SYMBOL>?interval=Min60&start=<s>&end=<s> (public,
no key), pages of at most 1,000 bars. Columns kept as in data/mexc_tradfi/klines_1h: t (bar open, ms), open, high,
low, close, vol, amount ("open" is MEXC's synthetic open, the previous close, as in the archive). One parquet per
symbol in <out>/klines_1h/, a receipt per response (sha256 of the bytes) in <out>/receipts.jsonl and a manifest.

usage: python scripts/fetch_mexc_stock_1h.py --symbols-from experiments/earnperp_v1/sample_b_symbols.txt \
           --start 2026-10-14T00:00:00Z --end 2026-11-11T00:00:00Z --out data/mexc_stock_post
"""
import argparse
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

URL = "https://contract.mexc.com/api/v1/contract/kline/{}?interval=Min60&start={}&end={}"
COLS = ["t", "open", "high", "low", "close", "vol", "amount"]
HOUR_S = 3600
PAGE = 1000


def epoch(s):
    return int(datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())


def fetch(symbol, start_s, end_s, receipts):
    rows = []
    lo = start_s
    while lo < end_s:
        hi = min(lo + PAGE * HOUR_S, end_s)
        url = URL.format(symbol, lo, hi)
        for k in range(5):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "lab-research-fetch/1.0"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    raw = r.read()
                break
            except Exception:
                if k == 4:
                    raise
                time.sleep(2 ** (k + 1))
        receipts.write(json.dumps({"url": url, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                                   "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
        d = json.loads(raw)
        if not d.get("success"):
            print(f"{symbol}: no data ({str(d)[:120]})", flush=True)
            break
        x = d["data"]
        for i, t in enumerate(x.get("time", [])):
            if lo <= t < end_s:
                rows.append([t * 1000, x["open"][i], x["high"][i], x["low"][i], x["close"][i], x["vol"][i],
                             x["amount"][i]])
        lo = hi
        time.sleep(0.25)
    df = pd.DataFrame(rows, columns=COLS).drop_duplicates("t").sort_values("t")
    df["t"] = df.t.astype("int64")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols-from", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    syms = [s.strip() for s in Path(a.symbols_from).read_text().split() if s.strip()]
    out = a.out / "klines_1h"
    out.mkdir(parents=True, exist_ok=True)
    s0, s1 = epoch(a.start), epoch(a.end)
    man = {"kind": "mexc_contract_klines_1h", "start": a.start, "end_exclusive": a.end, "symbols": {},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(a.out / "receipts.jsonl", "a") as rec:
        for s in syms:
            df = fetch(s, s0, s1, rec)
            path = out / f"{s}.parquet"
            df.to_parquet(path, index=False)
            man["symbols"][s] = {"rows": len(df), "first": int(df.t.min()) if len(df) else None,
                                 "last": int(df.t.max()) if len(df) else None,
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(len(syms), "symbols;", sum(v["rows"] for v in man["symbols"].values()), "rows")


if __name__ == "__main__":
    main()
