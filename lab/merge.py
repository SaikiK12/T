"""Merge lab: combine many signals into one forecast per (hour, symbol), re-learned walk-forward, and trade it only where
the forecast clears the cost of trading.

Each month, on the trailing training window only: every cell (view, bin) gets its mean forward return over horizon h
and a Newey-West t (the atlas statistics). The N strongest cells (by |t|, same sign in both halves of the window) form
the forecast f(t, s) = beta_N * sum of the cell means whose condition holds at (t, s); beta_N is the least-squares
scale of that sum against realized returns in the training window, which corrects for counting the same information
twice when correlated cells fire together. The forecast for the following month uses those cells and beta only.

Trading: a symbol enters long when f > k_in x its round-trip cost and short when f < -k_in x cost, exits when the
forecast in its direction falls to k_out x cost or below (after a minimum hold). "ls" mode weights longs and shorts as two
halves of the book, "dir" mode uses one pool. Costs are charged on every weight change.
"""
import numpy as np
from numba import njit, prange

from . import atlas


# ---- cell statistics on a training window -------------------------------------------------------------------------

def cell_stats(tens, F, X, cmat, index, t0, t1, horizons, min_support=0.01, min_days=150):
    """The usable cells of a training window for every (horizon, measure): {(h, measure): [table per tensor]} where a
    table is a dict of arrays (tensor, view, bin, mean, t). F, X are [len(horizons), t1 - t0, S]. Usable = support
    >= min_support of the view's cells, >= min_days days with data, the same sign in both halves of the window, and
    (excess) not a time-only view."""
    out = {}
    S = F.shape[2]
    group = np.zeros((cmat.shape[0], S), np.int8)
    for tname, (bins, names, time_only) in tens.items():
        views = np.arange(bins.shape[0], dtype=np.int64)
        acc = atlas.run(bins, views, F, X, cmat, index, group, 1, t0, t1)
        vi = np.repeat(np.arange(len(views)), acc["nb"])
        bi = np.concatenate([np.arange(n) for n in acc["nb"]])
        n_view = np.bincount(vi, weights=acc["cs"][:, 1])[vi]
        base = acc["cs"][:, 1] / np.maximum(n_view, 1) >= min_support
        for hi, h in enumerate(horizons):
            c = acc["cnt"][:, hi, 0].astype(np.float64)
            for measure, key in (("raw", "sf"), ("excess", "sx")):
                Y = np.where(c > 0, acc[key][:, hi, 0] / np.maximum(c, 1), np.nan)
                D = Y.shape[1]
                m, t, nd = atlas.nw_skip(Y, atlas.lag_for(h), np.array([0, D], np.int64))
                mh, _, _ = atlas.nw_skip(Y, atlas.lag_for(h), np.array([0, D // 2, D], np.int64))
                ok = base & (nd[:, 0] >= min_days) & np.isfinite(t[:, 0]) & (np.sign(mh[:, 0]) == np.sign(mh[:, 1]))
                if measure == "excess":
                    ok &= ~np.asarray(time_only, bool)[vi]
                out.setdefault((h, measure), []).append(
                    {"tensor": tname, "view": views[vi][ok], "bin": bi[ok], "mean": m[ok, 0], "t": t[ok, 0]})
    return out


def select(tables, n_max, t_min=2.0):
    """Top cells by |t| across tensors: list of (tensor, view, bin, mean, t), strongest first."""
    rows = [(d["tensor"], int(v), int(b), float(m), float(t)) for d in tables
            for v, b, m, t in zip(d["view"], d["bin"], d["mean"], d["t"]) if abs(t) >= t_min]
    rows.sort(key=lambda r: -abs(r[4]))
    return rows[:n_max]


# ---- forecasts ----------------------------------------------------------------------------------------------------

@njit(parallel=True, cache=True)
def _forecast(bins, cv, cb, cg, first, grow, eidx, ecnt, t0, t1, out):
    """out[n, t - t0, s] += cg[k, grow[t]] for every cell k with first[k] <= n whose bin matches at (t, s)."""
    nN = out.shape[0]
    for t in prange(t0, t1):
        g = grow[t]
        for j in range(ecnt[t]):
            s = eidx[t, j]
            for k in range(len(cv)):
                if bins[cv[k], t, s] == cb[k]:
                    for n in range(first[k], nN):
                        out[n, t - t0, s] += cg[k, g]


def forecast(tens, cells, grid, index, t0, t1, S, grow=None):
    """Raw (unscaled) forecasts for each N in grid (cells are strongest first; N uses the first N). A cell's mean is a
    number, or an array of per-group means picked by grow[t] (the group of each row) when grow is given."""
    out = np.zeros((len(grid), t1 - t0, S), np.float32)
    eidx, ecnt = index
    if grow is None:
        grow = np.zeros(t1, np.int8)
    first_all = np.searchsorted(np.asarray(grid), np.arange(len(cells)), side="right")
    for tname, (bins, _, _) in tens.items():
        k = [i for i, c in enumerate(cells) if c[0] == tname]
        if not k:
            continue
        cv = np.array([cells[i][1] for i in k], np.int64)
        cb = np.array([cells[i][2] for i in k], np.int8)
        cg = np.array([np.atleast_1d(cells[i][3]) for i in k], np.float32)
        _forecast(bins, cv, cb, cg, first_all[k].astype(np.int64), np.asarray(grow, np.int8), eidx, ecnt, t0, t1, out)
    return out


def calibrate(f, y, elig):
    """Least-squares slope through the origin of y on each forecast, over eligible cells with both finite."""
    beta = np.zeros(f.shape[0])
    ok = elig & np.isfinite(y)
    yy = np.where(ok, y, 0.0)
    for n in range(f.shape[0]):
        x = np.where(ok, f[n], 0.0)
        d = float((x.astype(np.float64) ** 2).sum())
        beta[n] = float((x.astype(np.float64) * yy).sum()) / d if d > 0 else 0.0
    return beta


# ---- trading ------------------------------------------------------------------------------------------------------

@njit(cache=True)
def _trade(f, ret, elig, eidx, ecnt, cmat, k_in, k_out, slots, min_hold, t0, t1, cmult, ls, out):
    """f is indexed from row t0. out[t] = (net, cost, gross, n_long, n_short, turnover)."""
    T, S = ret.shape
    pos = np.zeros(S, np.int8)
    age = np.zeros(S, np.int32)
    wprev = np.zeros(S)
    held = np.empty(S, np.int32)
    fresh = np.empty(S, np.int32)
    stamp = np.full(S, -1, np.int64)
    nheld = 0
    for t in range(t0, t1):
        tt = t - t0
        for i in range(nheld):
            s = held[i]
            if not elig[t, s]:
                pos[s] = 0
        nn = 0
        nl = 0
        ns = 0
        for j in range(ecnt[t]):
            s = eidx[t, j]
            x = f[tt, s]
            if np.isnan(x):
                x = 0.0
            c = 2.0 * cmat[t, s]
            p = pos[s]
            if p != 0:
                age[s] += 1
                if p * x <= k_out * c and age[s] >= min_hold:
                    p = 0
            if p == 0:
                if x > k_in * c:
                    p = 1
                    age[s] = 0
                elif x < -k_in * c:
                    p = -1
                    age[s] = 0
            pos[s] = p
            if p != 0:
                fresh[nn] = s
                nn += 1
                if p > 0:
                    nl += 1
                else:
                    ns += 1
        r = 0.0
        tc = 0.0
        to = 0.0
        for i in range(nn):
            s = fresh[i]
            if ls:
                w = 0.5 / max(nl, slots // 2) if pos[s] > 0 else -0.5 / max(ns, slots // 2)
            else:
                w = pos[s] / max(nn, slots)
            x = ret[t, s]
            if not np.isnan(x):
                r += w * x
            d = abs(w - wprev[s])
            tc += d * cmat[t, s] * cmult
            to += d
            wprev[s] = w
            stamp[s] = t
        for i in range(nheld):
            s = held[i]
            if stamp[s] != t and wprev[s] != 0.0:
                tc += abs(wprev[s]) * cmat[t, s] * cmult
                to += abs(wprev[s])
                wprev[s] = 0.0
        for i in range(nn):
            held[i] = fresh[i]
        nheld = nn
        out[tt, 0] = r - tc
        out[tt, 1] = tc
        out[tt, 2] = r
        out[tt, 3] = nl
        out[tt, 4] = ns
        out[tt, 5] = to


def trade(f, ret, elig, index, cmat, t0, t1, k_in=1.0, k_out=0.0, slots=10, min_hold=4, cmult=1.0, ls=True):
    """Hourly (net, cost, gross, n_long, n_short, turnover) for forecast f covering rows [t0, t1)."""
    out = np.zeros((t1 - t0, 6))
    eidx, ecnt = index
    _trade(np.asarray(f, np.float32), ret, elig, eidx, ecnt, cmat, k_in, k_out, slots, min_hold, t0, t1, cmult, ls, out)
    return out


# ---- walk-forward -------------------------------------------------------------------------------------------------

def walk_forward(tens, ret, elig, cmat, index, refits, train_days, embargo_h, horizons, grid, t_min=2.0, log=None,
                 min_days=None):
    """Re-learn the cells at each refit row and forecast until the next one.

    refits: increasing row indices; the last one is the end of the test span. Training for refit r uses rows
    [r - embargo_h - 24 * train_days, r - embargo_h), with forward returns cut at that window's end, so nothing after
    the embargo reaches the model. Returns ({(h, measure): forecasts [len(grid), rows, S]} covering
    [refits[0], refits[-1]), {(h, measure): list of selected cells per refit}). A cell needs data on min_days days
    of the window (default 60% of it)."""
    min_days = int(0.6 * train_days) if min_days is None else min_days
    S = ret.shape[1]
    r0, r_end = refits[0], refits[-1]
    keys = [(h, m) for h in horizons for m in ("excess", "raw")]
    fc = {k: np.zeros((len(grid), r_end - r0, S), np.float32) for k in keys}
    picks = {k: [] for k in keys}
    for r, r_next in zip(refits[:-1], refits[1:]):
        b = r - embargo_h
        a = max(0, b - 24 * train_days)
        F, X = atlas.forward(ret, elig, a, b, horizons)
        tables = cell_stats(tens, F, X, cmat, index, a, b, horizons, min_days=min_days)
        for k in keys:
            hi = horizons.index(k[0])
            cells = select(tables[k], max(grid), t_min)
            picks[k].append(cells)
            if not cells:
                continue
            y = (X if k[1] == "excess" else F)[hi]
            beta = calibrate(forecast(tens, cells, grid, index, a, b, S), y, np.asarray(elig[a:b]))
            f = forecast(tens, cells, grid, index, r, r_next, S)
            fc[k][:, r - r0:r_next - r0] = f * beta[:, None, None].astype(np.float32)
        if log:
            log(f"  refit at row {r}: train rows {a}-{b}, cells per key {[len(picks[k][-1]) for k in keys]}")
    return fc, picks


# ---- merge_v2: trade-consistent and session-aware -----------------------------------------------------------------

def cell_stats_episodes(tens, F, X, cmat, index, elig, group, n_groups, t0, t1, horizons, lam=50.0, min_episodes=30):
    """Trade-consistent statistics of a training window: each cell counts once per episode (the hour a symbol enters
    the bin), its score is the Newey-West t of the DAILY SUM of episode returns (a fixed stake per trade), its mean is
    per episode. With n_groups > 1 the cell also gets per-group means shrunk toward its pooled mean,
    (n_g m_g + lam m) / (n_g + lam). Returns {(h, measure): [table per tensor]}; a table holds tensor, view, bin,
    mean ([G] per-group means when grouped, else the pooled mean), pooled, t, episodes."""
    out = {}
    for tname, (bins, names, time_only) in tens.items():
        views = np.arange(bins.shape[0], dtype=np.int64)
        acc = atlas.run(bins, views, F, X, cmat, index, group, n_groups, t0, t1, elig=elig, episodes=True)
        vi = np.repeat(np.arange(len(views)), acc["nb"])
        bi = np.concatenate([np.arange(n) for n in acc["nb"]])
        D = acc["sf"].shape[3]
        for hi, h in enumerate(horizons):
            Cg = acc["cnt"][:, hi].astype(np.float64)                  # [NF, G, D]
            C = Cg.sum(axis=(1, 2))
            half = D // 2
            for measure, key in (("raw", "sf"), ("excess", "sx")):
                Sg = acc[key][:, hi].astype(np.float64)
                Yd = Sg.sum(axis=1)                                     # daily sum of episode returns
                _, t, _ = atlas.nw_skip(Yd, atlas.lag_for(h), np.array([0, D], np.int64))
                m = Yd.sum(axis=1) / np.maximum(C, 1)
                m1 = Yd[:, :half].sum(axis=1) / np.maximum(Cg[:, :, :half].sum(axis=(1, 2)), 1)
                m2 = Yd[:, half:].sum(axis=1) / np.maximum(Cg[:, :, half:].sum(axis=(1, 2)), 1)
                ok = (C >= min_episodes) & np.isfinite(t[:, 0]) & (np.sign(m1) == np.sign(m2)) & (m != 0)
                if measure == "excess":
                    ok &= ~np.asarray(time_only, bool)[vi]
                if n_groups > 1:
                    ng = Cg.sum(axis=2)
                    mg = Sg.sum(axis=2) / np.maximum(ng, 1)
                    means = (ng * mg + lam * m[:, None]) / (ng + lam)
                else:
                    means = m[:, None]
                out.setdefault((h, measure), []).append(
                    {"tensor": tname, "view": views[vi][ok], "bin": bi[ok], "mean": means[ok], "pooled": m[ok],
                     "t": t[ok, 0], "episodes": C[ok]})
    return out


def select_v2(tables, n_max, t_min=2.0):
    """Top cells by |t| across tensors: (tensor, view, bin, means, t, pooled mean), strongest first."""
    rows = [(d["tensor"], int(v), int(b), np.asarray(mm, np.float64), float(t), float(pm)) for d in tables
            for v, b, mm, t, pm in zip(d["view"], d["bin"], d["mean"], d["t"], d["pooled"]) if abs(t) >= t_min]
    rows.sort(key=lambda r: -abs(r[4]))
    return rows[:n_max]


def walk_forward_v2(tens, ret, elig, cmat, index, refits, train_days, embargo_h, horizons, grid, session=None,
                    n_groups=1, lam=50.0, t_min=2.0, min_episodes=30, log=None):
    """As walk_forward, with trade-consistent cell statistics and, when `session` ([T] int8 group of each row) is
    given, session-specific cell means in both the forecast and its calibration."""
    S = ret.shape[1]
    r0, r_end = refits[0], refits[-1]
    keys = [(h, m) for h in horizons for m in ("excess", "raw")]
    fc = {k: np.zeros((len(grid), r_end - r0, S), np.float32) for k in keys}
    picks = {k: [] for k in keys}
    grouped = session is not None and n_groups > 1
    grow = np.asarray(session, np.int8) if grouped else None
    group = (np.ascontiguousarray(np.broadcast_to(grow[:, None], ret.shape)) if grouped
             else np.zeros(ret.shape, np.int8))
    for r, r_next in zip(refits[:-1], refits[1:]):
        b = r - embargo_h
        a = max(0, b - 24 * train_days)
        F, X = atlas.forward(ret, elig, a, b, horizons)
        tables = cell_stats_episodes(tens, F, X, cmat, index, elig, group, n_groups if grouped else 1, a, b, horizons,
                                     lam, min_episodes)
        for k in keys:
            hi = horizons.index(k[0])
            cells = select_v2(tables[k], max(grid), t_min)
            picks[k].append(cells)
            if not cells:
                continue
            y = (X if k[1] == "excess" else F)[hi]
            beta = calibrate(forecast(tens, cells, grid, index, a, b, S, grow), y, np.asarray(elig[a:b]))
            f = forecast(tens, cells, grid, index, r, r_next, S, grow)
            fc[k][:, r - r0:r_next - r0] = f * beta[:, None, None].astype(np.float32)
        if log:
            log(f"  refit at row {r}: train rows {a}-{b}, cells per key {[len(picks[k][-1]) for k in keys]}")
    return fc, picks
