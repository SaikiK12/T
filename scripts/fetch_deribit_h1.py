"""R519 fix: Deribit hourly candles for the perps in data/deribit_perps, so that daily closes sit at 00:00 UTC like
Hyperliquid's (Deribit's 1D bars run 08:00 to 08:00 UTC). Uses the frozen R519 client (`fetch_deribit_perps.get`).
See experiments/deribitgap_v1/DEVIATIONS.md.

Writes data/deribit_perps/prices_1h/<BASE>.parquet (t = hourly bar open ms, close, volume) and
data/deribit_perps/prices_1h/manifest.json.

usage: python scripts/fetch_deribit_h1.py --end 2026-11-19
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
import fetch_deribit_perps as f  # noqa: E402  (frozen in R519)

H = 3_600_000
STEP = 150 * 24 * H


def hourly(name, a, b):
    parts, t = [], a
    while t < b:
        e = min(t + STEP, b)
        r = f.get("get_tradingview_chart_data", instrument_name=name, start_timestamp=t, end_timestamp=e,
                  resolution="60")
        parts.append(pd.DataFrame({"t": r.get("ticks", []), "close": r.get("close", []),
                                   "volume": r.get("volume", [])}))
        t = e
        time.sleep(0.2)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["t", "close", "volume"])
    return df.drop_duplicates("t").sort_values("t").astype({"t": "int64", "close": float, "volume": float})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--end", required=True)
    ap.add_argument("--data", default=str(ROOT / "data" / "deribit_perps"))
    a = ap.parse_args()
    data = Path(a.data)
    out = data / "prices_1h"
    out.mkdir(parents=True, exist_ok=True)
    raw = json.loads((data / "instruments.json").read_text())
    skipped = set(json.loads((data / "skipped_not_open.json").read_text()))
    b = f.ms(a.end)
    names = [(n, base) for n, base in f.perps(raw) if n not in skipped]
    for name, base in names:
        created = int(next(x["creation_timestamp"] for x in raw if x["instrument_name"] == name))
        hourly(name, max(f.ms("2022-03-01"), created), b).to_parquet(out / f"{base}.parquet", index=False)
    man = {"files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.parquet"))},
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "end": a.end}
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps({"files": len(man["files"])}))


if __name__ == "__main__":
    main()
