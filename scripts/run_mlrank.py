"""mlrank_v1 (R299): machine-learned cross-sectional rankers on the daily point-in-time panel. As set out in
experiments/mlrank_v1/PREREG.md (M042).

Each month a model is refit on every earlier decision whose target was known before the month began (purged, one day
of embargo), and it ranks the top 150 Binance perps every day of the month. The book is long the top fifth of the
ranking and short the bottom fifth, at API costs with funding.

The family: model {ridge, IC-weighted composite, gradient boosting} x horizon {1 day rebalanced daily, 7 days
rebalanced weekly} x features {point-in-time only, plus the Coin Metrics cap ratios} = 12 books. The best book in
discovery (2022-01..2023-12; 2021 only trains) by net t goes to validation (2024-01..2026-09), once.

Timing: row D of data/daily/panel.parquet is the decision at 00:00 UTC of day D and holds the 24 h that end then.
Features use rows up to D; entry is row D's close; a hold of h days exits at the last close in rows D+1..D+h and pays
the funding settled in those rows. The panel holds no row before 2021-01-02 or after 2026-09-30 (reserved).

usage: python scripts/run_mlrank.py [--plumbing]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_lotcap import costed, series_stats, turnover, weekly_grid  # noqa: E402

LANE = ROOT / "experiments" / "mlrank_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
DAY = 86_400_000
TOP, Q, MIN_NAMES = 150, 5, 30
MODELS = ("ridge", "ic", "gbm")
HOLDS = (1, 7)                                   # days
SETS = ("pit", "all")
STRATS = [(m, h, s) for m in MODELS for h in HOLDS for s in SETS]
TRIALS = len(STRATS)
FIRST_PRED = "2022-01-01"
DISC = ("2022-01-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
WINDOWS = {"disc": DISC, "valid": VALID}
COST = 8.5e-4                                    # API, per side, 1x
T_MIN = 2.0
RIDGE_ALPHA = 0.01                               # times the number of training rows
GBM = dict(learning_rate=0.05, max_iter=200, max_leaf_nodes=15, min_samples_leaf=1000, l2_regularization=1.0,
           early_stopping=False, random_state=299)
SPA_BOOT, SPA_BLOCK, SEED = 2000, 4, 299
PIT = ["rev1", "mom7", "mom30", "mom90", "vol30", "max7", "range7", "illiq30", "qvol_trend", "qvol30", "taker7",
       "tradesize7", "wick30", "fund3", "fund30", "premium", "basis", "spot_share", "oi_chg7", "oi_qvol",
       "top_ls_pos", "ls_acc", "taker_ls7", "fund_gap7", "n_venues", "kimchi7", "age"]
VINTAGE = ["size", "vol_mcap", "oi_mcap"]
FEATURES = {"pit": PIT, "all": PIT + VINTAGE}
GAP_VENUES = ("gate", "mexc", "dydx", "hyperliquid", "kucoin", "kraken")
COLS = ["close", "ret", "range", "qvol", "trades", "taker_buy", "fund", "premium", "basis", "spot_qvol", "wick_up",
        "wick_dn", "oi_usd", "top_ls_pos", "ls_acc", "taker_ls", "n_venues", "upbit_rel", "age_days", "rank_qvol30",
        "mcap_est", *[f"{v}_fund_gap" for v in GAP_VENUES]]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- panel
def wide(df):
    """{column: DataFrame day x perp} on a full calendar of days, so rolling windows count days, not rows."""
    days = pd.date_range(df.day.min(), df.day.max(), freq="D")
    perps = sorted(df.perp.unique())
    df = df.assign(day=pd.to_datetime(df.day))
    out = {}
    for c in COLS:
        if c in df:
            out[c] = df.pivot(index="day", columns="perp", values=c).reindex(index=days, columns=perps)
    return out


def features(w):
    """{name: day x perp} from rows up to each day only (rolling windows end on the row itself)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return _features(w)


