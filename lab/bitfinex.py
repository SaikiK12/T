"""Bitfinex public clients for forward carry lanes: USDt-margined perpetuals (`t<BASE>F0:USTF0`), no key.

Public endpoints only: nothing here can place an order. The request helper, the funding reduction and the candle
frame are R507's frozen ones (`scripts/fetch_bitfinex_history.py`), so a forward lane books funding exactly as R507
did:
- **Prices:** hourly trade candles (t = bar open, 00:00 UTC boundaries), loaded with `bar_h` 1. A daily close is the
  last hourly close at or before 00:00 UTC.
- **Funding:** the derivatives status history, reduced to one row per 8 h period, booked at the period's event time.
  Only periods ended by `end` are kept.
- **Mids and the live list:** `/v2/tickers?symbols=ALL`.
- **Books:** `/v2/book/{key}/P0`.
- **Symbols** are bases ("BTC", "DOGE"), as in R507's table.

`register()` adds a "bitfinex" venue to `lab.carrylane.VENUES` at run time (lab/carrylane.py is pinned by frozen
lanes). One worker: Bitfinex allows about 90 status requests a minute.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import fetch_bitfinex_history as fb  # noqa: E402  (frozen R507 client)

PACE = 0.8


def key(sym):
    return f"t{sym}F0:USTF0"


def prices(sym, start, end):
    """Hourly candles with t in [start, end): t, close, volume."""
    c = fb.fetch_candles(key(sym), start, end, PACE)
    if c.empty:
        return pd.DataFrame(columns=["t", "close", "volume"])
    return c[["t", "close", "volume"]].astype({"t": "int64", "close": float, "volume": float}).reset_index(drop=True)


def funding(sym, start, end):
    """One row per 8 h period ended by `end`: t = the period's event time, rate = the funding applied for it."""
    parts, since = [], start
    while since < end:
        rows = fb.get(f"{fb.API}/status/deriv/{key(sym)}/hist?start={since}&end={end - 1}&limit={fb.PAGE}&sort=1",
                      pace=PACE)
        rows = [r for r in rows or [] if r and r[0] is not None and since <= r[0] < end]
        if not rows:
            break
        parts += fb.reduce_page(rows)
        since = int(rows[-1][0]) + 1
        if len(rows) < fb.PAGE:
            break
    df = fb.combine(parts)
    if df.empty:
        return pd.DataFrame(columns=["t", "rate"])
    df = df[(df.t >= start) & (df.t <= end)]
    return df[["t", "rate"]].astype({"t": "int64", "rate": float}).reset_index(drop=True)


def _base(sym):
    return sym[1:-len("F0:USTF0")] if sym.startswith("t") and sym.endswith("F0:USTF0") else None


def mids():
    out = {}
    for r in fb.get(f"{fb.API}/tickers?symbols=ALL") or []:
        b = _base(str(r[0]))
        if b and len(r) > 3 and r[1] and r[3] and r[1] > 0 and r[3] > 0:
            out[b] = (float(r[1]) + float(r[3])) / 2
    return out


def listed():
    return {b for b in (_base(str(r[0])) for r in fb.get(f"{fb.API}/tickers?symbols=ALL") or []) if b}


def book(sym):
    """(bids, asks) as [[price, size in base units]], best first."""
    rows = fb.get(f"{fb.API}/book/{key(sym)}/P0?len=100") or []
    bids = sorted(([float(p), float(a)] for p, _, a in rows if a > 0), key=lambda x: -x[0])
    asks = sorted(([float(p), -float(a)] for p, _, a in rows if a < 0), key=lambda x: x[0])
    return bids, asks


def register():
    """Add the "bitfinex" venue to lab.carrylane.VENUES (hourly candles, 8 h funding periods)."""
    from . import carrylane
    carrylane.VENUES.setdefault("bitfinex", carrylane.Venue(prices, funding, mids, listed, "bitfinex_hist/candles_1h",
                                                            "volume", "bitfinex_hist/funding", 1, 1))
    return carrylane.VENUES["bitfinex"]
