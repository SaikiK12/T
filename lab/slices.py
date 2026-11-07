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


def book(ind, ret, elig, cmat, hold, unit, t0, t1, side=-1, hedge=True, cmult=1.0, basket=None,
         *, missing="legacy"):
    """ind: [T, S] bool, a slice opens at (t, s) when true (pass it already masked by eligibility). Returns a dict of
    hourly arrays over [t0, t1) and `daily` (sum of hours)."""
    return run(positions(ind, hold, t0, t1, unit, side), ret, elig, cmat, t0, t1, hedge, cmult, basket,
               missing=missing)


def _require_observed(values, required, name, t0, nonnegative=False):
    bad = required & ~np.isfinite(values)
    if nonnegative:
        bad |= required & (values < 0)
    if bad.any():
        row, column = np.unravel_index(bad.argmax(), bad.shape)
        condition = "finite and nonnegative" if nonnegative else "finite"
        raise ValueError(f"{name} must be {condition} at row {t0 + row}, column {column}")


def run(P, ret, elig, cmat, t0, t1, hedge=True, cmult=1.0, basket=None, *, missing="legacy"):
    """The book's hourly results for positions P [t1 - t0, S] (e.g. a sum of several cells' positions, so opposite
    slices net out before costs).

    Default missing="legacy" preserves archived zero-filling and the hedge's return-availability filter.
    A new preregistration can select missing="raise": require finite returns on every exposed main/hedge leg,
    finite nonnegative costs wherever size changes, and a nonempty predetermined basket when hedging or changing
    hedge size. Missing unexposed observations are irrelevant. Failure invalidates this evaluation; it does not
    liquidate, drop, renormalize or assign a zero return to an unknown position. The hedge's free internal
    rebalancing, weight-based accounting and open terminal positions remain idealizations in either policy.
    """
    if missing not in ("legacy", "raise"):
        raise ValueError(f"Unknown missing-data policy: {missing!r}")
    raw = np.asarray(ret[t0:t1], np.float64)
    c = np.asarray(cmat[t0:t1], np.float64)
    if missing == "raise":
        P = np.asarray(P, np.float64)
        if P.ndim != 2 or P.shape[0] != t1 - t0 or raw.shape != P.shape or c.shape != P.shape:
            raise ValueError("Positions, return interval and cost interval must have shape [t1 - t0, S]")
        if not np.isfinite(P).all():
            raise ValueError("Positions must be finite")
        if not np.isfinite(cmult) or cmult < 0:
            raise ValueError("Cost multiplier must be finite and nonnegative")
        _require_observed(raw, P != 0, "Exposed main return", t0)
    r = np.nan_to_num(raw) if missing == "legacy" else np.where(np.isfinite(raw), raw, 0.0)
    dP = np.diff(np.vstack([np.zeros((1, P.shape[1])), P]), axis=0)
    main_cost = c
    if missing == "raise":
        _require_observed(c, dP != 0, "Main trade cost", t0, nonnegative=True)
        main_cost = np.where(dP != 0, c, 0.0)
    out = {"gross": (P * r).sum(axis=1), "cost": cmult * (np.abs(dP) * main_cost).sum(axis=1),
           "gross_exposure": np.abs(P).sum(axis=1), "net_exposure": P.sum(axis=1), "turnover": np.abs(dP).sum(axis=1)}
    out["hedge"] = np.zeros(len(P))
    out["hedge_cost"] = np.zeros(len(P))
    if hedge:
        b = np.asarray((elig if basket is None else basket)[t0:t1])
        H = -out["net_exposure"]
        dH = np.diff(np.concatenate([[0.0], H]))
        hedge_cost = c
        if missing == "raise":
            if b.shape != P.shape or b.dtype.kind != "b":
                raise ValueError("Hedge basket interval must be a boolean array matching positions")
            needs_basket = (H != 0) | (dH != 0)
            empty = needs_basket & ~b.any(axis=1)
            if empty.any():
                raise ValueError(f"Empty required hedge basket at row {t0 + np.flatnonzero(empty)[0]}")
            _require_observed(raw, b & (H != 0)[:, None], "Exposed hedge return", t0)
            traded = b & (dH != 0)[:, None]
            _require_observed(c, traded, "Hedge trade cost", t0, nonnegative=True)
            hedge_cost = np.where(traded, c, 0.0)
            e = b  # Membership cannot depend on which next-bar returns are observed.
        else:
            e = b & np.isfinite(raw)
        n = np.maximum(e.sum(axis=1), 1)
        out["hedge"] = H * (np.where(e, r, 0).sum(axis=1) / n)
        cm = np.where(b, hedge_cost, 0).sum(axis=1) / np.maximum(b.sum(axis=1), 1)
        out["hedge_cost"] = cmult * np.abs(dH) * cm
    net = out["gross"] - out["cost"] + out["hedge"] - out["hedge_cost"]
    D = len(net) // 24
    out["net"] = net
    out["daily"] = net[: D * 24].reshape(D, 24).sum(axis=1)
    return out
