"""pivotfade_v1 (R248): fade a close beyond the prior day's floor pivot R1/S1 (the mirror of R243/R247's PIVOT_BREAK) on
daily world indices and forex (validation 2013-19, then the 2020-26 holdout once for passers) and on crypto 4 h and
1 d bars (validation 2024-01..2025-06 only), with a one-bar reversal control, as set out in
experiments/pivotfade_v1/PREREG.md.

usage: python scripts/run_pivotfade.py
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
from lab import flowfeat, prereg, research, screen, slices, stats  # noqa: E402
from run_chartist import prev_day_levels, resample, states  # noqa: E402
from run_chartxm import GROUPS, SHAS, asset_states, bars, book, row  # noqa: E402
from run_tsbattery import WINDOWS as CRYPTO_WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "pivotfade_v1"
XM_WINDOWS = (("validation", "2013-01-01", "2019-12-31"), ("holdout", "2020-01-01", "2026-10-19"))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def alpha(net, bench):
    n, bm = net.values, bench.reindex(net.index).fillna(0.0).values
    beta = np.linalg.lstsq(np.column_stack([np.ones(len(bm)), bm]), n, rcond=None)[0][1]
    return n - beta * bm


def xm_decide(w, r1, r2):
    if w == "validation":
        return r1["test_mean_bp_day"] > 0 and r1["test_t"] >= 2 and r2["test_mean_bp_day"] > 0 and r1["mean_bp_day"] > 0
    return r1["test_mean_bp_day"] > 0 and r1["test_t"] >= 2 and r2["test_mean_bp_day"] > 0


def cross_market(rows, stage, extra):
    for g, syms in GROUPS.items():
        fade, rev, rets = {}, {}, {}
        for sym in syms:
            d = bars(sym)
            st, rets[sym] = asset_states(d)
            fade[sym] = -st["PIVOT_BREAK"]
            rev[sym] = -np.sign(rets[sym])
        cal = pd.DatetimeIndex(sorted(set().union(*[r.index for r in rets.values()])))
        R = pd.DataFrame({s: rets[s].reindex(cal) for s in syms})
        started = R.notna().cummax()
        R = R.fillna(0.0)
        bench = R.where(started).mean(axis=1).fillna(0.0)
        bk = {}
        for kind, src in (("PIVOT_FADE", fade), ("REV1D", rev)):
            S = pd.DataFrame({s: src[s].reindex(cal, method="ffill") for s in syms})
            bk[kind] = {cm: book(S, R, cm) for cm in (1.0, 2.0, 3.0)}
        name = f"PIVOT_FADE/{g}"
        passed = True
        for w, a, b in XM_WINDOWS:
            if not passed:
                break
            m = (cal >= a) & (cal <= b)
            res = {}
            for kind in ("PIVOT_FADE", "REV1D"):
                for cm, x in bk[kind].items():
                    r = row(*(y[m] for y in x), bench)
                    rows.append({"book": f"{kind}/{g}", "window": w, "cmult": cm, **r})
                    res[(kind, cm)] = r
            d = alpha(bk["PIVOT_FADE"][1.0][0][m], bench) - alpha(bk["REV1D"][1.0][0][m], bench)
            extra["pivot_minus_rev1d"][f"{g}/{w}"] = {"alpha_diff_bp_day": float(d.mean() * 1e4),
                                                     "t_nw10": float(stats.newey_west_t(d, 10)[2])}
            r1, r2 = res[("PIVOT_FADE", 1.0)], res[("PIVOT_FADE", 2.0)]
            passed = bool(xm_decide(w, r1, r2))
            stage[name] = {"reached": w, "passed": passed}
            c1 = res[("REV1D", 1.0)]
            log(name, w, f"net {r1['mean_bp_day']:+.2f} (gross {r1['gross_bp_day']:+.2f}, cost {r1['cost_bp_day']:.2f}),"
                f" alpha {r1['test_mean_bp_day']:+.2f} t {r1['test_t']:+.2f} (2x {r2['test_mean_bp_day']:+.2f});"
                f" REV1D alpha {c1['test_mean_bp_day']:+.2f} t {c1['test_t']:+.2f};"
                f" diff {extra['pivot_minus_rev1d'][f'{g}/{w}']}", "PASS" if passed else "stop")


def crypto(rows, stage, extra):
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    kl = flowfeat.load("klines", t, u.p.symbols, ("open", "high", "low"))
    c = np.asarray(u.p["close"], np.float64)
    e = np.asarray(u.elig)
    s = screen.Screen(u, windows=CRYPTO_WINDOWS)
    a, b = s.rows["validation"]
    mk = market_daily(u, a, b)
    dbars, drows = resample(kl["open"], kl["high"], kl["low"], c, t, 24)
    for tf, k in (("4h", 4), ("1d", 24)):
        bb, rows_ = resample(kl["open"], kl["high"], kl["low"], c, t, k)
        day = prev_day_levels(dbars, drows, rows_)
        piv = -np.nan_to_num(states(bb, day)["PIVOT_BREAK"])
        pc = np.vstack([np.full((1, S), np.nan), bb["c"][:-1]])
        with np.errstate(invalid="ignore", divide="ignore"):
            rev = -np.nan_to_num(np.sign(bb["c"] / pc - 1))
        er = e[rows_]
        n = np.maximum(er.sum(axis=1, keepdims=True), 1)
        daily = {}
        for kind, x in (("PIVOT_FADE", piv), ("REV1D", rev)):
            D = np.where(er, x, 0.0) / n
            P = np.zeros((T, S))
            for j, r in enumerate(rows_):
                P[r:(rows_[j + 1] if j + 1 < len(rows_) else T)] = D[j]
            res = {}
            for cm in (1.0, 2.0, 3.0):
                o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                nd = o["daily"]
                Dd = len(nd)
                day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
                r = {"book": f"{kind}/CRYPTO-{tf}", "window": "validation", "cmult": cm,
                     "gross_bp_day": float(day_sum(o["gross"]).mean() * 1e4),
                     "cost_bp_day": float(day_sum(o["cost"]).mean() * 1e4),
                     "gross_exposure": float(o["gross_exposure"].mean()),
                     "net_exposure": float(o["net_exposure"].mean()),
                     **screen.window_stats(nd, s.days(a, b), mk[:Dd])}
                if cm == 1.0:
                    r["trimmed_bp_day"] = trimmed(nd)
                    daily[kind] = nd
                rows.append(r)
                res[cm] = r
            if kind == "PIVOT_FADE":
                r1 = res[1.0]
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0 and r1["resid_bp_day"] > 0
                stage[f"PIVOT_FADE/CRYPTO-{tf}"] = {"reached": "validation", "passed": bool(passed)}
            log(f"{kind}/CRYPTO-{tf}", f"{res[1.0]['mean_bp_day']:+.2f} bp/day t {res[1.0]['t_nw10']:+.2f} (2x "
                f"{res[2.0]['mean_bp_day']:+.2f}), gross {res[1.0]['gross_bp_day']:+.2f} cost {res[1.0]['cost_bp_day']:.2f},"
                f" alpha {res[1.0]['resid_bp_day']:+.2f} t {res[1.0]['resid_t_nw10']:+.2f}")
        d = daily["PIVOT_FADE"] - daily["REV1D"]
        extra["pivot_minus_rev1d"][f"CRYPTO-{tf}/validation"] = {"net_diff_bp_day": float(d.mean() * 1e4),
                                                                "t_nw10": float(stats.newey_west_t(d, 10)[2])}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    rows, stage, extra = [], {}, {"pivot_minus_rev1d": {}}
    cross_market(rows, stage, extra)
    crypto(rows, stage, extra)
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "data_sha256": SHAS, **extra,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "passers": [k for k, v in stage.items() if v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "passers", "pivot_minus_rev1d")}, indent=1))


if __name__ == "__main__":
    main()
