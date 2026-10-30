"""Staged beam search over conditions on feature bins, with a placebo to calibrate what counts as a find.

Stage 1 scores every single condition (feature x bin range x direction x minimum hold). Stage 2 ANDs the best
conditions into pairs and stage 3 into triples. A rule's score is its per-era Newey-West t after costs. Because
strategies work for a time, the library keeps rules that are strong in ANY era (peak t), not only in all of them;
whether that persists is what the policy test decides afterwards.
Every rule evaluated counts as a trial. A placebo (returns circularly shifted in time against the features) yields the
same score distribution under no relationship, so the keep-threshold is set from an estimated false discovery rate.
"""
import itertools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from numba import njit, prange

from . import research
from .engine import Rule

DAY = 24


# ---- scoring ------------------------------------------------------------------------------------------------------

@njit(parallel=True, cache=True)
def era_nw(d, edges, lag):
    """Per rule and era: mean daily return and Newey-West t. d: [R, D]; edges: era start days plus the end (len E + 1)."""
    R = d.shape[0]
    E = len(edges) - 1
    mean = np.zeros((R, E))
    tst = np.full((R, E), np.nan)
    for r in prange(R):
        for e in range(E):
            a, b = edges[e], edges[e + 1]
            n = b - a
            mu = 0.0
            for i in range(a, b):
                mu += d[r, i]
            mu /= n
            s = 0.0
            for i in range(a, b):
                s += (d[r, i] - mu) ** 2
            for l in range(1, lag + 1):
                g = 0.0
                for i in range(a + l, b):
                    g += (d[r, i] - mu) * (d[r, i - l] - mu)
                s += 2.0 * (1.0 - l / (lag + 1.0)) * g
            mean[r, e] = mu
            if s > 1e-24 * n:
                tst[r, e] = mu / (np.sqrt(s) / n)
    return mean, tst


def half_year_edges(p, row0, row1):
    """Day offsets (relative to row0) of calendar half-year starts inside [row0, row1), plus the end: era boundaries."""
    ts = pd.to_datetime(p.t[row0:row1:DAY], unit="ms", utc=True)
    key = np.asarray(ts.year * 2 + (ts.month > 6))
    starts = np.flatnonzero(np.diff(np.concatenate([[key[0] - 1], key])) != 0)
    return np.concatenate([starts, [len(ts)]]).astype(np.int64)


# ---- conditions and rules -----------------------------------------------------------------------------------------

def condition_catalog(bins, elig, t0, t1, min_support=0.005, max_support=0.40, views=None):
    """All edge-anchored ('<= j', '>= j') and single-bin conditions per view that fire on a sensible share of the
    eligible cells in [t0, t1). Returns arrays (view, lo, hi, support)."""
    out_v, out_lo, out_hi, out_sup = [], [], [], []
    mask = elig[t0:t1]
    total = float(mask.sum())
    for v in (range(bins.shape[0]) if views is None else views):
        x = np.asarray(bins[v, t0:t1])[mask]
        x = x[x >= 0]
        if x.size == 0:
            continue
        nb = int(x.max()) + 1
        c = np.bincount(x, minlength=nb) / total
        cands = {(0, j) for j in range(nb - 1)} | {(j, nb - 1) for j in range(1, nb)} | {(j, j) for j in range(1, nb - 1)}
        for lo, hi in sorted(cands):
            s = float(c[lo:hi + 1].sum())
            if min_support <= s <= max_support:
                out_v.append(v), out_lo.append(lo), out_hi.append(hi), out_sup.append(s)
    return np.array(out_v), np.array(out_lo), np.array(out_hi), np.array(out_sup)


def singles(cat, directions=(1, -1), holds=(4, 24, 72)):
    v, lo, hi, _ = cat
    return [Rule((int(v[i]),), (int(lo[i]),), (int(hi[i]),), 1, d, h)
            for i in range(len(v)) for d in directions for h in holds]


@dataclass
class Scored:
    rules: list
    ret: np.ndarray                 # [R, D] daily net returns
    cost: np.ndarray                # [R] mean daily cost
    active: np.ndarray              # [R] mean number of open positions
    mean: np.ndarray                # [R, E] per-era mean daily return
    t: np.ndarray                   # [R, E] per-era Newey-West t
    n_trials: int = 0

    @property
    def peak(self):
        return np.nanmax(np.where(np.isnan(self.t), -np.inf, self.t), axis=1)

    @property
    def pooled(self):
        return self.mean.mean(axis=1)


