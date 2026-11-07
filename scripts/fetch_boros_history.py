"""Public Boros (Pendle) funding-rate swap history for R412 boroslock_v1: the market list from the open API and, for every
BTC/ETH single-venue funding market, the monthly hourly market snapshots (best bid/ask implied APR) and the on-chain
settlement records, from https://historical-data.boros.finance (public, no login, no wallet).

Writes data/boros/markets.json (all markets, as listed now) and data/boros/hist/<kind>/<market>/<YYYY-MM>.ndjson.zip,
and docs/provenance/boros_hist.json (every file's sha256, request counts, fetch time). It reads no outcome.

usage: python scripts/fetch_boros_history.py
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg  # noqa: E402

API = "https://api-boros.pendle.finance/apis/v1/markets"
HIST = "https://historical-data.boros.finance"
OUT = data.ROOT / "boros"
PROV = ROOT / "docs" / "provenance" / "boros_hist.json"
KINDS = ("market-data", "settlement")
COINS = ("BTC", "ETH")
FIRST_MONTH = "2025-08"                          # Boros launched in 2025; earlier months return 404
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, tries=5):
    """(status, bytes); 404 is returned, other errors are retried then raised."""
    delay = 2.0
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab/1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 404, b""
            if i == tries - 1:
                raise
        except Exception:  # noqa: BLE001 - retried, then raised
            if i == tries - 1:
                raise
        time.sleep(delay)
        delay *= 2


def all_markets():
    out, tok, n = [], None, 0
    while True:
        st, body = get(API + (f"?resumeToken={tok}" if tok else ""))
        n += 1
        j = json.loads(body)
        res = j.get("results") or []
        out += res
        tok = j.get("resumeToken")
        if not res or not tok or n > 50:
            return out, n


def selected(markets, now_s):
    """Matured single-venue BTC/ETH funding markets: (folder name, maturity s)."""
    sel = []
    for m in markets:
        md, im = m["metadata"], m["imData"]
        if md.get("isSpreadMarket") or md.get("underlyingSymbol") not in COINS or im["maturity"] > now_s:
            continue
        sel.append((f"{m['marketId']}-{im['symbol']}", int(im["maturity"])))
    return sorted(set(sel))


def months(last_s):
    end = pd.Timestamp(last_s, unit="s").strftime("%Y-%m")
    return [p.strftime("%Y-%m") for p in pd.period_range(FIRST_MONTH, end, freq="M")]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    now_s = int(time.time())
    markets, n_api = all_markets()
    (OUT / "markets.json").write_text(json.dumps(markets))
    sel = selected(markets, now_s)
    log(f"{len(markets)} markets listed ({n_api} requests); {len(sel)} matured BTC/ETH single-venue markets")
    files, n_req, n_404 = [], 0, 0
    for name, mat in sel:
        for kind in KINDS:
            for ym in months(mat):
                st, body = get(f"{HIST}/{kind}/{name}/{ym}.ndjson.zip")
                n_req += 1
                if st == 404:
                    n_404 += 1
                    continue
                p = OUT / "hist" / kind / name / f"{ym}.ndjson.zip"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body)
                files.append({"path": p.relative_to(ROOT).as_posix(), "sha256": prereg.sha256_file(p), "bytes": len(body)})
        log(f"{name}: {len(files)} files so far, {n_req} requests")
    prov = {"source": f"{API} (market list) and {HIST} (monthly ndjson.zip)", "kinds": list(KINDS),
            "fetched_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now_s)), "markets_listed": len(markets),
            "markets_selected": [n for n, _ in sel], "requests": n_req + n_api, "not_found": n_404,
            "file_hashes": [{"path": (OUT / "markets.json").relative_to(ROOT).as_posix(),
                             "sha256": prereg.sha256_file(OUT / "markets.json")}] + files}
    PROV.write_text(json.dumps(prov, indent=1) + "\n")
    log(f"done: {len(files)} files, {sum(f['bytes'] for f in files) / 1e6:.1f} MB, {n_404} months not found")


if __name__ == "__main__":
    main()
