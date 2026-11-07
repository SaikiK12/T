"""Performance tear sheet for a daily return stream: quantstats' core metrics, plus the lab's honesty terms.

`tearsheet(returns)` takes daily simple returns (a pd.Series indexed by date, or anything pd.Series accepts) and
returns plain JSON-ready dicts:
  - metrics: total and annual return, annual volatility, Sharpe, Sortino, Calmar, max drawdown and its length,
    current drawdown, daily VaR / CVaR at 95%, tail ratio, skew, excess kurtosis, hit rate, profit factor, payoff
    ratio, best / worst day, longest losing streak, Kelly fraction, the t of the mean, PSR (P[true Sharpe > 0]) and
    a deflated Sharpe at a stated trial count;
  - serial dependence, which quantstats ignores: lag-1 autocorrelation, a Newey-West t (Bartlett kernel, at least 10
    lags), Lo's (2002) autocorrelation-adjusted annual Sharpe, and the AR(1) effective sample size
    n x (1 - rho1) / (1 + rho1). PSR and DSR use the effective size, so a smooth, autocorrelated stream (carry) is
    not credited with more independent days than it has;
  - curve: date, compounded equity (start 1.0), drawdown, rolling Sharpe over `window` days;
  - monthly: compounded return per calendar month.
Crypto trades every day, so annualizing uses 365 periods. Fewer than 2 observations give metrics of None, and a
stream shorter than MIN_ANNUAL days gets no CAGR or Calmar (19 days compounded to a year is noise, not a rate).

The deflated Sharpe uses the false-strategy bound: under no skill, the best per-period Sharpe of N independent tries
on T observations is about expected_max_sr(N, 1/T). It is the probability that the true Sharpe beats that bound,
so at the program's trial count (millions) it is a deliberately harsh haircut, not a verdict.
"""
import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from lab.inference import expected_max_sr, psr

PERIODS = 365
MIN_ANNUAL = 90


def _f(x):
    return None if x is None or not np.isfinite(x) else float(x)


def drawdown(equity):
    return equity / equity.cummax() - 1.0


def longest(mask):
    """Longest run of True."""
    best = run = 0
    for m in mask:
        run = run + 1 if m else 0
        best = max(best, run)
    return best


def autocorr(r, k):
    return float(np.corrcoef(r[:-k], r[k:])[0, 1]) if len(r) > k + 2 and r[:-k].std() > 0 and r[k:].std() > 0 else 0.0


def newey_west_t(r, lags=None):
    r = np.asarray(r, dtype=float)
    n = len(r)
    lags = lags if lags is not None else max(10, int(4 * (n / 100) ** (2 / 9)))
    lags = min(lags, n - 2)
    e = r - r.mean()
    lrv = e @ e / n
    for k in range(1, lags + 1):
        lrv += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / n
    return r.mean() / math.sqrt(lrv / n) if lrv > 0 else None


def lo_sharpe(r, q=PERIODS, max_lag=60):
    """Lo (2002): annualize a per-period Sharpe with the autocorrelations instead of sqrt(q)."""
    r = np.asarray(r, dtype=float)
    sd = r.std(ddof=1)
    if sd == 0:
        return None
    lags = min(q - 1, max_lag, len(r) // 4)
    denom = q + 2 * sum((q - k) * autocorr(r, k) for k in range(1, lags + 1))
    return r.mean() / sd * q / math.sqrt(denom) if denom > 0 else None


def metrics(r, n_trials=None):
    r = pd.Series(r, dtype=float).dropna()
    n = len(r)
    out = {"days": n}
    if n < 2:
        return out
    eq = (1 + r).cumprod()
    dd = drawdown(eq)
    mu, sd = r.mean(), r.std(ddof=1)
    down = r[r < 0]
    years = n / PERIODS
    total = eq.iloc[-1] - 1
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    maxdd = dd.min()
    under = dd < 0
    wins, losses = r[r > 0], r[r < 0]
    q5, q95 = np.quantile(r, [0.05, 0.95])
    sr = mu / sd if sd > 0 else np.nan
    sk, ku = sps.skew(r), sps.kurtosis(r, fisher=False)
    rho1 = autocorr(r.values, 1)
    n_eff = min(n, max(2.0, n * (1 - rho1) / (1 + rho1)))
    out.update({
        "total_return": total, "cagr": cagr if n >= MIN_ANNUAL else None, "ann_vol": sd * math.sqrt(PERIODS),
        "sharpe": sr * math.sqrt(PERIODS) if sd > 0 else None,
        "sortino": mu / math.sqrt((down ** 2).sum() / n) * math.sqrt(PERIODS) if len(down) else None,
        "calmar": cagr / -maxdd if maxdd < 0 and n >= MIN_ANNUAL else None,
        "max_drawdown": maxdd, "max_dd_days": longest(under), "current_drawdown": dd.iloc[-1],
        "var95": q5, "cvar95": r[r <= q5].mean(), "tail_ratio": q95 / -q5 if q5 < 0 else None,
        "skew": sk, "excess_kurtosis": ku - 3,
        "hit_rate": (r > 0).mean(), "profit_factor": wins.sum() / -losses.sum() if len(losses) else None,
        "payoff": wins.mean() / -losses.mean() if len(wins) and len(losses) else None,
        "best_day": r.max(), "worst_day": r.min(), "losing_streak": longest(r < 0),
        "kelly": mu / sd ** 2 if sd > 0 else None, "t": mu / (sd / math.sqrt(n)) if sd > 0 else None,
        "ac1": rho1, "t_nw": newey_west_t(r.values) if sd > 0 else None,
        "sharpe_ac": lo_sharpe(r.values), "n_eff": n_eff,
        "psr": psr(sr, 0.0, n_eff, sk, ku) if sd > 0 else None,
    })
    if n_trials and sd > 0:
        sr0 = expected_max_sr(n_trials, 1.0 / n_eff)
        out.update({"dsr": psr(sr, sr0, n_eff, sk, ku), "dsr_trials": int(n_trials),
                    "dsr_bar_sharpe": sr0 * math.sqrt(PERIODS)})
    return {k: (_f(v) if isinstance(v, (float, np.floating)) else v) for k, v in out.items()}


def tearsheet(returns, n_trials=None, window=90):
    r = pd.Series(returns, dtype=float).dropna().sort_index()
    out = {"metrics": metrics(r, n_trials), "curve": [], "monthly": []}
    if len(r) == 0:
        return out
    eq = (1 + r).cumprod()
    dd = drawdown(eq)
    roll = r.rolling(window).apply(lambda x: x.mean() / x.std(ddof=1) * math.sqrt(PERIODS) if x.std(ddof=1) > 0
                                   else np.nan, raw=True) if len(r) >= window else pd.Series(np.nan, index=r.index)
    for d, e, x, s in zip(r.index, eq, dd, roll):
        out["curve"].append({"date": str(pd.Timestamp(d).date()), "equity": _f(e), "drawdown": _f(x),
                             "rolling_sharpe": _f(s)})
    idx = pd.to_datetime(r.index)
    by_month = (1 + pd.Series(r.values, index=idx)).groupby([idx.year, idx.month]).prod() - 1
    out["monthly"] = [{"year": int(y), "month": int(m), "ret": _f(v)} for (y, m), v in by_month.items()]
    return out
