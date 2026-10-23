"""R305 mlaudit_v1: what carries R304's pick (GBM h7 on the 24 clean features)?

R304 (`scripts/run_mlrank2.py`, frozen) passed its rule: validation net 1x +58.9 bp/day, t 4.21. That is too large to
trust unexplained. A post-hoc look (lag test, permutation importance, leg profile) found that the long leg holds
old, calm coins and the short leg young, volatile ones. This lane tests that reading with six books and a beta check,
each against a label written before the run:

- GBM h7 refits on three feature subsets: without `age`, on the six risk features only, and without them;
- three fixed scores with signs set by the hypothesis, not by data: a low-risk composite, low `vol30`, high `age`;
- the pick's net per rebalance regressed on the equal-weight universe and on BTC over the same holds;
- the short leg's squeeze tail.

Everything else comes unchanged from `scripts/run_mlrank.py` and `scripts/run_mlrank2.py` (frozen).

usage: python scripts/run_mlaudit.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_mlrank import (WINDOWS, book, daily_ic, legs, load_panel, prepare, rank_target, report,  # noqa: E402
                                stack, targets, walk_forward, window_mask)
from scripts.run_mlrank2 import CLEAN  # noqa: E402

LANE = ROOT / "experiments" / "mlaudit_v1"
HOLD = 7
RISK = ["vol30", "range7", "wick30", "max7", "illiq30", "age"]
FITTED = {"gbm no-age": [f for f in CLEAN if f != "age"], "gbm risk-only": RISK,
          "gbm no-risk": [f for f in CLEAN if f not in RISK]}
SCORES = {"composite": {"vol30": -1, "range7": -1, "wick30": -1, "max7": -1, "age": 1},
          "lowvol": {"vol30": -1}, "old": {"age": 1}}
PRE_FREEZE = 1                      # the lag-test book of the post-hoc look, run before this freeze
TRIALS = len(FITTED) + len(SCORES) + PRE_FREEZE
PICK_VALID = 58.9165                # R304's pick, validation net 1x bp/day
PARITY_BP = 0.01
SQUEEZE = (0.5, 1.0)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def score_pred(X, signs, index):
    """A fixed score: the mean of the signed centred ranks in X (missing already 0), on `index`."""
    return sum(s * X[n].reindex(index) for n, s in signs.items()) / len(signs)


def ols_alpha(y, x):
    """OLS y = a + b x: (a, b, t of a, n), plain standard errors (the rebalances do not overlap)."""
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    n = len(y)
    if n < 10:
        return None, None, None, n
    A = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    s2 = resid @ resid / (n - 2)
    se = np.sqrt(s2 * np.linalg.inv(A.T @ A)[0, 0])
    return float(coef[0]), float(coef[1]), float(coef[0] / se), n


def labels(books, beta):
    """The labels written in the PREREG, from validation net 1x bp/day and the alpha t-stats."""
    v = {k: books[k]["valid"]["1x"].get("bp_day") for k in books}
    out = {"age_carried": v["gbm no-age"] is not None and v["gbm no-age"] < 0.5 * PICK_VALID,
           "risk_carried": v["gbm risk-only"] is not None and v["gbm risk-only"] >= 0.7 * PICK_VALID,
           "known_anomaly": v["composite"] is not None and v["composite"] >= 0.7 * PICK_VALID,
           "beta": any(beta[k]["alpha_t"] is None or beta[k]["alpha_t"] < 2.0 for k in ("ew_universe", "btc"))}
    out["unexplained"] = not any(out.values())
    return out


def squeeze(rows, ret, hold, win):
    """The short leg's tail in the window: worst single-name move against it, and the share of rebalances with a
    short name up more than each SQUEEZE level."""
    ts = np.array([r["t"] for r in rows], np.int64)
    m = window_mask(ts, hold, win)
    worst, hits = [], {lv: 0 for lv in SQUEEZE}
    for r, k in zip(rows, m):
        if not k:
            continue
        d = pd.Timestamp(r["t"], unit="ms")
        shorts = [s for s, x in r["w"].items() if x < 0]
        mx = float(ret.loc[d, shorts].max())
        worst.append(mx)
        for lv in SQUEEZE:
            hits[lv] += mx > lv
    n = len(worst)
    return {"rebalances": n, "max_short_name_ret": max(worst) if worst else None,
            "median_worst_short_name_ret": float(np.median(worst)) if worst else None,
            **{f"share_short_name_over_{int(lv * 100)}pct": hits[lv] / n if n else None for lv in SQUEEZE}}


def yearly(rows, net, hold, win):
    ts = np.array([r["t"] for r in rows], np.int64)
    m = window_mask(ts, hold, win)
    yr = pd.to_datetime(ts[m], unit="ms").year
    return {int(y): round(float(net[m][yr == y].mean() / hold * 1e4), 2) for y in np.unique(yr)}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    df = load_panel()
    w, f, uni = prepare(df)
    ret, fund = targets(w, HOLD)
    y = rank_target(ret - fund, uni).stack(future_stack=True)
    X = stack(f, CLEAN, uni)
    yl = y.reindex(X.index)

    log("pick: gbm h7 clean")
    pred, _ = walk_forward(X, yl, "gbm", HOLD, CLEAN)
    rows = {"pick": book(legs(pred, HOLD), ret, fund)}
    preds = {"pick": pred}
    for k, names in FITTED.items():
        log(f"fit {k}")
        preds[k], _ = walk_forward(X, yl, "gbm", HOLD, names)
        rows[k] = book(legs(preds[k], HOLD), ret, fund)
    for k, signs in SCORES.items():
        preds[k] = score_pred(X, signs, pred.index)
        rows[k] = book(legs(preds[k], HOLD), ret, fund)

    books, nets = {}, {}
    for k, r in rows.items():
        rep, ts, net1 = report(r, HOLD, daily_ic(preds[k], yl))
        books[k], nets[k] = rep, net1
        log(f"{k}: disc net {rep['disc']['1x'].get('bp_day')} t {rep['disc']['1x'].get('t')}; valid net "
            f"{rep['valid']['1x'].get('bp_day')} t {rep['valid']['1x'].get('t')}")
    parity = abs(books["pick"]["valid"]["1x"]["bp_day"] - PICK_VALID) <= PARITY_BP
    log(f"parity with R304: {parity}")

    # beta of the pick's net per rebalance on the same holds' equal-weight universe and BTC (net of funding)
    pr = rows["pick"]
    ts = np.array([r["t"] for r in pr], np.int64)
    days = pd.to_datetime(ts, unit="ms")
    ew = (ret - fund).where(uni).mean(axis=1).reindex(days).to_numpy()
    btc = (ret - fund)["BTCUSDT"].reindex(days).to_numpy()
    beta = {}
    for name, x in (("ew_universe", ew), ("btc", btc)):
        out = {}
        for win in WINDOWS:
            m = window_mask(ts, HOLD, win)
            a, b, t, n = ols_alpha(nets["pick"][m], x[m])
            out[win] = {"alpha_bp_day": None if a is None else a / HOLD * 1e4, "beta": b, "alpha_t": t, "n": n,
                        "x_mean_bp_day": float(np.nanmean(x[m]) / HOLD * 1e4)}
        beta[name] = {**out["valid"], "disc": out["disc"]}
    legs_mkt = {}
    for side in ("long", "short"):
        leg = np.array([r[side] for r in pr])
        m = window_mask(ts, HOLD, "valid")
        a, b, t, n = ols_alpha(leg[m], ew[m])
        legs_mkt[side] = {"alpha_bp_day": None if a is None else a / HOLD * 1e4, "beta": b, "alpha_t": t}

    lab = labels(books, beta)
    out = {"rid": "R305", "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, "parity_with_r304": bool(parity),
           "labels": lab,
           "books": {k: {win: {"net1x_bp_day": v[win]["1x"].get("bp_day"), "t": v[win]["1x"].get("t"),
                               "net2x_bp_day": v[win]["2x"].get("bp_day"), "net3x_bp_day": v[win]["3x"].get("bp_day"),
                               "gross_bp_day": v[win]["gross"].get("bp_day"),
                               "wo_best_bp": v[win]["1x"].get("mean_wo_best_bp"),
                               "long_bp": v[win]["long_bp"], "short_bp": v[win]["short_bp"],
                               "rank_ic": v[win]["rank_ic"]["mean"]} for win in WINDOWS}
                     for k, v in books.items()},
           "yearly_net1x_bp_day": {k: yearly(rows[k], nets[k], HOLD, "valid") | yearly(rows[k], nets[k], HOLD, "disc")
                                   for k in rows},
           "beta": beta, "legs_vs_ew": legs_mkt,
           "squeeze": {win: squeeze(pr, ret, HOLD, win) for win in WINDOWS}}
    log(f"labels {lab}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"book": k, "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
                   "net1x": n} for k in rows for r, n in zip(rows[k], nets[k])]).to_csv(
        res_dir / "periods.csv", index=False, float_format="%.8g")
    (res_dir / "summary.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    main()
