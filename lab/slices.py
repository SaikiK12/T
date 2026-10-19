"""Overlapping-slice books (the Jegadeesh-Titman construction): every hour a symbol is in the signal state, open a slice of
fixed size and close it `hold` hours later. The position in a symbol is the sum of its live slices, so the book earns
the signal's mean over all hours in the state (what the atlas measures), and each slice pays one round trip.

Position P[t, s] is set at the close of row t and earns ret[t, s] (the next bar, funding included). Costs are charged on
every change of position at the symbol's tier cost. The optional hedge holds the opposite of the book's net exposure in
an equal-weighted basket, by default the symbols eligible at t (idealized: the basket's internal rebalancing is free);
`basket` [T, S] bool picks another one (the top 10, or BTC alone).
"""
import numpy as np


def positions(ind, hold, t0, t1, unit, side):
    """P[t - t0, s] = side x unit x (number of slices opened in rows max(t0, t - hold + 1) .. t)."""
    x = np.asarray(ind[t0:t1], np.float64)
    c = np.cumsum(x, axis=0)
    live = c.copy()
    live[hold:] -= c[:-hold]
    return side * unit * live


def book(ind, ret, elig, cmat, hold, unit, t0, t1, side=-1, hedge=True, cmult=1.0, basket=None):
    """ind: [T, S] bool, a slice opens at (t, s) when true (pass it already masked by eligibility). Returns a dict of
    hourly arrays over [t0, t1) and `daily` (sum of hours)."""
    return run(positions(ind, hold, t0, t1, unit, side), ret, elig, cmat, t0, t1, hedge, cmult, basket)


def run(P, ret, elig, cmat, t0, t1, hedge=True, cmult=1.0, basket=None):
    """The book's hourly results for positions P [t1 - t0, S] (e.g. a sum of several cells' positions, so opposite
    slices net out before costs)."""
    r = np.nan_to_num(np.asarray(ret[t0:t1], np.float64))
    c = np.asarray(cmat[t0:t1], np.float64)
    dP = np.diff(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0)
    out = {"gross": (P * r).sum(axis=1), "cost": cmult * (np.abs(dP) * c).sum(axis=1),
           "gross_exposure": np.abs(P).sum(axis=1), "net_exposure": P.sum(axis=1), "turnover": np.abs(dP).sum(axis=1)}
    out["hedge"] = np.zeros(len(P))
    out["hedge_cost"] = np.zeros(len(P))
    if hedge:
        b = np.asarray((elig if basket is None else basket)[t0:t1])
        e = b & np.isfinite(np.asarray(ret[t0:t1]))
        n = np.maximum(e.sum(axis=1), 1)
        H = -out["net_exposure"]
        out["hedge"] = H * (np.where(e, r, 0).sum(axis=1) / n)
        cm = np.where(b, c, 0).sum(axis=1) / np.maximum(b.sum(axis=1), 1)
        out["hedge_cost"] = cmult * np.abs(np.diff(np.concatenate([[0.0], H]))) * cm
    net = out["gross"] - out["cost"] + out["hedge"] - out["hedge_cost"]
    D = len(net) // 24
    out["net"] = net
    out["daily"] = net[: D * 24].reshape(D, 24).sum(axis=1)
    return out
