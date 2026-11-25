"""Is the design-gap family decaying, or does it follow the market? (descriptive, R525's seen in-sample nets)

Panel: monthly return of each of R525's 12 pairs (sum of daily nets at 1x, months with at least 20 live days), pair
fixed effects, regressors: a linear time trend (years since 2021-01), BTC's past 120-day return at the month's start,
the month's BTC return and the month's realized daily volatility (Binance BTCUSDT hourly closes). Standard errors
clustered by month. Also the equal-weight portfolio's monthly series alone (Newey-West, 3 lags).

    python scripts/check_gap_trend.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def ols_cluster(y, X, groups):
    """OLS with cluster-robust (by group) standard errors. Returns (beta, se)."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ X.T @ y
    e = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        m = groups == g
        s = X[m].T @ e[m]
        meat += np.outer(s, s)
    G, n, k = len(np.unique(groups)), len(y), X.shape[1]
    c = G / (G - 1) * (n - 1) / (n - k)
    v = c * xtx_inv @ meat @ xtx_inv
    return b, np.sqrt(np.diag(v))


def ols_nw(y, X, lags=3):
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    xtx_inv = np.linalg.inv(X.T @ X)
    b = xtx_inv @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        g = u[L:].T @ u[:-L]
        S += w * (g + g.T)
    v = xtx_inv @ S @ xtx_inv
    return b, np.sqrt(np.diag(v))


def regime():
    d = pd.read_parquet(ROOT / "data/klines_1h/BTCUSDT.parquet", columns=["t", "close"])
    t = pd.to_datetime(d.t, unit="ms", utc=True) if d.t.dtype.kind in "iu" else pd.to_datetime(d.t, utc=True)
    c = pd.Series(d.close.to_numpy(float), index=t).resample("D").last().dropna()
    r = np.log(c).diff()
    out = pd.DataFrame({
        "btc_ret": np.log(c).resample("MS").last().diff().shift(-1) * 0 + np.nan,   # placeholder, set below
    })
    m_last = np.log(c).resample("MS").first()
    month_ret = (np.log(c).resample("MS").last() - np.log(c).resample("MS").first())
    vol = r.resample("MS").std() * np.sqrt(365)
    past = np.log(c).shift(1).resample("MS").first() - np.log(c).shift(121).resample("MS").first()
    out = pd.DataFrame({"btc_ret": month_ret, "btc_vol": vol, "btc_past120": past})
    out.index = out.index.strftime("%Y-%m")
    del m_last
    return out


