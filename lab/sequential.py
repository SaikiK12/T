"""Anytime-valid (e-value / e-process) monitoring for forward paper lanes (M479).

A forward paper lane yields a daily net-return series and is read today only at fixed
futility/decision dates. Reading it on every new day at a fixed level inflates the type-I
error, so the lab waits. An e-process removes that constraint: by Ville's inequality a
level-alpha test built from it may be inspected at *every* data-dependent stopping time.

Construction (testing by betting). For observations r_i bounded in [lo, hi] with lo < 0 and a
*predictable* bet fraction lambda_i in [0, 1/|lo|), the capital process

    K_t = prod_{i<=t} (1 + lambda_i * r_i)

is a nonnegative supermartingale under H0: E[r] <= 0, because for lambda >= 0 and E[r] <= 0

    E[1 + lambda r] = 1 + lambda E[r] <= 1,

and each factor stays positive while lambda_i < 1/|lo| (the worst case r_i = lo gives
1 + lambda lo > 0). Hence E[K_t] <= 1, and Ville's inequality gives

    P[ sup_t K_t >= 1/alpha ] <= alpha

for every stopping time. So `sup_t K_t >= 1/alpha` rejects H0 at level alpha, any time.
The always-valid p-value is min(1, 1 / sup_t K_t).

Sources: Waudby-Smith & Ramdas (2024), "Estimating means of bounded random variables by
betting", JRSS-B; Ramdas, Grunwald, Vovk & Shafer (2023), "Game-theoretic statistics and safe
anytime-valid inference", Statistical Science 38(4); Howard, Ramdas, McAuliffe & Sekhon (2021),
"Time-uniform, nonparametric confidence sequences", JRSS-B. Only the first is needed for the
process above; the others place it in the wider literature.

This module is a *monitor*. It changes no frozen lane rule and prices no execution risk: a
rejected H0 says the lane's realised net mean is positive at level alpha, not that the strategy
is profitable net of live fills. A null is a result.
"""
import math

import numpy as np

__all__ = ["e_process", "hedged_bet", "block_means", "mixture_e_process",
           "lane_monitor", "min_detectable_mean", "DEFAULT_ALPHA"]

DEFAULT_ALPHA = 0.05


def hedged_bet(sigma_hat: float, t: int, lo: float, hi: float, alpha: float, hedge: float = 0.5) -> float:
    """A predictable, valid bet fraction in [0, 1/|lo|).

    The GRAPA-style plug-in size `hedge * sqrt(2 ln(1/alpha) / (t * sigma_hat^2))`, where
    `sigma_hat` is the running *standard deviation* of past returns. It carries the units of
    1/return (variance in the denominator), so the process is invariant under a change of the
    return scale, and it is capped just below the positivity boundary 1/|lo|. `hedge` is the
    Waudby-Smith & Ramdas hedging constant (0.5 is the usual choice): any predictable lambda in
    [0, 1/|lo|) keeps `e_process` a valid supermartingale, so `hedge` tunes power, never validity.
    A weak variance estimate degrades power, never validity.
    """
    cap = 0.999 / abs(lo)
    var = max(sigma_hat, 1e-12) ** 2
    lam = hedge * math.sqrt(2.0 * math.log(1.0 / alpha) / (max(1, t) * var))
    return float(min(lam, cap))


