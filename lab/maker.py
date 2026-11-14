"""Maker entries: trade a signal with a resting limit order instead of a market order, so the entry pays the maker fee
and earns the distance to the reference price instead of paying spread and slippage, at the price of fills that come
mostly when the price moves against the order (adverse selection).

A signal fires for symbol s at row t (the close of bar t is known). A long posts a buy limit at P = close[t] (1 - d);
it is filled only if bar t + 1 trades through it, low[t + 1] < P (1 - eps), so a fill does not depend on queue position.
A short mirrors it with the high. The filled position is closed at the close of bar t + h (a market order at the tier
cost), or, in exit mode 1, by a limit at that close resting during bar t + h + 1 (maker fee if traded through, else the
close of bar t + h + 1 at the tier cost). d = kappa x the symbol's trailing hourly volatility; kappa < 0 means a market
entry at close[t] (the taker baseline, tier cost). Longs pay funding settled while the position is open.

Costs are kept apart so any fee or cost multiple can be applied afterwards: net = gross - cmult x taker_cost - fee x
maker_legs.
"""
import numpy as np
import pandas as pd
from numba import njit, prange


def trailing_vol(close, window=168):
    """Std of the hourly returns of bars t - window + 1 .. t, known at the close of bar t. NaN until window / 2 bars."""
    c = np.asarray(close, np.float64)
    r = np.full(c.shape, np.nan)
    r[1:] = c[1:] / c[:-1] - 1
    return pd.DataFrame(r).rolling(window, min_periods=window // 2).std().values


@njit(cache=True)
def _trade(t, s, h, side, close, low, high, fund, vol, cmat, t1, kappa, eps, exit_mode):
    """(status, exit row, gross, taker cost, maker legs); status -1 = not posted, 0 = posted and not filled, 1 = filled."""
    c0 = close[t, s]
    last = t + h + (1 if exit_mode == 1 else 0)
    if np.isnan(c0) or last >= t1:
        return -1, 0, 0.0, 0.0, 0
    tcost = 0.0
    legs = 0
    if kappa < 0:
        p = c0
        tcost += cmat[t, s]
    else:
        sg = vol[t, s]
        if np.isnan(sg):
            return -1, 0, 0.0, 0.0, 0
        p = c0 * (1.0 - side * kappa * sg)
        legs += 1
        if side > 0:
            if not (low[t + 1, s] < p * (1.0 - eps)):
                return 0, 0, 0.0, 0.0, 0
        else:
            if not (high[t + 1, s] > p * (1.0 + eps)):
                return 0, 0, 0.0, 0.0, 0
    x = close[t + h, s]
    te = t + h
    if exit_mode == 1 and not np.isnan(x):
        if side > 0:
            hit = high[t + h + 1, s] > x * (1.0 + eps)
        else:
            hit = low[t + h + 1, s] < x * (1.0 - eps)
        if hit:
            legs += 1
        else:
            x = close[t + h + 1, s]
            te = t + h + 1
            tcost += cmat[t, s]
    else:
        tcost += cmat[t, s]
    if np.isnan(x):
        return -1, 0, 0.0, 0.0, 0
    fsum = 0.0
    for k in range(t + 1, te + 1):
        f = fund[k, s]
        if not np.isnan(f):
            fsum += f
    return 1, te, side * (x / p - 1.0) - side * fsum, tcost, legs


@njit(cache=True)
def _fires(bins, v, b, t, s, elig, episodes):
    if v < 0:
        return True
    if bins[v, t, s] != b:
        return False
    return not (episodes and t > 0 and elig[t - 1, s] and bins[v, t - 1, s] == b)


@njit(parallel=True, cache=True)
def _cells(bins, cv, cb, ch, cside, close, low, high, fund, vol, eidx, ecnt, elig, cmat, t0, t1, kappa, eps,
           exit_mode, episodes, gross, tcost, legs, fills, posts):
    for i in prange(len(cv)):
        for t in range(t0, t1):
            d = (t - t0) // 24
            for j in range(ecnt[t]):
                s = eidx[t, j]
                if not _fires(bins, cv[i], cb[i], t, s, elig, episodes):
                    continue
                st, te, g, tc, lg = _trade(t, s, ch[i], cside[i], close, low, high, fund, vol, cmat, t1, kappa, eps,
                                           exit_mode)
                if st < 0:
                    continue
                posts[i, d] += 1
                if st == 1:
                    fills[i, d] += 1
                    gross[i, d] += g
                    tcost[i, d] += tc
                    legs[i, d] += lg


def run_cells(bins, cells, close, low, high, fund, vol, elig, cmat, index, t0, t1, kappa, eps=2e-4, exit_mode=0,
              episodes=True):
    """cells: int array [C, 4] of (view or -1 for every eligible symbol and hour, bin, horizon, side). Returns a dict of
    [C, D] daily arrays: gross (sum over the day's filled trades), tcost, legs, fills and posts (counts)."""
    cells = np.asarray(cells, np.int64)
    C, D = len(cells), (t1 - t0) // 24
    out = {k: np.zeros((C, D)) for k in ("gross", "tcost", "legs", "fills", "posts")}
    eidx, ecnt = index
    _cells(bins, cells[:, 0], cells[:, 1], cells[:, 2], cells[:, 3], close, low, high, fund, vol, eidx, ecnt, elig,
           cmat, t0, t1, float(kappa), eps, exit_mode, episodes, out["gross"], out["tcost"], out["legs"], out["fills"],
           out["posts"])
    return out


def net(o, fee, cmult=1.0):
    return o["gross"] - cmult * o["tcost"] - fee * o["legs"]


@njit(cache=True)
def _book(bins, cv, cb, ch, cside, close, low, high, fund, vol, eidx, ecnt, elig, cmat, t0, t1, kappa, eps,
          exit_mode, episodes, slots, gross, tcost, legs, n_open, conflicts):
    """One position per symbol, at most `slots` at a time, each 1/slots of capital. At each hour the cells are visited
    in order and the first that fires for a free symbol posts its order; a filled trade books its result on its exit
    day. Signals of opposite sides on the same symbol and hour cancel (counted in conflicts)."""
    T, S = close.shape
    busy = np.zeros(S, np.int64)          # row until which the symbol is held (exclusive)
    open_ = 0
    ends = np.zeros(t1 + 2, np.int64)     # positions ending at each row
    for t in range(t0, t1):
        open_ -= ends[t]
        for j in range(ecnt[t]):
            s = eidx[t, j]
            if busy[s] > t or open_ >= slots:
                continue
            side = 0
            hh = 0
            for i in range(len(cv)):
                if _fires(bins, cv[i], cb[i], t, s, elig, episodes):
                    if side == 0:
                        side, hh = cside[i], ch[i]
                    elif side != cside[i]:
                        side = 2
                        break
            if side == 0:
                continue
            if side == 2:
                conflicts[0] += 1
                continue
            st, te, g, tc, lg = _trade(t, s, hh, side, close, low, high, fund, vol, cmat, t1, kappa, eps, exit_mode)
            if st != 1:
                continue
            d = (te - t0) // 24
            if d >= len(gross):
                continue
            gross[d] += g / slots
            tcost[d] += tc / slots
            legs[d] += lg / slots
            busy[s] = te + 1
            ends[te + 1] += 1
            open_ += 1
        n_open[(t - t0) // 24] += open_ / 24.0


def book(bins, cells, close, low, high, fund, vol, elig, cmat, index, t0, t1, kappa, eps=2e-4, exit_mode=0,
         episodes=True, slots=10):
    """Daily book over rows [t0, t1) that takes the cells' signals (cells listed by priority). Returns a dict of [D]
    arrays (gross, tcost, legs as fractions of capital; n_open = mean open positions) and the conflict count."""
    cells = np.asarray(cells, np.int64)
    D = (t1 - t0) // 24
    out = {k: np.zeros(D) for k in ("gross", "tcost", "legs", "n_open")}
    conflicts = np.zeros(1, np.int64)
    eidx, ecnt = index
    _book(bins, cells[:, 0], cells[:, 1], cells[:, 2], cells[:, 3], close, low, high, fund, vol, eidx, ecnt, elig,
          cmat, t0, t1, float(kappa), eps, exit_mode, episodes, slots, out["gross"], out["tcost"], out["legs"],
          out["n_open"], conflicts)
    out["conflicts"] = int(conflicts[0])
    return out
