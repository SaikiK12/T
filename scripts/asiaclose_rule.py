"""R468 asiaclose_v1 rule, frozen in experiments/asiaclose_v1/PREREG.md: Asian single-stock perps on trade.xyz and
Lighter trade every hour, but their reference exchange (KRX, TSE, HKEX, SSE) is shut about 17 hours each weekday and
over the weekend. While it is shut the perp is priced from its own book (trade.xyz's documented internal pricing;
Lighter's staleness-driven internal price). Does the perp's move over the local closure overshoot, so that fading it
pays once the local market reopens, or under-react, so that following it pays?

Pure functions over hourly candles (labelled by open time, epoch ms) and hourly funding. scripts/run_asiaclose.py feeds
it. No exchange here observes daylight saving time, so every instant is a fixed UTC hour.

One market-open: D a local trading day of the market's exchange, P the local trading day before it. All times UTC:
- R   P at r_h: inside P's main session, before its close (the last external price is at or after R)
- E   D at e_h (the calendar day before D when e_h is 23): entry, before D's session opens
- X1  D at x1_h: about an hour into D's session
- X2  D at x2_h: late in D's session (the same clock as R)
- P(T)  the close of the last hourly candle that opens in [T - 3 h, T - 1 h] (xyzwknd_rule.price_at)
- W   1e4 ln(P(E) / P(R)), the closure move; s = -sign(W) is the fade side (+1 long); W = 0 is dropped
- c_k s * 1e4 ln(P(X_k) / P(E)); f_k -s * 1e4 * funding settled in (E, X_k]; g_k = c_k + f_k (before trading costs)
- kind  "night" when P is the calendar day before D (a weekday night), else "gap" (a weekend or a holiday between)
"""
import math
from datetime import date, datetime, timedelta, timezone

import xyzwknd_rule as wk  # R462's frozen helpers: price_at, funding_sum

HOUR_MS = 3_600_000
# exchange: (R hour, E hour, X1 hour, X2 hour), UTC. E at 23 is on the calendar day before D.
CLOCK = {"KRX": (6, 23, 1, 6), "TSE": (6, 23, 1, 6), "HKEX": (7, 1, 3, 7), "SSE": (6, 1, 3, 6)}
EXITS = ("x1", "x2")


def _d(*days):
    return {date.fromisoformat(x) for x in days}


# Full-day closures from trade.xyz's holiday table (docs.trade.xyz llms-full.txt, sha256 7ac7ef34...) plus, for KRX,
# the two 2026 closures that table omits (Korea Exchange notice of 2026-05-20: local election day 06-03 and
# Constitution Day 07-17). Half days (HKEX 02-16, 12-24, 12-31) are listed in HALF and never serve as P.
HOLIDAYS = {
    "KRX": _d("2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-02", "2026-05-01", "2026-05-05",
              "2026-05-25", "2026-06-03", "2026-07-17", "2026-08-17", "2026-09-24", "2026-09-25", "2026-10-05",
              "2026-10-09", "2026-12-25", "2026-12-31"),
    "TSE": _d("2026-01-01", "2026-01-02", "2026-01-12", "2026-02-11", "2026-02-23", "2026-03-20", "2026-04-29",
              "2026-05-04", "2026-05-05", "2026-05-06", "2026-07-20", "2026-08-11", "2026-09-21", "2026-09-22",
              "2026-09-23", "2026-10-12", "2026-11-03", "2026-11-23", "2026-12-31"),
    "HKEX": _d("2026-01-01", "2026-02-17", "2026-02-18", "2026-02-19", "2026-04-03", "2026-04-06", "2026-04-07",
               "2026-05-01", "2026-05-25", "2026-06-19", "2026-07-01", "2026-10-01", "2026-10-19", "2026-12-25"),
    "SSE": _d("2026-01-01", "2026-01-02", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
              "2026-02-23", "2026-04-06", "2026-05-01", "2026-05-04", "2026-05-05", "2026-06-19", "2026-09-25",
              "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"),
}
HALF = {"HKEX": _d("2026-02-16", "2026-12-24", "2026-12-31")}


def trading_day(exchange, d):
    return d.weekday() < 5 and d not in HOLIDAYS[exchange]


def ms(d, hour):
    return int(datetime(d.year, d.month, d.day, hour, tzinfo=timezone.utc).timestamp() * 1000)


def previous_day(exchange, d):
    p = d - timedelta(days=1)
    while not trading_day(exchange, p):
        p -= timedelta(days=1)
    return p


def opening(exchange, d):
    """Instants of the closure that ends with D's open, or None when D is not a trading day or P is a half day."""
    if not trading_day(exchange, d):
        return None
    p = previous_day(exchange, d)
    if p in HALF.get(exchange, set()):
        return None
    r_h, e_h, x1_h, x2_h = CLOCK[exchange]
    e_day = d - timedelta(days=1) if e_h == 23 else d
    return {"D": d.isoformat(), "P": p.isoformat(), "kind": "night" if p == d - timedelta(days=1) else "gap",
            "R": ms(p, r_h), "E": ms(e_day, e_h), "X1": ms(d, x1_h), "X2": ms(d, x2_h)}


def openings(exchange, first, last):
    """Every opening dict whose D lies in [first, last] (dates)."""
    out, d = [], first
    while d <= last:
        o = opening(exchange, d)
        if o:
            out.append(o)
        d += timedelta(days=1)
    return out


def event_row(t_open, close, f_time, f_rate, o):
    """W, side and the fade's returns for one market and one opening dict."""
    p = {k: wk.price_at(t_open, close, o[k]) for k in ("R", "E", "X1", "X2")}
    row = {"W": math.nan, "s": 0}
    for k in EXITS:
        row.update({f"c_{k}": math.nan, f"f_{k}": math.nan, f"g_{k}": math.nan})
    if not (p["R"] > 0 and p["E"] > 0):
        return row
    wv = 1e4 * math.log(p["E"] / p["R"])
    if wv == 0:
        return row
    s = -1 if wv > 0 else 1
    row.update(W=wv, s=s)
    for k in EXITS:
        px = p[k.upper()]
        if px > 0:
            c = s * 1e4 * math.log(px / p["E"])
            f = -s * 1e4 * wk.funding_sum(f_time, f_rate, o["E"], o[k.upper()])
            row.update({f"c_{k}": c, f"f_{k}": f, f"g_{k}": c + f})
    return row
