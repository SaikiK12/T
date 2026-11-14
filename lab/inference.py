"""Honest statistics for a program that tries thousands of strategies.

Sharpe ratios here are per observation (not annualized) because the formulas below are stated in those units.
  - psr / dsr: Bailey & Lopez de Prado, probabilistic and deflated Sharpe ratio (selection bias, non-normality).
  - cscv_pbo: Bailey, Borwein, Lopez de Prado & Zhu, probability of backtest overfitting by combinatorial CV.
  - spa: Hansen's superior predictive ability test, with White's reality check as the p_upper variant.
  - model_confidence_set: Hansen, Lunde & Nason, T_max elimination.
  - lord_plus / OnlineFDR: Ramdas et al., online false discovery rate control across a stream of lanes.
  - bh: Benjamini-Hochberg within a batch.  eb_shrink: empirical-Bayes shrinkage against the winner's curse.
"""
import itertools
from dataclasses import dataclass, field

import numpy as np
from scipy import stats as sps

EULER = 0.5772156649015329


# ---- Sharpe ratio under selection ----------------------------------------------------------------------------------

def sharpe(x, axis=0):
    x = np.asarray(x, dtype=float)
    return x.mean(axis=axis) / x.std(axis=axis, ddof=1)


def psr(sr, sr_star, n_obs, skew=0.0, kurt=3.0):
    """P(true Sharpe > sr_star) given an estimated per-period Sharpe `sr` from n_obs returns (kurt is non-excess)."""
    denom = np.sqrt(1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2)
    return sps.norm.cdf((sr - sr_star) * np.sqrt(n_obs - 1.0) / denom)


def expected_max_sr(n_trials, var_sr, mean_sr=0.0):
    """Expected best Sharpe among n_trials independent strategies with no skill, whose Sharpes have variance var_sr."""
    if n_trials < 2:
        return mean_sr
    z = (1.0 - EULER) * sps.norm.ppf(1.0 - 1.0 / n_trials) + EULER * sps.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return mean_sr + np.sqrt(var_sr) * z


def dsr(returns, sr_trials, n_trials=None):
    """Deflated Sharpe ratio of one selected strategy. `returns` are its per-period returns; `sr_trials` are the
    per-period Sharpes of every strategy tried (their variance sets the spread); n_trials defaults to len(sr_trials)
    and should be the count of INDEPENDENT trials, or all trials to be conservative."""
    r = np.asarray(returns, dtype=float)
    sr_trials = np.asarray(sr_trials, dtype=float)
    n = len(sr_trials) if n_trials is None else n_trials
    sr0 = expected_max_sr(n, sr_trials.var(ddof=1), sr_trials.mean())
    return float(psr(sharpe(r), sr0, len(r), sps.skew(r), sps.kurtosis(r, fisher=False)))


# ---- probability of backtest overfitting ---------------------------------------------------------------------------

