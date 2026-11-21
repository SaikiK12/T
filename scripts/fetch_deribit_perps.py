"""Inputs for R519 deribitgap_v1: Deribit's linear USDC perpetuals, funding history and daily candles. Keyless,
public Deribit API v2; run once after the freeze.

- **Universe.** `public/get_instruments` (kind future, live), settlement period "perpetual", instrument type
  "linear". The base is the name before "_USDC". Inverse BTC-PERPETUAL and ETH-PERPETUAL are left out (their PnL is
  in coin).
- **Files:**
  - <out>/instruments.json: the raw list;
  - <out>/funding/<BASE>.parquet (t ms, rate per hour = interest_1h);
  - <out>/prices/<BASE>.parquet (t = daily bar open ms, close, volume);
  - <out>/manifest.json: every file's sha256.

usage: python scripts/fetch_deribit_perps.py --start 2022-03-01 --end 2026-11-19 --out data/deribit_perps
"""
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

API = "https://www.deribit.com/api/v2/public/"
DAY = 86_400_000


def get(method, **params):
    url = API + method + "?" + urllib.parse.urlencode(params)
    for k in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["result"]
        except Exception:
            time.sleep(2 * (k + 1))
    raise SystemExit(f"failed: {method} {params}")


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


def perps(raw):
    return sorted((x["instrument_name"], x["instrument_name"].split("_USDC")[0]) for x in raw
                  if x.get("settlement_period") == "perpetual" and x.get("instrument_type") == "linear")


def funding(name, a, b):
    rows, t = [], max(a, 0)
    while t < b:
        e = min(t + 30 * DAY, b)
        rows += get("get_funding_rate_history", instrument_name=name, start_timestamp=t, end_timestamp=e) or []
        t = e
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    if not len(df):
        return pd.DataFrame({"t": pd.Series(dtype="int64"), "rate": pd.Series(dtype=float)})
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    return pd.DataFrame({"t": df.timestamp.astype("int64"), "rate": df.interest_1h.astype(float)})


def candles(name, a, b):
    r = get("get_tradingview_chart_data", instrument_name=name, start_timestamp=a, end_timestamp=b, resolution="1D")
    df = pd.DataFrame({"t": r.get("ticks", []), "close": r.get("close", []), "volume": r.get("volume", [])})
    return df.astype({"t": "int64", "close": float, "volume": float})


def fetch(start, end, out):
    out = Path(out)
    for sub in ("funding", "prices"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    raw = get("get_instruments", currency="any", kind="future", expired="false")
    (out / "instruments.json").write_text(json.dumps(raw, indent=1))
    a, b = ms(start), ms(end)
    names = perps(raw)
    for name, base in names:
        created = next(x["creation_timestamp"] for x in raw if x["instrument_name"] == name)
        funding(name, max(a, int(created)), b).to_parquet(out / "funding" / f"{base}.parquet", index=False)
        candles(name, max(a, int(created)), b).to_parquet(out / "prices" / f"{base}.parquet", index=False)
    man = {"source": "www.deribit.com/api/v2/public (get_instruments, get_funding_rate_history, "
                     "get_tradingview_chart_data 1D)", "start": start, "end": end,
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({"perps": len(names), "files": len(man["files"])}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2022-03-01")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default="data/deribit_perps")
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