def main() -> int:
    d = pd.read_csv(ROOT / "experiments/gap_breadth_v1/results/pair_daily_net_1x.csv", parse_dates=["day"])
    d = d.set_index("day")
    pairs = list(d.columns)
    rows = []
    for p in pairs:
        s = d[p].dropna()
        g = s.groupby(s.index.strftime("%Y-%m"))
        m = pd.DataFrame({"ret": g.sum() * 100, "days": g.size()})
        m = m[m.days >= 20]
        for mo, x in m.iterrows():
            rows.append({"pair": p, "month": mo, "ret": x.ret})
    P = pd.DataFrame(rows)
    R = regime()
    P = P.join(R, on="month").dropna()
    t0 = pd.Timestamp("2021-01-01")
    P["trend"] = (pd.to_datetime(P.month + "-01") - t0).dt.days / 365.25
    print(f"panel: {len(P)} pair-months, {P.pair.nunique()} pairs, {P.month.nunique()} months; mean monthly return "
          f"{P.ret.mean():+.3f}% ({P.ret.mean() * 12:+.2f}%/yr)")
    fe = pd.get_dummies(P.pair, drop_first=False).astype(float).to_numpy()
    groups = P.month.to_numpy()
    for label, cols in (("trend only", ["trend"]),
                        ("trend + regime", ["trend", "btc_past120", "btc_ret", "btc_vol"])):
        X = np.column_stack([P[cols].to_numpy(float), fe])
        b, se = ols_cluster(P.ret.to_numpy(), X, groups)
        txt = ", ".join(f"{c} {b[i]:+.3f} (t {b[i] / se[i]:+.2f})" for i, c in enumerate(cols))
        print(f"  pair FE, {label}: {txt}")
    # The trend in % of the family's mean level per year
    X = np.column_stack([P[["trend", "btc_past120", "btc_ret", "btc_vol"]].to_numpy(float), fe])
    b, se = ols_cluster(P.ret.to_numpy(), X, groups)
    print(f"  regime-adjusted trend: {b[0]:+.3f} %/month per year = {100 * b[0] / P.ret.mean():+.0f}% of the mean "
          f"level per year (t {b[0] / se[0]:+.2f})")
    # Same without the Kraken pairs (which only exist from 2025-12)
    Q = P[~P.pair.str.startswith("kraken")]
    feq = pd.get_dummies(Q.pair).astype(float).to_numpy()
    Xq = np.column_stack([Q[["trend", "btc_past120", "btc_ret", "btc_vol"]].to_numpy(float), feq])
    bq, seq = ols_cluster(Q.ret.to_numpy(), Xq, Q.month.to_numpy())
    print(f"  without Kraken pairs: trend {bq[0]:+.3f} (t {bq[0] / seq[0]:+.2f}), past120 {bq[1]:+.3f} "
          f"(t {bq[1] / seq[1]:+.2f}), month ret {bq[2]:+.3f} (t {bq[2] / seq[2]:+.2f}), vol {bq[3]:+.3f} "
          f"(t {bq[3] / seq[3]:+.2f}); mean {Q.ret.mean():+.3f}%/month")
    # Per pair: trend alone and regime-adjusted
    print("\n| pair | months | mean %/month | trend alone (t) | trend, regime-adjusted (t) |")
    print("|---|---|---|---|---|")
    for p, g in P.groupby("pair"):
        if len(g) < 18:
            print(f"| {p} | {len(g)} | {g.ret.mean():+.2f} | (too short) | |")
            continue
        X1 = np.column_stack([np.ones(len(g)), g.trend])
        b1, s1 = ols_nw(g.ret.to_numpy(), X1)
        X2 = np.column_stack([np.ones(len(g)), g[["trend", "btc_past120", "btc_ret", "btc_vol"]].to_numpy(float)])
        b2, s2 = ols_nw(g.ret.to_numpy(), X2)
        print(f"| {p} | {len(g)} | {g.ret.mean():+.2f} | {b1[1]:+.3f} ({b1[1] / s1[1]:+.2f}) | "
              f"{b2[1]:+.3f} ({b2[1] / s2[1]:+.2f}) |")
    # Equal-weight portfolio of live non-Kraken pairs, by year and on regime
    ew = Q.groupby("month").ret.mean()
    E = R.loc[ew.index]
    E["ret"] = ew
    E["trend"] = (pd.to_datetime(E.index + "-01") - t0).days / 365.25
    Xe = np.column_stack([np.ones(len(E)), E[["trend", "btc_past120", "btc_ret", "btc_vol"]].to_numpy(float)])
    be, sse = ols_nw(E.ret.to_numpy(), Xe)
    print(f"\nequal-weight non-Kraken portfolio, {len(E)} months: trend {be[1]:+.3f} (t {be[1] / sse[1]:+.2f}), "
          f"past120 {be[2]:+.3f} (t {be[2] / sse[2]:+.2f}), month ret {be[3]:+.3f} (t {be[3] / sse[3]:+.2f}), "
          f"vol {be[4]:+.3f} (t {be[4] / sse[4]:+.2f})")
    print("by year (non-Kraken equal weight, %/month):",
          E.groupby(E.index.str[:4]).ret.mean().round(2).to_dict())
    # Quartiles of the past-120-day return
    E["q"] = pd.qcut(E.btc_past120, 4, labels=["Q1 (fallen most)", "Q2", "Q3", "Q4 (risen most)"])
    print("by BTC past-120-day return quartile (%/month):", E.groupby("q", observed=True).ret.mean().round(2).to_dict())
    E["vq"] = pd.qcut(E.btc_vol, 4, labels=["calmest", "V2", "V3", "most volatile"])
    print("by the month's BTC volatility quartile (%/month):", E.groupby("vq", observed=True).ret.mean().round(2).to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
