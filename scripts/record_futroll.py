"""Recorder for R480 futroll_fwd: the NYMEX contracts trade.xyz's commodity perps reference, and the perps' own 1-hour
candles and funding, merged into CSVs on the data branch claude/futroll-data. Stdlib only (the runner's python3).

Why record: Yahoo drops a futures contract's history once it expires, and Hyperliquid keeps only the latest 5,000
1-hour candles (about 208 days), while R480's reads come 6 and 12 months later. Each run saves the last 60 days of
Yahoo 60-minute bars and the last 10 days of the venue's candles and funding, and merges them by bar start, so a
daily run (or a few missed ones) loses nothing.

<out>/yahoo/<SYM>.csv          open_ms, open, high, low, close, volume  (complete 60-minute bars, e.g. NGF27.NYM)
<out>/xyz/<NAME>_1h.csv        open_ms, open, high, low, close, volume  (complete 1-hour candles of xyz:<NAME>)
<out>/xyz/<NAME>_funding.csv   time, fundingRate, premium              (hourly funding prints)
Contracts: NG and CL for the next 1-4 calendar months, BZ (Brent) for the next 2-5, which covers xyz's designated
front and next contracts (NATGAS and CL reference the next month's contract, BRENTOIL the one after) through each
roll and until the old front expires.

usage: python3 scripts/record_futroll.py --out .futroll-data [--now 2026-11-12T20:00:00Z]
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INFO = "https://api.hyperliquid.xyz/info"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=60d&interval=60m"
UA = "Mozilla/5.0 (research client)"
CODES = "FGHJKMNQUVXZ"
ROOTS = {"NG": 1, "CL": 1, "BZ": 2}          # first contract month ahead of the calendar month
AHEAD = 4                                   # contracts per root
PERPS = ("NATGAS", "CL", "BRENTOIL")
H = 3_600_000
BAR_COLS = ["open_ms", "open", "high", "low", "close", "volume"]
FUND_COLS = ["time", "fundingRate", "premium"]
VENUE_DAYS = 10


def request(url, body=None, tries=5):
    head = {"User-Agent": UA}
    data = None
    if body is not None:
        head["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=head), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if (e.code != 429 and e.code < 500) or k == tries - 1:
                raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if k == tries - 1:
                raise
        time.sleep(15 * (k + 1))


def contracts(now):
    """Yahoo symbols of the contracts to keep, e.g. NGF27.NYM, for a datetime `now` (UTC)."""
    out = []
    for root, first in ROOTS.items():
        for k in range(first, first + AHEAD):
            m = now.month - 1 + k
            y, mo = now.year + m // 12, m % 12
            out.append(f"{root}{CODES[mo]}{y % 100:02d}.NYM")
    return out


def yahoo_bars(sym, now_ms):
    raw = request(CHART.format(s=sym))
    if raw is None:
        return []
    res = (json.loads(raw).get("chart") or {}).get("result") or []
    if not res or not res[0].get("timestamp"):
        return []
    r = res[0]
    q = r["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(r["timestamp"]):
        t = int(ts) * 1000
        c = q["close"][i]
        if c is None or t % H or t + H > now_ms:          # hour-aligned, complete bars only
            continue
        rows.append({"open_ms": t, "open": q["open"][i], "high": q["high"][i], "low": q["low"][i], "close": c,
                     "volume": q["volume"][i]})
    return rows


def venue_candles(coin, start_ms, now_ms):
    page = json.loads(request(INFO, {"type": "candleSnapshot",
                                     "req": {"coin": coin, "interval": "1h", "startTime": start_ms,
                                             "endTime": now_ms}}) or b"[]")
    return [{"open_ms": int(c["t"]), "open": c["o"], "high": c["h"], "low": c["l"], "close": c["c"], "volume": c["v"]}
            for c in page if int(c["t"]) + H <= now_ms]


def venue_funding(coin, start_ms, now_ms):
    rows, t = [], start_ms
    while t < now_ms:
        page = json.loads(request(INFO, {"type": "fundingHistory", "coin": coin, "startTime": t,
                                         "endTime": now_ms}) or b"[]")
        rows += [{"time": int(p["time"]), "fundingRate": p["fundingRate"], "premium": p.get("premium", "")}
                 for p in page]
        if len(page) < 500:
            break
        t = int(page[-1]["time"]) + 1
        time.sleep(1.5)
    return rows


def merge(path, rows, key, cols):
    """Merge rows into the CSV at path by `key` (new values replace old ones); sorted; returns rows added."""
    have = {}
    if path.exists():
        with path.open(newline="") as f:
            for r in csv.DictReader(f):
                have[int(r[key])] = r
    before = len(have)
    for r in rows:
        have[int(r[key])] = {c: r[c] for c in cols}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for k in sorted(have):
            w.writerow(have[k])
    tmp.replace(path)
    return len(have) - before


def record(out, now):
    out = Path(out)
    now_ms = int(now.timestamp() * 1000)
    fail = 0
    for sym in contracts(now):
        try:
            rows = yahoo_bars(sym, now_ms)
            added = merge(out / "yahoo" / f"{sym}.csv", rows, "open_ms", BAR_COLS) if rows else 0
            print(f"{sym}: {len(rows)} bars, {added} new", flush=True)
        except Exception as e:  # noqa: BLE001  (one symbol's failure must not stop the rest)
            print(f"{sym}: FAILED {type(e).__name__}: {e}", flush=True)
            fail = 1
        time.sleep(2)
    start = now_ms - VENUE_DAYS * 24 * H
    for name in PERPS:
        coin = f"xyz:{name}"
        try:
            c = venue_candles(coin, start, now_ms)
            a = merge(out / "xyz" / f"{name}_1h.csv", c, "open_ms", BAR_COLS)
            time.sleep(1.5)
            fr = venue_funding(coin, start, now_ms)
            b = merge(out / "xyz" / f"{name}_funding.csv", fr, "time", FUND_COLS)
            print(f"{coin}: {len(c)} candles ({a} new), {len(fr)} funding ({b} new)", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{coin}: FAILED {type(e).__name__}: {e}", flush=True)
            fail = 1
        time.sleep(1.5)
    return fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--now", default=None, help="UTC time, e.g. 2026-11-12T20:00:00Z (default: now)")
    a = ap.parse_args()
    now = (datetime.strptime(a.now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if a.now
           else datetime.now(timezone.utc))
    sys.exit(record(a.out, now))


if __name__ == "__main__":
    main()
