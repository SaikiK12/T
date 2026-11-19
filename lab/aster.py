"""Aster (asterdex.com) public clients for forward carry lanes: USDT perpetuals, Binance-style API.

Public endpoints only, no key: nothing here can place an order.
- Daily klines: `/fapi/v1/klines?interval=1d` (t = bar open, 00:00 UTC).
- Funding settlements: `/fapi/v1/fundingRate` (intervals of 1, 4 or 8 h; each row is one settlement, as paid).
- Mids: `/fapi/v1/ticker/bookTicker`. Live list: `/fapi/v1/exchangeInfo` (status TRADING).
- Books: `/fapi/v1/depth`.

`register()` adds an "aster" venue to `lab.carrylane.VENUES` at run time (lab/carrylane.py is pinned by frozen lanes).
"""
import json
import time
import urllib.error
import urllib.request

import pandas as pd

BASE = "https://fapi.asterdex.com"
DAY = 86_400_000
PACE = 0.15


def _json(url, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 429:
                time.sleep(30)
            elif e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def prices(sym, start, end):
    """Daily bars with t in [start, end): t, close, volume (base units)."""
    rows = _json(f"{BASE}/fapi/v1/klines?symbol={sym}&interval=1d&startTime={start}&endTime={end - 1}&limit=1500")
    time.sleep(PACE)
    df = pd.DataFrame({"t": [int(r[0]) for r in rows or []], "close": [float(r[4]) for r in rows or []],
                       "volume": [float(r[5]) for r in rows or []]})
    if df.empty:
        return pd.DataFrame(columns=["t", "close", "volume"])
    return df[(df.t >= start) & (df.t < end)].astype({"t": "int64"}).drop_duplicates("t").sort_values(
        "t", ignore_index=True)


def funding(sym, start, end):
    """Settlements with t in [start, end]: t, rate."""
    out, s = [], start
    while s <= end:
        rows = _json(f"{BASE}/fapi/v1/fundingRate?symbol={sym}&startTime={s}&endTime={end}&limit=1000")
        time.sleep(PACE)
        if not rows:
            break
        out += rows
        last = int(rows[-1]["fundingTime"])
        if last < s or len(rows) < 1000:
            break
        s = last + 1
    if not out:
        return pd.DataFrame(columns=["t", "rate"])
    df = pd.DataFrame({"t": [int(r["fundingTime"]) for r in out], "rate": [float(r["fundingRate"]) for r in out]})
    return df[(df.t >= start) & (df.t <= end)].astype({"t": "int64"}).drop_duplicates("t").sort_values(
        "t", ignore_index=True)


def mids():
    out = {}
    for t in _json(f"{BASE}/fapi/v1/ticker/bookTicker") or []:
        b, a = float(t.get("bidPrice") or 0), float(t.get("askPrice") or 0)
        if b > 0 and a > 0:
            out[t["symbol"]] = (b + a) / 2
    return out


def listed():
    info = _json(f"{BASE}/fapi/v1/exchangeInfo")
    return {s["symbol"] for s in info.get("symbols", [])
            if s.get("contractType") == "PERPETUAL" and s.get("status") == "TRADING"}


def book(sym):
    d = _json(f"{BASE}/fapi/v1/depth?symbol={sym}&limit=100")
    return ([[float(p), float(q)] for p, q in d.get("bids", [])], [[float(p), float(q)] for p, q in d.get("asks", [])])


def register():
    """Add the "aster" venue to lab.carrylane.VENUES (daily klines, settlement funding)."""
    from . import carrylane
    carrylane.VENUES.setdefault("aster", carrylane.Venue(prices, funding, mids, listed, "aster_hist/candles_1d",
                                                         "volume", "aster_hist/funding", 24, 2))
    return carrylane.VENUES["aster"]