def score_rules(u, bins, rules, t0, t1, edges, lag=3, ret_override=None, cmult=1.0, batch=128, log=None):
    """Evaluate rules over [t0, t1) and score them per era. `ret_override` swaps in shifted returns for a placebo."""
    uu = u if ret_override is None else _with_ret(u, ret_override)
    D = (t1 - t0) // DAY
    ret = np.zeros((len(rules), D), np.float32)
    cost = np.zeros(len(rules), np.float32)
    act = np.zeros(len(rules), np.float32)
    for a in range(0, len(rules), batch * 8):
        chunk = rules[a:a + batch * 8]
        r, c, n = research.eval_rules(uu, bins, chunk, t0, t1, cmult=cmult, batch=batch)
        ret[a:a + len(chunk)], cost[a:a + len(chunk)], act[a:a + len(chunk)] = r, c.mean(axis=1), n.mean(axis=1)
        if log and (a // (batch * 8)) % 10 == 0:
            log(f"    scored {a + len(chunk)}/{len(rules)}")
    mean, t = era_nw(ret, edges.astype(np.int64), lag)
    return Scored(rules, ret, cost, act, mean, t, n_trials=len(rules))


def _with_ret(u, ret):
    from dataclasses import replace
    return replace(u, ret=ret)


def shifted_returns(u, shift, limit=None):
    """Placebo: returns moved `shift` hours in time against the features and eligibility, circularly inside rows
    [0, limit). Pass limit = the end of the discovery window so no later return (test, holdout) leaks into it."""
    limit = len(u.ret) if limit is None else limit
    out = np.full_like(u.ret, np.nan)
    out[:limit] = np.roll(u.ret[:limit], -shift, axis=0)
    return out


# ---- stage 2 and 3: conjunctions ----------------------------------------------------------------------------------

def top_conditions(sc, cat, n=250, per_view=6):
    """The n best distinct conditions (by peak era t over their direction/hold variants), at most per_view per feature."""
    v, lo, hi, _ = cat
    best = {}
    for i, r in enumerate(sc.rules):
        key = (r.view[0], r.lo[0], r.hi[0])
        if key not in best or sc.peak[i] > best[key][0]:
            best[key] = (sc.peak[i], r.direction, r.hold)
    order = sorted(best.items(), key=lambda kv: -kv[1][0])
    out, seen = [], {}
    for (vv, l, h), (pk, d, hold) in order:
        if seen.get(vv, 0) >= per_view:
            continue
        seen[vv] = seen.get(vv, 0) + 1
        out.append((vv, l, h))
        if len(out) == n:
            break
    return out


def pairs(conds, directions=(1, -1), holds=(24, 72)):
    rules = []
    for (a, b) in itertools.combinations(conds, 2):
        if a[0] == b[0]:
            continue
        for d in directions:
            for h in holds:
                rules.append(Rule((a[0], b[0]), (a[1], b[1]), (a[2], b[2]), 2, d, h))
    return rules


def triples(sc_pairs, conds, n_pairs=400):
    order = np.argsort(-sc_pairs.peak)[: n_pairs]
    rules, seen = [], set()
    for i in order:
        r = sc_pairs.rules[i]
        for c in conds:
            if c[0] in r.view:
                continue
            key = (tuple(sorted(zip(r.view + (c[0],), r.lo + (c[1],), r.hi + (c[2],)))), r.direction, r.hold)
            if key in seen:
                continue
            seen.add(key)
            rules.append(Rule(r.view + (c[0],), r.lo + (c[1],), r.hi + (c[2],), 3, r.direction, r.hold))
    return rules


# ---- calibration and library --------------------------------------------------------------------------------------

def empirical_fdr(real_peak, null_peaks, grid=None):
    """For each threshold: expected false discoveries (mean count of placebo rules at or above it) over the count of real
    rules at or above it. Returns (thresholds, estimated FDR, real counts)."""
    grid = np.arange(1.5, 8.01, 0.25) if grid is None else grid
    real = np.array([(real_peak >= g).sum() for g in grid])
    null = np.array([np.mean([(n >= g).sum() for n in null_peaks]) for g in grid])
    return grid, np.where(real > 0, np.minimum(null / np.maximum(real, 1), 1.0), np.nan), real


def dedupe(ret, order, rho=0.7, block=256, cap=2000):
    """Greedy diversity: walk rules in `order`, keep one unless its daily returns correlate above rho (in absolute
    value) with a rule already kept. Returns the kept row indices."""
    z = (ret - ret.mean(axis=1, keepdims=True)).astype(np.float32)
    z /= np.maximum(np.linalg.norm(z, axis=1, keepdims=True), 1e-12)
    kz = np.empty((cap, ret.shape[1]), np.float32)
    kept = []
    for a in range(0, len(order), block):
        idx = np.asarray(order[a:a + block])
        blk = z[idx]
        ok = np.ones(len(idx), bool)
        if kept:
            ok &= np.abs(blk @ kz[:len(kept)].T).max(axis=1) < rho
        fresh = []
        for j in np.flatnonzero(ok):
            if fresh and np.abs(blk[fresh] @ blk[j]).max() >= rho:
                continue
            fresh.append(j)
        for j in fresh:
            if len(kept) >= cap:
                return kept
            kz[len(kept)] = blk[j]
            kept.append(int(idx[j]))
    return kept
