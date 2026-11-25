"""Hourly snapshot of every Variational Omni listing (public read-only API), for the closed-market rule comparison
(room 2026-11-25, docs/reviews/room_20261125/synthesis.md). Public data, no key, no order. Stdlib only.

Why: Variational's docs say equity perps use "Fixed Mode (Daily Maintenance, Holidays and Weekends) ... the Price Index
remains fixed at the last available value", while trade.xyz and Lighter run a book-driven EMA. Whether Variational's
OLP quotes follow that frozen index over a weekend, and how far they sit from xyz's mids, is the decisive observation.
These snapshots let a later, registered read answer it on weekends the lab has not looked at.

Writes OUT/variational/stats/YYYY-MM-DD.csv (merged by [ts, ticker], so a re-run is idempotent): ts (the run's time,
ms), quote_ts (the API's quotes.updated_at), ticker, contract_type, mark_price, base_bid, base_ask, bid_1k, ask_1k,
bid_100k, ask_100k, bid_1m, ask_1m, base_spread_bps, volume_24h, long_oi, short_oi, funding_last (the raw JSON of
funding.last). One GET per run (the API allows 10 per 10 s per IP).

usage: python scripts/record_variational.py --out DIR
"""
import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://omni-client-api.prod.ap-northeast-1.variational.io/metadata/v2/stats"
COLS = ["ts", "quote_ts", "ticker", "contract_type", "mark_price", "base_bid", "base_ask", "bid_1k", "ask_1k",
        "bid_100k", "ask_100k", "bid_1m", "ask_1m", "base_spread_bps", "volume_24h", "long_oi", "short_oi",
        "funding_last"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def get(url=URL, tries=4):
    delay, err = 2.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "lab-research/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"variational stats: {err}")


def rows_of(stats, ts_ms):
    """One row per listing from a /metadata/v2/stats response (pure; tested offline)."""
    out = []
    for x in stats.get("listings", []):
        q = x.get("quotes") or {}
        side = lambda k, s: (q.get(k) or {}).get(s)  # noqa: E731
        oi = x.get("open_interest") or {}
        f = x.get("funding") or {}
        out.append({"ts": ts_ms, "quote_ts": q.get("updated_at"), "ticker": x.get("ticker"),
                    "contract_type": x.get("contract_type"), "mark_price": x.get("mark_price"),
                    "base_bid": side("base", "bid"), "base_ask": side("base", "ask"),
                    "bid_1k": side("size_1k", "bid"), "ask_1k": side("size_1k", "ask"),
                    "bid_100k": side("size_100k", "bid"), "ask_100k": side("size_100k", "ask"),
                    "bid_1m": side("size_1m", "bid"), "ask_1m": side("size_1m", "ask"),
                    "base_spread_bps": x.get("base_spread_bps"), "volume_24h": x.get("volume_24h"),
                    "long_oi": oi.get("long_open_interest"), "short_oi": oi.get("short_open_interest"),
                    "funding_last": json.dumps(f.get("last"), separators=(",", ":")) if f.get("last") is not None
                    else ""})
    return out


def merge_rows(path, rows, cols=COLS, keys=("ts", "ticker")):
    """Merge rows into one CSV by key (new rows win), sorted; returns the number of rows added or changed."""
    old = {}
    if path.exists():
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                old[tuple(r[k] for k in keys)] = r
    n = 0
    for r in rows:
        r = {c: "" if r.get(c) is None else str(r.get(c)) for c in cols}
        k = tuple(r[c] for c in keys)
        if old.get(k) != r:
            n += 1
            old[k] = r
    if n:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(cols), lineterminator="\n")
            w.writeheader()
            w.writerows(old[k] for k in sorted(old))
        tmp.replace(path)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ts = int(time.time() * 1000)
    rows = rows_of(get(), ts)
    day = datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d")
    n = merge_rows(Path(a.out) / "variational" / "stats" / f"{day}.csv", rows)
    log(f"variational: {len(rows)} listings, {n} rows written")


if __name__ == "__main__":
    main()
