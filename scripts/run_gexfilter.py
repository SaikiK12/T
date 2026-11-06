"""R416 gexfilter_v1: does the S&P 500 dealer gamma exposure (SqueezeMetrics' free daily GEX) known after the US close
predict BTC and ETH volatility over the next US session, beyond VIX and the coins' own recent volatility? As set out in
experiments/gexfilter_v1/PREREG.md. A volatility or risk filter, not a trade.

Inputs, read locally:
- data/squeezemetrics/DIX_20261106.csv (date, price, dix, gex), from squeezemetrics.com/monitor/static/DIX.csv;
- data/klines_1h/<COIN>USDT.parquet, Binance USD-M hourly bars, read from 2021-01-01 only;
- data/cboe/VIX.parquet, the VIX daily close.

For each US trading day d with a next trading day d':
- the window W = [d' 12:00 UTC, d' + 1 day 12:00 UTC); y = log realized volatility over W (24 hourly log returns);
- controls known at the start of W: log RV over the 24 h before it, log RV over the 7 days before it (per day), and
  log VIX at d's close;
- signal: the rank of GEX(d) among the 252 GEX values ending at d (a fraction in (0, 1]).
y = a + b1 x1 + b2 x2 + b3 x3 + c rank, OLS with Newey-West (lag 10) standard errors.

usage: python scripts/run_gexfilter.py [--plumbing]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "gexfilter_v1"
GEX = ROOT / "data" / "squeezemetrics" / "DIX_20261106.csv"
KL = ROOT / "data" / "klines_1h"
VIX = ROOT / "data" / "cboe" / "VIX.parquet"
COINS = ("BTC", "ETH")
FIRST_MS = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)     # 2020 is reserved: never read
START, SPLIT, END = "2021-01-08", "2025-07-01", "2026-10-01"           # d' windows: IS [START, SPLIT), HOLD [SPLIT, END)
RANK_N = 252
MIN_BARS = 22
NW = 10
BAR_IS, BAR_HOLD = -2.5, -2.0
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def hourly(coin):
    t = pq.read_table(KL / f"{coin}USDT.parquet", columns=["t", "close"], filters=[("t", ">=", FIRST_MS)]).to_pandas()
    s = pd.Series(t.close.to_numpy(float), index=pd.to_datetime(t.t, unit="ms", utc=True)).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return np.log(s).diff().dropna()                                      # r at bar open t: close(t) / close(t - 1h)


def rv(r, start, hours):
    """sqrt(sum r^2) over the hourly returns whose bar opens in [start, start + hours); NaN with too few bars."""
    x = r.loc[start:start + pd.Timedelta(hours=hours) - pd.Timedelta(seconds=1)]
    need = MIN_BARS * hours / 24
    return float(np.sqrt((x ** 2).sum())) if len(x) >= need else np.nan


def gex_frame(path=GEX, vix_path=VIX):
    g = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    g["rank"] = g.gex.rolling(RANK_N).apply(lambda w: (w <= w[-1]).mean(), raw=True)
    g["rank_lag"] = g["rank"].shift(1)                                    # sensitivity: one more trading day of lag
    g["next"] = g.date.shift(-1)
    g["spx_next_abs"] = np.log(g.price).diff().shift(-1).abs()           # SPX self-check: |log return| on d'
    v = pd.read_parquet(vix_path, columns=["day", "close"])
    v["day"] = pd.to_datetime(v.day)
    g = g.merge(v.rename(columns={"day": "date", "close": "vix"}), on="date", how="left")
    return g.dropna(subset=["next"])


def rows(coin, g):
    r = hourly(coin)
    out = []
    for _, x in g.iterrows():
        w0 = pd.Timestamp(x.next).tz_localize("UTC") + pd.Timedelta(hours=12)
        out.append({"d": x.date, "d1": x.next, "y": rv(r, w0, 24), "x1": rv(r, w0 - pd.Timedelta(hours=24), 24),
                    "x2": rv(r, w0 - pd.Timedelta(hours=168), 168) / np.sqrt(7), "vix": x.vix, "rank": x["rank"],
                    "rank_lag": x.rank_lag, "neg": float(x.gex < 0), "gex": x.gex, "spx_next_abs": x.spx_next_abs,
                    "ret": float(r.loc[w0:w0 + pd.Timedelta(hours=24) - pd.Timedelta(seconds=1)].sum())})
    d = pd.DataFrame(out)
    for c in ("y", "x1", "x2", "vix"):
        d["l" + c] = np.log(d[c])
    return d


def ols_nw(y, X, lag=NW):
    """OLS coefficients and Newey-West (Bartlett, lag) t statistics, rows in time order."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, min(lag, n - 1) + 1):
        G = u[l:].T @ u[:-l]
        S += (1 - l / (lag + 1)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return b, b / np.sqrt(np.diag(V)), float(r2)


def fit(d, signal="rank", controls=("lx1", "lx2", "lvix"), y="ly"):
    z = d.dropna(subset=[y, signal, *controls])
    X = np.column_stack([np.ones(len(z)), *[z[c] for c in controls], z[signal]])
    b, t, r2 = ols_nw(z[y], X)
    X0 = X[:, :-1]
    r2_0 = ols_nw(z[y], X0)[2] if X0.shape[1] > 1 else 0.0
    return {"n": int(len(z)), "c": float(b[-1]), "t": float(t[-1]), "r2": r2, "r2_without_signal": r2_0,
            "rv_ratio_rank_0.9_vs_0.1": float(np.exp(b[-1] * 0.8)) if signal.startswith("rank") else None}


def window(d, a, b):
    return d[(d.d1 >= a) & (d.d1 < b)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only")
    a = ap.parse_args()
    if not a.plumbing:
        sha = prereg.verify(LANE / "PREREG.md")
        from scripts.run_clockflow import check_inputs
        log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match")
    g = gex_frame()
    g = g[(g.next >= START) & (g.next < END)]
    data = {c: rows(c, g) for c in COINS}
    if a.plumbing:
        for c, d in data.items():
            for name, (lo, hi) in {"IS": (START, SPLIT), "HOLD": (SPLIT, END)}.items():
                w = window(d, lo, hi)
                ok = w.dropna(subset=["ly", "lx1", "lx2", "lvix", "rank"])
                log(f"{c} {name}: {len(w)} trading days, {len(ok)} complete rows, {int(w.neg.sum())} with GEX < 0, "
                    f"first {w.d1.min().date()} last {w.d1.max().date()}")
        return
    res = {"prereg_sha256": sha, "coins": {}, "decision": {}}
    for c, d in data.items():
        out = {}
        for name, (lo, hi) in {"IS": (START, SPLIT), "HOLD": (SPLIT, END)}.items():
            w = window(d, lo, hi)
            out[name] = {"primary": fit(w),
                         "rank_lag": fit(w, "rank_lag"), "neg_dummy": fit(w, "neg"),
                         "no_vix": fit(w, controls=("lx1", "lx2")),
                         "abs_ret_low_rank_vs_rest": [float(w.ret.abs()[w["rank"] <= 0.2].mean()),
                                                      float(w.ret.abs()[w["rank"] > 0.2].mean())],
                         "spx_self_check": fit(w.assign(ly=np.log(w.spx_next_abs.clip(lower=1e-5))),
                                               controls=("lvix",))}
        checks = {"IS_t_le_-2.5": out["IS"]["primary"]["t"] <= BAR_IS and out["IS"]["primary"]["c"] < 0,
                  "HOLD_t_le_-2.0": out["HOLD"]["primary"]["t"] <= BAR_HOLD and out["HOLD"]["primary"]["c"] < 0}
        res["coins"][c] = out
        res["decision"][c] = {"checks": checks, "verdict": "GEX_FILTER" if all(checks.values()) else "NULL"}
        log(f"{c}: {res['decision'][c]['verdict']} IS c {out['IS']['primary']['c']:+.3f} t {out['IS']['primary']['t']:+.2f}; "
            f"HOLD c {out['HOLD']['primary']['c']:+.3f} t {out['HOLD']['primary']['t']:+.2f}")
        (LANE / "results").mkdir(parents=True, exist_ok=True)
        d.to_csv(LANE / "results" / f"rows_{c}.csv", index=False, float_format="%.6g")
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    log("done")


if __name__ == "__main__":
    main()
