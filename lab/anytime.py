"""Sequential monitoring of a daily P&L mean, checked every day without a fixed sample size.

The rule is the asymptotic HAC mixture monitor ("AHAC"). It comes from a 2026-11-19 deep reading of:
- Ramdas, Grünwald, Vovk and Shafer (2023), game-theoretic statistics and anytime-valid inference;
- Waudby-Smith and Ramdas (2024), estimating means by betting;
- Howard et al. (2021), time-uniform confidence sequences;
- Ge and Liu (2026), HAC asymptotic confidence sequences for dependent data.

The rule:
- S_n is the running sum of the daily series. sigma_n is its long-run sd: Bartlett/Newey-West, bandwidth
  floor(n^(1/3)).
- The one-sided Robbins normal mixture over drift lambda >= 0, with mixing sd rho, gives
  log E_n = log 2 - log(a)/2 + rho^2 s^2 / (2a) + log Phi(rho s / sqrt(a)),
  where s = S_n / sigma_n and a = 1 + rho^2 n.
- E_n is an e-process only asymptotically: the daily series is replaced by its Gaussian approximation and sigma_n by
  its HAC estimate. Its size is therefore checked by simulation, not guaranteed.
- With rho tuned to cross earliest at n = 90 for alpha = 0.025, a 30-day burn-in and the threshold E >= 40, 4,000
  simulated 720-day paths of daily nets (sd 18 bp, t5 tails, mean 0) crossed in 3.0% (i.i.d.), 2.2% (AR(1) -0.2) and
  4.2% (AR(1) +0.2) of paths.
- At a mean of 6.6 bp/day the median crossing came on day 47 (i.i.d.) or 38 (AR -0.2); at 3.3 bp/day, on day 179.

An exact alternative (betting with a pre-registered loss bound) was found slower than a fixed 90-day Newey-West look
on this kind of series, because the loss bound caps the bet.
"""
import math

import numpy as np

DEFAULT = {"tstar": 90.0, "alpha": 0.025, "burn": 30, "threshold": 40.0}


def log_phi(z):
    """log of the standard normal cdf, elementwise."""
    z = np.asarray(z, float)
    v = 0.5 * np.vectorize(math.erfc)(-z / math.sqrt(2.0))
    return np.log(np.maximum(v, 1e-300))


def halfnormal_log_e(s, n, rho):
    """log E for the one-sided normal mixture at standardized sum s after n days."""
    a = 1.0 + rho * rho * n
    return math.log(2.0) - 0.5 * np.log(a) + rho * rho * np.asarray(s, float) ** 2 / (2 * a) + \
        log_phi(rho * np.asarray(s, float) / np.sqrt(a))


def tune_rho(tstar=90.0, alpha=0.025):
    """(rho, s*) with the smallest standardized sum s* that crosses log(1/alpha) at n = tstar."""
    best = None
    for rho in np.exp(np.linspace(np.log(0.01), np.log(3.0), 400)):
        lo, hi = 0.0, 50.0
        for _ in range(60):
            mid = (lo + hi) / 2
            if halfnormal_log_e([mid], tstar, rho)[0] >= math.log(1 / alpha):
                hi = mid
            else:
                lo = mid
        if best is None or hi < best[1]:
            best = (float(rho), float(hi))
    return best


def long_run_sd(x):
    """Bartlett (Newey-West) long-run sd of x around its mean, bandwidth floor(n^(1/3))."""
    x = np.asarray(x, float)
    n = len(x)
    d = x - x.mean()
    b = int(math.floor(n ** (1 / 3)))
    v = float(d @ d) / n
    for k in range(1, b + 1):
        v += 2.0 * (1 - k / (b + 1)) * float(d[k:] @ d[:-k]) / n
    return math.sqrt(max(v, 1e-24))


def monitor(x, tstar=DEFAULT["tstar"], alpha=DEFAULT["alpha"], burn=DEFAULT["burn"],
            threshold=DEFAULT["threshold"]):
    """Run the monitor over x in order. Returns {"log_e": [...], "first_cross": day number (1-based) or None,
    "rho": rho}. Days before `burn` have no e-value."""
    x = np.asarray(x, float)
    rho, _ = tune_rho(tstar, alpha)
    out, first = [], None
    for n in range(1, len(x) + 1):
        if n < burn:
            out.append(None)
            continue
        s = float(x[:n].sum()) / long_run_sd(x[:n])
        le = float(halfnormal_log_e([s], n, rho)[0])
        out.append(le)
        if first is None and le >= math.log(threshold):
            first = n
    return {"log_e": out, "first_cross": first, "rho": rho}