def e_process(returns, lo: float, hi: float, *, alpha: float = DEFAULT_ALPHA, bet=None):
    """Run the betting e-process for H0: mean(returns) <= 0.

    Parameters
    ----------
    returns : sequence of float
        Daily net returns in return units (e.g. 0.001 for 10 bp). NaN entries are skipped
        (a missing day is not a zero) but still advance the look counter. An empty or
        all-NaN series returns e_value = 1.0 and rejects nothing.
    lo, hi : float
        Honest bounds with lo < 0 < hi and every r_i in [lo, hi]. The caller's PREREG fixes
        them; this module never guesses a bound from the data it is testing.
    alpha : float
        Level of the anytime test; the rejection threshold is 1/alpha.
    bet : callable, optional
        `bet(sigma_hat, t, lo, hi, alpha) -> lambda`. Defaults to `hedged_bet`. The bet must be
        predictable (a function of past observations only); the running variance passed to it
        uses observations strictly before the current one.

    Returns
    -------
    dict with: `path` (K_t after each observed day, NaN on skipped days), `log_path`,
    `running_max`, `e_value` (sup_t K_t), `p_anytime` (min(1, 1/e_value)), `reject` (bool),
    `threshold` (1/alpha), `n_observed`, `n_skipped`, `first_reject_index` (0-based index into
    the observed days, or None), `alpha`, `lo`, `hi`, `bet_cap`.
    """
    if not (lo < 0.0 < hi):
        raise ValueError("bounds must straddle zero: lo < 0 < hi")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    if bet is None:
        bet = hedged_bet

    x = np.asarray(returns, dtype=float)
    if x.ndim != 1:
        raise ValueError("returns must be one-dimensional")
    if np.any(np.isfinite(x) & ((x < lo) | (x > hi))):
        raise ValueError(f"an observation lies outside [{lo}, {hi}]: fix the bound, do not clip silently")

    observed = x[np.isfinite(x)]
    if observed.size == 0:
        return dict(path=np.array([]), log_path=np.array([]), running_max=np.array([]),
                    e_value=1.0, p_anytime=1.0, reject=False, threshold=1.0 / alpha,
                    n_observed=0, n_skipped=int(x.size), first_reject_index=None,
                    alpha=alpha, lo=lo, hi=hi, bet_cap=0.999 / abs(lo))

    log_k = 0.0
    log_path = np.empty(observed.size)
    running_max = np.empty(observed.size)
    run_max = 1.0
    first_reject = None
    threshold = 1.0 / alpha
    n = 0
    sum_r = 0.0
    sum_r2 = 0.0
    for i, r in enumerate(observed):
        n += 1
        sigma_hat = math.sqrt(max(sum_r2 / (n - 1) - (sum_r / (n - 1)) ** 2, 0.0)) if n > 1 else abs(hi - lo) / 2.0
        lam = float(bet(sigma_hat, n, lo, hi, alpha))
        if not (0.0 <= lam < 1.0 / abs(lo)):
            raise ValueError(f"bet fraction {lam} is outside [0, 1/|lo|) at step {n}")
        factor = 1.0 + lam * float(r)
        log_k += math.log(factor)
        k = math.exp(log_k)
        log_path[i] = log_k
        run_max = max(run_max, k)
        running_max[i] = run_max
        if first_reject is None and run_max >= threshold:
            first_reject = i
        sum_r += float(r)
        sum_r2 += float(r) * float(r)
    e_value = float(run_max)
    return dict(path=np.exp(log_path), log_path=log_path, running_max=running_max,
                e_value=e_value, p_anytime=min(1.0, 1.0 / e_value), reject=bool(e_value >= threshold),
                threshold=threshold, n_observed=int(observed.size), n_skipped=int(x.size - observed.size),
                first_reject_index=first_reject, alpha=alpha, lo=lo, hi=hi, bet_cap=0.999 / abs(lo))


