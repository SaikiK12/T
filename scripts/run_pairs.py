"""pairs_v1 (R250): weekly-formed pairs on the top-50 perps, distance (Gatev) and Engle-Granger selection, z-score
entry 2 and exit 0, as set out in experiments/pairs_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_pairs.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg, research, screen, slices  # noqa: E402
from run_tsbattery import WINDOWS, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "pairs_v1"
FORM, TRADE, K, Z_IN, DF_CRIT = 720, 168, 10, 2.0, -3.34
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def select_dist(lp):
    """lp [FORM, m] log prices. Returns [(i, j, beta=1, alpha=0, mean, std, kind)] for the K smallest SSD pairs."""
    x = np.exp(lp - lp[0])
    g = x.T @ x
    sq = np.diag(g)
    ssd = sq[:, None] + sq[None, :] - 2 * g
    iu = np.triu_indices(len(sq), 1)
    order = np.argsort(ssd[iu])[:K]
    out = []
    for k in order:
        i, j = iu[0][k], iu[1][k]
        s = x[:, i] - x[:, j]
        out.append((i, j, 1.0, 0.0, float(s.mean()), float(s.std())))
    return out


def df_stats(lp, liq):
    """For every pair (i more liquid than j by `liq`): OLS of log p_i on log p_j and the Dickey-Fuller t of the
    residual. Returns arrays i, j, alpha, beta, t."""
    m = lp.shape[1]
    iu = np.triu_indices(m, 1)
    a_idx, b_idx = iu
    swap = liq[a_idx] > liq[b_idx]                    # higher rank number = less liquid
    I = np.where(swap, b_idx, a_idx)
    J = np.where(swap, a_idx, b_idx)
    Y, X = lp[:, I], lp[:, J]
    xm, ym = X.mean(0), Y.mean(0)
    beta = ((X - xm) * (Y - ym)).sum(0) / ((X - xm) ** 2).sum(0)
    alpha = ym - beta * xm
    e = Y - alpha - beta * X
    de, el = np.diff(e, axis=0), e[:-1]
    elm, dem = el.mean(0), de.mean(0)
    sxx = ((el - elm) ** 2).sum(0)
    b = ((el - elm) * (de - dem)).sum(0) / sxx
    a = dem - b * elm
    res = de - a - b * el
    s2 = (res ** 2).sum(0) / (len(de) - 2)
    t = b / np.sqrt(s2 / sxx)
    return I, J, alpha, beta, t, e


def select_eg(lp, liq):
    I, J, alpha, beta, t, e = df_stats(lp, liq)
    ok = (beta >= 0.2) & (beta <= 5) & (t < DF_CRIT)
    idx = np.flatnonzero(ok)
    idx = idx[np.argsort(t[idx])][:K]
    return [(I[k], J[k], float(beta[k]), float(alpha[k]), float(e[:, k].mean()), float(e[:, k].std())) for k in idx]


def build(u, method, top, r_end):
    """Positions [T, S] for one book up to row r_end, plus trade records."""
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    c = np.asarray(u.p["close"], np.float64)
    lc = np.where(c > 0, np.log(np.where(c > 0, c, 1)), np.nan)
    e = np.asarray(u.elig)
    rank = np.asarray(u.rank)
    ts = pd.to_datetime(t, unit="ms", utc=True)
    mondays = np.flatnonzero((np.asarray(ts.weekday) == 0) & (np.asarray(ts.hour) == 0))
    P = np.zeros((T, S))
    trades, n_pairs = [], []
    for f in mondays:
        if f < FORM or f + TRADE > r_end:
            continue
        win = lc[f - FORM:f]
        cand = np.flatnonzero(np.isfinite(win).all(0) & e[f - FORM:f].all(0) & e[f - 1])
        if top == "TOP20":
            cand = cand[rank[f - 1, cand] <= 20]
        if len(cand) < 2:
            n_pairs.append(0)
            continue
        lp = win[:, cand]
        pairs = select_dist(lp) if method == "DIST" else select_eg(lp, rank[f - 1, cand].astype(float))
        n_pairs.append(len(pairs))
        for (a, b, beta, alpha, mu, sd) in pairs:
            i, j = cand[a], cand[b]
            if not sd > 0:
                continue
            wi, wj = 1.0 / (K * (1 + beta)), -beta / (K * (1 + beta))
            pos, start = 0, None
            for r in range(f, f + TRADE - 1):          # the week's last row stays flat
                if method == "DIST":
                    sp = np.exp(lc[r, i] - lc[f - FORM, i]) - np.exp(lc[r, j] - lc[f - FORM, j])
                else:
                    sp = lc[r, i] - beta * lc[r, j] - alpha
                ok = e[r, i] and e[r, j] and np.isfinite(sp)
                z = (sp - mu) / sd if ok else np.nan
                if pos != 0:
                    why = None
                    if not ok:
                        why = "elig"
                    elif (pos == 1 and z >= 0) or (pos == -1 and z <= 0):
                        why = "revert"
                    if why:
                        trades.append({"hours": r - start, "exit": why})
                        pos = 0
                if pos == 0 and ok:
                    if z > Z_IN:
                        pos, start = -1, r
                    elif z < -Z_IN:
                        pos, start = 1, r
                if pos != 0:
                    P[r, i] += pos * wi
                    P[r, j] += pos * wj
            if pos != 0:
                trades.append({"hours": f + TRADE - 1 - start, "exit": "week_end"})
    return P, trades, n_pairs


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u, windows=WINDOWS)
    r_end = s.rows["validation"][1]
    rows, stage, info = [], {}, {}
    for method in ("DIST", "EG"):
        for top in ("TOP20", "TOP50"):
            name = f"{method}/{top}"
            P, trades, n_pairs = build(u, method, top, r_end)
            tr = pd.DataFrame(trades)
            info[name] = {"trades": len(tr), "mean_hours": float(tr.hours.mean()) if len(tr) else np.nan,
                          "exit_share": tr.exit.value_counts(normalize=True).round(3).to_dict() if len(tr) else {},
                          "pairs_per_week_mean": float(np.mean(n_pairs)), "weeks": len(n_pairs)}
            log(name, info[name])
            passed = True
            for w, (a, b) in s.rows.items():
                if w == "holdout" or not passed:
                    break
                res = {}
                for cm in (1.0, 2.0, 3.0):
                    o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                    nd = o["daily"]
                    Dd = len(nd)
                    day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
                    r = {"book": name, "window": w, "cmult": cm,
                         "gross_bp_day": float(day_sum(o["gross"]).mean() * 1e4),
                         "cost_bp_day": float(day_sum(o["cost"]).mean() * 1e4),
                         "gross_exposure": float(o["gross_exposure"].mean()),
                         "net_exposure": float(o["net_exposure"].mean()),
                         **screen.window_stats(nd, s.days(a, b))}
                    if cm == 1.0:
                        r["trimmed_bp_day"] = trimmed(nd)
                    rows.append(r)
                    res[cm] = r
                r1 = res[1.0]
                if w == "discovery":
                    passed = r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0
                else:
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5
                stage[name] = {"reached": w, "passed": bool(passed)}
                log(name, w, f"{r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.2f}),"
                    f" gross {r1['gross_bp_day']:+.2f} cost {r1['cost_bp_day']:.2f}, exposure {r1['gross_exposure']:.2f}",
                    "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "info": info,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
