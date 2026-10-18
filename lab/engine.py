"""Vectorized backtester. A rule is read off feature bins; a position decided at row t earns the return of bar t + 1.

Rule: up to K conditions "lo <= bin(view v) <= hi"; the signal fires when at least `need` of them hold (need = K is AND,
1 is OR, in between is a vote). Direction is fixed per rule. Entries are held at least `hold` bars, then exit when the
signal goes off. Each position gets weight 1 / max(active, slots), so rare signals do not concentrate the book.
Costs are paid on every change of a symbol's signed weight, at a per-symbol one-way rate; funding is charged to
positions held through the settlement that follows their entry (conservative at the instant of entry).
"""
from dataclasses import dataclass

import numpy as np
from numba import njit, prange

DAY = 24


@dataclass(frozen=True)
class Rule:
    view: tuple      # indices into the bins array, one per condition
    lo: tuple
    hi: tuple
    need: int
    direction: int   # +1 long, -1 short
    hold: int        # minimum bars to hold an entry

    def key(self):
        return (self.view, self.lo, self.hi, self.need, self.direction, self.hold)


def forward_returns(close, fund_event):
    """ret[t] = close[t+1] / close[t] - 1, less the funding a long position pays at a settlement inside bar t + 1.

    fund_event[t] is the rate that settles on bar t (NaN otherwise), so symbols with 4h or 1h intervals pay each time.
    """
    ret = np.full_like(close, np.nan)
    ret[:-1] = close[1:] / close[:-1] - 1
    charge = np.zeros_like(close)
    charge[:-1] = np.nan_to_num(fund_event[1:], nan=0.0)
    return ret - charge


def cost_matrix(rank, tiers=((20, 6e-4), (50, 8e-4), (100, 12e-4)), beyond=20e-4):
    """One-way cost per unit of weight traded, by trailing-liquidity tier (fee plus assumed slippage)."""
    c = np.full(rank.shape, beyond, np.float32)
    for top, v in reversed(tiers):
        c[rank <= top] = v
    return c


@njit(cache=True)
def _run(bins, ret, elig, cmat, vidx, lo, hi, need, direction, hold, slots, t0, t1, cmult, out):
    T, S = ret.shape
    K = len(vidx)
    pos = np.zeros(S, np.int8)
    age = np.zeros(S, np.int32)
    wprev = np.zeros(S, np.float32)
    newpos = np.zeros(S, np.int8)
    for t in range(t0, t1):
        n_act = 0
        for s in range(S):
            sig = 0
            if elig[t, s]:
                cnt = 0
                for k in range(K):
                    x = bins[vidx[k], t, s]
                    if x >= lo[k] and x <= hi[k]:
                        cnt += 1
                if cnt >= need:
                    sig = direction
            p = pos[s]
            if not elig[t, s]:
                p = 0
            elif p != 0:
                age[s] += 1
                if sig != p and age[s] >= hold:
                    p = 0
            else:
                if sig != 0:
                    p = sig
                    age[s] = 0
            pos[s] = p
            newpos[s] = p
            if p != 0:
                n_act += 1
        denom = max(n_act, slots)
        r = 0.0
        tc = 0.0
        for s in range(S):
            w = newpos[s] / denom
            x = ret[t, s]
            if w != 0.0 and not np.isnan(x):
                r += w * x
            d = w - wprev[s]
            if d != 0.0:
                tc += abs(d) * cmat[t, s] * cmult
            wprev[s] = w
        out[t, 0] = r - tc
        out[t, 1] = tc
        out[t, 2] = n_act


@njit(parallel=True, cache=True)
def _run_many(bins, ret, elig, cmat, vidx, lo, hi, need, direction, hold, slots, t0, t1, cmult, out):
    for i in prange(len(need)):
        _run(bins, ret, elig, cmat, vidx[i], lo[i], hi[i], need[i], direction[i], hold[i], slots, t0, t1, cmult, out[i])


def run_rules(bins, ret, elig, cmat, rules, t0, t1, slots=10, cmult=1.0):
    """Hourly results for each rule: array [R, T, 3] of (net return, cost paid, active positions)."""
    R, K = len(rules), max(len(r.view) for r in rules)
    vidx = np.zeros((R, K), np.int64)
    lo = np.full((R, K), 127, np.int8)   # unused slots can never match
    hi = np.full((R, K), -127, np.int8)
    for i, r in enumerate(rules):
        n = len(r.view)
        vidx[i, :n], lo[i, :n], hi[i, :n] = r.view, r.lo, r.hi
    need = np.array([r.need for r in rules], np.int64)
    out = np.zeros((R, ret.shape[0], 3), np.float32)
    _run_many(bins, ret, elig, cmat, vidx, lo, hi, need, np.array([r.direction for r in rules], np.int64),
              np.array([r.hold for r in rules], np.int64), slots, t0, t1, cmult, out)
    return out


@njit(cache=True)
def nw_t(x, lag):
    """Newey-West t of the mean of a complete (no gaps) series."""
    n = len(x)
    if n < 3:
        return np.nan
    mu = 0.0
    for i in range(n):
        mu += x[i]
    mu /= n
    s = 0.0
    for i in range(n):
        s += (x[i] - mu) ** 2
    for l in range(1, min(lag, n - 1) + 1):
        g = 0.0
        for i in range(l, n):
            g += (x[i] - mu) * (x[i - l] - mu)
        s += 2.0 * (1.0 - l / (lag + 1.0)) * g
    if s <= 1e-24 * n:
        return np.nan
    return mu / (np.sqrt(s) / n)


def daily(r_hourly, t0, t1):
    """Sum hourly returns into UTC days over [t0, t1); both must sit on day boundaries."""
    assert t0 % DAY == 0 and t1 % DAY == 0
    return r_hourly[t0:t1].reshape(-1, DAY).sum(axis=1)


def era_table(out, t0, t1, edges, lag=3):
    """Per-rule, per-era (mean daily return, NW t). `edges` are day indices into [t0, t1) that split it into eras."""
    d = out[:, t0:t1, 0].reshape(len(out), -1, DAY).sum(axis=2)
    bounds = [0, *edges, d.shape[1]]
    mean = np.empty((len(out), len(bounds) - 1), np.float64)
    tst = np.empty_like(mean)
    for j, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        for i in range(len(out)):
            seg = d[i, a:b].astype(np.float64)
            mean[i, j] = seg.mean()
            tst[i, j] = nw_t(seg, lag)
    return mean, tst
