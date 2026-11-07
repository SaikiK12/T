"""vpin_v1 (R291): does VPIN, the order-flow toxicity measure of Easley, López de Prado and O'Hara, forecast the
realized volatility of the BTC, ETH and SOL perps beyond volume and past volatility? As set out in
experiments/vpin_v1/PREREG.md (M085, from the owner's reel on order-flow toxicity).

Binance 1-minute bars carry the taker-buy volume, so VPIN is built from the exchange's own trade sides ("exact") and,
as the contrast, from bulk volume classification ("bvc"), which guesses the sides from each bar's price change.
Andersen and Bondarenko found that with exact sides VPIN adds nothing beyond volume and volatility; this is their
test in crypto. No trades: a forecast comparison fitted on 2021-04..2023 and read out of sample on 2024-01..2026-09.

usage: python scripts/run_vpin.py
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, orderflow, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "vpin_v1"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
MIN, HOUR, DAY = 60_000, 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
PER_DAY, N = 50, 50                  # buckets per average day of volume; buckets in the VPIN window
SIZE_DAYS, SIZE_NEED, DAY_BARS = 30, 20, 1200
SIG_BARS, HOUR_BARS = 1000, 50
STALE = 1440                         # VPIN is missing when its last bucket filled more than a day ago
LAGS = {1: 24, 24: 48}               # horizon (hours) -> Newey-West lag (hours)
KINDS = ("exact", "bvc")
TRIALS = len(KINDS) * len(LAGS)      # 4
T_MIN, MSE_MIN = 2.0, 0.01
CRASH_K, CRASH_LOOK, CRASH_NEED = 4.0, 720, 600
BASE = ["lrv_h", "lrv_d", "lrv_w", "lrelv_h", "lrelv_d"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------------------ bars
def load_bars(path, t0=T0, t1=T1):
    """Close, volume, quote volume and taker-buy volume of the bar opening at t0 + i minutes, NaN where the bar is
    missing or invalid (count 0 or close <= 0)."""
    k = pd.read_parquet(path, columns=["t", "close", "volume", "quote_volume", "taker_buy_volume", "count"])
    k = k[(k.t >= t0) & (k.t < t1)].drop_duplicates("t")
    k = k[(k["count"] > 0) & (k.close > 0)]
    n = (t1 - t0) // MIN
    i = ((k.t.values - t0) // MIN).astype(np.int64)
    out = {}
    for c in ("close", "volume", "quote_volume", "taker_buy_volume"):
        a = np.full(n, np.nan)
        a[i] = k[c].values
        out[c] = a
    return out


def bucket_size(V):
    """Per bar: the mean volume of the previous SIZE_DAYS UTC days that have at least DAY_BARS valid bars (at least
    SIZE_NEED such days), over PER_DAY. NaN until then."""
    d = V.reshape(-1, 1440)
    tot = np.where(np.isfinite(d).sum(1) >= DAY_BARS, np.nansum(d, 1), np.nan)
    s = pd.Series(tot).shift(1).rolling(SIZE_DAYS, min_periods=SIZE_NEED).mean().values / PER_DAY
    return np.repeat(s, 1440)


def day_sigma(r):
    """Per bar: the standard deviation of 1-minute log returns over the previous UTC day (at least SIG_BARS)."""
    d = r.reshape(-1, 1440)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        sd = np.where(np.isfinite(d).sum(1) >= SIG_BARS, np.nanstd(d, axis=1, ddof=1), np.nan)
    return np.repeat(pd.Series(sd).shift(1).values, 1440)


def buys(bars):
    """Taker-buy volume per bar: exact (Binance's) and BVC (from the price change, neutral where it is unknown)."""
    C, V = bars["close"], bars["volume"]
    r = np.r_[np.nan, np.log(C[1:] / C[:-1])]
    bvc = orderflow.bvc_buy(V, r, day_sigma(r))
    bvc = np.where(np.isfinite(bvc), bvc, V / 2)
    return {"exact": bars["taker_buy_volume"], "bvc": bvc}, r


def vpin_at_hours(V, B, size, nh):
    """VPIN known at each hour boundary h (time t0 + h hours): the value of the last bucket that filled in a bar
    before h * 60, NaN if none filled within the previous STALE bars."""
    end, share = orderflow.volume_buckets(V, B, size)
    vp = orderflow.vpin(share, N)
    last = np.arange(nh) * 60 - 1
    j = np.searchsorted(end, last, side="right") - 1
    jj = np.clip(j, 0, None)
    fresh = (j >= 0) & (end[jj] >= last - STALE + 1) if len(end) else np.zeros(nh, bool)
    return np.where(fresh, vp[jj] if len(vp) else np.nan, np.nan)


# ---------------------------------------------------------------------------------------------------------- hourly
def _log(x):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(np.where(x > 0, x, np.nan))


def hourly(bars, t0=T0):
    """One row per hour h. Targets: realized variance of hour h (y1) and the mean over hours h..h+23 (y24).
    Features use only bars before hour h: last hour's, last day's and last week's realized variance; last hour's and
    last day's quote volume relative to the previous 30 days; VPIN (exact and BVC) at the boundary; hour and
    weekend. The hourly return and its trailing standard deviation feed the crash table (reported only)."""
    B, r = buys(bars)
    V, Q, C = bars["volume"], bars["quote_volume"], bars["close"]
    nh = len(C) // 60
    R = r[: nh * 60].reshape(nh, 60)
    n_ok = np.isfinite(R).sum(1)
    rv = np.where(n_ok >= HOUR_BARS, np.nansum(R ** 2, 1) * 60 / np.maximum(n_ok, 1), np.nan)
    q = Q[: nh * 60].reshape(nh, 60)
    qv = np.where(np.isfinite(q).sum(1) >= HOUR_BARS, np.nansum(q, 1), np.nan)
    s, qs = pd.Series(rv), pd.Series(qv)
    ref = qs.rolling(720, min_periods=600).mean().shift(1)
    f = pd.DataFrame({"h": np.arange(nh), "t": t0 + np.arange(nh) * HOUR})
    f["lrv_h"] = _log(s.shift(1).values)
    f["lrv_d"] = _log(s.rolling(24, min_periods=20).mean().shift(1).values)
    f["lrv_w"] = _log(s.rolling(168, min_periods=140).mean().shift(1).values)
    f["lrelv_h"] = _log((qs.shift(1) / ref).values)
    f["lrelv_d"] = _log((qs.rolling(24, min_periods=20).mean().shift(1) / ref).values)
    size = bucket_size(V)
    for k in KINDS:
        f[f"vpin_{k}"] = vpin_at_hours(V, B[k], size, nh)
    f["y1"] = _log(rv)
    y24 = s[::-1].rolling(24, min_periods=20).mean()[::-1].values.copy()
    y24[nh - 23:] = np.nan                                       # the window must lie inside the data
    f["y24"] = _log(y24)
    ts = pd.to_datetime(f.t, unit="ms")
    f["hod"] = ts.dt.hour.values
    f["wkend"] = (ts.dt.dayofweek >= 5).astype(float).values
    ch = C[: nh * 60].reshape(nh, 60)[:, -1]
    hr = np.r_[np.nan, np.log(ch[1:] / ch[:-1])]
    f["hret"] = hr
    f["hsd"] = pd.Series(hr).rolling(CRASH_LOOK, min_periods=CRASH_NEED).std().shift(1).values
    return f


def window_of(t, horizon):
    """'disc', 'valid' or '' per row: every target hour must lie inside the window."""
    out = np.full(len(t), "", dtype=object)
    for name, (a, b) in (("disc", DISC), ("valid", VALID)):
        lo = pd.Timestamp(a, tz="UTC").value // 10**6
        hi = pd.Timestamp(b, tz="UTC").value // 10**6 + DAY
        out[(t >= lo) & (t + horizon * HOUR <= hi)] = name
    return out


# ------------------------------------------------------------------------------------------------------- inference
def design(f, kind=None):
    cols = [np.ones(len(f))] + [f[c].values for c in BASE]
    cols += [(f.hod.values == k).astype(float) for k in range(1, 24)] + [f.wkend.values]
    if kind:
        cols.append(f[f"vpin_{kind}"].values)
    return np.column_stack(cols)


def ols(X, y, m):
    beta = np.linalg.lstsq(X[m], y[m], rcond=None)[0]
    return beta, y - X @ beta


def hac_se(X, e, m, lag):
    """Coefficient standard errors, Newey-West (Bartlett); rows outside `m` count as zero, so lags are in
    calendar hours."""
    U = np.where(m[:, None], X * np.nan_to_num(e)[:, None], 0.0)
    A = np.linalg.inv(X[m].T @ X[m])
    S = U.T @ U
    for l in range(1, lag + 1):
        G = U[l:].T @ U[:-l]
        S += (1 - l / (lag + 1)) * (G + G.T)
    return np.sqrt(np.clip(np.diag(A @ S @ A), 0, None))


def evaluate(frames, horizon, kinds=KINDS):
    """Per coin: fit base and base + VPIN on discovery, forecast validation, and compare squared errors of log RV on
    the same rows. Pooled: the mean loss differential per hour across coins, Newey-West t (Diebold-Mariano)."""
    lag = LAGS[horizon]
    y_col = f"y{horizon}"
    per, d = {}, {k: [] for k in kinds}
    sse = {k: [0.0, 0.0] for k in kinds}
    for coin, f in frames.items():
        w = window_of(f.t.values, horizon)
        X0 = design(f)
        y = f[y_col].values
        good = np.isfinite(y) & np.isfinite(X0).all(1) & np.isfinite(f[[f"vpin_{k}" for k in KINDS]].values).all(1)
        md, mv = good & (w == "disc"), good & (w == "valid")
        b0, e0 = ols(X0, y, md)
        per[coin] = {"rows_disc": int(md.sum()), "rows_valid": int(mv.sum()),
                     "r2_valid_base": float(1 - np.mean(e0[mv] ** 2) / np.var(y[mv]))}
        for k in kinds:
            X1 = design(f, k)
            b1, e1 = ols(X1, y, md)
            se = hac_se(X1, e1, md, lag)
            dd = np.where(mv, e0 ** 2 - e1 ** 2, np.nan)
            n, mu, t = stats.newey_west_t(dd[mv.argmax():], lag) if mv.any() else (0, np.nan, np.nan)
            per[coin][k] = {"coef": float(b1[-1]), "coef_t_disc": float(b1[-1] / se[-1]),
                            "dm_t": float(t), "mse_cut": float(1 - np.sum(e1[mv] ** 2) / np.sum(e0[mv] ** 2)),
                            "r2_valid": float(1 - np.mean(e1[mv] ** 2) / np.var(y[mv]))}
            d[k].append(pd.Series(dd, index=f.h.values))
            sse[k][0] += float(np.sum(e0[mv] ** 2))
            sse[k][1] += float(np.sum(e1[mv] ** 2))
    pooled = {}
    for k in kinds:
        x = pd.concat(d[k], axis=1).mean(axis=1, skipna=True).values
        ok = np.where(np.isfinite(x))[0]
        x = x[ok[0]: ok[-1] + 1] if len(ok) else x
        n, mu, t = stats.newey_west_t(x, lag)
        pooled[k] = {"dm_t": float(t), "mse_cut": 1 - sse[k][1] / sse[k][0] if sse[k][0] else float("nan"),
                     "coef_positive_all": bool(all(per[c][k]["coef"] > 0 for c in frames))}
    return {"per_coin": per, "pooled": pooled}


def informative(p):
    return bool(p["coef_positive_all"] and p["dm_t"] >= T_MIN and p["mse_cut"] >= MSE_MIN)


def correlations(frames):
    out = {}
    for coin, f in frames.items():
        m = (window_of(f.t.values, 1) == "disc")
        g = f.loc[m, ["vpin_exact", "vpin_bvc", "lrelv_d", "lrv_d", "lrv_h"]].dropna()
        c = g.corr()
        out[coin] = {"exact~relvol_d": c.loc["vpin_exact", "lrelv_d"], "exact~rv_d": c.loc["vpin_exact", "lrv_d"],
                     "bvc~relvol_d": c.loc["vpin_bvc", "lrelv_d"], "bvc~rv_d": c.loc["vpin_bvc", "lrv_d"],
                     "exact~bvc": c.loc["vpin_exact", "vpin_bvc"], "mean_exact": float(g.vpin_exact.mean()),
                     "mean_bvc": float(g.vpin_bvc.mean())}
    return {k: {a: round(float(b), 4) for a, b in v.items()} for k, v in out.items()}


def crash_table(frames, col):
    """Share of hours whose |return| exceeds CRASH_K trailing standard deviations, by decile of `col` known at the
    hour's start; decile edges from each coin's discovery rows. Pooled counts over coins."""
    rows = {w: np.zeros((10, 2)) for w in ("disc", "valid")}
    for f in frames.values():
        w = window_of(f.t.values, 1)
        x = f[col].values
        ev = np.abs(f.hret.values) > CRASH_K * f.hsd.values
        ok = np.isfinite(x) & np.isfinite(f.hret.values) & np.isfinite(f.hsd.values)
        edges = np.nanquantile(x[ok & (w == "disc")], np.linspace(0.1, 0.9, 9))
        dec = np.searchsorted(edges, x, side="right")
        for name in rows:
            m = ok & (w == name)
            np.add.at(rows[name], (dec[m], 0), 1)
            np.add.at(rows[name], (dec[m], 1), ev[m].astype(float))
    return {name: {"hours": a[:, 0].astype(int).tolist(),
                   "events": a[:, 1].astype(int).tolist(),
                   "rate_pct": np.round(100 * a[:, 1] / np.maximum(a[:, 0], 1), 3).tolist()}
            for name, a in rows.items()}


def analyze(frames):
    res = {f"h{h}": evaluate(frames, h) for h in LAGS}
    primary = res["h1"]["pooled"]["exact"]
    verdicts = {f"{k}_h{h}": informative(res[f"h{h}"]["pooled"][k]) for k in KINDS for h in LAGS}
    return {"primary": "exact_h1", "informative": informative(primary), "variants_informative": verdicts,
            "forecast": res, "correlations_disc": correlations(frames),
            "crash_by_vpin_exact_decile": crash_table(frames, "vpin_exact"),
            "crash_by_relvol_decile": crash_table(frames, "lrelv_d")}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    frames = {}
    for sym in COINS:
        frames[sym] = hourly(load_bars(data.ROOT / "klines_1m" / f"{sym}.parquet"))
        f = frames[sym]
        log(f"{sym}: {len(f)} hours, vpin exact {np.isfinite(f.vpin_exact).sum()}, bvc {np.isfinite(f.vpin_bvc).sum()}")
    res = analyze(frames)
    for h in LAGS:
        for k in KINDS:
            p = res["forecast"][f"h{h}"]["pooled"][k]
            log(f"h{h} {k}: DM t {p['dm_t']:.2f}, MSE cut {100 * p['mse_cut']:.2f}%, coef>0 all "
                f"{p['coef_positive_all']}; " + ", ".join(
                    f"{c} b {v[k]['coef']:+.3f} (t {v[k]['coef_t_disc']:.1f})"
                    for c, v in res["forecast"][f"h{h}"]["per_coin"].items()))
    verdict = "PARTIAL" if res["informative"] else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    keep = ["t", "lrv_h", "lrv_d", "lrelv_d", "vpin_exact", "vpin_bvc", "y1", "y24"]
    pd.concat([f[keep].assign(coin=c) for c, f in frames.items()]).to_csv(
        out / "hourly.csv.gz", index=False, float_format="%.6g")
    summary = {"rid": "R291", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **res}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}: exact VPIN at 1 h is {'informative' if res['informative'] else 'not informative'}")
    return summary


if __name__ == "__main__":
    main()
