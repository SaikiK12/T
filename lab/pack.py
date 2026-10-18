"""A pack: many signal cells traded in one book, each entry a limit order (lab/maker.py rules) or a market order, marked
to market every hour, with an optional hedge that holds the opposite of the book's net exposure in one instrument (BTC).

Each hour the cells are visited in priority order, and for each the eligible symbols in index order; a cell that fires
(episode start, and its context gate open) on a symbol with no open position and no order this hour posts an order if
the book has room (open positions plus orders this hour < slots). Each position is 1/slots of capital. A cell may carry
a gate: a context tensor index and a code, with mode +1 = trade only when the context has that code, -1 = never then.

Hourly accounting for a filled long opened at P during bar t + 1 and closed at the close of bar te: bar t + 1 earns
close/P - 1, later bars close-to-close returns, every bar pays the funding settled in it; shorts mirror. Costs: the entry
leg (maker fee or taker tier cost) and the exit (taker tier cost at the close of te, times cmult) are charged on the
fill and exit bars. The hedge holds -beta x net exposure (set at each close) in the hedge column, paying its tier cost on
every change.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _fires(bins, v, b, t, s, elig):
    if bins[v, t, s] != b:
        return False
    return not (t > 0 and elig[t - 1, s] and bins[v, t - 1, s] == b)


@njit(cache=True)
def _gate_ok(ctx, gk, gc, gm, t, s):
    if gk < 0:
        return True
    c = ctx[gk, t, s]
    if gm > 0:
        return c == gc
    return c != gc


@njit(cache=True)
def _run(bins, ctx, cv, cb, ch, cside, gk, gc, gm, close, low, high, fund, vol, eidx, ecnt, elig, cmat, t0, t1, kappa,
         eps, fee, cmult, slots, hedge_col, beta, out):
    """out[t - t0] = (gross, entry cost, exit cost, hedge pnl, hedge cost, net exposure, open positions, fills)."""
    T, S = close.shape
    side = np.zeros(S, np.int64)
    ent = np.zeros(S)                 # fill price
    t_fill = np.full(S, -1, np.int64)
    t_exit = np.full(S, -1, np.int64)
    posted = np.full(S, -1, np.int64)
    n_open = 0
    hpos = 0.0
    w = 1.0 / slots
    for t in range(t0, t1):
        o = t - t0
        # 1) bar t: mark open positions, settle fills and exits that happen inside bar t
        g = 0.0
        ec = 0.0
        xc = 0.0
        fills = 0
        for s in range(S):
            if side[s] == 0 or t_fill[s] < 0 or t_fill[s] >= t:
                continue
            r = close[t, s] / close[t - 1, s] - 1.0        # a missing bar (halt, delisting) counts as no move
            if not np.isnan(r):
                g += side[s] * w * r
            f = fund[t, s]
            if not np.isnan(f):
                g -= side[s] * w * f
            if t_exit[s] == t:
                xc += w * cmult * cmat[t, s]
                side[s] = 0
                n_open -= 1
        # orders posted at the previous close: filled in bar t if it trades through them, else cancelled
        for s in range(S):
            if posted[s] != t - 1 or side[s] == 0 or t_fill[s] != -2:
                continue
            ok = low[t, s] < ent[s] * (1.0 - eps) if side[s] > 0 else high[t, s] > ent[s] * (1.0 + eps)
            if ok:
                t_fill[s] = t
                fills += 1
                r = close[t, s] / ent[s] - 1.0
                if not np.isnan(r):
                    g += side[s] * w * r
                f = fund[t, s]
                if not np.isnan(f):
                    g -= side[s] * w * f
                ec += w * fee
                if t_exit[s] == t:
                    xc += w * cmult * cmat[t, s]
                    side[s] = 0
                    n_open -= 1
            else:
                side[s] = 0
                n_open -= 1
        # hedge earns on bar t with the exposure set at the previous close
        hp = 0.0
        if hedge_col >= 0 and t > t0:
            r = close[t, hedge_col] / close[t - 1, hedge_col] - 1.0
            if not np.isnan(r):
                hp = hpos * r
        # 2) at the close of bar t: new signals
        for i in range(len(cv)):
            for j in range(ecnt[t]):
                if n_open >= slots:
                    break
                s = eidx[t, j]
                if side[s] != 0 or posted[s] == t:
                    continue
                if not _fires(bins, cv[i], cb[i], t, s, elig) or not _gate_ok(ctx, gk[i], gc[i], gm[i], t, s):
                    continue
                c0 = close[t, s]
                te = t + ch[i]
                if np.isnan(c0) or te >= t1:
                    continue
                if kappa < 0:
                    side[s] = cside[i]
                    ent[s] = c0
                    t_fill[s] = t
                    t_exit[s] = te
                    ec += w * cmult * cmat[t, s]
                    fills += 1
                else:
                    sg = vol[t, s]
                    if np.isnan(sg):
                        continue
                    side[s] = cside[i]
                    ent[s] = c0 * (1.0 - cside[i] * kappa * sg)
                    t_fill[s] = -2        # pending
                    t_exit[s] = te
                posted[s] = t
                n_open += 1
        # net exposure of filled positions at this close, hedge rebalance
        e = 0.0
        for s in range(S):
            if side[s] != 0 and t_fill[s] >= 0:
                e += side[s] * w
        hc = 0.0
        if hedge_col >= 0:
            target = -beta * e
            hc = abs(target - hpos) * cmult * cmat[t, hedge_col]
            hpos = target
        out[o, 0] = g
        out[o, 1] = ec
        out[o, 2] = xc
        out[o, 3] = hp
        out[o, 4] = hc
        out[o, 5] = e
        out[o, 6] = n_open
        out[o, 7] = fills


def run(bins, cells, close, low, high, fund, vol, elig, cmat, index, t0, t1, kappa=1.0, eps=2e-4, fee=2e-4, cmult=1.0,
        slots=10, hedge_col=-1, beta=1.0, ctx=None):
    """cells: int array [C, 7] of (view, bin, horizon, side, gate context index or -1, gate code, gate mode), in
    priority order. Returns a dict of hourly arrays over [t0, t1) and the daily net (sum of hours)."""
    cells = np.asarray(cells, np.int64)
    if cells.shape[1] == 4:
        cells = np.c_[cells, np.full((len(cells), 3), -1)]
    if ctx is None:
        ctx = np.zeros((1, 1, 1), np.int8)
    out = np.zeros((t1 - t0, 8))
    eidx, ecnt = index
    _run(bins, ctx, cells[:, 0], cells[:, 1], cells[:, 2], cells[:, 3], cells[:, 4], cells[:, 5], cells[:, 6], close,
         low, high, fund, vol, eidx, ecnt, elig, cmat, t0, t1, float(kappa), eps, fee, cmult, slots, hedge_col, beta, out)
    names = ("gross", "entry_cost", "exit_cost", "hedge", "hedge_cost", "exposure", "n_open", "fills")
    res = {k: out[:, i] for i, k in enumerate(names)}
    net = out[:, 0] - out[:, 1] - out[:, 2] + out[:, 3] - out[:, 4]
    D = (t1 - t0) // 24
    res["net"] = net
    res["daily"] = net[: D * 24].reshape(D, 24).sum(axis=1)
    return res