def _features(w):
    lr = np.log1p(w["ret"])
    roll = lambda x, n, mp=None: x.rolling(n, min_periods=mp or max(2, int(0.7 * n)))
    q = w["qvol"]
    f = {
        "rev1": lr,
        "mom7": roll(lr, 7).sum(),
        "mom30": roll(lr, 30).sum(),
        "mom90": roll(lr, 90, 60).sum(),
        "vol30": roll(lr, 30).std(),
        "max7": roll(w["ret"], 7).max(),
        "range7": roll(w["range"], 7).mean(),
        "illiq30": np.log(roll(w["ret"].abs() / q.where(q > 0), 30).mean() * 1e6 + 1e-12),
        "qvol_trend": np.log(roll(q, 7).mean() / roll(q, 30).mean()),
        "qvol30": np.log(roll(q, 30).mean()),
        "taker7": roll(w["taker_buy"], 7).mean() - 0.5,
        "tradesize7": np.log(roll(q / w["trades"].where(w["trades"] > 0), 7).mean()),
        "wick30": roll(w["wick_up"] - w["wick_dn"], 30).mean(),
        "fund3": roll(w["fund"].fillna(0.0), 3, 3).sum().where(w["close"].notna()),
        "fund30": roll(w["fund"].fillna(0.0), 30, 30).sum().where(w["close"].notna()),
        "premium": w["premium"],
        "basis": w["basis"],
        "spot_share": np.log(roll(w["spot_qvol"], 7).mean() / roll(q, 7).mean()),
        "oi_chg7": np.log(w["oi_usd"] / w["oi_usd"].shift(7)),
        "oi_qvol": np.log(w["oi_usd"] / roll(q, 7).mean()),
        "top_ls_pos": np.log(w["top_ls_pos"]),
        "ls_acc": np.log(w["ls_acc"]),
        "taker_ls7": roll(np.log(w["taker_ls"]), 7).mean(),
        "fund_gap7": roll(pd.concat([w[f"{v}_fund_gap"] for v in GAP_VENUES if f"{v}_fund_gap" in w]).groupby(
            level=0).mean().reindex(index=w["close"].index, columns=w["close"].columns), 7, 3).sum(),
        "n_venues": w["n_venues"],
        "kimchi7": roll(w["upbit_rel"], 7, 3).mean(),
        # age: NaN for coins already trading at the panel start, so they rank as the oldest (tied)
        "age": np.log1p(w["age_days"]).where(w["age_days"].notna(), 1e9).where(w["close"].notna()),
        "size": np.log(w["mcap_est"]),
        "vol_mcap": np.log(roll(q, 30).mean() / w["mcap_est"]),
        "oi_mcap": np.log(w["oi_usd"] / w["mcap_est"]),
    }
    for k, v in f.items():
        f[k] = v.replace([np.inf, -np.inf], np.nan)
    return f


def targets(w, h):
    """(ret, funding) of a position entered at row D's close and held h days: the exit is the last close in rows
    D+1..D+h (none: return 0), funding is the sum over those rows (paid by longs)."""
    c = w["close"]
    exit_ = c.ffill(limit=h - 1).shift(-h) if h > 1 else c.shift(-1)
    ret = (exit_ / c - 1.0).where(c.notna())
    ret = ret.where(exit_.notna() | c.isna(), 0.0)
    fund = sum(w["fund"].shift(-k).fillna(0.0) for k in range(1, h + 1)).where(c.notna())
    # the last h rows of the panel have no full hold: NaN
    ret.iloc[-h:] = np.nan
    fund.iloc[-h:] = np.nan
    return ret, fund


def universe(w):
    """Row D's top TOP perps by trailing volume, among those that traded on row D."""
    return (w["rank_qvol30"] <= TOP) & w["close"].notna()


def stack(f, names, uni):
    """Long table (day, perp, features ranked across the universe into [-0.5, 0.5], missing -> 0)."""
    u = uni.stack(future_stack=True)
    idx = u[u.fillna(False).astype(bool)].index
    cols = {}
    for n in names:
        x = f[n].where(uni)
        r = x.rank(axis=1, pct=True)
        cnt = x.notna().sum(axis=1)
        # centred: (rank - 1/2n) - 1/2, so a row spans symmetrically around 0
        c = r.sub(0.5 / cnt.where(cnt > 0), axis=0) - 0.5
        cols[n] = c.stack(future_stack=True).reindex(idx).to_numpy()
    return pd.DataFrame(cols, index=idx).fillna(0.0)


