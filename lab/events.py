"""Event studies on the hourly panel: per-event returns over a holding window, clustered statistics, and the daily PnL
of a book that takes every event with a fixed stake.

An event is (symbol column, row). The position opens at the close of row + delay and is held for `hold` hours;
its return is the sum of next-bar returns over that span (funding included, longs pay), minus the benchmark's over the
same span when one is given. Per-event costs are one round trip at the symbol's one-way cost at entry.
"""
import numpy as np
import pandas as pd

from . import stats


def cum(ret):
    c = np.zeros((ret.shape[0] + 1,) + ret.shape[1:])
    c[1:] = np.cumsum(np.nan_to_num(np.asarray(ret, np.float64)), axis=0)
    return c


def event_returns(ret, events, delay, hold, bench=None, end=None):
    """Return of each event over rows [row + delay, row + delay + hold) and the benchmark's over the same rows.
    Events whose window passes `end` (default: the panel end) or whose symbol has no return at entry are NaN."""
    T = ret.shape[0]
    end = T if end is None else end
    c = cum(ret)
    cb = cum(bench) if bench is not None else None
    out = np.full(len(events), np.nan)
    ob = np.full(len(events), np.nan)
    for i, (s, r) in enumerate(events):
        a, b = r + delay, r + delay + hold
        if b > end or a >= T or np.isnan(ret[a, s]):
            continue
        out[i] = c[b, s] - c[a, s]
        if cb is not None:
            ob[i] = cb[b] - cb[a]
    return out, ob


def clustered_t(x, cluster):
    """Mean of x and its t with standard errors clustered by `cluster` (e.g. the event month)."""
    ok = np.isfinite(x)
    x, cluster = np.asarray(x)[ok], np.asarray(cluster)[ok]
    n = len(x)
    if n < 3:
        return n, np.nan, np.nan
    mu = x.mean()
    e = x - mu
    g = pd.Series(e).groupby(cluster).sum().values
    G = len(g)
    var = (g ** 2).sum() / n ** 2 * (G / max(G - 1, 1))
    return n, mu, mu / np.sqrt(var) if var > 0 else np.nan


def book(ret, events, delay, hold, side, bench=None, cost=None, start=0, end=None, stake=1.0, slots=10):
    """Daily PnL of a book that opens `side` (+1 long, -1 short) on every event with stake/max(open positions, slots)
    of capital, hedged with the opposite position in the benchmark when given. Returns daily (net, gross, n_open)
    over rows [start, end)."""
    T = ret.shape[0]
    end = T if end is None else end
    pos = np.zeros(T, np.int64)
    opened = []
    for s, r in events:
        a, b = r + delay, min(r + delay + hold, end)
        if a < end and a >= start and not np.isnan(ret[a, s]):
            opened.append((s, a, b))
            pos[a:b] += 1
    gross = np.zeros(T)
    costs = np.zeros(T)
    for s, a, b in opened:
        w = side * stake / np.maximum(pos[a:b], slots)
        r = np.nan_to_num(ret[a:b, s])
        if bench is not None:
            r = r - np.nan_to_num(bench[a:b])
        gross[a:b] += w * r
        if cost is not None:
            k = 2.0 if bench is None else 4.0       # in and out, both legs when hedged
            costs[a] += k / 2 * abs(w[0]) * cost[a, s]
            costs[b - 1] += k / 2 * abs(w[-1]) * cost[min(b - 1, T - 1), s]
    D = (end - start) // 24
    g = gross[start:start + 24 * D].reshape(D, 24).sum(1)
    c = costs[start:start + 24 * D].reshape(D, 24).sum(1)
    n = pos[start:start + 24 * D].reshape(D, 24).mean(1)
    return g - c, g, n


def summary(daily):
    d = np.asarray(daily, float)
    if len(d) < 30 or d.std() == 0:
        return {}
    eq = np.cumsum(d)
    return {"ann": d.mean() * 365, "sharpe": d.mean() / d.std(ddof=1) * np.sqrt(365),
            "t_nw": stats.newey_west_t(d, 10)[2], "max_dd": float(np.max(np.maximum.accumulate(eq) - eq))}
