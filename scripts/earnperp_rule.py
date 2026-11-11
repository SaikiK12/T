"""R461 earnperp_v1 rule, frozen in experiments/earnperp_v1/PREREG.md: when a US company files its earnings release
(SEC 8-K, Item 2.02) outside cash hours, its 24/7 stock perpetual reacts while the cash market is shut. Does the
perp keep moving the way it first moved, or turn back, by the next cash open and close, by more than a round trip?

Pure functions over hourly perp bars (labelled by open time, epoch ms; the price at instant T is the open of the bar
that starts at T, which on MEXC equals the previous bar's close). scripts/run_earnperp.py feeds it.

One event, acceptance instant A (EDGAR), New York time:
- session   amc: 16:00 <= A < 21:00 on a trading day D;  bmo: 04:00 <= A < 09:30 on a trading day D; else skipped
- R         reference: 16:00 (or the early close) on D for amc, on the trading day before D for bmo
- E         entry: A rounded up to the hour, plus one hour
- N         next session: the trading day after D for amc, D itself for bmo
- X1        N 10:00 (half an hour after the cash open);  X2  N's cash close (16:00, or 13:00 on an early close)
- r0        1e4 ln(P(E) / P(R)), the first reaction; s = sign(r0), events with r0 = 0 are dropped
- c_k       s * 1e4 ln(P(X_k) / P(E)), the continuation (negative = reversal), bp before costs
A horizon whose exit is not after E, or whose price is missing, is missing for that event.
"""
import math
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from lab.sessions import NYSEHolidays

NY = ZoneInfo("America/New_York")
HOUR_MS = 3_600_000
PRICE_TOL_MS = 2 * HOUR_MS        # the price at T is the first bar open in [T, T + 2 h)
EARLY_CLOSE = {date(2025, 7, 3), date(2025, 11, 28), date(2025, 12, 24), date(2026, 11, 27), date(2026, 12, 24)}
UNIT_COST_BP = 30.0               # xyz taker 9 bp each way + 10 bp spread and slippage off-hours + 2 bp funding
COST_MULTS = (1, 2, 3)
DECISIONS = (("amc", "x2"), ("amc", "x1"))
MIN_A, MIN_B = 100, 30
ALPHA = 0.05
DRAWS = 200_000
SEED = 461
Z_MDE = 2.8
_HOL = set(NYSEHolidays().holidays(pd.Timestamp("2024-01-01"), pd.Timestamp("2027-12-31")).date)


def trading_day(d):
    return d.weekday() < 5 and d not in _HOL


def next_trading_day(d):
    d += timedelta(days=1)
    while not trading_day(d):
        d += timedelta(days=1)
    return d


def prev_trading_day(d):
    d -= timedelta(days=1)
    while not trading_day(d):
        d -= timedelta(days=1)
    return d


def close_time(d):
    return time(13, 0) if d in EARLY_CLOSE else time(16, 0)


def ms(d, t):
    return int(datetime.combine(d, t, tzinfo=NY).timestamp() * 1000)


def instants(acc_ms):
    """dict(session, R, E, X1, X2) in epoch ms, or session None when the filing is outside both windows."""
    a = datetime.fromtimestamp(acc_ms / 1000, tz=NY)
    d, m = a.date(), a.hour * 60 + a.minute
    if not trading_day(d):
        return {"session": None}
    if close_time(d).hour * 60 <= m < 21 * 60:
        sess, ref_day, n = "amc", d, next_trading_day(d)
    elif 4 * 60 <= m < 9 * 60 + 30:
        sess, ref_day, n = "bmo", prev_trading_day(d), d
    else:
        return {"session": None}
    e = (acc_ms // HOUR_MS + (1 if acc_ms % HOUR_MS else 0)) * HOUR_MS + HOUR_MS
    return {"session": sess, "R": ms(ref_day, close_time(ref_day)), "E": e, "X1": ms(n, time(10, 0)),
            "X2": ms(n, close_time(n)), "N": n.isoformat()}


def price_at(t_bars, open_bars, t):
    ix = int(np.searchsorted(t_bars, t))
    if ix < len(t_bars) and t <= t_bars[ix] < t + PRICE_TOL_MS and open_bars[ix] > 0:
        return float(open_bars[ix])
    return math.nan


def event_row(t_bars, open_bars, inst):
    """r0, sign and continuations for one event's instants."""
    p = {k: price_at(t_bars, open_bars, inst[k]) for k in ("R", "E", "X1", "X2")}
    row = {"r0": math.nan, "s": 0, "x1": math.nan, "x2": math.nan}
    if not (p["R"] > 0 and p["E"] > 0):
        return row
    r0 = 1e4 * math.log(p["E"] / p["R"])
    if r0 == 0:
        return row
    s = 1 if r0 > 0 else -1
    row.update(r0=r0, s=s)
    for k in ("X1", "X2"):
        if inst[k] > inst["E"] and p[k] > 0:
            row[k.lower()] = s * 1e4 * math.log(p[k] / p["E"])
    return row


def cluster_flip_p(x, clusters, rng, draws=DRAWS):
    """Two-sided p of 'mean continuation is 0': signs flipped together within each cluster (the next-session day),
    so same-day events that share a market move are not counted as independent."""
    x = np.asarray(x, dtype=float)
    _, inv = np.unique(np.asarray(clusters), return_inverse=True)
    sums = np.bincount(inv, weights=x)
    obs = abs(sums.sum())
    k = len(sums)
    hits = 0
    done = 0
    while done < draws:
        b = min(20_000, draws - done)
        sg = rng.choice((-1.0, 1.0), size=(b, k))
        hits += int(np.sum(np.abs(sg @ sums) >= obs - 1e-9))
        done += b
    return (1 + hits) / (1 + draws)


def holm(p):
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    out = np.empty_like(p)
    run = 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(p) - k) * p[i]))
        out[i] = run
    return out


def mde80(sd, n):
    return Z_MDE * sd / math.sqrt(n) if n > 1 and np.isfinite(sd) else math.nan


def verdict(cells):
    """cells: dicts with n_a, mean_a, p_holm, n_b, mean_b. Returns (state, text)."""
    states = []
    for c in cells:
        side = np.sign(c["mean_a"]) if np.isfinite(c["mean_a"]) else 0
        same_b = c["n_b"] >= MIN_B and np.sign(c["mean_b"]) == side and side != 0
        if c["n_a"] < MIN_A:
            states.append("INCONCLUSIVE")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > 2 * UNIT_COST_BP and same_b \
                and abs(c["mean_b"]) > UNIT_COST_BP:
            states.append("PASS")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > UNIT_COST_BP and same_b:
            states.append("PARTIAL")
        else:
            states.append("NULL")
    rank = {"PASS": 3, "PARTIAL": 2, "NULL": 1, "INCONCLUSIVE": 0}
    best = max(states, key=lambda s: rank[s]) if states else "INCONCLUSIVE"
    text = "; ".join(f"{s} {h}: {st}" for (s, h), st in zip(DECISIONS, states))
    return best, text
