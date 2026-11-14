"""Inputs for llphouse_v1 (R484, M536): Hyperliquid's daily BTC and ETH perp candles and their hourly funding,
2025-01-01 to the end of 2026-11-10 UTC (the lane's seen-data cutoff). Run once, after the PREREG freeze.

Keyless, public: POST https://api.hyperliquid.xyz/info
- {"type": "candleSnapshot", "req": {"coin", "interval": "1d", "startTime", "endTime"}}, one body per coin, saved
  byte-exact as raw/hl/<COIN>_candles_1d.json;
- {"type": "fundingHistory", "coin", "startTime", "endTime"}, paged by 500 rows, each body saved byte-exact as
  raw/hl/<COIN>_funding_<NNN>.json.
raw/manifest.json lists every request, the fetch time and every body's sha256; scripts/run_llphouse.py checks it.
Data collection only: no order, no key.

usage: python scripts/fetch_llphouse.py [--out experiments/llphouse_v1/raw] [--pause 1.1]
"""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.hyperliquid.xyz/info"
OUT = ROOT / "experiments" / "llphouse_v1" / "raw"
COINS = ("BTC", "ETH")
START = "2025-01-01"
CUTOFF = "2026-11-10"            # last UTC day of any value fetched
DAY = 86_400_000


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def post(body, tries=5):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(API, json.dumps(body).encode(), {"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{body}: {err}")


def fetch(out=OUT, pause=1.1):
    out = Path(out)
    (out / "hl").mkdir(parents=True, exist_ok=True)
    a = ms(START)
    candle_end = ms(CUTOFF) + DAY - 1            # the last bar opens 2026-11-10 00:00
    funding_end = ms(CUTOFF) + DAY               # the settlement at 2026-11-11 00:00 closes 2026-11-10's last hour
    man = {"source": API + " (candleSnapshot 1d, fundingHistory); public, no key",
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requests": [], "files": {}}
    for coin in COINS:
        body = {"type": "candleSnapshot", "req": {"coin": coin, "interval": "1d", "startTime": a,
                                                  "endTime": candle_end}}
        raw = post(body)
        name = f"hl/{coin}_candles_1d.json"
        (out / name).write_bytes(raw)
        man["requests"].append({"file": name, "body": body})
        time.sleep(pause)
        s, page = a, 0
        while s <= funding_end:
            body = {"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": funding_end}
            raw = post(body)
            rows = json.loads(raw)
            if not rows:
                break
            name = f"hl/{coin}_funding_{page:03d}.json"
            (out / name).write_bytes(raw)
            man["requests"].append({"file": name, "body": body})
            page += 1
            time.sleep(pause)
            last = int(rows[-1]["time"])
            if len(rows) < 500 or last <= s:
                break
            s = last + 1
    for p in sorted((out / "hl").glob("*.json")):
        man["files"][str(p.relative_to(out))] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--pause", type=float, default=1.1)
    a = ap.parse_args()
    out = fetch(a.out, a.pause)
    man = json.loads((out / "manifest.json").read_text())
    print(f"{len(man['files'])} bodies written to {out}")       # counts only: no value is printed


if __name__ == "__main__":
    main()
