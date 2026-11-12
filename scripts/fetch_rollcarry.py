"""Inputs for rollcarry_v1 (M532): trade.xyz's futures-priced perps and the US funds that hold the same front futures.

Keyless, public:
- api.hyperliquid.xyz/info for xyz:NATGAS, xyz:CL and xyz:BRENTOIL:
  - hourly funding (fundingHistory, paged), saved as xyz/<NAME>_funding.csv;
  - 4-hour candles (back past each listing), saved as xyz/<NAME>_4h.csv;
  - 1-hour candles (the venue keeps the latest 5,000), saved as xyz/<NAME>_1h.csv.
- Yahoo's chart API, daily, for UNG, USO and BNO (the hedges) and ^IRX (the bill): yahoo/<T>.json raw and
  yahoo/<T>.parquet (date, close, adjclose).
<out>/manifest.json lists every file's sha256. The clients are R475's (`fetch_hip3stock.funding`, `.candles`, `.request`),
paced and retried on HTTP 429; the 1-hour pages use the same client.

usage: python scripts/fetch_rollcarry.py --start 2025-12-01 --end 2026-11-12 [--out data/rollcarry]
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

OUT = ROOT / "data" / "rollcarry"
PAIRS = {"NATGAS": "UNG", "CL": "USO", "BRENTOIL": "BNO"}
YAHOO = {"UNG": "UNG", "USO": "USO", "BNO": "BNO", "IRX": "%5EIRX"}


def candles_1h(coin, start_ms, end_ms):
    """The latest 5,000 hourly candles in the range (one page), in R475's column layout."""
    page = fs.post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": start_ms,
                                                      "endTime": end_ms}}) or []
    cols = ["open_ms", "open", "high", "low", "close", "volume"]
    df = pd.DataFrame(page)
    if not len(df):
        return pd.DataFrame(columns=cols)
    df = df.rename(columns={"t": "open_ms", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    return df[cols].drop_duplicates("open_ms").sort_values("open_ms")


def fetch(start, end, out=OUT):
    out = Path(out)
    for sub in ("xyz", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "api.hyperliquid.xyz/info (fundingHistory, candleSnapshot 4h and 1h for xyz:NATGAS, xyz:CL, "
                     "xyz:BRENTOIL) and query1.finance.yahoo.com/v8/finance/chart (UNG, USO, BNO, ^IRX); public, no key",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a, b = fs.ms(start), fs.ms(end)
    for name in PAIRS:
        coin = f"xyz:{name}"
        fs.funding(coin, a, b).to_csv(out / "xyz" / f"{name}_funding.csv", index=False)
        time.sleep(1.5)
        fs.candles(coin, a, b).to_csv(out / "xyz" / f"{name}_4h.csv", index=False)
        time.sleep(1.5)
        candles_1h(coin, a, b).to_csv(out / "xyz" / f"{name}_1h.csv", index=False)
        time.sleep(1.5)
    for name, sym in YAHOO.items():
        raw = fs.request(CHART.format(t=sym, a=epoch(start), b=epoch(end)))
        (out / "yahoo" / f"{name}.json").write_bytes(raw)
        parse_chart(json.loads(raw))[["date", "close", "adjclose"]].to_parquet(out / "yahoo" / f"{name}.parquet",
                                                                               index=False)
        time.sleep(2)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-12-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
