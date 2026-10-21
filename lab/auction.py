"""Auction-market levels from bars: anchored VWAP with standard-deviation bands, volume and TPO profiles, the point of
control and value area, high- and low-volume nodes, and the initial balance (docs/AUCTION_AND_FLOW.md).

Every function takes plain arrays (one row per bar, oldest first) and uses only the bars it is given, so a caller
that passes the bars of a session up to time t gets the levels known at t. Prices are binned on a fixed tick:
bin(p) = floor(p / tick) * tick.

Crypto trades around the clock, so a "session" is whatever anchor the caller picks (UTC midnight, 09:30 New York,
or a random clock as a placebo). Nothing here decides which anchor is right; lanes test that.
"""
import numpy as np
import pandas as pd


def session_ids(t, anchor_ms):
    """Session index of each bar: the number of anchors at or before its open time. `anchor_ms` is sorted epoch ms;
    bars before the first anchor get -1."""
    return np.searchsorted(np.asarray(anchor_ms, np.int64), np.asarray(t, np.int64), side="right") - 1


def vwap_bands(high, low, close, volume, session=None, ks=(1, 2, 3)):
    """Anchored VWAP of the typical price (h + l + c) / 3, reset at each new session id, with volume-weighted
    standard-deviation bands vwap ± k sd, where sd² = Σ v (p − vwap)² / Σ v over the session so far."""
    p = (np.asarray(high, float) + np.asarray(low, float) + np.asarray(close, float)) / 3
    v = np.nan_to_num(np.asarray(volume, float))
    g = np.zeros(len(p), np.int64) if session is None else np.asarray(session)
    df = pd.DataFrame({"g": g, "pv": p * v, "p2v": p * p * v, "v": v})
    c = df.groupby("g")[["pv", "p2v", "v"]].cumsum()
    with np.errstate(invalid="ignore", divide="ignore"):
        vwap = c.pv / c.v
        sd = np.sqrt(np.maximum(c.p2v / c.v - vwap * vwap, 0.0))
    out = pd.DataFrame({"vwap": vwap, "sd": sd})
    for k in ks:
        out[f"up{k}"] = vwap + k * sd
        out[f"dn{k}"] = vwap - k * sd
    return out


def spread(lo, hi, weight, tick):
    """Add weight[i] (any sign) to every bin from bin(lo[i]) to bin(hi[i]); a Series by bin price, ascending, with
    empty bins inside the range as 0. Bars with a missing price or a zero or missing weight are left out."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    w = np.asarray(weight, float)
    ok = np.isfinite(lo) & np.isfinite(hi) & np.isfinite(w) & (w != 0)
    a = np.floor(lo[ok] / tick).astype(np.int64)
    b = np.floor(hi[ok] / tick).astype(np.int64)
    w = w[ok]
    ok = b >= a
    a, b, w = a[ok], b[ok], w[ok]
    if not len(a):
        return pd.Series(dtype=float)
    lo0 = a.min()
    acc = np.zeros(b.max() - lo0 + 2)
    np.add.at(acc, a - lo0, w)                     # a difference array: + at the first bin, - after the last
    np.add.at(acc, b - lo0 + 1, -w)
    return pd.Series(np.cumsum(acc)[:-1], index=(np.arange(lo0, b.max() + 1) * tick).round(12))


def volume_profile(high, low, volume, tick):
    """Volume at each price bin, each bar's volume spread evenly over the bins between its low and high.
    Returns a Series indexed by the bin's lower price, ascending, with empty bins inside the range as 0."""
    n = np.floor(np.asarray(high, float) / tick) - np.floor(np.asarray(low, float) / tick) + 1
    with np.errstate(invalid="ignore", divide="ignore"):
        return spread(low, high, np.asarray(volume, float) / n, tick)


def tpo_profile(high, low, tick, period):
    """Time-price opportunities: within each block of `period` bars, every bin the price touched counts once."""
    block = np.arange(len(high)) // period
    hi = pd.Series(np.asarray(high, float)).groupby(block).max().values
    lo = pd.Series(np.asarray(low, float)).groupby(block).min().values
    return spread(lo, hi, np.ones(len(hi)), tick)


def value_area(profile, share=0.70):
    """Point of control (the bin with the most volume, the lowest on ties) and the value area: starting at the POC,
    add the larger of the next bin above and the next bin below until `share` of the total is inside.
    Returns (poc, val, vah) as bin prices; val and vah are the lower prices of the edge bins."""
    x = np.asarray(profile, float)
    if not len(x) or x.sum() <= 0:
        return np.nan, np.nan, np.nan
    px = np.asarray(profile.index, float)
    i = j = int(np.argmax(x))
    inside, need = x[i], share * x.sum()
    while inside < need and (i > 0 or j < len(x) - 1):
        up = x[j + 1] if j < len(x) - 1 else -1.0
        dn = x[i - 1] if i > 0 else -1.0
        if up >= dn:
            j += 1
            inside += up
        else:
            i -= 1
            inside += dn
    return px[int(np.argmax(x))], px[i], px[j]


def nodes(profile, width=5, high=1.5, low=0.5):
    """High- and low-volume nodes: local maxima and minima of the profile smoothed over `width` bins, kept when the
    smoothed volume is at least `high` (HVN) or at most `low` (LVN) times the profile's median nonzero bin.
    Returns (hvn_prices, lvn_prices)."""
    y = np.asarray(profile, float)
    x = pd.Series(y).rolling(width, center=True, min_periods=1).mean().values
    if len(x) < 3 or not (y > 0).any():
        return [], []
    med = np.median(y[y > 0])
    px = np.asarray(profile.index, float)
    peak = (x[1:-1] >= x[:-2]) & (x[1:-1] > x[2:])
    trough = (x[1:-1] <= x[:-2]) & (x[1:-1] < x[2:])
    k = np.arange(1, len(x) - 1)
    hvn = [px[i] for i in k[peak] if x[i] >= high * med]
    lvn = [px[i] for i in k[trough] if x[i] <= low * med]
    return hvn, lvn


def initial_balance(t, high, low, start_ms, minutes=60, bar_ms=60_000):
    """High and low of the bars that open in [start, start + minutes). The classic initial balance is the first hour
    of the session; an opening range is the same thing over a shorter window (5-30 minutes). Returns (ibh, ibl),
    NaN when no bar is inside."""
    t = np.asarray(t, np.int64)
    m = (t >= start_ms) & (t + bar_ms <= start_ms + minutes * 60_000)
    if not m.any():
        return np.nan, np.nan
    return float(np.nanmax(np.asarray(high, float)[m])), float(np.nanmin(np.asarray(low, float)[m]))
