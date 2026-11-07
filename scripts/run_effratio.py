"""er_v1 (R293): can tomorrow's efficiency ratio be forecast, and does skipping predicted chop days improve a trend
rule? As set out in experiments/er_v1/PREREG.md (M314, from the owner's reel DeF5_5yPtDb).

The efficiency ratio (Kaufman) of a UTC day is |net move| / distance travelled over its 5-minute closes: near 1 when
price went one way, near 0 when it chopped. The reel fits a logistic regression on 15 measurements of recent price
behaviour to forecast whether the next day is efficient, and skips its NQ strategy's trades on predicted chop days.
Here: the same 15 measurements on the BTC, ETH and SOL perps, a pooled logistic regression fitted on 2021-04..2023
and read on 2024-01..2026-09, and the gate applied to one fixed trend rule (follow the first UTC hour's move until the
day's close).

usage: python scripts/run_effratio.py
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
from lab import data, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs, funding_paid, load_funding  # noqa: E402
from scripts.run_vpin import load_bars  # noqa: E402

LANE = ROOT / "experiments" / "er_v1"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
MIN, DAY = 60_000, 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HALVES = (("2024-01-01", "2025-06-30"), ("2025-07-01", "2026-09-30"))
STEP, NEED_STEPS = 5, 270            # 5-minute path; a day needs 270 of its 288 steps
CHOP_LOOK, CHOP_NEED = 100, 60       # chop: ER below its trailing median (days up to and including that day)
COST, API = 3e-4, 8.5e-4             # per side: manual web at 1x; MEXC API reported
RIDGE = 1e-3
B, BLOCK, SEED = 2000, 10, 293
AUC_MIN, P_GATE = 0.53, 0.5
FEATURES = ["rv", "er", "er20", "vr", "fbreak", "d50",                       # what the market just did
            "chop_run", "er5", "er10", "er_mean20", "er_1", "er_2", "dvol", "chop5", "chop10"]   # lately
BASELINE = ["er", "er_mean20"]
TRIALS = 3                           # predictability, the ungated rule, the gated rule
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------------------ daily
def _ratio(num, den):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def daily(C, t0=T0):
    """One row per UTC day from 1-minute closes C (NaN where missing): the efficiency ratio of the 5-minute path
    (start = the close at 00:00), realized volatility, the day's close, path high and low, and the trend rule's
    prices: P(00:00), P(01:00) and the entry P(01:01), exit P(24:00)."""
    nd = len(C) // 1440
    M = C[: nd * 1440].reshape(nd, 1440)
    start = np.r_[np.nan, M[:-1, -1]]
    path = np.column_stack([start, M[:, STEP - 1::STEP]])
    with np.errstate(invalid="ignore", divide="ignore"):
        r = np.diff(np.log(path), axis=1)
    n = np.isfinite(r).sum(1)
    ok = n >= NEED_STEPS
    d = pd.DataFrame({"t": t0 + np.arange(nd) * DAY})
    d["er"] = np.where(ok, _ratio(np.abs(np.nansum(r, 1)), np.nansum(np.abs(r), 1)), np.nan)
    d["rv"] = np.where(ok, np.sqrt(np.nansum(r ** 2, 1) * 288 / np.maximum(n, 1)), np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        d["hi"] = np.where(ok, np.nanmax(path, 1), np.nan)
        d["lo"] = np.where(ok, np.nanmin(path, 1), np.nan)
    d["close"] = M[:, -1]
    d["p0"], d["p1"], d["entry"], d["exit"] = start, M[:, 59], M[:, 60], M[:, -1]
    return d


def features(d):
    """The reel's 15 measurements, each known at the close of day d (rows), and the target: day d+1's ER."""
    er, rv, c = d.er, d.rv, d.close
    lr = np.log(c / c.shift(1))
    absr = lr.abs()
    f = pd.DataFrame({"t": d.t})
    f["rv"] = np.log(rv)
    f["er"] = er
    for k in (5, 10, 20):
        f[f"er{k}"] = _ratio(np.abs(np.log(c / c.shift(k))).values, absr.rolling(k, min_periods=k).sum().values)
    r5 = np.log(c / c.shift(5))
    f["vr"] = _ratio(r5.rolling(60, min_periods=50).var().values, 5 * lr.rolling(60, min_periods=50).var().values)
    ph, pl = d.hi.shift(1), d.lo.shift(1)
    brk = (d.hi > ph) | (d.lo < pl)
    inside = (c >= pl) & (c <= ph)
    fb = (brk & inside).astype(float).where(ph.notna() & d.hi.notna())
    f["fbreak"] = fb.rolling(20, min_periods=15).mean()
    f["d50"] = np.log(c / c.rolling(50, min_periods=45).mean())
    med = er.rolling(CHOP_LOOK, min_periods=CHOP_NEED).median()
    chop = (er < med).astype(float).where(er.notna() & med.notna())
    run = np.zeros(len(chop))
    for i, v in enumerate(chop.values):
        run[i] = (run[i - 1] + 1 if i and np.isfinite(run[i - 1]) else 1) if v == 1 else (0 if v == 0 else np.nan)
    f["chop_run"] = run
    f["er_mean20"] = er.rolling(20, min_periods=15).mean()
    f["er_1"], f["er_2"] = er.shift(1), er.shift(2)
    f["dvol"] = np.log(rv) - np.log(rv.rolling(20, min_periods=15).mean())
    f["chop5"] = chop.rolling(5, min_periods=4).mean()
    f["chop10"] = chop.rolling(10, min_periods=8).mean()
    f["er_next"] = er.shift(-1)
    f["t_next"] = d.t + DAY
    return f


def window_of(t):
    out = np.full(len(t), "", dtype=object)
    for name, (a, b) in (("disc", DISC), ("valid", VALID)):
        lo = pd.Timestamp(a, tz="UTC").value // 10**6
        hi = pd.Timestamp(b, tz="UTC").value // 10**6 + DAY
        out[(t >= lo) & (t < hi)] = name
    return out


# ------------------------------------------------------------------------------------------------------------ model
def logit_fit(X, y, ridge=RIDGE, iters=50):
    """Logistic regression by Newton steps with a small ridge on the slopes (not the intercept)."""
    X1 = np.column_stack([np.ones(len(X)), X])
    w = np.zeros(X1.shape[1])
    R = ridge * len(X) * np.eye(X1.shape[1])
    R[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X1 @ w))
        g = X1.T @ (p - y) + R @ w
        H = (X1 * (p * (1 - p))[:, None]).T @ X1 + R
        step = np.linalg.solve(H, g)
        w -= step
        if np.max(np.abs(step)) < 1e-10:
            break
    return w


def logit_predict(w, X):
    return 1 / (1 + np.exp(-(w[0] + X @ w[1:])))


def auc(score, y):
    """Mann-Whitney AUC, ties averaged."""
    score, y = np.asarray(score, float), np.asarray(y, bool)
    n1, n0 = y.sum(), (~y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    rk = pd.Series(score).rank().values
    return float((rk[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def block_auc_ci(score, y, day, rng, B=B, block=BLOCK):
    """2.5% and 97.5% quantiles of the AUC over a block bootstrap of days (coins on a day move together)."""
    days = np.unique(day)
    pos = {v: i for i, v in enumerate(days)}
    di = np.array([pos[v] for v in day])
    rows = [np.where(di == i)[0] for i in range(len(days))]
    n = len(days)
    out = []
    for _ in range(B):
        starts = rng.integers(0, n, size=n // block + 1)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n] % n
        sel = np.concatenate([rows[i] for i in idx])
        out.append(auc(score[sel], y[sel]))
    return [float(np.nanquantile(out, 0.025)), float(np.nanquantile(out, 0.975))]


# ------------------------------------------------------------------------------------------------------------- book
def rule_trades(d, F, rate):
    """Follow the first UTC hour: side = sign of P(01:00) / P(00:00) - 1, entry P(01:01), exit P(24:00)."""
    side = np.sign(d.p1.values - d.p0.values)
    e, x = d.entry.values, d.exit.values
    ok = np.isfinite(e) & np.isfinite(x) & (side != 0) & np.isfinite(side)
    t_in, t_out = d.t.values + 61 * MIN, d.t.values + DAY
    fund = np.where(ok, funding_paid(F, rate, np.where(ok, side, 0), t_in, t_out), 0.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        gross = np.where(ok, side * (x / e - 1), np.nan)
    return pd.DataFrame({"t": d.t.values, "traded": ok, "gross": gross, "funding": fund})


def book(trades, take):
    """Daily book over coins (each a third of capital): gross, funding and trade count per day for the trades in
    `take` (dict coin -> bool per day)."""
    g = sum(np.where(take[c] & tr.traded.values, tr.gross.values, 0.0) for c, tr in trades.items()) / 3
    f = sum(np.where(take[c] & tr.traded.values, tr.funding.values, 0.0) for c, tr in trades.items()) / 3
    n = sum((take[c] & tr.traded.values).astype(float) for c, tr in trades.items())
    t = next(iter(trades.values())).t.values
    return pd.DataFrame({"t": t, "gross": g, "funding": f, "n": n})


def net(b, c):
    return (b.gross - b.funding - 2 * c * b.n / 3).values


def book_stats(b):
    out = {}
    for name, (a, z) in (("disc", DISC), ("valid", VALID), ("valid_h1", HALVES[0]), ("valid_h2", HALVES[1])):
        lo = pd.Timestamp(a, tz="UTC").value // 10**6
        hi = pd.Timestamp(z, tz="UTC").value // 10**6 + DAY
        m = (b.t.values >= lo) & (b.t.values < hi)
        x1 = net(b, COST)[m]
        trades = float(b.n.values[m].sum())
        out[name] = {"days": int(m.sum()), "trades": int(trades),
                     "gross_bp_per_trade": float(3 * b.gross.values[m].sum() / trades * 1e4) if trades else None,
                     "net_bp_day": {k: float(net(b, c)[m].mean() * 1e4)
                                    for k, c in (("1x", COST), ("2x", 2 * COST), ("3x", 3 * COST), ("api", API))},
                     "nw_t_1x": float(stats.newey_west_t(x1, 10)[2])}
    return out


# ---------------------------------------------------------------------------------------------------------- analyze
def analyze(dailies, fundings, seed=SEED):
    feats = {c: features(d) for c, d in dailies.items()}
    rows = []
    for c, f in feats.items():
        g = f.copy()
        g["coin"] = c
        g["win"] = window_of(g.t_next.values)
        rows.append(g)
    A = pd.concat(rows, ignore_index=True)
    good = A[FEATURES + ["er_next"]].notna().all(axis=1).values & np.isfinite(A[FEATURES].values).all(axis=1)
    disc = good & (A.win.values == "disc")
    valid = good & (A.win.values == "valid")
    med = {c: float(A.loc[disc & (A.coin.values == c), "er_next"].median()) for c in dailies}
    y = (A.er_next.values > A.coin.map(med).values).astype(float)
    Z = np.full((len(A), len(FEATURES)), np.nan)
    for c in dailies:
        m = A.coin.values == c
        mu = A.loc[disc & m, FEATURES].mean().values
        sd = A.loc[disc & m, FEATURES].std().values
        Z[m] = (A.loc[m, FEATURES].values - mu) / np.where(sd > 0, sd, 1)
    w = logit_fit(Z[disc], y[disc])
    p = logit_predict(w, np.nan_to_num(Z))
    bi = [FEATURES.index(k) for k in BASELINE]
    wb = logit_fit(Z[disc][:, bi], y[disc])
    pb = logit_predict(wb, np.nan_to_num(Z[:, bi]))
    rng = np.random.default_rng(seed)
    pred = {"auc_disc": auc(p[disc], y[disc]), "auc_valid": auc(p[valid], y[valid]),
            "auc_valid_ci": block_auc_ci(p[valid], y[valid], A.t_next.values[valid], rng),
            "auc_valid_baseline": auc(pb[valid], y[valid]),
            "auc_valid_by_coin": {c: auc(p[valid & (A.coin.values == c)], y[valid & (A.coin.values == c)])
                                  for c in dailies},
            "base_rate_valid": float(y[valid].mean()), "median_er_disc": med,
            "weights": dict(zip(["const"] + FEATURES, np.round(w, 4).tolist())),
            "rows_disc": int(disc.sum()), "rows_valid": int(valid.sum())}
    pred["predictable"] = bool(pred["auc_valid"] >= AUC_MIN and pred["auc_valid_ci"][0] > 0.5)

    trades = {c: rule_trades(dailies[c], *fundings[c]) for c in dailies}
    take_all, take_gate, terc, fc = {}, {}, {}, {}
    cuts = np.quantile(p[disc], [1 / 3, 2 / 3])
    for c, tr in trades.items():
        m = A.coin.values == c
        pc = pd.Series(np.where(good[m], p[m], np.nan), index=A.t_next.values[m])
        pt = pc.reindex(tr.t.values).values                 # forecast made at the previous day's close
        fc[c] = pt
        take_all[c] = np.ones(len(tr), bool)
        take_gate[c] = np.isfinite(pt) & (pt > P_GATE)
        terc[c] = np.where(np.isfinite(pt), np.searchsorted(cuts, pt), -1)
    b_all, b_gate = book(trades, take_all), book(trades, take_gate)
    s_all, s_gate = book_stats(b_all), book_stats(b_gate)
    tradeable = lambda s: bool(s["valid"]["nw_t_1x"] >= 2.0 and s["valid"]["net_bp_day"]["2x"] > 0
                               and s["valid_h1"]["net_bp_day"]["1x"] > 0 and s["valid_h2"]["net_bp_day"]["1x"] > 0)
    g_gate, g_all = s_gate["valid"]["gross_bp_per_trade"], s_all["valid"]["gross_bp_per_trade"]
    lift = g_gate - g_all if g_gate is not None and g_all is not None else None
    gate_pass = bool(pred["predictable"] and tradeable(s_gate) and lift is not None and lift > 0)
    rule_pass = tradeable(s_all)
    by_tercile = {}
    for k, name in enumerate(("low", "mid", "high")):
        for wname in ("disc", "valid"):
            g, n = 0.0, 0
            for c, tr in trades.items():
                m = (terc[c] == k) & tr.traded.values & (window_of(tr.t.values) == wname)
                g += float(tr.gross.values[m].sum())
                n += int(m.sum())
            by_tercile[f"{name}_{wname}"] = {"trades": n, "gross_bp_per_trade": g / n * 1e4 if n else None}
    return {"prediction": pred, "rule_ungated": s_all, "rule_gated": s_gate, "gross_by_forecast_tercile": by_tercile,
            "gate_lift_bp_per_trade_valid": lift, "gate_pass": gate_pass, "rule_pass": rule_pass, "books": {"ungated": b_all, "gated": b_gate}, "forecast": fc}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    dailies, fundings = {}, {}
    for sym in COINS:
        dailies[sym] = daily(load_bars(data.ROOT / "klines_1m" / f"{sym}.parquet")["close"])
        fundings[sym] = load_funding(data.ROOT / "fundingRate" / f"{sym}.parquet")
        log(f"{sym}: {len(dailies[sym])} days, ER defined {int(dailies[sym].er.notna().sum())}")
    res = analyze(dailies, fundings)
    p = res["prediction"]
    log(f"prediction: AUC disc {p['auc_disc']:.4f}, valid {p['auc_valid']:.4f} CI {p['auc_valid_ci']}, baseline "
        f"{p['auc_valid_baseline']:.4f}; predictable {p['predictable']}")
    for k in ("rule_ungated", "rule_gated"):
        v = res[k]["valid"]
        log(f"{k}: valid {v['trades']} trades, gross {v['gross_bp_per_trade']} bp/trade, net 1x/2x/3x "
            f"{[round(v['net_bp_day'][c], 2) for c in ('1x', '2x', '3x')]} bp/day, t {v['nw_t_1x']:.2f}")
    verdict = "PARTIAL" if res["gate_pass"] or res["rule_pass"] else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"t": res["books"]["ungated"].t, "ungated_net1": net(res["books"]["ungated"], COST),
                  "gated_net1": net(res["books"]["gated"], COST),
                  **{f"p_{c}": v for c, v in res["forecast"].items()}}).to_csv(out / "daily.csv", index=False,
                                                                                float_format="%.8g")
    summary = {"rid": "R293", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               **{k: v for k, v in res.items() if k not in ("books", "forecast")}}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}")
    return summary


if __name__ == "__main__":
    main()
