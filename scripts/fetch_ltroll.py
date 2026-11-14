"""Inputs for ltroll_v1 (R481, M532 on Lighter): Lighter's futures-priced commodity perps and Yahoo's continuous front
futures they are priced against.

Keyless, public:
- Lighter (mainnet.zklighter.elliot.ai/api/v1) for NATGAS, WTI, BRENTOIL and XCU, through lab.carrylane's paced
  client (one Lighter client per machine, 60 requests a minute):
  - 1-hour candles, saved as lighter/<NAME>_1h.csv (t = bar open in ms, close, volume);
  - hourly funding settlements, saved as lighter/<NAME>_funding.csv (t in ms, rate signed + when longs pay).
- Yahoo's chart API:
  - 60-minute bars of the continuous front futures NG=F, CL=F, BZ=F and HG=F, saved raw as yahoo/<SYM>_60m.json and as
    yahoo/<SYM>_60m.csv (open_ms, close);
  - daily ^IRX (the 13-week bill), saved raw as yahoo/IRX.json and as yahoo/IRX.csv (date, close).
<out>/manifest.json lists every file's sha256.

usage: .venv/bin/python scripts/fetch_ltroll.py --start 2026-01-15 --end 2026-10-16 [--out data/ltroll]
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import carrylane as cl  # noqa: E402
import fetch_hip3stock as fs  # noqa: E402  (frozen in R475)
from fetch_cryptomon import CHART, epoch, parse_chart  # noqa: E402  (frozen in R471)
from fetch_hip3carry import retry  # noqa: E402

OUT = ROOT / "data" / "ltroll"
MARKETS = {"NATGAS": "NG=F", "WTI": "CL=F", "BRENTOIL": "BZ=F", "XCU": "HG=F"}
URL60 = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={a}&period2={b}&interval=60m"


def parse_60m(js):
    r = js["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"open_ms": np.asarray(r["timestamp"], np.int64) * 1000, "close": q["close"]})
    return df.dropna().drop_duplicates("open_ms", keep="last").sort_values("open_ms", ignore_index=True)


def fetch(start, end, out=OUT):
    out = Path(out)
    for sub in ("lighter", "yahoo"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    man = {"source": "mainnet.zklighter.elliot.ai/api/v1 (candles 1h, fundings 1h for NATGAS, WTI, BRENTOIL, XCU) and "
                     "query1.finance.yahoo.com/v8/finance/chart (NG=F, CL=F, BZ=F, HG=F 60m; ^IRX 1d); public, no key",
           "start": start, "end": end, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    a = int(pd.Timestamp(start, tz="UTC").value // 1_000_000)
    b = int(pd.Timestamp(end, tz="UTC").value // 1_000_000)
    for name, sym in MARKETS.items():
        cl.lighter_prices(name, a, b).to_csv(out / "lighter" / f"{name}_1h.csv", index=False)
        cl.lighter_funding(name, a, b).to_csv(out / "lighter" / f"{name}_funding.csv", index=False)
        raw = retry(fs.request, URL60.format(t=sym, a=a // 1000, b=b // 1000))
        stem = sym.replace("=", "_")
        (out / "yahoo" / f"{stem}_60m.json").write_bytes(raw)
        parse_60m(json.loads(raw)).to_csv(out / "yahoo" / f"{stem}_60m.csv", index=False)
        time.sleep(2)
    raw = retry(fs.request, CHART.format(t="%5EIRX", a=epoch(start), b=epoch(end)))
    (out / "yahoo" / "IRX.json").write_bytes(raw)
    parse_chart(json.loads(raw))[["date", "close"]].to_csv(out / "yahoo" / "IRX.csv", index=False)
    for p in sorted(out.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            man["files"][str(p.relative_to(out))] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-01-15")
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    fetch(a.start, a.end, a.out)


if __name__ == "__main__":
    main()
