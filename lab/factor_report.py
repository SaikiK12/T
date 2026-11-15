"""Reusable cross-sectional factor report: rank IC, quantile books and turnover.

Closes the BENCHMARK "Factor analytics" gap (an alphalens-style report over the lab's own panels).
Pure functions over daily arrays; no data loading, no search, no decision rule and no sample-read
permission. A caller owns its universe, its point-in-time eligibility and its gates; this module
only describes a factor against forward returns that the caller has already aligned.

Conventions match lab.panel and R222 (xsalt_v1): a row is one UTC day, the factor on row d is
computed from data through the 00:00 UTC close of day d, and forward returns are log changes of
the 00:00 UTC close. NaN means missing; a missing value is never treated as zero or fresh.
"""
import numpy as np
from scipy import stats as _stats

from .stats import newey_west_t


def _check_panel(factor, fwd, elig):
    factor = np.asarray(factor, dtype=float)
    fwd = np.asarray(fwd, dtype=float)
    if factor.ndim != 2 or fwd.shape != factor.shape:
        raise ValueError("factor and fwd must be 2-D with the same shape [days, symbols]")
    if elig is None:
        elig = np.ones(factor.shape, dtype=bool)
    else:
        elig = np.asarray(elig, dtype=bool)
        if elig.shape != factor.shape:
            raise ValueError("elig must have the same shape as factor")
    return factor, fwd, elig


def rank_ic(factor, fwd, elig=None, *, min_obs=5):
    """Daily Spearman rank IC between the factor and the forward return over eligible symbols.

    Returns (ic [D], n [D]); ic[d] is NaN when fewer than min_obs paired observations exist.
    Ties get average ranks (scipy.stats.rankdata)."""
    factor, fwd, elig = _check_panel(factor, fwd, elig)
    if min_obs < 2:
        raise ValueError("min_obs must be at least 2")
    d = factor.shape[0]
    ic = np.full(d, np.nan)
    n = np.zeros(d, dtype=int)
    for i in range(d):
        ok = elig[i] & np.isfinite(factor[i]) & np.isfinite(fwd[i])
        n[i] = int(ok.sum())
        if n[i] >= min_obs:
            a = _stats.rankdata(factor[i][ok])
            b = _stats.rankdata(fwd[i][ok])
            sa, sb = a.std(), b.std()
            if sa > 0 and sb > 0:
                ic[i] = float(np.corrcoef(a, b)[0, 1])
    return ic, n


def ic_summary(ic, *, lag=10):
    """Mean IC, NW t (calendar-day Bartlett weights as lab.stats), hit share and observed days."""
    ic = np.asarray(ic, dtype=float)
    n, mean, t = newey_west_t(ic, lag)
    ok = np.isfinite(ic)
    return {"days": n, "mean_ic": mean, "nw_t": t,
            "hit_share": float((ic[ok] > 0).mean()) if n else float("nan")}


def ic_decay(factor, fwd, elig=None, *, horizons=(1, 3, 7, 14, 30), min_obs=5, lag=10):
    """IC of the factor against the cumulative forward log return over each horizon.

    fwd is the daily forward log-return panel; the h-day target sums h consecutive rows, so it
    needs h-1 rows beyond the factor's last day (the tail is NaN, never padded)."""
    factor, fwd, elig = _check_panel(factor, fwd, elig)
    out = {}
    d, s = fwd.shape
    for h in horizons:
        if h < 1:
            raise ValueError("horizons must be positive")
        target = np.full_like(fwd, np.nan)
        if h == 1:
            target[:] = fwd
        elif h <= d:
            win = np.lib.stride_tricks.sliding_window_view(fwd, h, axis=0)  # [d-h+1, s, h]
            total = np.where(np.isnan(win).any(axis=2), np.nan, np.nansum(win, axis=2))
            target[:d - h + 1] = total
        ic, n = rank_ic(factor, target, elig, min_obs=min_obs)
        out[h] = ic_summary(ic, lag=lag)
    return out


def quantile_returns(factor, fwd, elig=None, *, q=5, min_obs=None):
    """Equal-weight forward returns of factor quantiles, ranked cross-sectionally each day.

    Returns (means [D, q], counts [D, q]); row d is NaN where fewer than q eligible observations
    exist (min_obs defaults to q). Quantile 0 is the lowest factor value, q-1 the highest.
    Symbols are assigned by average rank so ties never straddle a boundary silently."""
    factor, fwd, elig = _check_panel(factor, fwd, elig)
    if q < 2:
        raise ValueError("q must be at least 2")
    need = q if min_obs is None else min_obs
    d, s = factor.shape
    means = np.full((d, q), np.nan)
    counts = np.zeros((d, q), dtype=int)
    for i in range(d):
        ok = elig[i] & np.isfinite(factor[i]) & np.isfinite(fwd[i])
        n = int(ok.sum())
        if n < max(need, q):
            continue
        r = _stats.rankdata(factor[i][ok], method="ordinal") - 1
        bucket = (r * q) // n
        vals = fwd[i][ok]
        for k in range(q):
            sel = bucket == k
            counts[i, k] = int(sel.sum())
            if sel.any():
                means[i, k] = float(vals[sel].mean())
    return means, counts


