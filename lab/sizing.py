"""Causal, bounded sizing primitives for a future confidence lane.

These functions only transform inputs supplied by a caller.  They do not
estimate a return edge from the same observations on which a position is
scored.  A new lane must provide lagged forecasts, uncertainty and costs, then
compare the result with a matched constant exposure.
"""
import numpy as np


def lagged_ewma_vol(returns, halflife=30.0, min_periods=90):
    """Per-period EWMA standard deviation known at each return timestamp.

    The value at ``t`` uses only observations strictly before ``t``.  Missing
    observations are skipped, and the output stays NaN until ``min_periods``
    finite observations are available.
    """
    x = np.asarray(returns, dtype=float).reshape(-1)
    if halflife <= 0 or min_periods < 1:
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
                           initial=1.0):
    """Lagged, capped volatility target multiplier for a one-dimensional book."""
    if target_vol < 0 or floor < 0 or cap < floor or initial < floor or initial > cap:
        raise ValueError("invalid volatility multiplier bounds")
    vol = lagged_ewma_vol(returns, halflife, min_periods)
    out = np.full(len(vol), float(initial))
    ok = np.isfinite(vol) & (vol > 0)
    out[ok] = np.clip(float(target_vol) / vol[ok], floor, cap)
    return out


def lower_bound_multiplier(mu, se, hurdle, sigma, z=1.645, floor=0.0, cap=1.0, unknown=0.0):
    """Bounded sizing from a lower confidence bound, with no implicit leverage.

    ``mu - z*se`` must clear the per-period round-trip hurdle.  Invalid or
    non-positive volatility inputs receive ``unknown`` (zero by default).
    """
    if z < 0 or floor < 0 or cap < floor or unknown < floor or unknown > cap:
        raise ValueError("invalid confidence multiplier bounds")
    mu, se, hurdle, sigma = np.broadcast_arrays(np.asarray(mu, float), np.asarray(se, float),
                                                 np.asarray(hurdle, float), np.asarray(sigma, float))
    out = np.full(mu.shape, float(unknown), dtype=float)
    ok = np.isfinite(mu) & np.isfinite(se) & np.isfinite(hurdle) & np.isfinite(sigma) & (sigma > 0)
    edge = np.where(ok, mu - z * se - hurdle, 0.0)
    out[ok] = np.clip(edge[ok] / sigma[ok], floor, cap)
    return out.item() if out.ndim == 0 else out


def apply_multiplier(positions, multiplier, max_symbol=None, max_gross=None):
    """Scale a position matrix and enforce optional per-symbol and gross caps."""
    p = np.asarray(positions, dtype=float)
    if p.ndim != 2:
        raise ValueError("positions must be a [time, symbol] matrix")
    m = np.asarray(multiplier, dtype=float)
    if m.ndim != 1 or len(m) != len(p) or not np.isfinite(m).all() or (m < 0).any():
        raise ValueError("multiplier must be finite, non-negative and aligned to positions")
    q = p * m[:, None]
    if max_symbol is not None:
        if max_symbol < 0:
            raise ValueError("max_symbol must be non-negative")
        q = np.clip(q, -max_symbol, max_symbol)
    if max_gross is not None:
        if max_gross < 0:
            raise ValueError("max_gross must be non-negative")
        gross = np.abs(q).sum(axis=1)
        q = q * np.minimum(1.0, float(max_gross) / np.maximum(gross, 1e-30))[:, None]
    return q


def matched_constant_multiplier(positions, multiplier):
    """Return constant gross exposure matched to a dynamic multiplier."""
    p = np.asarray(positions, dtype=float)
    q = apply_multiplier(p, multiplier)
    base = np.abs(p).sum(axis=1)
    denom = float(np.nanmean(base))
    if not np.isfinite(denom) or denom <= 0:
        raise ValueError("positions have no finite gross exposure")
    return float(np.nanmean(np.abs(q).sum(axis=1)) / denom)


def turnover(positions):
    """Exact position transition size, including the initial entry from zero."""
    p = np.asarray(positions, dtype=float)
    if p.ndim != 2:
        raise ValueError("positions must be a [time, symbol] matrix")
    return np.abs(np.diff(np.vstack([np.zeros((1, p.shape[1])), p]), axis=0)).sum(axis=1)
