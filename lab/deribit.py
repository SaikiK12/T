"""Deribit public clients for forward carry lanes: linear USDC perpetuals (API v2, no key).

Public endpoints only: nothing here can place an order.
- **Prices:** `get_tradingview_chart_data` with resolution 60 (hourly bars, t = bar open).
  - Deribit's 1D bars run 08:00 to 08:00 UTC (R519's deviation). The lane loads hourly bars with `bar_h` 1, so each
    daily close is the last hourly close at or before 00:00 UTC, as on Hyperliquid.
- **Funding:** `get_funding_rate_history`, hourly rows; the rate is `interest_1h`.
- **Mids:** `get_book_summary_by_currency` (USDC futures).
- **Live list:** `get_instruments` (linear perpetuals, active).
- **Books:** `get_order_book` (amounts in base units).
- **Symbols** are bases ("BTC", "1000PEPE"), as in `data/deribit_perps`. The instrument is "<BASE>_USDC-PERPETUAL".

`register()` adds a "deribit" venue to `lab.carrylane.VENUES` at run time (lab/carrylane.py is pinned by frozen lanes).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

import pandas as pd

API = "https://www.deribit.com/api/v2/public/"
H = 3_600_000
DAY = 24 * H
PACE = 0.15
CHART_STEP = 150 * DAY
FUND_STEP = 30 * DAY


def instrument(base):
    return f"{base}_USDC-PERPETUAL"


def _get(method, **params):
    url = API + method + "?" + urllib.parse.urlencode(params)
    delay, err = 1.0, None
    for _ in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "research-client"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())["result"]
        except urllib.error.HTTPError as e:
            err = e
            body = {}
            try:
                body = json.loads(e.read() or b"{}")
            except ValueError:
                pass
            if (body.get("error") or {}).get("code") == -32602:     # invalid params, e.g. "instrument is not open"
                break
            if e.code == 429:
                time.sleep(10)
        except (OSError, ValueError, KeyError) as e:
            err = e
        time.sleep(delay)
        delay *= 2
    raise RuntimeError(f"{method} {params}: {err}")


def prices(sym, start, end):
    """Hourly bars with t in [start, end): t, close, volume."""
    parts, t = [], start
    while t < end:
        e = min(t + CHART_STEP, end)
        r = _get("get_tradingview_chart_data", instrument_name=instrument(sym), start_timestamp=t, end_timestamp=e,
                 resolution="60")
        parts.append(pd.DataFrame({"t": r.get("ticks", []), "close": r.get("close", []), "volume": r.get("volume", [])}))
        time.sleep(PACE)
        t = e
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["t", "close", "volume"])
    if df.empty:
        return pd.DataFrame(columns=["t", "close", "volume"])
    df = df.astype({"t": "int64", "close": float, "volume": float})
    return df[(df.t >= start) & (df.t < end)].drop_duplicates("t").sort_values("t", ignore_index=True)


def funding(sym, start, end):
    """Hourly funding with t in [start, end]: t, rate (interest_1h, + when longs pay)."""
    rows, t = [], start
    while t <= end:
        e = min(t + FUND_STEP, end)
        rows += _get("get_funding_rate_history", instrument_name=instrument(sym), start_timestamp=t,
                     end_timestamp=e) or []
        time.sleep(PACE)
        if e >= end:
            break
        t = e
    if not rows:
        return pd.DataFrame(columns=["t", "rate"])
    df = pd.DataFrame({"t": [int(r["timestamp"]) for r in rows], "rate": [float(r["interest_1h"]) for r in rows]})
    return df[(df.t >= start) & (df.t <= end)].drop_duplicates("t").sort_values("t", ignore_index=True)


def _base(name):
    return name.split("_USDC")[0] if name.endswith("_USDC-PERPETUAL") else None


def mids():
    out = {}
    for x in _get("get_book_summary_by_currency", currency="USDC", kind="future") or []:
        b = _base(x.get("instrument_name", ""))
        bid, ask = x.get("bid_price"), x.get("ask_price")
        if b and bid and ask and bid > 0 and ask > 0:
            out[b] = (float(bid) + float(ask)) / 2
    return out


def listed():
    return {_base(x["instrument_name"]) for x in _get("get_instruments", currency="USDC", kind="future", expired="false")
            if x.get("settlement_period") == "perpetual" and x.get("instrument_type") == "linear"
            and x.get("is_active", True) and _base(x["instrument_name"])}


def book(sym):
    d = _get("get_order_book", instrument_name=instrument(sym), depth=100)
    return ([[float(p), float(q)] for p, q in d.get("bids", [])], [[float(p), float(q)] for p, q in d.get("asks", [])])


def register():
    """Add the "deribit" venue to lab.carrylane.VENUES (hourly bars, hourly funding)."""
    from . import carrylane
    carrylane.VENUES.setdefault("deribit", carrylane.Venue(prices, funding, mids, listed, "deribit_perps/prices_1h",
                                                           "volume", "deribit_perps/funding", 1, 2))
    return carrylane.VENUES["deribit"]