def rank_target(y, uni):
    """The forward net return ranked across the universe into [-0.5, 0.5]."""
    x = y.where(uni)
    cnt = x.notna().sum(axis=1)
    return x.rank(axis=1, pct=True).sub(0.5 / cnt.where(cnt > 0), axis=0) - 0.5


# ---------------------------------------------------------------------------------------------------------- models
def fit_predict(model, X_tr, y_tr, X_te, days_tr=None):
    X_tr, X_te = np.asarray(X_tr, float), np.asarray(X_te, float)
    y_tr = np.asarray(y_tr, float)
    if model == "ridge":
        n, k = X_tr.shape
        A = X_tr.T @ X_tr + RIDGE_ALPHA * n * np.eye(k)
        coef = np.linalg.solve(A, X_tr.T @ y_tr)
        return X_te @ coef, coef
    if model == "ic":
        # per-day correlation of each ranked feature with the ranked target, averaged over training days
        d = pd.Series(days_tr)
        ics = []
        for _, idx in d.groupby(d).indices.items():
            if len(idx) < MIN_NAMES:
                continue
            xs, ys = X_tr[idx], y_tr[idx]
            sx, sy = xs.std(axis=0), ys.std()
            if sy == 0:
                continue
            c = ((xs - xs.mean(axis=0)) * (ys - ys.mean())[:, None]).mean(axis=0) / np.where(sx > 0, sx * sy, np.inf)
            ics.append(c)
        w = np.mean(ics, axis=0) if ics else np.zeros(X_tr.shape[1])
        return X_te @ w, w
    if model == "gbm":
        from sklearn.ensemble import HistGradientBoostingRegressor
        m = HistGradientBoostingRegressor(**GBM).fit(X_tr, y_tr)
        return m.predict(X_te), None
    raise ValueError(model)


def month_starts(days, first=FIRST_PRED):
    d = pd.DatetimeIndex(days)
    return [m for m in pd.date_range(first, d.max(), freq="MS")]


def walk_forward(Xl, ylong, model, h, names):
    """Out-of-sample predictions for every day from FIRST_PRED: each month's model sees decisions D with
    D + h + 1 day <= the month's first day (purged; one day of embargo). Returns (pred Series, weights by month)."""
    days = Xl.index.get_level_values(0)
    preds, weights = [], {}
    tr_all = ylong.notna().to_numpy()
    for m0 in month_starts(days.unique()):
        m1 = m0 + pd.offsets.MonthBegin(1)
        tr = tr_all & (days <= m0 - pd.Timedelta(days=h + 1))
        te = (days >= m0) & (days < m1)
        if tr.sum() < 1000 or te.sum() == 0:
            continue
        p, w = fit_predict(model, Xl[names].to_numpy()[tr], ylong.to_numpy()[tr], Xl[names].to_numpy()[te],
                           days_tr=days[tr])
        preds.append(pd.Series(p, index=Xl.index[te]))
        if w is not None:
            weights[str(m0.date())] = [float(v) for v in w]
    return (pd.concat(preds) if preds else pd.Series(dtype=float)), weights


