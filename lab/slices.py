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


def run_exact(P, ret, elig, cmat, t0, t1, hedge=True, cmult=1.0, basket=None,
              initial_positions=None, liquidate=False, terminal_cmat=None):
    """Account for a complete venue book, with explicit availability and costs.

    This opt-in path is for new lanes; ``run`` retains its historical convention.
    P[t-t0] is the signal target known before ret[t]. The hedge is allocated
    across the basket at t, without looking at future return availability, and
    combined with P before trading: Q = P + hedge_positions. Costs are charged
    on abs(Q[t] - Q[t-1]) per instrument, including basket membership changes.

    ``gross_exposure`` is abs(Q).sum, including hedges after venue netting;
    ``leg_gross_exposure`` also shows the pre-net signal and hedge legs.
    An unavailable held return or execution cost makes that hour and its
    calendar day's PnL missing. No halt/delisting price is invented.

    The default boundary is an open book. To close after the last return,
    pass liquidate=True and the one-way costs available at that exit close.
    Terminal components are already included in cost/turnover and daily PnL;
    do not add them again. t0 must be day-aligned; a partial final day is kept
    in hourly outputs only.
    All weights use the lab's fixed-notional target convention; this is not
    a contract-unit, fill, margin, or self-financing price-drift simulator.
    """
    p = np.asarray(P, dtype=float)
    if (not isinstance(t0, (int, np.integer)) or not isinstance(t1, (int, np.integer)) or
            p.ndim != 2 or not np.isfinite(p).all() or not 0 <= t0 < t1 or len(p) != t1 - t0):
        raise ValueError("P must be a finite [t1-t0, symbol] matrix with a nonempty window")
    if t0 % 24:
        raise ValueError("t0 must be aligned to a UTC day on the panel clock")
    if np.ndim(cmult) != 0 or not np.isfinite(cmult) or cmult < 0:
        raise ValueError("cmult must be finite and non-negative")
    if terminal_cmat is not None and not liquidate:
        raise ValueError("terminal_cmat requires liquidate=True")
    r = np.asarray(ret[t0:t1], dtype=float)
    c = np.asarray(cmat[t0:t1], dtype=float)
    b = np.asarray((elig if basket is None else basket)[t0:t1])
    if any(x.shape != p.shape for x in (r, c, b)):
        raise ValueError("return, cost and basket matrices must align with P")
    if b.dtype.kind not in "biuf" or not np.isfinite(b).all() or not np.isin(b, (0, 1)).all():
        raise ValueError("basket membership must be a finite boolean or zero/one matrix")
    b = b.astype(bool)
    prior = np.zeros(p.shape[1]) if initial_positions is None else np.asarray(initial_positions, dtype=float)
    if prior.shape != (p.shape[1],) or not np.isfinite(prior).all():
        raise ValueError("initial_positions must be a finite vector of prior venue holdings")

    h = np.zeros_like(p)
    count = b.sum(axis=1)
    missing_hedge = np.zeros(len(p), dtype=bool)
    if hedge:
        target = -p.sum(axis=1)
        missing_hedge = (target != 0) & (count == 0)
        h = b * (target / np.maximum(count, 1))[:, None]
    q = p + h
    moves = np.abs(np.diff(np.vstack([prior[None, :], q]), axis=0))
    active = q != 0
    missing_return = active & ~np.isfinite(r)
    missing_cost = (moves > 0) & (~np.isfinite(c) | (c < 0)) & (cmult > 0)
    valid = ~(missing_hedge | missing_return.any(axis=1) | missing_cost.any(axis=1))
    gross = (q * np.where(np.isfinite(r), r, 0.0)).sum(axis=1)
    cost = cmult * (moves * np.where(np.isfinite(c) & (c >= 0), c, 0.0)).sum(axis=1)
    turnover = moves.sum(axis=1)
    terminal_cost = np.zeros(len(p))
    terminal_turnover = np.zeros(len(p))
    if liquidate:
        if terminal_cmat is None:
            raise ValueError("liquidation requires explicit costs at the exit close")
        exit_c = np.asarray(terminal_cmat, dtype=float)
        if exit_c.shape != prior.shape or np.any((q[-1] != 0) & (~np.isfinite(exit_c) | (exit_c < 0))):
            raise ValueError("terminal_cmat must have a finite non-negative exit cost for every held instrument")
        terminal_turnover[-1] = np.abs(q[-1]).sum()
        terminal_cost[-1] = cmult * (np.abs(q[-1]) * np.where(np.isfinite(exit_c), exit_c, 0.0)).sum()
        cost += terminal_cost
        turnover += terminal_turnover
    gross[missing_return.any(axis=1) | missing_hedge] = np.nan
    cost[missing_cost.any(axis=1)] = np.nan
    net = np.where(valid, gross - cost, np.nan)
    days = len(p) // 24
    return {"positions": q, "hedge_positions": h, "gross": gross, "cost": cost, "net": net,
            "daily": net[:days * 24].reshape(days, 24).sum(axis=1),
            "valid": valid, "daily_valid": valid[:days * 24].reshape(days, 24).all(axis=1),
            "missing_return_exposure": np.where(missing_return, np.abs(q), 0.0).sum(axis=1),
            "missing_cost_turnover": np.where(missing_cost, moves, 0.0).sum(axis=1),
            "missing_hedge": missing_hedge, "basket_count": count, "hedge_covered": ~missing_hedge,
            "signal_gross_exposure": np.abs(p).sum(axis=1), "hedge_gross_exposure": np.abs(h).sum(axis=1),
            "leg_gross_exposure": np.abs(p).sum(axis=1) + np.abs(h).sum(axis=1),
            "gross_exposure": np.abs(q).sum(axis=1), "net_exposure": q.sum(axis=1),
            "turnover": turnover, "terminal_cost": terminal_cost, "terminal_turnover": terminal_turnover,
            "closing_positions": np.zeros_like(prior) if liquidate else q[-1].copy()}
