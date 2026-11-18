"""Kraken Futures public clients for forward carry lanes (linear `PF_*` perps), plus order-book walking.

Public endpoints only, no key: nothing here can place an order.
- Daily trade candles: `/api/charts/v1/trade/<symbol>/1d` (t = bar open, 00:00 UTC).
- Funding: `/derivatives/api/v4/historicalfundingrates` (the venue serves about the last year). `relativeFundingRate`
  is the hourly rate as a fraction of notional, the unit R508 tested; a positive rate is paid by longs.
- Mids and the live list: `/derivatives/api/v3/tickers`.
- Books: `/derivatives/api/v3/orderbook`.

`register()` adds a "kraken" venue to `lab.carrylane.VENUES` at run time, so lab/carrylane.py (pinned by frozen lanes)
is not edited.
"""
import json
import time
import urllib.error
import urllib.request

import numpy as np
import pandas as pd

BASE = "https://futures.kraken.com"
HL = "https://api.hyperliquid.xyz/info"
DAY = 86_400_000


def _json(url, body=None, tries=5):
    delay, err = 1.0, None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                         {"Content-Type": "application/json", "User-Agent": "lab-paper/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404):
                break
        except (OSError, ValueError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{url}: {err}")


def iso_ms(s):
    t = pd.Timestamp(s)
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    return int(t.value // 10**6)


def prices(sym, start, end):
    """Daily bars with t in [start, end): t, close, volume."""
    rows = _json(f"{BASE}/api/charts/v1/trade/{sym}/1d?from={start // 1000}&to={end // 1000}").get("candles") or []
    if not rows:
        return pd.DataFrame(columns=["t", "close", "volume"])
    df = pd.DataFrame({"t": [int(x["time"]) for x in rows], "close": [float(x["close"]) for x in rows],
                       "volume": [float(x["volume"]) for x in rows]})
    df = df[(df.t >= start) & (df.t < end)]
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def funding(sym, start, end):
    """Hourly settlements with t in [start, end]: t, rate (relative, per hour)."""
    rows = _json(f"{BASE}/derivatives/api/v4/historicalfundingrates?symbol={sym}").get("rates") or []
    if not rows:
        return pd.DataFrame(columns=["t", "rate"])
    df = pd.DataFrame({"t": [iso_ms(x["timestamp"]) for x in rows],
                       "rate": [float(x["relativeFundingRate"]) for x in rows]})
    df = df[(df.t >= start) & (df.t <= end)]
    return df.astype({"t": "int64"}).drop_duplicates("t").sort_values("t", ignore_index=True)


def _tickers():
    return _json(f"{BASE}/derivatives/api/v3/tickers").get("tickers") or []


def mids():
    out = {}
    for t in _tickers():
        b, a = t.get("bid"), t.get("ask")
        if str(t.get("symbol", "")).startswith("PF_") and b and a and float(b) > 0 and float(a) > 0:
            out[t["symbol"]] = (float(b) + float(a)) / 2
    return out


def listed():
    return {t["symbol"] for t in _tickers()
            if str(t.get("symbol", "")).startswith("PF_") and not t.get("suspended") and t.get("tag") == "perpetual"}


# ---------------------------------------------------------------- books

def walk(levels, usd):
    """Average fill price of a market order of `usd` notional against `levels` [[price, size], ...] best first, or
    None when the book is too thin."""
    left, cost, got = float(usd), 0.0, 0.0
    for px, q in levels:
        if px <= 0 or q <= 0:
            continue
        take = min(q, left / px)
        got += take
        cost += take * px
        left -= take * px
        if left <= 1e-9:
            return cost / got
    return None


def kraken_book(sym):
    ob = _json(f"{BASE}/derivatives/api/v3/orderbook?symbol={sym}").get("orderBook") or {}
    bids = sorted(([float(p), float(q)] for p, q in ob.get("bids", [])), key=lambda x: -x[0])
    asks = sorted(([float(p), float(q)] for p, q in ob.get("asks", [])), key=lambda x: x[0])
    return bids, asks


def hl_book(coin):
    lv = (_json(HL, {"type": "l2Book", "coin": coin}) or {}).get("levels") or [[], []]
    return ([[float(x["px"]), float(x["sz"])] for x in lv[0]], [[float(x["px"]), float(x["sz"])] for x in lv[1]])


BOOKS = {"kraken": kraken_book, "hyperliquid": hl_book}


def side_fill(bids, asks, side, usd):
    """(mid, average fill, cost in bp of mid) for a `side` ("buy" or "sell") market order of `usd`."""
    if not bids or not asks:
        return None, None, None
    mid = (bids[0][0] + asks[0][0]) / 2
    px = walk(asks if side == "buy" else bids, usd)
    if px is None:
        return mid, None, None
    return mid, px, (px / mid - 1) * 1e4 * (1 if side == "buy" else -1)


def register():
    """Add the "kraken" venue to lab.carrylane.VENUES (daily candles, hourly funding)."""
    from . import carrylane
    carrylane.VENUES.setdefault("kraken", carrylane.Venue(prices, funding, mids, listed,
                                                          "kraken_hist/open/candles_1d", "volume",
                                                          "kraken_hist/open/funding", 24, 2))
    return carrylane.VENUES["kraken"]


def sides(action, long_venue, short_venue):
    """Which side each venue trades for a ticket: entering buys the long and sells the short; exiting the reverse."""
    if action in ("enter", "inherit"):
        return {long_venue: "buy", short_venue: "sell"}
    return {long_venue: "sell", short_venue: "buy"}


def finite(x):
    return x is not None and np.isfinite(x)
