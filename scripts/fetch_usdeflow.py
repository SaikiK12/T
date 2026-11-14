"""Inputs for usdeflow_v1 (R488, M535): USDe's daily circulating supply from DefiLlama and Hyperliquid's hourly BTC
and ETH funding, 2024-01-01 00:00 UTC to 2026-11-09 00:00 UTC (exclusive; the last target week ends 2026-11-08).
Run once, after the PREREG freeze.

Keyless, public:
- GET https://stablecoins.llama.fi/stablecoin/146 (Ethena USDe; id from the /stablecoins list), saved byte-exact as
  raw/llama/stablecoin_146.json. The body is DefiLlama's latest vintage of the whole history.
- POST https://api.hyperliquid.xyz/info {"type": "fundingHistory", "coin", "startTime", "endTime"}, paged by 500 rows,
  each body saved byte-exact as raw/hl/<COIN>_funding_<NNN>.json.
raw/manifest.json lists every request, the fetch time and every body's sha256; scripts/run_usdeflow.py checks it.
Data collection only: no order, no key. Prints counts only, no value.

usage: python scripts/fetch_usdeflow.py [--out experiments/usdeflow_v1/raw] [--pause 1.1]
"""
import argparse
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HL = "https://api.hyperliquid.xyz/info"
LLAMA_ID = 146
LLAMA = f"https://stablecoins.llama.fi/stablecoin/{LLAMA_ID}"
OUT = ROOT / "experiments" / "usdeflow_v1" / "raw"
COINS = ("BTC", "ETH")
START = "2024-01-01"
END = "2026-11-09"             # exclusive: 00:00 UTC on the Monday after the last target week
PAGE = 500


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


def request(url, body=None, tries=5):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            data = json.dumps(body).encode() if body is not None else None
            hdr = {"Content-Type": "application/json"} if body is not None else {}
            hdr["User-Agent"] = "T-lab-research/1.0"
            req = urllib.request.Request(url, data, hdr)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except OSError as e:
            err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"{url} {body}: {err}")


def fetch(out=OUT, pause=1.1):
    out = Path(out)
    (out / "hl").mkdir(parents=True, exist_ok=True)
    (out / "llama").mkdir(parents=True, exist_ok=True)
    man = {"source": f"{LLAMA} (GET); {HL} fundingHistory (POST); public, no key",
           "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "requests": [], "files": {}}
    status, raw = request(LLAMA)
    name = f"llama/stablecoin_{LLAMA_ID}.json"
    (out / name).write_bytes(raw)
    man["requests"].append({"file": name, "url": LLAMA, "status": status})
    end = ms(END) - 1
    for coin in COINS:
        s, page = ms(START), 0
        while s <= end:
            time.sleep(pause)
            body = {"type": "fundingHistory", "coin": coin, "startTime": s, "endTime": end}
            status, raw = request(HL, body)
            rows = json.loads(raw)
            if not rows:
                break
            name = f"hl/{coin}_funding_{page:03d}.json"
            (out / name).write_bytes(raw)
            man["requests"].append({"file": name, "url": HL, "body": body, "status": status, "rows": len(rows)})
            page += 1
            last = int(rows[-1]["time"])
            if len(rows) < PAGE or last <= s:
                break
            s = last + 1
    for p in sorted(out.glob("*/*.json")):
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
