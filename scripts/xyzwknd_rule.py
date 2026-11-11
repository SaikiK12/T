"""R462 xyzwknd_v1 rule, frozen in experiments/xyzwknd_v1/PREREG.md: trade.xyz (Hyperliquid HIP-3) US-equity perps are
priced internally from Friday 20:00 to Sunday 20:05 New York time. The oracle is a 30-minute EMA of the perp's own book,
starting from the last external print. Does the perp's weekend move overshoot, so that fading it pays once external
prices return (Sunday evening overnight session, then the Monday cash open)?

Pure functions over hourly candles (labelled by open time, epoch ms) and hourly funding. scripts/run_xyzwknd.py feeds
it.

One stock-weekend: F a NYSE trading Friday (not an early close) whose next trading day is the calendar Monday M = F + 3.
All times New York:
- R   Friday 20:00, the end of the external session (last external print)
- E   Sunday 19:00, entry, about an hour before external prices resume
- X1  Sunday 22:00, about two hours after the Blue Ocean overnight session resumes
- X2  Monday 10:00, half an hour after the cash open
- P(T)  the close of the last hourly candle that opens in [T - 3 h, T - 1 h]: the last trade before T, at most 3 h old
- W   1e4 ln(P(E) / P(R)), the weekend move; s = -sign(W) is the fade side (+1 long); W = 0 is dropped
- c_k s * 1e4 ln(P(X_k) / P(E)), the fade's price return in bp
- f_k -s * 1e4 * sum of the hourly funding rates settled in (E, X_k], the funding the fade receives (+) or pays (-)
- g_k = c_k + f_k, the fade's return before trading costs
"""
import math
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab.sessions import NYSEHolidays

NY = ZoneInfo("America/New_York")
HOUR_MS = 3_600_000
STALE_MS = 3 * HOUR_MS
EARLY_CLOSE = {date(2025, 7, 3), date(2025, 11, 28), date(2025, 12, 24), date(2026, 11, 27), date(2026, 12, 24)}
GROWTH_TAKER_BP = 0.9             # HIP-3 growth mode: a tenth of the 9 bp standard xyz taker fee, one way
STANDARD_TAKER_BP = 9.0
SLIPPAGE_BP = 4.0                 # round trip, both fills (assumed; xyz books are recorded only from 2026-11-11)
COST_MULTS = (1, 2, 3)
THETAS = (0, 50, 100, 200)
EXITS = ("x1", "x2")
GROUPS = ("all", "single", "etf", "rel")
DECISIONS = (("all", 50, "x2"), ("all", 50, "x1"))
MIN_A, MIN_WEEKENDS_A = 100, 10
MIN_B, MIN_WEEKENDS_B = 30, 4
ALPHA = 0.05
DRAWS = 200_000
SEED = 462
_HOL = set(NYSEHolidays().holidays(pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")).date)


def trading_day(d):
    return d.weekday() < 5 and d not in _HOL


def ms(d, t):
    return int(datetime.combine(d, t, tzinfo=NY).timestamp() * 1000)


def weekend(friday):
    """Instants of the weekend that starts on `friday` (a date), or None when it is not a plain Friday-Monday
    weekend: Friday not a trading day or an early close, or Monday not a trading day."""
    if friday.weekday() != 4 or not trading_day(friday) or friday in EARLY_CLOSE:
        return None
    monday = friday + timedelta(days=3)
    if not trading_day(monday):
        return None
    sunday = friday + timedelta(days=2)
    return {"F": friday.isoformat(), "R": ms(friday, time(20, 0)), "E": ms(sunday, time(19, 0)),
            "X1": ms(sunday, time(22, 0)), "X2": ms(monday, time(10, 0))}


def fridays(first, last):
    """Every weekend dict whose Friday lies in [first, last] (dates)."""
    out, d = [], first + timedelta(days=(4 - first.weekday()) % 7)
    while d <= last:
        w = weekend(d)
        if w:
            out.append(w)
        d += timedelta(days=7)
    return out


def price_at(t_open, close, t):
    """Close of the last candle that opens in [t - 3 h, t - 1 h]; nan when there is none."""
    ix = int(np.searchsorted(t_open, t - HOUR_MS, side="right")) - 1
    if ix >= 0 and t_open[ix] >= t - STALE_MS and close[ix] > 0:
        return float(close[ix])
    return math.nan


def funding_sum(f_time, f_rate, start, end):
    """Sum of hourly funding rates settled in (start, end]."""
    lo = int(np.searchsorted(f_time, start, side="right"))
    hi = int(np.searchsorted(f_time, end, side="right"))
    return float(np.sum(f_rate[lo:hi]))


def event_row(t_open, close, f_time, f_rate, w):
    """W, side and the fade's returns for one market and one weekend dict."""
    p = {k: price_at(t_open, close, w[k]) for k in ("R", "E", "X1", "X2")}
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
            f = -s * 1e4 * funding_sum(f_time, f_rate, w["E"], w[k.upper()])
            row.update({f"c_{k}": c, f"f_{k}": f, f"g_{k}": c + f})
    return row


def unit_cost(growth_enabled):
    """Round-trip cost unit in bp: two taker fees plus the slippage assumption."""
    fee = GROWTH_TAKER_BP if growth_enabled else STANDARD_TAKER_BP
    return 2 * fee + SLIPPAGE_BP


def relative(per, exit_key):
    """'rel' rows: each market's W and fade return net of that weekend's median over all eligible markets (a
    long-short book; funding not included). Returns DataFrame(F, coin, W, g, unit)."""
    rows = []
    for f, g in per.groupby("F"):
        g = g[np.isfinite(g.W) & np.isfinite(g[f"c_{exit_key}"])]
        if len(g) < 5:
            continue
        mw = float(np.median(g.W))
        # the raw (unfaded) move from E to X: c = s * move, so move = c * s
        move = g[f"c_{exit_key}"].to_numpy() * g.s.to_numpy()
        mm = float(np.median(move))
        wr = g.W.to_numpy() - mw
        sr = np.where(wr > 0, -1.0, np.where(wr < 0, 1.0, 0.0))
        for coin, w_, s_, mv, u in zip(g.coin, wr, sr, move, g.unit):
            if s_ != 0:
                rows.append({"F": f, "coin": coin, "W": w_, "g": s_ * (mv - mm), "unit": 2 * u})
    return pd.DataFrame(rows, columns=["F", "coin", "W", "g", "unit"])


def verdict(cells):
    """cells: dicts with n_a, wk_a, mean_a, unit_a, p_holm, n_b, wk_b, mean_b, unit_b. Returns (state, text)."""
    states = []
    for c in cells:
        side = np.sign(c["mean_a"]) if np.isfinite(c["mean_a"]) else 0
        same_b = (c["n_b"] >= MIN_B and c["wk_b"] >= MIN_WEEKENDS_B and side != 0
                  and np.sign(c["mean_b"]) == side)
        if c["n_a"] < MIN_A or c["wk_a"] < MIN_WEEKENDS_A:
            states.append("INCONCLUSIVE")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > 2 * c["unit_a"] and same_b \
                and abs(c["mean_b"]) > c["unit_b"]:
            states.append("PASS")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > c["unit_a"] and same_b:
            states.append("PARTIAL")
        else:
            states.append("NULL")
    rank = {"PASS": 3, "PARTIAL": 2, "NULL": 1, "INCONCLUSIVE": 0}
    best = max(states, key=lambda s: rank[s]) if states else "INCONCLUSIVE"
    text = "; ".join(f"{g} theta {th} {x}: {st}" for (g, th, x), st in zip(DECISIONS, states))
    return best, text
