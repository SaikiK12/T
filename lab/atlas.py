"""Edge atlas: what each feature bin says about future returns BEFORE fees, at several horizons, split by a grouping
(market session, liquidity tier, BTC regime), with a placebo to say how much of it chance alone produces.

For a cell (view v, bin b, horizon h, group g) and day d, the atlas averages over eligible (hour, symbol) cells in that
bin the forward h-hour return, raw (F, includes market timing) and in excess of the equal-weighted eligible universe at
that hour (X, pure selection). A daily series per cell gives a mean and a Newey-West t (lag ceil(h/24) + 2), one per
calendar half-year too. Views that put every symbol in the same bin at a given hour (calendar, BTC state) carry
information only through F, never X.

The edge is gross: what a trade would earn with no fees. `cost_rt` is the round-trip cost (2 x the one-way tier cost of
the cells in the bin) so edge / cost says how far a signal is from paying for itself.
"""
import warnings

import numpy as np
import pandas as pd
from numba import njit, prange

from . import sessions

HORIZONS = (1, 4, 12, 24, 72)


# ---- forward returns ----------------------------------------------------------------------------------------------

def forward(ret, elig, t0, t1, horizons=HORIZONS):
    """F[h, t - t0, s]: sum of next-bar returns over h bars from row t (NaN when the window passes t1 or the symbol has
    any nonfinite return in that window); X: F minus the mean of F over eligible symbols at t. Both float32.

    Bounds refer to return rows: ret[t1 - 1] still depends on the price at row t1. Callers must protect price splits.
    """
    T = t1 - t0
    r = np.asarray(ret[t0:t1], np.float64)
    valid = np.isfinite(r)
    c = np.zeros((T + 1, r.shape[1]))
    c[1:] = np.cumsum(np.where(valid, r, 0.0), axis=0)
    missing = np.zeros((T + 1, r.shape[1]), np.int64)
    missing[1:] = np.cumsum(~valid, axis=0)
    F = np.full((len(horizons), T, r.shape[1]), np.nan, np.float32)
    X = np.full_like(F, np.nan)
    e = np.asarray(elig[t0:t1])
    for i, h in enumerate(horizons):
        if h <= 0:
            raise ValueError("forward horizons must be positive")
        f = np.full((T, r.shape[1]), np.nan)
        if h <= T:
            n = T - h + 1
            complete = missing[h:] == missing[:n]
            f[:n] = np.where(complete, c[h:] - c[:n], np.nan)
        m = np.where(e & np.isfinite(f), f, np.nan)
        with np.errstate(invalid="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mu = np.nanmean(m, axis=1, keepdims=True)
        F[i] = f
        X[i] = f - mu
    return F, X


# ---- the pass -----------------------------------------------------------------------------------------------------

@njit(parallel=True, cache=True)
def max_bins(bins, views, eidx, ecnt, t0, t1):
    out = np.full(len(views), -1, np.int64)
    for i in prange(len(views)):
        v = views[i]
        m = -1
        for t in range(t0, t1):
            for j in range(ecnt[t]):
                b = bins[v, t, eidx[t, j]]
                if b > m:
                    m = b
        out[i] = m
    return out


@njit(parallel=True, cache=True)
def _pass(bins, views, off, F, X, cmat, eidx, ecnt, group, t0, t1, sf, sx, cnt, pf, px, pc, cs, elig, ep):
    """ep: count a cell only at an episode start, the hour a symbol enters the bin (it was in another bin or not
    tradable the hour before), so a condition that persists counts once, as one trade would."""
    H = F.shape[0]
    for i in prange(len(views)):
        v = views[i]
        for t in range(t0, t1):
            d = (t - t0) // 24
            tt = t - t0
            for j in range(ecnt[t]):
                s = eidx[t, j]
                b = bins[v, t, s]
                if b < 0:
                    continue
                if ep and t > 0 and elig[t - 1, s] and bins[v, t - 1, s] == b:
                    continue
                f = off[i] + b
                g = group[t, s]
                if g < 0:
                    continue
                cs[f, 0] += cmat[t, s]
                cs[f, 1] += 1.0
                for h in range(H):
                    x = X[h, tt, s]
                    if np.isnan(x):
                        continue
                    y = F[h, tt, s]
                    sf[f, h, g, d] += y
                    sx[f, h, g, d] += x
                    cnt[f, h, g, d] += 1
                    pf[f, h, s] += y
                    px[f, h, s] += x
                    pc[f, h, s] += 1


@njit(parallel=True, cache=True)
def _time_only(bins, views, eidx, ecnt, t0, t1, step):
    """1 when, on every sampled hour, all eligible symbols share one bin (the view is a function of time only)."""
    out = np.ones(len(views), np.int8)
    for i in prange(len(views)):
        v = views[i]
        for t in range(t0, t1, step):
            first = -2
            for j in range(ecnt[t]):
                b = bins[v, t, eidx[t, j]]
                if first == -2:
                    first = b
                elif b != first:
                    out[i] = 0
                    break
            if out[i] == 0:
                break
    return out


def run(bins, views, F, X, cmat, index, group, n_groups, t0, t1, nb=None, elig=None, episodes=False):
    """One pass over the given views. Returns the raw accumulators as a dict (see `stats`). With episodes=True (needs
    elig) only episode starts count."""
    eidx, ecnt = index
    views = np.asarray(views, np.int64)
    if nb is None:
        nb = max_bins(bins, views, eidx, ecnt, t0, t1) + 1
    off = np.concatenate([[0], np.cumsum(nb)[:-1]]).astype(np.int64)
    NF, H, D, S = int(nb.sum()), F.shape[0], (t1 - t0) // 24, F.shape[2]
    acc = {"sf": np.zeros((NF, H, n_groups, D), np.float32), "sx": np.zeros((NF, H, n_groups, D), np.float32),
           "cnt": np.zeros((NF, H, n_groups, D), np.int32), "pf": np.zeros((NF, H, S), np.float64),
           "px": np.zeros((NF, H, S), np.float64), "pc": np.zeros((NF, H, S), np.int32),
           "cs": np.zeros((NF, 2), np.float64)}
    if elig is None:
        assert not episodes, "episodes need the eligibility mask"
        elig = np.zeros((1, 1), bool)
    _pass(bins, views, off, F, X, cmat, eidx, ecnt, group, t0, t1, acc["sf"], acc["sx"], acc["cnt"], acc["pf"],
          acc["px"], acc["pc"], acc["cs"], elig, episodes)
    acc.update(views=views, nb=nb, off=off)
    return acc


# ---- statistics ---------------------------------------------------------------------------------------------------

@njit(parallel=True, cache=True)
def nw_skip(Y, lag, edges):
    """Mean and Newey-West t of each row of Y over the days in each [edges[e], edges[e+1]) span, skipping NaN days
    (the kept days are treated as consecutive). Returns mean [N, E], t [N, E], days [N, E]."""
    N = Y.shape[0]
    E = len(edges) - 1
    mean = np.full((N, E), np.nan)
    tst = np.full((N, E), np.nan)
    nd = np.zeros((N, E), np.int64)
    for r in prange(N):
        buf = np.empty(Y.shape[1])
        for e in range(E):
            n = 0
            for i in range(edges[e], edges[e + 1]):
                if not np.isnan(Y[r, i]):
                    buf[n] = Y[r, i]
                    n += 1
            nd[r, e] = n
            if n < 10:
                continue
            mu = buf[:n].mean()
            s = 0.0
            for i in range(n):
                s += (buf[i] - mu) ** 2
            for l in range(1, lag + 1):
                g = 0.0
                for i in range(l, n):
                    g += (buf[i] - mu) * (buf[i - l] - mu)
                s += 2.0 * (1.0 - l / (lag + 1.0)) * g
            mean[r, e] = mu
            if s > 1e-30:
                tst[r, e] = mu / (np.sqrt(s) / n)
    return mean, tst, nd


def lag_for(h):
    return int(np.ceil(h / 24)) + 2


def stats(acc, names, horizons, eras, group_names, time_only=None, min_symbol_cells=100):
    """Tidy table: one row per (view, bin, horizon, group incl. 'all', measure in {raw, excess}).
    `eras` are day offsets of era starts plus the end (as search.half_year_edges returns)."""
    nb, views = acc["nb"], acc["views"]
    NF, H, G, D = acc["sf"].shape
    vi = np.repeat(np.arange(len(views)), nb)
    bi = np.concatenate([np.arange(n) for n in nb])
    eras = np.asarray(eras, np.int64)
    whole = np.array([0, D], np.int64)
    n_view = np.bincount(vi, weights=acc["cs"][:, 1])[vi]
    cost_rt = 2e4 * acc["cs"][:, 0] / np.maximum(acc["cs"][:, 1], 1)
    out = []
    for gi, gname in enumerate(list(group_names) + ["all"]):
        if gname == "all":
            sf, sx, cnt = acc["sf"].sum(axis=2), acc["sx"].sum(axis=2), acc["cnt"].sum(axis=2)
        else:
            sf, sx, cnt = acc["sf"][:, :, gi], acc["sx"][:, :, gi], acc["cnt"][:, :, gi]
        for hi, h in enumerate(horizons):
            c = cnt[:, hi].astype(np.float64)
            for meas, s in (("raw", sf), ("excess", sx)):
                Y = np.where(c > 0, s[:, hi] / np.maximum(c, 1), np.nan)
                m_all, t_all, n_all = nw_skip(Y, lag_for(h), whole)
                m_era, t_era, _ = nw_skip(Y, lag_for(h), eras)
                sign = np.sign(m_all[:, 0])
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    worst = np.nanmin(t_era * sign[:, None], axis=1)
                row = {"view": views[vi], "name": np.asarray(names)[views[vi]], "bin": bi, "h": h, "group": gname,
                       "measure": meas, "mean_bp": m_all[:, 0] * 1e4, "t": t_all[:, 0], "days": n_all[:, 0],
                       "eras_same_sign": np.sum(np.sign(m_era) == sign[:, None], axis=1),
                       "eras": np.sum(np.isfinite(m_era), axis=1), "worst_era_t": worst,
                       "cells": c.sum(axis=1), "support": acc["cs"][:, 1] / np.maximum(n_view, 1), "cost_rt_bp": cost_rt}
                if gname == "all":
                    p = acc["pf" if meas == "raw" else "px"][:, hi]
                    pc = acc["pc"][:, hi]
                    ok = pc >= min_symbol_cells
                    with np.errstate(invalid="ignore", divide="ignore"):
                        sym = p / pc
                    n_ok = ok.sum(axis=1)
                    row["symbols"] = n_ok
                    row["breadth"] = np.where(n_ok > 0, np.sum((np.sign(sym) == sign[:, None]) & ok, axis=1) / np.maximum(n_ok, 1), np.nan)
                out.append(pd.DataFrame(row))
    df = pd.concat(out, ignore_index=True)
    if time_only is not None:
        df["time_only"] = pd.Series(np.asarray(time_only), index=views).reindex(df["view"]).values.astype(bool)
    df["edge_cost"] = df["mean_bp"].abs() / df["cost_rt_bp"]
    return df


def lift_stats(acc, names, horizons, eras, group_names, min_days=10):
    """Context lift: for a pass whose groups are the codes of a context view, compare each cell inside context code k
    with the same cell outside it, day by day. One row per (view, bin, horizon, code, measure):
      base_bp:  the cell's mean over all codes (its edge without the context)
      cond_bp, cond_t:  the cell's mean and NW t inside code k
      lift_bp, lift_t:  mean and NW t of the daily difference inside k minus outside k (days with both)
      lift_eras_same_sign, lift_eras: half-years where the lift has the sign of the whole-sample lift
      share: the fraction of the cell's observations that fall in code k; support: the cell's share of its view"""
    nb, views = acc["nb"], acc["views"]
    NF, H, G, D = acc["sf"].shape
    vi = np.repeat(np.arange(len(views)), nb)
    bi = np.concatenate([np.arange(n) for n in nb])
    eras = np.asarray(eras, np.int64)
    whole = np.array([0, D], np.int64)
    cost_rt = 2e4 * acc["cs"][:, 0] / np.maximum(acc["cs"][:, 1], 1)
    support = acc["cs"][:, 1] / np.maximum(np.bincount(vi, weights=acc["cs"][:, 1])[vi], 1)
    out = []
    for hi, h in enumerate(horizons):
        lag = lag_for(h)
        cnt = acc["cnt"][:, hi].astype(np.float64)        # [NF, G, D]
        C = cnt.sum(axis=1)
        for meas, key in (("raw", "sf"), ("excess", "sx")):
            s = acc[key][:, hi].astype(np.float64)
            S_ = s.sum(axis=1)
            base = np.where(C > 0, S_ / np.maximum(C, 1), np.nan)
            m_base = nw_skip(base, lag, whole)[0][:, 0]
            for gi, gname in enumerate(group_names):
                ck, sk = cnt[:, gi], s[:, gi]
                yin = np.where(ck > 0, sk / np.maximum(ck, 1), np.nan)
                co = C - ck
                yout = np.where(co > 0, (S_ - sk) / np.maximum(co, 1), np.nan)
                m_in, t_in, n_in = nw_skip(yin, lag, whole)
                dif = yin - yout
                m_l, t_l, n_l = nw_skip(dif, lag, whole)
                m_le, _, n_le = nw_skip(dif, lag, eras)
                sign = np.sign(m_l[:, 0])
                tot = C.sum(axis=1)
                out.append(pd.DataFrame({
                    "view": views[vi], "name": np.asarray(names)[views[vi]], "bin": bi, "h": h, "code": gi,
                    "context_code": gname, "measure": meas, "base_bp": m_base * 1e4,
                    "cond_bp": m_in[:, 0] * 1e4, "cond_t": t_in[:, 0], "cond_days": n_in[:, 0],
                    "lift_bp": m_l[:, 0] * 1e4, "lift_t": t_l[:, 0], "lift_days": n_l[:, 0],
                    "lift_eras_same_sign": np.sum(np.sign(m_le) == sign[:, None], axis=1),
                    "lift_eras": np.sum(np.isfinite(m_le), axis=1),
                    "share": ck.sum(axis=1) / np.maximum(tot, 1), "cells": ck.sum(axis=1), "support": support,
                    "cost_rt_bp": cost_rt}))
    df = pd.concat(out, ignore_index=True)
    df.loc[df.lift_days < min_days, ["lift_bp", "lift_t"]] = np.nan
    df["amplifies"] = np.sign(df.lift_bp) == np.sign(df.base_bp)
    df["cond_edge_cost"] = df.cond_bp.abs() / df.cost_rt_bp
    return df


def placebo_fdr(real_t, null_ts, grid=None):
    """Thresholds on |t|, the estimated FDR (mean placebo count at or above / real count) and the real count."""
    grid = np.arange(2.0, 10.01, 0.25) if grid is None else grid
    a = np.abs(real_t[np.isfinite(real_t)])
    real = np.array([(a >= g).sum() for g in grid])
    null = np.array([np.mean([(np.abs(n[np.isfinite(n)]) >= g).sum() for n in null_ts]) for g in grid])
    return grid, np.where(real > 0, np.minimum(null / np.maximum(real, 1), 1.0), np.nan), real, null


def threshold(real_t, null_ts, q, min_real=5):
    grid, fdr, real, _ = placebo_fdr(real_t, null_ts)
    ok = np.flatnonzero((fdr <= q) & (real >= min_real))
    return float(grid[ok.min()]) if len(ok) else np.inf


# ---- groupings ----------------------------------------------------------------------------------------------------

SESSION_NAMES = ("asia", "europe", "us_open", "us_afternoon", "us_evening", "weekend")


def session_groups(t):
    """[T] int8 session of each decision time: asia 00-07 UTC, europe 07 UTC to 08:00 New York, us_open decisions
    08:00-12:00 New York (the 08:30 data releases and the 09:30 open), us_afternoon 13:00-15:00, us_evening after that,
    weekend = Saturday and Sunday UTC. NYSE holidays on weekdays follow the same UTC hours with us_* as evening."""
    tau = sessions.decision_time(t)
    hour = (tau // sessions.HOUR) % 24
    dow = ((tau // sessions.HOUR) // 24 + 3) % 7
    us = sessions.us_clock(tau)
    g = np.select([dow >= 5, (us >= 3) & (us <= 7), (us >= 8) & (us <= 10), hour < 7, (us <= 2) & (hour >= 7)],
                  [5, 2, 3, 0, 1], 4)
    return g.astype(np.int8)


TIER_NAMES = ("top10", "rank11_25", "rank26_50")


def tier_groups(rank):
    return np.select([rank <= 10, rank <= 25, rank <= 50], [0, 1, 2], -1).astype(np.int8)


REGIME_NAMES = ("btc_up_calm", "btc_up_wild", "btc_down_calm", "btc_down_wild")


def regime_groups(btc_close, window=720, vol_window=24 * 365):
    """BTC trailing 30-day return sign x trailing 30-day realized vol above or below its trailing 1-year median. Causal."""
    c = pd.Series(np.asarray(btc_close, np.float64)).ffill()
    r = np.log(c).diff()
    up = (c / c.shift(window) - 1) > 0
    vol = r.rolling(window, min_periods=window // 2).std()
    wild = vol > vol.rolling(vol_window, min_periods=window).median()
    g = np.where(up, 0, 2) + np.where(wild, 1, 0)
    g = np.where(c.shift(window).isna() | vol.isna(), -1, g)
    return g.astype(np.int8)
