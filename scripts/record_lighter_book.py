"""Hourly snapshot of what a taker order costs on Lighter, the zero-fee perp DEX (docs/VENUE_STRUCTURE.md): for every
active perp, the best bid and ask, the cost per side of a market order of USD 1k and 10k walked through the shown book,
the mark and index price, 24 h volume and open interest. Paper only: public endpoints, no account, places nothing.

Lighter's Standard account (the default) pays 0 maker and 0 taker fees, through the app and the API, with a 300 ms
delay on taker orders and cancels and 60 requests a minute (apidocs.lighter.xyz, account types and rate limits, read
2026-10-21). With no fee, the spread and the book are the whole cost, and nothing on Lighter was measured before this.
No archive keeps Lighter's book, so the clock starts with this recorder.

One file per UTC hour, data/recorders/lighter_book/<YYYY-MM-DD>/<HH>.parquet (gitignored, digests committed by
record_digest.py); a second run in the same hour writes nothing. The request pace stays under the 60 per minute that
a Standard account gets, so a snapshot of about 200 books takes about 4 minutes; forward_all.sh runs it in the
background. Data collection only.

usage: python scripts/record_lighter_book.py [--limit N]
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

OUT = data.ROOT / "recorders" / "lighter_book"
BASE = "https://mainnet.zklighter.elliot.ai/api/v1"
SIZES = (1_000, 10_000)
DEPTH = 100                                  # orders per side read (the endpoint allows 250)
PACE_S = 1.1                                 # 60 requests a minute for a Standard account; keep under it
COLS = ["ts", "symbol", "market_id", "bid", "ask", "half_spread_bp", "buy_1k_bp", "sell_1k_bp", "buy_10k_bp",
        "sell_10k_bp", "bid_usd_shown", "ask_usd_shown", "mark", "index", "vol24_usd", "oi_base", "taker_fee",
        "maker_fee"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def http(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "lab/1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def levels(orders):
    return [(float(o["price"]), float(o["remaining_base_amount"])) for o in orders or []]


def impact(side, usd, mid):
    """bp between mid and the average fill of a market order of `usd` notional walked through `side`
    [(price, base), ...] best first; NaN when the shown book is too thin."""
    left, paid, qty = float(usd), 0.0, 0.0
    for p, q in side:
        take = min(left, p * q)
        paid += take
        qty += take / p
        left -= take
        if left <= 1e-9:
            return abs(paid / qty / mid - 1) * 1e4
    return np.nan


def row(ts, d, book):
    a, b = levels(book.get("asks")), levels(book.get("bids"))
    if not a or not b:
        return None
    ask, bid = a[0][0], b[0][0]
    mid = (ask + bid) / 2
    out = {"ts": ts, "symbol": d["symbol"], "market_id": int(d["market_id"]), "bid": bid, "ask": ask,
           "half_spread_bp": (ask - bid) / mid / 2 * 1e4,
           "bid_usd_shown": sum(p * q for p, q in b), "ask_usd_shown": sum(p * q for p, q in a),
           "mark": float(d.get("mark_price") or np.nan), "index": float(d.get("index_price") or np.nan),
           "vol24_usd": float(d.get("daily_quote_token_volume") or np.nan),
           "oi_base": float(d.get("open_interest") or np.nan),
           "taker_fee": float(d.get("taker_fee") or 0), "maker_fee": float(d.get("maker_fee") or 0)}
    for usd in SIZES:
        k = f"{usd // 1000}k"
        out[f"buy_{k}_bp"] = impact(a, usd, mid)
        out[f"sell_{k}_bp"] = impact(b, usd, mid)
    return out


def snapshot(get=None, pace=None, limit=None):
    get = get or http
    pace = PACE_S if pace is None else pace
    ts = int(time.time() * 1000)
    det = [d for d in get("/orderBookDetails?filter=perp")["order_book_details"] if d.get("status") == "active"]
    rows, failed, last = [], [], time.monotonic()
    for d in det[:limit]:
        time.sleep(max(0.0, pace - (time.monotonic() - last)))   # pace counts from the previous request's start
        last = time.monotonic()
        try:
            r = row(ts, d, get(f"/orderBookOrders?market_id={int(d['market_id'])}&limit={DEPTH}"))
        except Exception as e:  # noqa: BLE001 - one market failing does not stop the snapshot
            failed.append(f"{d['symbol']}: {e}")
            continue
        if r:
            rows.append(r)
    return pd.DataFrame(rows, columns=COLS), failed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    now = time.gmtime()
    path = OUT / time.strftime("%Y-%m-%d", now) / f"{time.strftime('%H', now)}.parquet"
    if path.exists():
        log(f"lighter book: {path.relative_to(ROOT)} already written")
        return path
    df, failed = snapshot(limit=a.limit)
    if failed:
        log(f"lighter book: {len(failed)} markets failed, first: {failed[0]}")
    if df.empty:
        log("lighter book: nothing read")
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")              # record_digest.py skips .part files
    df.to_parquet(tmp, index=False)
    tmp.replace(path)
    log(f"lighter book: {len(df)} markets -> {path.relative_to(ROOT)}; median half-spread "
        f"{df.half_spread_bp.median():.2f} bp, median 1k side "
        f"{np.nanmedian((df.buy_1k_bp + df.sell_1k_bp) / 2):.2f} bp")
    return path


if __name__ == "__main__":
    main()
