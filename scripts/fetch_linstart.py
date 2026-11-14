"""OKX public daily candles (bar 1Dutc) and funding-rate history for the swaps in experiments/linstart_v1/events.csv
(R485). Run once, after the lane's PREREG is frozen. Keyless public endpoints, one request at a time with a pause
(OKX allows 20 requests per 2 s on these endpoints; this stays near 3 per second).

Writes experiments/linstart_v1/raw/okx/<instId>_1Dutc.json (the candle rows of every page, newest first, as OKX
returns them) and <instId>_funding.json, plus raw/manifest.json with the sha256 and row count of each file.
Candles: every bar opening before 2026-11-07 00:00 UTC (the last needed close is 2026-11-06's, D+14 of the last
archive D), back to the swap's first bar. Funding: whatever history OKX serves (recent months only).

usage: python scripts/fetch_linstart.py
"""
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "experiments" / "linstart_v1"
OUT = LANE / "raw" / "okx"
BASE = "https://www.okx.com/api/v5"
END_MS = int(pd.Timestamp("2026-11-07", tz="UTC").value // 1_000_000)
PAUSE = 0.35
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(path, **params):
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    delay = 2.0
    for _ in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lab/1"}), timeout=30) as r:
                body = json.loads(r.read())
            if body.get("code") == "0":
                time.sleep(PAUSE)
                return body["data"]
            err = body
        except OSError as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def candles(inst):
    rows, after = [], END_MS
    while True:
        page = get("/market/history-candles", instId=inst, bar="1Dutc", after=after, limit=100)
        if not page:
            return rows
        rows += page
        oldest = min(int(r[0]) for r in page)
        if oldest >= after:
            return rows
        after = oldest


def funding(inst):
    rows, after = [], None
    while True:
        kw = {"instId": inst, "limit": 100}
        if after:
            kw["after"] = after
        page = get("/public/funding-rate-history", **kw)
        if not page:
            return rows
        rows += page
        oldest = min(int(r["fundingTime"]) for r in page)
        if after and oldest >= after:
            return rows
        after = oldest


def main():
    ev = pd.read_csv(LANE / "events.csv")
    insts = sorted(ev[ev.window == "archive"].inst_id.unique())
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"source": BASE, "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    for inst in insts:
        for kind, fn in (("1Dutc", candles), ("funding", funding)):
            rows = fn(inst)
            raw = json.dumps(rows, separators=(",", ":")).encode()
            name = f"okx/{inst}_{kind}.json"
            (LANE / "raw" / name).write_bytes(raw)
            manifest["files"][name] = {"rows": len(rows), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            log(inst, kind, len(rows))
    (LANE / "raw" / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    log(f"done: {len(insts)} swaps -> {OUT}")


if __name__ == "__main__":
    sys.exit(main())
