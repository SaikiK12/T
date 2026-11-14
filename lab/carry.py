"""Funding carry: short the perpetual and hold the same coin spot, so price moves cancel and the position collects the
funding that longs pay shorts, minus changes in the perp-spot basis and the cost of four trades (two legs, in and out).

Per hour and unit of notional the hedged position earns +funding at its settlement hour (shorts receive a positive
rate) minus the change of the basis b = perp / index - 1 (here the premium index), so over a holding period the basis
part is entry basis minus exit basis. The signal is trailing funding: the sum of the last `look` hours of settled
rates, annualized. Only positive carry is taken (the reverse needs borrowed spot).
"""
import numpy as np
from numba import njit

YEAR_H = 24 * 365


def trailing_apr(fund_event, look=72):
    """Sum of settled funding over the last `look` hours (rows t - look + 1 .. t), annualized. NaN until `look` rows."""
    x = np.nan_to_num(np.asarray(fund_event, np.float64))
    c = np.zeros((x.shape[0] + 1, x.shape[1]))
    c[1:] = np.cumsum(x, axis=0)
    out = np.full(x.shape, np.nan)
    out[look - 1:] = (c[look:] - c[:-look]) * (YEAR_H / look)
    return out


@njit(cache=True)
def _run(apr, fund, basis, elig, ok, perp_cost, spot_cost, th_in, th_out, slots, t0, t1, out):
    """out[t] = (net, funding, basis, cost, n_open). Positions open when apr > th_in and close when apr < th_out or the
    symbol stops being eligible; the next hour's funding and basis change accrue to positions held at the close of t."""
    T, S = apr.shape
    pos = np.zeros(S, np.int8)
    w = np.zeros(S)
    for t in range(t0, t1 - 1):
        n = 0
        for s in range(S):
            a = apr[t, s]
            live = elig[t, s] and ok[t, s] and not np.isnan(a) and not np.isnan(basis[t, s])
            if pos[s] == 1 and (not live or a < th_out):
                pos[s] = 0
            elif pos[s] == 0 and live and a > th_in:
                pos[s] = 1
            n += pos[s]
        fr = 0.0
        br = 0.0
        tc = 0.0
        for s in range(S):
            nw = pos[s] / max(n, slots) if pos[s] else 0.0
            d = abs(nw - w[s])
            if d > 0:
                tc += d * (perp_cost[t, s] + spot_cost)
            w[s] = nw
            if nw > 0:
                f = fund[t + 1, s]
                if not np.isnan(f):
                    fr += nw * f
                b0, b1 = basis[t, s], basis[t + 1, s]
                if not np.isnan(b0) and not np.isnan(b1):
                    br -= nw * (b1 - b0)
        out[t, 0] = fr + br - tc
        out[t, 1] = fr
        out[t, 2] = br
        out[t, 3] = tc
        out[t, 4] = n


def run(apr, fund, basis, elig, has_spot, perp_cost, spot_cost, th_in, th_out, t0, t1, slots=10):
    """has_spot: [S] or [T, S] bool, whether the coin can be held spot (at that hour)."""
    ok = np.asarray(has_spot, np.bool_)
    if ok.ndim == 1:
        ok = np.broadcast_to(ok, apr.shape)
    out = np.zeros((apr.shape[0], 5))
    _run(apr, fund, basis, elig, np.ascontiguousarray(ok), perp_cost, float(spot_cost), th_in, th_out, slots, t0, t1, out)
    return out[t0:t1]


def spot_pair(bases, spot, quote="USDT", prefixes=("1000000", "1000")):
    """The first spot pair in `spot` for any of the candidate bases (each also tried without a 1000/1000000 prefix,
    as 1000BONKUSDT perp -> BONKUSDT spot), or None."""
    for b in bases:
        for c in [b] + [b[len(p):] for p in prefixes if b.startswith(p)]:
            if c + quote in spot:
                return c + quote
    return None