def quantile_spread(means, *, lag=10):
    """NW t and mean of the daily top-minus-bottom quantile spread (bp/day left to the caller)."""
    means = np.asarray(means, dtype=float)
    spread = means[:, -1] - means[:, 0]
    n, mean, t = newey_west_t(spread, lag)
    return {"days": n, "mean_spread": mean, "nw_t": t}


def book_weights(factor, elig=None, *, q=5, mode="ls", min_obs=None):
    """Dollar-neutral top/bottom quantile book weights, or an equal-weight long-only top book.

    mode 'ls': long the top quantile, short the bottom, each leg gross 1 (net 0).
    mode 'long': equal weight over the top quantile, gross 1.
    Weights are [D, S]; a day with too few eligible names is all zero (no position)."""
    factor, _, elig = _check_panel(factor, np.zeros_like(factor), elig)
    if mode not in ("ls", "long"):
        raise ValueError("mode must be 'ls' or 'long'")
    if q < 2:
        raise ValueError("q must be at least 2")
    need = q if min_obs is None else min_obs
    d, s = factor.shape
    w = np.zeros((d, s))
    for i in range(d):
        ok = elig[i] & np.isfinite(factor[i])
        n = int(ok.sum())
        if n < max(need, q):
            continue
        idx = np.flatnonzero(ok)
        r = _stats.rankdata(factor[i][ok], method="ordinal") - 1
        bucket = (r * q) // n
        top = idx[bucket == q - 1]
        w[i, top] = 1.0 / len(top)
        if mode == "ls":
            bot = idx[bucket == 0]
            w[i, bot] = -1.0 / len(bot)
    return w


def turnover(weights):
    """Daily one-way turnover sum |w_d - w_{d-1}| / 2, in units of total gross.

    The first day trades from cash (w = 0). A dollar-neutral book (long 1, short 1, gross 2)
    entering or fully replacing both legs has one-way turnover 1; holding has 0."""
    w = np.asarray(weights, dtype=float)
    if w.ndim != 2:
        raise ValueError("weights must be [days, symbols]")
    prev = np.vstack([np.zeros((1, w.shape[1])), w[:-1]])
    return 0.5 * np.abs(w - prev).sum(axis=1)


def apply_costs(gross, weights, cost_per_side):
    """Net daily returns charging every traded unit: net = gross - turnover * cost_per_side.

    cost_per_side is a fraction of notional (fee + half-spread + impact). Turnover already sums
    both legs' traded notional, so a fully replaced dollar-neutral book (turnover 2 per unit of
    long-leg gross) pays 2 * cost_per_side."""
    gross = np.asarray(gross, dtype=float)
    to = turnover(weights)
    if gross.shape != to.shape:
        raise ValueError("gross must be one value per day of weights")
    if cost_per_side < 0:
        raise ValueError("cost_per_side must be nonnegative")
    return gross - to * cost_per_side


def gross_book(weights, fwd):
    """Daily book return sum_s w[d, s] * fwd[d, s]; NaN forward returns contribute zero weight
    only when the weight is zero, otherwise the day is NaN (a held name without a price)."""
    w = np.asarray(weights, dtype=float)
    f = np.asarray(fwd, dtype=float)
    if w.shape != f.shape:
        raise ValueError("weights and fwd must have the same shape")
    bad = (w != 0) & ~np.isfinite(f)
    out = np.where(w != 0, w * np.nan_to_num(f), 0.0).sum(axis=1)
    out[bad.any(axis=1)] = np.nan
    return out


def factor_report(factor, fwd, elig=None, *, q=5, horizons=(1, 3, 7, 14, 30),
                  cost_per_side=0.0, cost_mult=(1, 2, 3), lag=10, min_obs=5):
    """One JSON-ready dict describing a factor: IC, decay, quantiles, and the ls book at costs.

    The book holds one day (weights are recomputed daily); callers with longer holds should
    resample the factor themselves. No gate is applied here."""
    factor, fwd, elig = _check_panel(factor, fwd, elig)
    ic, n = rank_ic(factor, fwd, elig, min_obs=min_obs)
    means, counts = quantile_returns(factor, fwd, elig, q=q)
    w = book_weights(factor, elig, q=q, mode="ls")
    gross = gross_book(w, fwd)
    to = turnover(w)
    nets = {}
    for m in cost_mult:
        net = apply_costs(gross, w, cost_per_side * m)
        nn, mean, t = newey_west_t(net, lag)
        nets[str(m)] = {"days": nn, "mean_bp_day": mean * 1e4, "nw_t": t}
    return {
        "ic": ic_summary(ic, lag=lag),
        "ic_decay": ic_decay(factor, fwd, elig, horizons=horizons, min_obs=min_obs, lag=lag),
        "quantiles": {"mean_bp_day": (np.nanmean(means, axis=0) * 1e4).tolist(),
                      "spread": quantile_spread(means, lag=lag)},
        "book": {"gross_bp_day": float(np.nanmean(gross)) * 1e4,
                 "mean_one_way_turnover": float(np.nanmean(to)),
                 "net": nets},
        "coverage": {"days_with_ic": int(np.isfinite(ic).sum()),
                     "mean_eligible": float(elig.sum(axis=1).mean()),
                     "mean_scored": float(n[n > 0].mean()) if (n > 0).any() else 0.0},
    }
