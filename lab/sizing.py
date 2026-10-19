"""Causal, bounded sizing primitives for a future confidence lane.

These functions only transform inputs supplied by a caller.  They do not
estimate a return edge from the same observations on which a position is
scored.  A new lane must provide lagged forecasts, uncertainty and costs, then
compare the result with a matched constant exposure.
"""
import numpy as np


def _nonnegative_scalar(value, name):
    if np.ndim(value) != 0 or not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return float(value)


def _bounds(floor, cap):
    floor = _nonnegative_scalar(floor, "floor")
    cap = _nonnegative_scalar(cap, "cap")
    if cap < floor:
        raise ValueError("cap must be at least floor")
    return floor, cap


def _positions(positions):
    p = np.asarray(positions, dtype=float)
    if p.ndim != 2 or not np.isfinite(p).all():
        raise ValueError("positions must be a finite [time, symbol] matrix")
    return p


def lagged_ewma_vol(returns, halflife=30.0, min_periods=90):
    """Per-period EWMA standard deviation known at each return timestamp.

    The value at ``t`` uses observations strictly before ``t``. Non-finite
    outcomes reset history from the following row, rather than making stale
    volatility available after an outage. Requires a regular observation clock
    and ``min_periods`` consecutive finite observations after each reset.
    """
    x = np.asarray(returns, dtype=float)
    halflife = _nonnegative_scalar(halflife, "halflife")
    if x.ndim != 1 or halflife == 0 or not isinstance(min_periods, (int, np.integer)) or min_periods < 1:
        raise ValueError("halflife must be positive and min_periods must be at least one")
    out = np.full(len(x), np.nan)
    alpha = 1.0 - np.exp(np.log(0.5) / float(halflife))
    mean = 0.0
    var = 0.0
    n = 0
    for t, value in enumerate(x):
        if n >= min_periods:
            out[t] = np.sqrt(max(var, 0.0))
        if not np.isfinite(value):
            n, mean, var = 0, 0.0, 0.0
            continue
        if n == 0:
            mean = value
            var = 0.0
        else:
            delta = value - mean
            mean += alpha * delta
            var = (1.0 - alpha) * (var + alpha * delta * delta)
        n += 1
    return out


def volatility_multiplier(returns, target_vol, halflife=30.0, min_periods=90, floor=0.0, cap=1.0,
                          initial=0.0, unknown=0.0):
    """Lagged volatility scaling; warmup/unknown estimates default to no size.

    ``initial`` applies only to the first ``min_periods`` decision rows.
    Thereafter invalid or zero estimates receive ``unknown``, including after
    an outage. A zero target always produces zero exposure. Positive floors
    apply only to usable risk.
    """
    target_vol = _nonnegative_scalar(target_vol, "target_vol")
    floor, cap = _bounds(floor, cap)
    initial = _nonnegative_scalar(initial, "initial")
    unknown = _nonnegative_scalar(unknown, "unknown")
    if initial > cap or unknown > cap:
        raise ValueError("invalid volatility multiplier bounds")
    vol = lagged_ewma_vol(returns, halflife, min_periods)
    if target_vol == 0:
        return np.zeros(len(vol))
    out = np.full(len(vol), unknown)
    out[:min_periods] = initial
    ok = np.isfinite(vol) & (vol > 0)
    out[ok] = np.clip(target_vol / vol[ok], floor, cap)
    return out


def lower_bound_multiplier(mu, se, hurdle, sigma, z=1.645, floor=0.0, cap=1.0, unknown=0.0):
    """Bounded sizing from a lower confidence bound, with no implicit leverage.

    ``mu - z*se`` must clear the per-period round-trip hurdle.  Invalid or
    non-positive volatility inputs receive ``unknown`` (zero by default).
    """
    z = _nonnegative_scalar(z, "z")
    floor, cap = _bounds(floor, cap)
    unknown = _nonnegative_scalar(unknown, "unknown")
    if unknown > cap:
        raise ValueError("invalid confidence multiplier bounds")
    mu, se, hurdle, sigma = np.broadcast_arrays(np.asarray(mu, float), np.asarray(se, float),
                                              np.asarray(hurdle, float), np.asarray(sigma, float))
    out = np.full(mu.shape, float(unknown), dtype=float)
    ok = (np.isfinite(mu) & np.isfinite(se) & (se >= 0) & np.isfinite(hurdle) & (hurdle >= 0) &
          np.isfinite(sigma) & (sigma > 0))
    with np.errstate(over="ignore", invalid="ignore"):
        edge = mu - z * se - hurdle
    clear = ok & np.isfinite(edge) & (edge > 0)
    out[ok & ~clear] = 0.0
    out[clear] = np.clip(edge[clear] / sigma[clear], floor, cap)
    return out.item() if out.ndim == 0 else out


def apply_multiplier(positions, multiplier, max_symbol=None, max_gross=None):
    """Scale a complete venue position matrix, including any hedge, then cap it.

    Inputs must be signed capital weights in common notional units, not raw
    contract quantities. Adding a hedge afterwards bypasses these caps.
    """
    p = _positions(positions)
    m = np.asarray(multiplier, dtype=float)
    if m.ndim != 1 or len(m) != len(p) or not np.isfinite(m).all() or (m < 0).any():
        raise ValueError("multiplier must be finite, non-negative and aligned to positions")
    with np.errstate(over="raise", invalid="raise"):
        q = p * m[:, None]
    if max_symbol is not None:
        max_symbol = _nonnegative_scalar(max_symbol, "max_symbol")
        q = np.clip(q, -max_symbol, max_symbol)
    if max_gross is not None:
        max_gross = _nonnegative_scalar(max_gross, "max_gross")
        gross = np.abs(q).sum(axis=1)
        q = q * np.minimum(1.0, float(max_gross) / np.maximum(gross, 1e-30))[:, None]
    return q


def matched_constant_multiplier(positions, multiplier, max_symbol=None, max_gross=None):
    """Post-hoc constant matching the capped dynamic book's mean gross.

    Both sides receive identical caps. Freeze this constant on a burn-in
    period to make it a deployable control; matching on the evaluation sample
    is an attribution diagnostic, not a causal sizing rule.
    """
    p = _positions(positions)
    q = apply_multiplier(p, multiplier, max_symbol, max_gross)
    base = np.abs(p).sum(axis=1)
    denom = float(np.mean(base)) if len(base) else 0.0
    if not np.isfinite(denom) or denom <= 0:
        raise ValueError("positions have no finite gross exposure")
    target = float(np.abs(q).sum(axis=1).mean())
    if max_symbol is None and max_gross is None:
        return target / denom
    lo, hi = 0.0, float(np.max(multiplier))
    for _ in range(80):
        mid = (lo + hi) / 2.0
        control = apply_multiplier(p, np.full(len(p), mid), max_symbol, max_gross)
        if np.abs(control).sum(axis=1).mean() < target:
            lo = mid
        else:
            hi = mid
    return hi


def turnover(positions):
    """Exact position transition size, including the initial entry from zero."""
    p = _positions(positions)
    return np.abs(np.diff(np.vstack([np.zeros((1, p.shape[1])), p]), axis=0)).sum(axis=1)
