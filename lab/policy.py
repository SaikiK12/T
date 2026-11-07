"""Judging the PROCESS of picking strategies, because strategies work for a time and not forever.

All functions take R, a [D, N] matrix of daily net returns of N strategies over D days, already net of each strategy's
own trading costs. Three questions, in order:
  locality    when did each strategy work?                       rolling_t, episodes
  persistence does recent performance predict the near future    persistence_ic, persistence_test
              more than it predicts the distant future?          (fixed skill predicts both equally; a regime does not)
  policy      does choosing the currently-best strategies beat   run_policy, policy_vs_random
              choosing at random from the same pool?
Selection happens inside the loop and uses only days before the rebalance, so the policy has a handful of knobs
(lookback, K, rebalance step, shrinkage) however many strategies it chooses among.
"""
import numpy as np
from scipy import stats as sps

from . import engine, inference


def _cum(R):
    z = np.zeros((1, R.shape[1]))
    return np.vstack([z, np.cumsum(R, axis=0)]), np.vstack([z, np.cumsum(R ** 2, axis=0)])


def trailing_moments(R, L):
    """For each day t: mean, standard error and t of every strategy over days [t - L, t). NaN for t < L."""
    D, N = R.shape
    c1, c2 = _cum(R)
    mean = np.full((D, N), np.nan)
    se = np.full((D, N), np.nan)
    mean[L:] = (c1[L:D] - c1[:D - L]) / L
    var = np.maximum((c2[L:D] - c2[:D - L]) / L - mean[L:] ** 2, 1e-18) * L / (L - 1)
    se[L:] = np.sqrt(var / L)
    return mean, se


def rolling_t(R, window):
    """Where the strategy's recent window looked good: (mean / standard error) over the trailing window, shifted so
    row t uses days up to and including t. A descriptive map, not a test (it ignores autocorrelation)."""
    mean, se = trailing_moments(R, window)
    out = np.full_like(mean, np.nan)
    out[window - 1:-1] = (mean / se)[window:]
    last = R[-window:]
    out[-1] = last.mean(axis=0) / (last.std(axis=0, ddof=1) / np.sqrt(window))
    return out


def episodes(t_roll, thresh=2.0, min_days=30):
    """Per strategy, the (start, end) day ranges where the rolling t stayed at or above thresh for at least min_days."""
    out = []
    for k in range(t_roll.shape[1]):
        on = np.nan_to_num(t_roll[:, k], nan=-np.inf) >= thresh
        edges = np.flatnonzero(np.diff(np.concatenate([[0], on.astype(int), [0]])))
        out.append([(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2]) if b - a >= min_days])
    return out


# ---- persistence ---------------------------------------------------------------------------------------------------

def _row_ranks(A):
    return A.argsort(axis=1).argsort(axis=1).astype(float)  # continuous data, so ties do not arise


def persistence_ic(R, L=60, H=20, gap=0, start=None):
    """Mean rank correlation across strategies between trailing performance (L days ending `gap` days before the
    rebalance) and forward performance (the next H days), over non-overlapping rebalance dates."""
    D, N = R.shape
    mean, se = trailing_moments(R, L)
    c1, _ = _cum(R)
    dates = np.arange(max(start or 0, L + gap), D - H + 1, H)
    past = (mean / se)[dates - gap]
    fwd = (c1[dates + H] - c1[dates]) / H
    keep = np.isfinite(past).all(axis=1)
    rp, rf = _row_ranks(past[keep]), _row_ranks(fwd[keep])
    rp -= rp.mean(axis=1, keepdims=True)
    rf -= rf.mean(axis=1, keepdims=True)
    ics = (rp * rf).sum(axis=1) / np.sqrt((rp ** 2).sum(axis=1) * (rf ** 2).sum(axis=1))
    return float(ics.mean()), ics


def persistence_test(R, L=60, H=20, far_gap=250, n_perm=200, block=20, rng=None, min_dates=8):
    """Recent-vs-distant predictive power. diff = IC(gap 0) - IC(gap far_gap). A strategy with a fixed edge predicts
    equally well at both gaps; a regime-bound one predicts better when the trailing window is recent. The null permutes
    whole blocks of days jointly across strategies, which keeps each strategy's returns and the cross-correlations but
    removes any dependence of performance on recent history longer than `block` days."""
    rng = rng or np.random.default_rng(0)
    D = len(R)
    n_dates = len(range(L + far_gap, D - H + 1, H))
    if n_dates < min_dates:
        return {"diff": np.nan, "ic_recent": np.nan, "ic_far": np.nan, "p": np.nan, "null_mean": np.nan,
                "insufficient": f"{n_dates} rebalance dates after the {L + far_gap}-day warm-up (need {min_dates})"}

    def stat(M):
        return persistence_ic(M, L, H, 0, start=L + far_gap)[0] - persistence_ic(M, L, H, far_gap, start=L + far_gap)[0]

    obs = stat(R)
    n_blocks = D // block
    null = np.empty(n_perm)
    for i in range(n_perm):
        order = rng.permutation(n_blocks)
        null[i] = stat(np.vstack([R[b * block:(b + 1) * block] for b in order]))
    return {"diff": obs, "ic_recent": persistence_ic(R, L, H, 0, start=L + far_gap)[0],
            "ic_far": persistence_ic(R, L, H, far_gap, start=L + far_gap)[0],
            "p": float((1 + (null >= obs).sum()) / (1 + n_perm)), "null_mean": float(null.mean())}


