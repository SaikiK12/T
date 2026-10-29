"""usopen_fwd (R371): R300's pick, forward. The rule as frozen in experiments/usopen_fwd/PREREG.md.

On each NYSE trading day, at D = 10:00 New York (14:00 UTC in summer time, 15:00 in winter time): rank the Binance USDT
perps trading at D by the quote volume of their last 720 hourly bars and keep the top 50. A coin's move is its close at D
(the bar that closed at D) over its close at 00:00 UTC. Long the 3 strongest, short the 3 weakest (R300's "us10 n3 follow"),
flat at 24:00 UTC. Two books come from the same day: B, R300's own universe priced on Binance closes at API cost (a
replica of the discovery and validation numbers on new days), and M, the same rule among the coins that also have a MEXC
crypto perp, priced at one-minute opens on MEXC at the measured web cost (what the owner could trade by hand).

No I/O except the NYSE calendar. The daemon (scripts/forward_usopen.py) fetches the data and writes the journals.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab import sessions, stats

MIN, H, DAY = 60_000, 3_600_000, 86_400_000
TOP, MIN_NAMES, N_LEG, WINDOW = 50, 30, 3, 720   # R300's universe, floor on eligible names, names a leg, rank window (bars)
TICKET_DEADLINE_MS = 2 * MIN                     # a ticket written later than D + this is not written: "missed"
ENTRY_LAG_MIN = EXIT_LAG_MIN = 3                 # book M fills at the open of the minute this long after D / 24:00 UTC
COST_API = 8.5e-4                                # R300's API cost per side at 1x; book B turns over 4 units a day
TURNOVER = 4.0
SPREAD_FALLBACK = 0.0010                         # half-spread, one fill, when the ticker recorder has no quote that hour
NW_LAG = 5                                       # as R300
N_FUTILE, N_DECIDE = 125, 500                    # scored days of book M
BEST_DROP = 10


# ----------------------------------------------------------------------------------------------------------- clock
def is_nyse_day(day_ms):
    """Is the New York date of this UTC midnight a NYSE trading day (weekends and the exchange's holidays excluded)?"""
    noon = int(day_ms) + 12 * H
    trading, _ = sessions._nyse_open_day(sessions._local([noon], "America/New_York"))
    return bool(trading[0])


def decision_ms(day_ms):
    """10:00 America/New_York on the date of this UTC midnight, in UTC ms (14:00 UTC in EDT, 15:00 in EST)."""
    d = datetime.fromtimestamp(int(day_ms) / 1000, timezone.utc)
    return int(datetime(d.year, d.month, d.day, 10, 0, tzinfo=ZoneInfo("America/New_York")).timestamp() * 1000)


def decision_days(from_ms, n=12):
    """(day_ms, D) for the next n trading days whose UTC date is the date of from_ms or later."""
    out, day = [], int(from_ms) // DAY * DAY
    while len(out) < n:
        if is_nyse_day(day):
            out.append((day, decision_ms(day)))
        day += DAY
    return out


# ----------------------------------------------------------------------------------------------------- cross section
def cross_section(frames, day_ms, D):
    """One row per symbol that traded in the bar closing at D: trailing quote volume, close at D (c_e), close at 00:00
    UTC (c_s, NaN when that bar did not trade), the move sig = c_e / c_s - 1 and the liquidity rank (1 = largest volume,
    ties by symbol). frames: {symbol: DataFrame with t (bar open ms), close, quote_volume}. Only bars with open time in
    [D - 720 h, D) are read, so nothing after D can enter."""
    rows = []
    for sym, b in frames.items():
        w = b[(b.t >= D - WINDOW * H) & (b.t < D)]
        e = w[w.t == D - H]
        if e.empty or not (float(e.quote_volume.iloc[0]) > 0 and float(e.close.iloc[0]) > 0):
            continue
        s = w[w.t == day_ms - H]
        c_s = float(s.close.iloc[0]) if len(s) and float(s.quote_volume.iloc[0]) > 0 and float(s.close.iloc[0]) > 0 \
            else np.nan
        c_e = float(e.close.iloc[0])
        rows.append((sym, float(np.nan_to_num(w.quote_volume.to_numpy(float)).sum()), c_e, c_s, c_e / c_s - 1.0))
    cs = pd.DataFrame(rows, columns=["symbol", "vol", "c_e", "c_s", "sig"])
    if cs.empty:
        cs["rank"] = []
        return cs
    cs = cs.sort_values(["vol", "symbol"], ascending=[False, True], kind="stable").reset_index(drop=True)
    cs["rank"] = np.arange(1, len(cs) + 1)
    return cs


def pick(cs, n=N_LEG):
    """(longs, shorts, eligible): the n strongest and n weakest among the top-TOP names with a finite move, or None when
    fewer than MIN_NAMES are eligible. Order inside a leg: strongest first for longs, weakest first for shorts."""
    e = cs[(cs["rank"] <= TOP) & cs.sig.notna()].sort_values(["sig", "symbol"], kind="stable")
    if len(e) < MIN_NAMES:
        return None
    return list(e.symbol.iloc[::-1].iloc[:n]), list(e.symbol.iloc[:n]), int(len(e))


# ----------------------------------------------------------------------------------------------------------- scoring
def book_return(longs, shorts):
    """longs, shorts: lists of dict(ret, fund), a leg's price return over the hold and the funding rates settled in it
    (positive = longs pay). Each side is the equal-weight mean, one unit per side as R300. Returns (price, funding):
    price = mean long ret - mean short ret; funding = what the book receives (shorts receive, longs pay)."""
    lr, sr = np.mean([x["ret"] for x in longs]), np.mean([x["ret"] for x in shorts])
    lf, sf = np.mean([x["fund"] for x in longs]), np.mean([x["fund"] for x in shorts])
    return float(lr - sr), float(sf - lf)


def api_cost(k=1):
    """Book B's cost for k times R300's API cost: TURNOVER units of COST_API."""
    return k * TURNOVER * COST_API


def leg_cost(taker, spread_entry, spread_exit):
    """One leg's round trip on MEXC web: a taker fee at entry and exit plus the half-spread of both fills."""
    return 2.0 * float(taker) + float(spread_entry) + float(spread_exit)


def web_cost(long_costs, short_costs):
    """Book M's 1x cost: the mean leg cost of each side (one unit a side), summed."""
    return float(np.mean(long_costs) + np.mean(short_costs))


# ------------------------------------------------------------------------------------------------------------ verdict
def day_series(days_ms, nets):
    """The calendar-day grid R300's t is computed on: nets at day starts, NaN on days with no observation."""
    days_ms = np.asarray(days_ms, np.int64)
    nets = np.asarray(nets, float)
    if len(nets) == 0:
        return np.array([])
    grid = np.full(int((days_ms.max() - days_ms.min()) // DAY) + 1, np.nan)
    grid[(days_ms - days_ms.min()) // DAY] = nets
    return grid


def summarize(days_ms, nets, nets_2x=None):
    """n, mean, NW t (lag 5, calendar grid), mean without the 10 best days, hit rate, share of the best 10 days."""
    x = np.asarray(nets, float)
    n = len(x)
    out = {"n": n, "mean": None, "t": None, "mean_wo_best": None, "hit": None, "best_share": None}
    if n == 0:
        return out
    out["mean"], out["hit"] = float(x.mean()), float((x > 0).mean())
    if n >= 2:
        _, _, t = stats.newey_west_t(day_series(days_ms, x), NW_LAG)
        out["t"] = float(t) if np.isfinite(t) else None
    best = np.sort(x)[::-1]
    out["mean_wo_best"] = float(best[BEST_DROP:].mean()) if n > BEST_DROP else None
    out["best_share"] = float(best[:BEST_DROP].sum() / x.sum()) if n > BEST_DROP and x.sum() > 0 else None
    if nets_2x is not None:
        out["mean_2x"] = float(np.mean(nets_2x))
    return out


def verdict(s):
    """The PREREG's decision from a summarize() of exactly the days it is read on. At N_DECIDE scored days: PASS needs t >= 2
    at 1x, a positive 2x mean and a positive mean without the 10 best days, else NULL. At N_FUTILE: NULL when the 1x mean is
    negative with t <= -1. Otherwise pending."""
    n = s["n"]
    if n >= N_DECIDE:
        ok = s["t"] is not None and s["t"] >= 2 and (s.get("mean_2x") or 0) > 0 and (s["mean_wo_best"] or 0) > 0
        return "PASS" if ok else "NULL"
    if n >= N_FUTILE and (s["mean"] or 0) < 0 and (s["t"] or 0) <= -1:
        return f"NULL (futility at {N_FUTILE})"
    return f"pending ({n} of {N_DECIDE} scored)"


def decision(days_ms, nets, nets_2x):
    """(summary, verdict) with the verdict read once and kept: futility on the first N_FUTILE scored days, PASS/NULL on the
    first N_DECIDE. Later days are descriptive and cannot move either (a mean that recovers after day 125 does not undo
    the futility stop)."""
    order = np.argsort(np.asarray(days_ms, np.int64), kind="stable")
    d, a, b = (np.asarray(x, float)[order] for x in (days_ms, nets, nets_2x))
    n = len(a)
    if n >= N_FUTILE:
        s = summarize(d[:N_FUTILE].astype(np.int64), a[:N_FUTILE], b[:N_FUTILE])
        if verdict(s).startswith("NULL"):
            return s, verdict(s)
    if n >= N_DECIDE:
        s = summarize(d[:N_DECIDE].astype(np.int64), a[:N_DECIDE], b[:N_DECIDE])
        return s, verdict(s)
    return summarize(d.astype(np.int64), a, b), f"pending ({n} of {N_DECIDE} scored)"