def block_means(returns, block: int):
    """Non-overlapping block means of a daily series, dropping a trailing incomplete block.

    Under serial dependence the daily observations are not martingale differences, so the
    betting guarantee on the raw series is only approximate. Grouping into `block`-day means
    restores an (approximately) uncorrelated stream: the block-mean e-process is then valid
    where the raw one is not. Complete blocks only; a trailing partial block is dropped, never
    padded. Returns (means, lo_block, hi_block) with the block bounds implied by [lo, hi].
    """
    if block < 1:
        raise ValueError("block must be >= 1")
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    n_full = (x.size // block) * block
    if n_full == 0:
        return np.array([]), None, None
    return x[:n_full].reshape(-1, block).mean(axis=1), None, None


def mixture_e_process(returns, lo: float, hi: float, *, alpha: float = DEFAULT_ALPHA,
                      grid: int = 200, cap_eps: float = 1e-3):
    """Method-of-mixtures e-process: average the capital process over a fixed log grid of bets.

    `E_t = mean_{lambda in L} prod_{i<=t} (1 + lambda r_i)` with `L` a log-spaced grid on
    `(0, (1-cap_eps)/|lo|)` fixed before the data. An average of nonnegative supermartingales
    is a supermartingale, so Ville's inequality still holds and no variance estimate is needed
    (the Waudby-Smith & Ramdas method of mixtures). It is the most robust choice under heavy
    tails; the price is a wider (more conservative) process than a well-tuned Kelly bet.
    Returns the same dict shape as `e_process` (path is the mixture capital, not a product).
    """
    if not (lo < 0.0 < hi):
        raise ValueError("bounds must straddle zero: lo < 0 < hi")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    if grid < 2:
        raise ValueError("grid must be >= 2")
    x = np.asarray(returns, dtype=float)
    x = x[np.isfinite(x)]
    threshold = 1.0 / alpha
    if x.size == 0:
        return dict(path=np.array([]), running_max=np.array([]), e_value=1.0, p_anytime=1.0,
                    reject=False, threshold=threshold, n_observed=0, n_skipped=0,
                    first_reject_index=None, alpha=alpha, lo=lo, hi=hi, grid=grid)
    cap = (1.0 - cap_eps) / abs(lo)
    lams = np.exp(np.linspace(math.log(cap * 1e-4), math.log(cap), grid))
    log_caps = np.zeros(grid)
    path = np.empty(x.size)
    running_max = np.empty(x.size)
    run_max = 1.0
    first_reject = None
    for i, r in enumerate(x):
        log_caps += np.log1p(lams * float(r))
        k = float(np.mean(np.exp(log_caps - log_caps.max())) * math.exp(log_caps.max()))
        path[i] = k
        run_max = max(run_max, k)
        running_max[i] = run_max
        if first_reject is None and run_max >= threshold:
            first_reject = i
    e_value = float(run_max)
    return dict(path=path, running_max=running_max, e_value=e_value,
                p_anytime=min(1.0, 1.0 / e_value), reject=bool(e_value >= threshold),
                threshold=threshold, n_observed=int(x.size), n_skipped=0,
                first_reject_index=first_reject, alpha=alpha, lo=lo, hi=hi, grid=grid)


def lane_monitor(returns, lo: float, hi: float, *, alpha: float = DEFAULT_ALPHA,
                 block: int = 1, mode: str = "bet", bet=None):
    """The single call a forward script makes to monitor one lane's daily net series.

    `returns` is the lane's daily net (return units, NaN for a missing day). `lo < 0 < hi` are
    the PREREG's frozen support bounds. `mode`:
      - "bet"      : the adaptive hedged-bet e-process on the raw daily series (`e_process`);
      - "block"    : the same, on non-overlapping `block`-day means (use when the lane's daily
                     series is autocorrelated, so the raw martingale guarantee is inexact);
      - "mixture"  : the method-of-mixtures e-process on the raw daily series (`mixture_e_process`).
    The verdict is unchanged in every mode: reject H0: mean <= 0 the first day the running max
    of the capital process reaches 1/alpha. Returns the monitor dict plus `mode` and `block`.
    """
    if mode not in ("bet", "block", "mixture"):
        raise ValueError("mode must be 'bet', 'block' or 'mixture'")
    x = np.asarray(returns, dtype=float)
    if mode == "mixture":
        out = mixture_e_process(x, lo, hi, alpha=alpha)
    elif mode == "block":
        if block < 1:
            raise ValueError("block must be >= 1")
        means, _, _ = block_means(x, block)
        # a block mean of values in [lo, hi] lies in [lo, hi]
        out = e_process(means, lo, hi, alpha=alpha, bet=bet)
        out["n_blocks"] = int(means.size)
    else:
        out = e_process(x, lo, hi, alpha=alpha, bet=bet)
    out["mode"] = mode
    out["block"] = block if mode == "block" else 1
    return out


def min_detectable_mean(n_days: int, lo: float, hi: float, *, alpha: float = DEFAULT_ALPHA, power: float = 0.8):
    """A rough design number: the smallest positive mean a fixed-n e-process tends to detect.

    Uses the plug-in bet size at the detection scale and a Gaussian working model for the log
    capital, giving mu* such that `sqrt(2 n ln(1/alpha)) * mu* / span` reaches the normal
    (1-power) quantile. It is a planning aid for a PREREG's power paragraph, not a guarantee;
    the realised power depends on the bet schedule and the true variance.
    """
    if n_days < 1 or not (0.0 < alpha < 1.0) or not (0.0 < power < 1.0):
        raise ValueError("n_days >= 1, alpha and power in (0, 1)")
    from statistics import NormalDist
    z = NormalDist().inv_cdf(power)
    span = hi - lo
    return float(z * span / math.sqrt(2.0 * n_days * math.log(1.0 / alpha)))
