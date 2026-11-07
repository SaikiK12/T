"""ICT / smart-money concepts as mechanical, causal detectors on [T, S] bar arrays (one timeframe at a time).

Each detector keeps the latest zone of each side and reports a distance in ATR units, so every value at row i uses
bars through i only. Ordering inside a bar: existing zones are tested for mitigation first, then new ones are formed.
These are one reading of discretionary concepts; the variants (min gap, impulse size, lookbacks) are the search space.
All distances are positive when price is on the far side of the zone from where it would trade (above a bullish zone,
below a bearish one), zero inside it, and NaN when no live zone exists.
"""
import numpy as np
from numba import njit, prange

NAN = np.float32(np.nan)


@njit(parallel=True, cache=True)
def fvg(high, low, close, atr, min_gap):
    """Fair value gaps. Bullish: high[i-2] < low[i]; bearish: low[i-2] > high[i]; gap at least min_gap * ATR.

    Returns (bull_dist, bull_age, bear_dist, bear_age). A bullish zone [bottom, top] = [high[i-2], low[i]] dies when a
    later low trades at or below its bottom; a bearish zone [high[i], low[i-2]] dies when a later high reaches its top.
    """
    T, S = high.shape
    bd = np.full((T, S), NAN)
    ba = np.full((T, S), NAN)
    sd = np.full((T, S), NAN)
    sa = np.full((T, S), NAN)
    for s in prange(S):
        bb = bt = sb = st = np.nan
        b_i = s_i = -1
        for i in range(2, T):
            a = atr[i, s]
            if np.isnan(a) or np.isnan(high[i, s]) or np.isnan(low[i, s]) or np.isnan(close[i, s]):
                continue
            if not np.isnan(bb) and low[i, s] <= bb:
                bb = bt = np.nan
            if not np.isnan(st) and high[i, s] >= st:
                sb = st = np.nan
            h2, l2 = high[i - 2, s], low[i - 2, s]
            if not np.isnan(h2) and low[i, s] - h2 > min_gap * a and low[i, s] > h2:
                bb, bt, b_i = h2, low[i, s], i
            if not np.isnan(l2) and l2 - high[i, s] > min_gap * a and l2 > high[i, s]:
                sb, st, s_i = high[i, s], l2, i
            if not np.isnan(bb):
                bd[i, s] = max(close[i, s] - bt, 0.0) / a
                ba[i, s] = i - b_i
            if not np.isnan(st):
                sd[i, s] = max(sb - close[i, s], 0.0) / a
                sa[i, s] = i - s_i
    return bd, ba, sd, sa


@njit(parallel=True, cache=True)
def order_block(open_, high, low, close, atr, impulse, lookback):
    """Order blocks. Bullish: a displacement bar (close - open >= impulse * ATR of the prior bar) marks the most recent
    down-close bar within `lookback` bars before it; that bar's [low, high] is the zone. It dies when a close falls below
    its low. Bearish is the mirror image. Returns (bull_dist, bear_dist)."""
    T, S = high.shape
    bd = np.full((T, S), NAN)
    sd = np.full((T, S), NAN)
    for s in prange(S):
        bl = bh = sl = sh = np.nan
        for i in range(lookback + 1, T):
            a = atr[i - 1, s]
            if np.isnan(a) or np.isnan(close[i, s]) or np.isnan(open_[i, s]):
                continue
            if not np.isnan(bl) and close[i, s] < bl:
                bl = bh = np.nan
            if not np.isnan(sh) and close[i, s] > sh:
                sl = sh = np.nan
            body = close[i, s] - open_[i, s]
            if body >= impulse * a:
                for j in range(i - 1, i - lookback - 1, -1):
                    if close[j, s] < open_[j, s]:
                        bl, bh = low[j, s], high[j, s]
                        break
            elif -body >= impulse * a:
                for j in range(i - 1, i - lookback - 1, -1):
                    if close[j, s] > open_[j, s]:
                        sl, sh = low[j, s], high[j, s]
                        break
            if not np.isnan(bl):
                bd[i, s] = max(close[i, s] - bh, 0.0) / a
            if not np.isnan(sl):
                sd[i, s] = max(sl - close[i, s], 0.0) / a
    return bd, sd


@njit(parallel=True, cache=True)
def sweep(high, low, close, n):
    """Liquidity sweeps. Bullish: the bar's low takes out the lowest low of the previous n bars but it closes back above
    that level. Returns bars since the last bullish and bearish sweep (0 on the sweep bar, NaN before any)."""
    T, S = high.shape
    bs = np.full((T, S), NAN)
    ss = np.full((T, S), NAN)
    for s in prange(S):
        b_i = s_i = -1
        for i in range(n, T):
            if np.isnan(close[i, s]) or np.isnan(low[i, s]) or np.isnan(high[i, s]):
                continue
            lo = np.inf
            hi = -np.inf
            ok = True
            for j in range(i - n, i):
                if np.isnan(low[j, s]) or np.isnan(high[j, s]):
                    ok = False
                    break
                lo = min(lo, low[j, s])
                hi = max(hi, high[j, s])
            if ok:
                if low[i, s] < lo and close[i, s] > lo:
                    b_i = i
                if high[i, s] > hi and close[i, s] < hi:
                    s_i = i
            if b_i >= 0:
                bs[i, s] = i - b_i
            if s_i >= 0:
                ss[i, s] = i - s_i
    return bs, ss


@njit(parallel=True, cache=True)
def structure(high, low, close, fractal):
    """Market structure from confirmed swings. A swing high at j needs `fractal` lower highs on each side, so it is only
    known at j + fractal. A close above the last swing high is a break up (state +1), below the last swing low a break
    down (state -1). Returns (state, bars since the last break, premium/discount, retrace of the last up-leg), where
    premium/discount is where the close sits in [last swing low, last swing high] (0 discount, 1 premium)."""
    T, S = high.shape
    state = np.full((T, S), NAN)
    since = np.full((T, S), NAN)
    pd_ = np.full((T, S), NAN)
    ote = np.full((T, S), NAN)
    for s in prange(S):
        sh = sl = np.nan
        st = 0.0
        brk = -1
        for i in range(2 * fractal, T):
            if np.isnan(close[i, s]):
                continue
            j = i - fractal
            h, l = high[j, s], low[j, s]
            if not (np.isnan(h) or np.isnan(l)):
                is_h = True
                is_l = True
                for k in range(1, fractal + 1):
                    if not (h > high[j - k, s] and h > high[j + k, s]):
                        is_h = False
                    if not (l < low[j - k, s] and l < low[j + k, s]):
                        is_l = False
                if is_h:
                    sh = h
                if is_l:
                    sl = l
            if not np.isnan(sh) and close[i, s] > sh and st != 1.0:
                st, brk = 1.0, i
            elif not np.isnan(sl) and close[i, s] < sl and st != -1.0:
                st, brk = -1.0, i
            if st != 0.0:
                state[i, s] = st
                since[i, s] = i - brk
            if not (np.isnan(sh) or np.isnan(sl)) and sh > sl:
                pd_[i, s] = (close[i, s] - sl) / (sh - sl)
                ote[i, s] = (sh - close[i, s]) / (sh - sl)
    return state, since, pd_, ote