# ---- adaptive policy -----------------------------------------------------------------------------------------------

def _sets(R, L, K, H, shrink, start):
    """The chosen strategy set at every rebalance day t in start, start + H, ..."""
    mean, se = trailing_moments(R, L)
    days, chosen = [], []
    for t in range(max(start, L), len(R), H):
        m, s = mean[t], se[t]
        score = inference.eb_shrink(m, s)[0] if shrink else m
        chosen.append(np.argpartition(-score, K - 1)[:K])
        days.append(t)
    return days, chosen


def _apply(R, days, chosen, H, K, switch_cost):
    D = len(R)
    out = np.full(D, np.nan)
    prev = set()
    for t, idx in zip(days, chosen):
        cur = set(idx.tolist())
        swaps = len(cur - prev) + len(prev - cur) if prev else len(cur)
        seg = slice(t, min(t + H, D))
        out[seg] = R[seg][:, idx].mean(axis=1)
        out[t] -= switch_cost * swaps / K
        prev = cur
    return out


def run_policy(R, L=60, K=10, H=7, shrink=True, switch_cost=0.0015, start=0):
    """Daily return series of the adaptive policy (NaN before the first rebalance). Charging switch_cost per unit of
    capital moved in or out of a strategy stands in for establishing and closing its book."""
    days, chosen = _sets(R, L, K, H, shrink, start)
    return _apply(R, days, chosen, H, K, switch_cost)


def random_policies(R, chosen, H, switch_cost=0.0015, n_rep=300, start=0, L=60, rng=None):
    """No-skill baseline from the same pool, MATCHED ON TURNOVER: at every rebalance it swaps exactly as many strategies
    as the real policy did, picked at random. (Re-drawing a whole random set each time would pay far more switching cost
    than a sticky policy and make any trailing-score rule look skilled on pure noise.)"""
    rng = rng or np.random.default_rng(0)
    N = R.shape[1]
    days, sets = chosen
    K = len(sets[0])
    swaps = [len(sets[0])] + [len(set(b.tolist()) - set(a.tolist())) for a, b in zip(sets[:-1], sets[1:])]
    out = []
    for _ in range(n_rep):
        cur = set(rng.choice(N, K, replace=False).tolist())
        rand_sets = [np.array(sorted(cur))]
        for n_swap in swaps[1:]:
            drop = set(int(x) for x in rng.choice(sorted(cur), n_swap, replace=False)) if n_swap else set()
            pool = np.setdiff1d(np.arange(N), np.array(sorted(cur)), assume_unique=True)   # excludes the dropped ones too
            cur = (cur - drop) | (set(int(x) for x in rng.choice(pool, n_swap, replace=False)) if n_swap else set())
            rand_sets.append(np.array(sorted(cur)))
        out.append(_apply(R, days, rand_sets, H, K, switch_cost))
    return np.vstack(out)


def policy_vs_random(R, L=60, K=10, H=7, shrink=True, switch_cost=0.0015, n_rep=300, start=0, lag=10, rng=None):
    """Policy mean daily return against turnover-matched random selection, with a Newey-West t on the paired difference."""
    days, chosen = _sets(R, L, K, H, shrink, start)
    pol = _apply(R, days, chosen, H, K, switch_cost)
    rnd = random_policies(R, (days, chosen), H, switch_cost, n_rep, start, L, rng)
    ok = ~np.isnan(pol)
    diff = pol[ok] - np.nanmean(rnd[:, ok], axis=0)
    rnd_means = rnd[:, ok].mean(axis=1)
    return {"mean": float(pol[ok].mean()), "random_mean": float(rnd_means.mean()),
            "sharpe_annual": float(pol[ok].mean() / pol[ok].std(ddof=1) * np.sqrt(365)),
            "t_vs_random": float(engine.nw_t(diff, lag)),
            "p_random": float((1 + (rnd_means >= pol[ok].mean()).sum()) / (1 + n_rep)),
            "n_days": int(ok.sum()), "series": pol}