# ----------------------------------------------------------------------------------------------------------- books
def legs(pred, hold, seed=SEED):
    """{day: (longs, shorts)}: the top and bottom fifth (floor(n / Q) each) of the prediction, rebalanced every day
    (hold 1) or every 7th day from the first prediction day (hold 7). Ties break by a seeded random order, never by
    symbol."""
    rng = np.random.default_rng(seed)
    out = {}
    df = pred.rename("p").reset_index()
    df.columns = ["day", "perp", "p"]
    days = np.sort(df.day.unique())
    keep = days if hold == 1 else days[((days - days[0]) // np.timedelta64(1, "D")) % hold == 0]
    for d, g in df[df.day.isin(keep)].groupby("day"):
        n = len(g)
        if n < MIN_NAMES:
            continue
        g = g.assign(tb=rng.random(n)).sort_values(["p", "tb"])
        k = n // Q
        s = g.perp.to_numpy()
        out[pd.Timestamp(d)] = (tuple(s[-k:]), tuple(s[:k]))
    return out


def book(lg, ret, fund):
    """Rows per rebalance: gross = mean long (ret - funding) + mean short (-ret + funding), legs, weights."""
    rows = []
    for d in sorted(lg):
        L, S = lg[d]
        rl, fl = ret.loc[d, list(L)], fund.loc[d, list(L)]
        rs, fs = ret.loc[d, list(S)], fund.loc[d, list(S)]
        okl, oks = rl.notna(), rs.notna()
        if not okl.any() or not oks.any():
            continue
        lg_ret = float((rl[okl] - fl[okl]).mean())
        sh_ret = float((-rs[oks] + fs[oks]).mean())
        rows.append({"t": int(d.value // 10**6), "gross": lg_ret + sh_ret, "long": lg_ret, "short": sh_ret,
                     "n_long": int(okl.sum()), "n_short": int(oks.sum()), "covered": [],
                     "w": {**{s: 1.0 / okl.sum() for s in rl.index[okl]},
                           **{s: -1.0 / oks.sum() for s in rs.index[oks]}}})
    return rows


def window_mask(ts, hold, win):
    """Rebalances decided in the window whose hold ends inside it (row D + hold <= the window's last row)."""
    a, b = WINDOWS[win]
    lo = pd.Timestamp(a).value // 10**6
    hi = pd.Timestamp(b).value // 10**6
    ts = np.asarray(ts, np.int64)
    return (ts >= lo) & (ts + hold * DAY <= hi)


def daily_ic(pred, ylong):
    """Per-day rank correlation of the prediction with the ranked target."""
    df = pd.DataFrame({"p": pred, "y": ylong.reindex(pred.index)}).dropna()
    g = df.groupby(level=0)
    return g.apply(lambda x: x.p.rank().corr(x.y.rank()) if len(x) >= MIN_NAMES else np.nan).dropna()


def report(rows, hold, ic):
    ts = np.array([r["t"] for r in rows], np.int64)
    nets = {k: costed(rows, m * COST) for k, m in (("1x", 1), ("2x", 2), ("3x", 3))}
    gross = np.array([r["gross"] for r in rows])
    turn = turnover(rows)
    ic_ts = np.array([pd.Timestamp(d).value // 10**6 for d in ic.index], np.int64)
    rep = {}
    for w in WINDOWS:
        m = window_mask(ts, hold, w)
        mi = window_mask(ic_ts, hold, w)
        icw = ic.to_numpy()[mi]
        n_ic, ic_mean, ic_t = stats.newey_west_t(icw, max(5, 2 * hold)) if len(icw) > 10 else (len(icw), None, None)
        rep[w] = {"gross": series_stats(gross[m], ts[m], hold * 24),
                  **{k: series_stats(v[m], ts[m], hold * 24) for k, v in nets.items()},
                  "long_bp": float(np.mean([r["long"] for r, k in zip(rows, m) if k]) * 1e4) if m.any() else None,
                  "short_bp": float(np.mean([r["short"] for r, k in zip(rows, m) if k]) * 1e4) if m.any() else None,
                  "names_per_leg": float(np.mean([r["n_short"] for r, k in zip(rows, m) if k])) if m.any() else None,
                  "turnover_per_period": float(turn[m].mean()) if m.any() else None,
                  "rank_ic": {"days": int(n_ic), "mean": None if ic_mean is None else float(ic_mean),
                              "t": None if ic_t is None or not np.isfinite(ic_t) else float(ic_t)}}
    return rep, ts, nets["1x"]


def decide(reports):
    """The discovery pick (highest net 1x t with a positive mean) and its validation verdict."""
    cand = [(k, r["disc"]["1x"]) for k, r in reports.items() if r["disc"]["1x"].get("t") is not None
            and r["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = reports[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": v["2x"].get("mean_bp", -1) > 0,
              "wo_best": v["1x"].get("mean_wo_best_bp", -1) > 0}
    return pick, all(checks.values()), checks


def label(k):
    m, h, s = k
    return f"{m} h{h} {s}"


# ------------------------------------------------------------------------------------------------------------ main
def prepare(df):
    w = wide(df)
    f = features(w)
    uni = universe(w)
    return w, f, uni


def build(df, models=MODELS):
    w, f, uni = prepare(df)
    X = {s: stack(f, FEATURES[s], uni) for s in SETS}
    res, ics, weights = {}, {}, {}
    for h in HOLDS:
        ret, fund = targets(w, h)
        y = rank_target(ret - fund, uni).stack(future_stack=True)
        for s in SETS:
            Xl = X[s]
            yl = y.reindex(Xl.index)
            for m in models:
                log(f"fit {m} h{h} {s}")
                pred, wts = walk_forward(Xl, yl, m, h, FEATURES[s])
                lg = legs(pred, h)
                res[(m, h, s)] = book(lg, ret, fund)
                ics[(m, h, s)] = daily_ic(pred, yl)
                weights[(m, h, s)] = wts
    return res, ics, weights


def analyze(res, ics, weights):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = report(rows, k[1], ics[k])
        series[k] = (ts, net1)
    pick, ok, checks = decide(reports)
    # reported: all minus pit, paired per model and horizon
    paired = {}
    for m, h, s in STRATS:
        if s != "all" or (m, h, "pit") not in series:
            continue
        ta, xa = series[(m, h, "all")]
        tb, xb = series[(m, h, "pit")]
        common, ia, ib = np.intersect1d(ta, tb, return_indices=True)
        d = xa[ia] - xb[ib]
        paired[f"{m} h{h}"] = {w: series_stats(d[mk], common[mk], h * 24) for w in WINDOWS
                               for mk in [window_mask(common, h, w)]}
    # reported: SPA / reality check over the books on a common weekly grid, per window
    spa = {}
    anchors_all = np.sort(np.unique(np.concatenate([series[k][0] for k in series if k[1] == 7])))
    for w in WINDOWS:
        an = anchors_all[window_mask(anchors_all, 7, w)]
        cols = []
        for k in STRATS:
            if k not in series:
                continue
            ts, net = series[k]
            mk = window_mask(ts, k[1], w)
            cols.append(weekly_grid(ts[mk], net[mk], an))
        D = np.column_stack(cols)
        spa[w] = inference.spa(D, n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        spa[w]["best"] = label([k for k in STRATS if k in series][spa[w]["best"]])
        spa[w]["weeks"] = int(len(an))
    # reported: average linear weights per feature (ridge coefficients, IC weights)
    avg_w = {}
    for k, wts in weights.items():
        if wts:
            names = FEATURES[k[2]]
            avg_w[label(k)] = dict(zip(names, np.mean(list(wts.values()), axis=0).round(5).tolist()))
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL",
            "all_minus_pit": paired, "spa": spa, "linear_weights": avg_w}


def load_panel():
    return pd.read_parquet(PANEL, columns=["day", "perp", *COLS])


def plumbing(df):
    """Counts only: days, names in the universe, feature coverage, rebalances per window. No return is read."""
    w = wide(df.drop(columns=["ret"]).assign(ret=np.nan))     # returns blanked: nothing here can read one
    uni = universe(w)
    f = features(w)
    n = uni.sum(axis=1)
    days = n.index
    pred_days = days[days >= pd.Timestamp(FIRST_PRED)]
    out = {"days": int(len(days)), "first": str(days.min().date()), "last": str(days.max().date()),
           "universe_median": float(n.median()), "universe_min_2022on": int(n[pred_days].min()),
           "prediction_months": len(month_starts(days)),
           "coverage_in_universe": {k: round(float(v.where(uni).notna().sum().sum() / uni.sum().sum()), 3)
                                    for k, v in f.items() if k not in ("rev1", "mom7", "mom30", "mom90", "vol30",
                                                                        "max7", "illiq30")}}
    for h in HOLDS:
        reb = pred_days if h == 1 else pred_days[((pred_days - pred_days[0]).days % h) == 0]
        ts = np.array([d.value // 10**6 for d in reb], np.int64)
        out[f"h{h}"] = {w_: int(window_mask(ts, h, w_).sum()) for w_ in WINDOWS}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    df = load_panel()
    if a.plumbing:
        print(json.dumps(plumbing(df), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    res, ics, weights = build(df)
    out = analyze(res, ics, weights)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}; rank IC disc {v['disc']['rank_ic']['mean']} "
            f"valid {v['valid']['rank_ic']['mean']}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "n_long": r["n_long"], "n_short": r["n_short"]} for k, rs in res.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    pd.DataFrame({label(k): v for k, v in ics.items()}).to_csv(res_dir / "rank_ic.csv", float_format="%.5f")
    import sklearn
    summary = {"rid": "R299", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "sklearn": sklearn.__version__, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