def cscv_pbo(returns, n_blocks=16, max_combos=None, rng=None, chunk=512):
    """returns: [T, N] per-period returns of N candidate strategies. Splits time into n_blocks, and for every way of
    choosing half the blocks as in-sample picks the in-sample best strategy and ranks it out of sample.
    Returns dict(pbo, logits): pbo is the share of splits where the in-sample winner lands at or below the OOS median."""
    R = np.asarray(returns, dtype=float)
    T, N = R.shape
    L = T // n_blocks
    R = R[: L * n_blocks].reshape(n_blocks, L, N)
    s1, s2 = R.sum(axis=1), (R ** 2).sum(axis=1)                       # [S, N]
    combos = np.array(list(itertools.combinations(range(n_blocks), n_blocks // 2)))
    if max_combos and len(combos) > max_combos:
        rng = rng or np.random.default_rng(0)
        combos = combos[rng.choice(len(combos), max_combos, replace=False)]
    logits = []
    for a in range(0, len(combos), chunk):
        c = combos[a: a + chunk]
        mask = np.zeros((len(c), n_blocks))
        np.put_along_axis(mask, c, 1.0, axis=1)

        def sr_of(m):
            n_obs = m.sum(axis=1, keepdims=True) * L
            mean = (m @ s1) / n_obs
            var = (m @ s2) / n_obs - mean ** 2
            return mean / np.sqrt(np.maximum(var, 1e-30))

        is_sr, oos_sr = sr_of(mask), sr_of(1.0 - mask)
        best = is_sr.argmax(axis=1)
        pick = oos_sr[np.arange(len(c)), best]
        rank = (oos_sr < pick[:, None]).sum(axis=1) + 1                # 1 = worst .. N = best
        w = rank / (N + 1.0)
        logits.append(np.log(w / (1.0 - w)))
    logits = np.concatenate(logits)
    return {"pbo": float((logits <= 0).mean()), "logits": logits}


# ---- bootstrap machinery, SPA and the model confidence set ---------------------------------------------------------

def stationary_counts(n, n_boot, block, rng):
    """Politis-Romano stationary bootstrap: returns [n_boot, n] counts of how often each observation is drawn."""
    p = 1.0 / block
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    jump = rng.random((n_boot, n)) < p
    fresh = rng.integers(0, n, (n_boot, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    counts = np.zeros((n_boot, n), dtype=np.float32)
    rows = np.repeat(np.arange(n_boot), n)
    np.add.at(counts, (rows, idx.ravel()), 1.0)
    return counts


def boot_means(X, n_boot=1000, block=10, rng=None):
    rng = rng or np.random.default_rng(0)
    X = np.asarray(X, dtype=np.float32)
    return (stationary_counts(len(X), n_boot, block, rng) @ X) / len(X)


def spa(d, n_boot=1000, block=10, rng=None):
    """Does any strategy beat the benchmark? d: [n, K] performance of each strategy minus the benchmark's (for cash,
    just the strategy returns). Returns dict of p-values: 'consistent' (Hansen SPA), 'upper' (White's reality check),
    'lower', plus the studentized best statistic and the index of the best strategy."""
    d = np.asarray(d, dtype=np.float64)
    n, K = d.shape
    dbar = d.mean(axis=0)
    bm = boot_means(d, n_boot, block, rng).astype(np.float64)               # [B, K]
    omega = np.sqrt(n * bm.var(axis=0, ddof=1))
    omega = np.where(omega <= 0, np.inf, omega)
    stat = max(float((np.sqrt(n) * dbar / omega).max()), 0.0)
    a_n = np.sqrt(2.0 * np.log(np.log(n)))
    poor = np.sqrt(n) * dbar / omega <= -a_n
    centred = np.sqrt(n) * (bm - dbar) / omega                              # null-centred bootstrap
    out = {}
    for name, mu in (("consistent", np.where(poor, dbar, 0.0)), ("upper", np.zeros(K)), ("lower", np.minimum(dbar, 0.0))):
        t_star = np.maximum((centred + np.sqrt(n) * mu / omega).max(axis=1), 0.0)
        out[name] = float((t_star >= stat).mean())
    out["stat"] = stat
    out["best"] = int(np.argmax(dbar / omega))
    return out


def model_confidence_set(loss, alpha=0.10, n_boot=1000, block=10, rng=None):
    """Hansen-Lunde-Nason MCS with the T_max statistic. loss: [n, K], lower is better. Returns (surviving model indices,
    MCS p-value of every model: a model is in the set at level alpha when its p-value is at least alpha)."""
    loss = np.asarray(loss, dtype=np.float64)
    n, K = loss.shape
    bm = boot_means(loss, n_boot, block, rng).astype(np.float64)
    lbar = loss.mean(axis=0)
    alive = list(range(K))
    pvals = np.zeros(K)
    running = 0.0
    stopped = False
    while len(alive) > 1:
        m = np.array(alive)
        d_i = lbar[m] - lbar[m].mean()                                      # mean loss differential vs the rest of the set
        boot_i = bm[:, m] - bm[:, m].mean(axis=1, keepdims=True)
        centred = boot_i - boot_i.mean(axis=0)
        se = np.sqrt(np.maximum((centred ** 2).mean(axis=0), 1e-30))
        t_i = d_i / se
        p = float(((centred / se).max(axis=1) >= t_i.max()).mean())
        running = max(running, p)
        worst = alive[int(np.argmax(t_i))]
        if p >= alpha:
            stopped = True
            break
        pvals[worst] = running
        alive.remove(worst)
    for k in alive:
        pvals[k] = running if stopped else 1.0                               # a lone survivor has p = 1 by convention
    return alive, pvals


# ---- online false discovery rate -----------------------------------------------------------------------------------

def _gamma(t):
    t = np.asarray(t, dtype=float)
    g = np.zeros_like(t)
    ok = t >= 1
    g[ok] = 0.07720838 * np.log(np.maximum(t[ok], 2)) / (t[ok] * np.exp(np.sqrt(np.log(t[ok]))))
    return g


def lord_plus(pvals, alpha=0.05, w0=None):
    """LORD++ over an ordered stream of p-values. Returns (reject flags, the test level used for each p-value).
    Each rejection earns back testing wealth, so a program that keeps finding real effects can keep testing."""
    w0 = alpha / 2 if w0 is None else w0
    p = np.asarray(pvals, dtype=float)
    levels = np.zeros(len(p))
    rej = np.zeros(len(p), dtype=bool)
    taus = []
    for t in range(len(p)):
        lvl = _gamma(t + 1) * w0
        if taus:
            lvl = lvl + (alpha - w0) * _gamma((t + 1) - (taus[0] + 1))
            lvl = lvl + alpha * float(_gamma((t + 1) - (np.array(taus[1:]) + 1)).sum())
        levels[t] = float(lvl)
        if p[t] <= levels[t]:
            rej[t] = True
            taus.append(t)
    return rej, levels


@dataclass
class OnlineFDR:
    """A running ledger of tests: append one p-value at a time and get that test's level and decision."""
    alpha: float = 0.05
    pvals: list = field(default_factory=list)

    def test(self, p):
        rej, lev = lord_plus(self.pvals + [p], self.alpha)
        self.pvals.append(p)
        return bool(rej[-1]), float(lev[-1])


def bh(pvals, q=0.05):
    """Benjamini-Hochberg: boolean mask of rejected hypotheses at FDR level q (independent or PRDS p-values)."""
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ok = p[order] <= q * (np.arange(1, len(p) + 1) / len(p))
    keep = np.zeros(len(p), dtype=bool)
    if ok.any():
        keep[order[: np.flatnonzero(ok).max() + 1]] = True
    return keep


# ---- shrinkage ------------------------------------------------------------------------------------------------------

def eb_shrink(m, se):
    """Empirical-Bayes posterior of true effects given noisy estimates m with standard errors se, assuming
    true ~ N(mu0, tau2). tau2 by method of moments. Returns (posterior mean, posterior sd, mu0, tau2).
    With no real spread (tau2 = 0) every estimate collapses to mu0, which removes the winner's curse."""
    m, se = np.asarray(m, dtype=float), np.asarray(se, dtype=float)
    w = 1.0 / (se ** 2 + 1e-18)
    mu0 = float((w * m).sum() / w.sum())
    tau2 = max(0.0, float(m.var(ddof=1) - np.mean(se ** 2)))
    b = tau2 / (tau2 + se ** 2)
    post = mu0 + b * (m - mu0)
    return post, np.sqrt(b) * se, mu0, tau2
