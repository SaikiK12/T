"""posfam_v1 (R211): the two halves of top_vs_crowd and the top-account ratio as 72 h slice books; posfam_v2 (R212):
the top-account ratio as a contrarian book. As set out in experiments/posfam_v1/PREREG.md and posfam_v2/PREREG.md.

usage: python scripts/run_posfam.py [--lane posfam_v1|posfam_v2]
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
from lab import data, events, features, flowfeat, prereg, research, slices, stats  # noqa: E402

START, VAL, HOLD_OUT, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
HOLD, K_TVC = 72, 2.418
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def window_stats(n, ref):
    s = events.summary(n)
    X = np.column_stack([np.ones(len(n)), ref])
    beta = np.linalg.lstsq(X, n, rcond=None)[0]
    resid = n - beta[1] * ref
    return {"days": len(n), "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
            "t_nw10": float(stats.newey_west_t(n, 10)[2]), "sharpe": s.get("sharpe", np.nan),
            "max_dd": s.get("max_dd", np.nan), "corr_tvc": float(np.corrcoef(n, ref)[0, 1]),
            "beta_tvc": float(beta[1]), "alpha_bp_day": float(resid.mean() * 1e4),
            "alpha_t_nw10": float(stats.newey_west_t(resid, 10)[2])}


def v1():
    LANE = ROOT / "experiments" / "posfam_v1"
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    m = flowfeat.load("metrics", u.p.t, u.p.symbols, ("top_ls_count", "top_ls_sum", "ls_count"))
    lg = {k: flowfeat._log(v) for k, v in m.items()}
    feats = {"whale_vs_top": lg["top_ls_sum"] - lg["top_ls_count"],
             "topacct_vs_crowd": lg["top_ls_count"] - lg["ls_count"], "top_acct": lg["top_ls_count"]}
    del m, lg
    log("coverage of top_ls_count among eligible cells:",
        f"{np.isfinite(feats['top_acct'][t0:th])[u.elig[t0:th]].mean():.4f}")
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    tvc_ind = (np.asarray(fb[fn.index("flow:top_vs_crowd/xs8")]) == 0) & u.elig

    def run(ind, side, K, a, b, cm=1.0):
        """Book over rows [a, b), warmed up from a - HOLD so slices opened before a are held."""
        w = max(a - HOLD, 0)
        o = slices.book(ind, u.ret, u.elig, u.cmat, HOLD, 1.0 / (HOLD * K), w, b, side=side, cmult=cm)
        skip = (a - w) // 24
        D = (b - a) // 24
        day = lambda x: x[(a - w): (a - w) + D * 24].reshape(D, 24).sum(1)
        return o["daily"][skip:skip + D], day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"])

    windows = {"discovery": (t0, tv), "validation": (tv, th), "holdout": (th, t1 - (t1 - th) % 24)}
    tvc = {w: run(tvc_ind, -1, K_TVC, a, b)[0] for w, (a, b) in windows.items() if w != "holdout"}
    rows, stage = [], {}
    for f, x in feats.items():
        bins = features.bins_xs(x, u.elig, 8)
        for b_, side in ((0, -1), (7, 1)):
            name = f"{f}/bin{b_}/{'short' if side < 0 else 'long'}"
            ind = (bins == b_) & u.elig
            K = float(ind[t0:tv].sum(axis=1).mean())
            passed = True
            for w, (a, b) in windows.items():
                if not passed:
                    break
                if w not in tvc:                         # the reference's holdout only if a book reaches it
                    tvc[w] = run(tvc_ind, -1, K_TVC, a, b)[0]
                res = {}
                for cm in (1.0, 2.0, 3.0):
                    n, g, c = run(ind, side, K, a, b, cm)
                    res[cm] = n
                    rows.append({"book": name, "K": K, "window": w, "cmult": cm,
                                 "gross_bp_day": float(g.mean() * 1e4), "cost_bp_day": float(c.mean() * 1e4),
                                 **window_stats(n, tvc[w])})
                r1 = rows[-3]
                if w == "discovery":
                    passed = r1["t_nw10"] >= 2 and res[2.0].mean() > 0
                elif w == "validation":
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5
                else:
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2
                stage[name] = {"reached": w, "passed": bool(passed)}
                log(name, w, f"mean {r1['mean_bp_day']:+.1f} bp/day t {r1['t_nw10']:+.2f}", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage,
               "confirmed": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


def v2():
    lane = ROOT / "experiments" / "posfam_v2"
    log("prereg sha", prereg.verify(lane / "PREREG.md")[:12])
    out = lane / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    m = flowfeat.load("metrics", u.p.t, u.p.symbols, ("top_ls_count",))
    gb = features.bins_xs(flowfeat._log(m["top_ls_count"]), u.elig, 8)
    del m
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    cb = np.asarray(fb[fn.index("flow:crowd_ls/xs8")])
    tvc_ind = (np.asarray(fb[fn.index("flow:top_vs_crowd/xs8")]) == 0) & u.elig
    kof = lambda ind: float(ind[t0:tv].sum(axis=1).mean())

    def run(parts, K, a, b, cm=1.0):
        """parts: [(ind, side)] summed before costs; rows [a, b) warmed up from a - HOLD."""
        w = max(a - HOLD, 0)
        P = sum(slices.positions(ind, HOLD, w, b, 1.0 / (HOLD * K), side) for ind, side in parts)
        o = slices.run(P, u.ret, u.elig, u.cmat, w, b, cmult=cm)
        D = (b - a) // 24
        day = lambda x: x[(a - w): (a - w) + D * 24].reshape(D, 24).sum(1)
        return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"])

    L, S = ((gb == 0) & u.elig, 1), ((gb == 7) & u.elig, -1)
    CL, CS = ((cb == 0) & u.elig, 1), ((cb == 7) & u.elig, -1)
    books = {"C": ([L, S], (kof(L[0]) + kof(S[0])) / 2 * 2), "L": ([L], kof(L[0])), "S": ([S], kof(S[0])),
             "crowd_ref": ([CL, CS], (kof(CL[0]) + kof(CS[0])) / 2 * 2)}
    windows = {"discovery": (t0, tv), "validation": (tv, th), "holdout": (th, t1 - (t1 - th) % 24)}
    rows, tvc, passed = [], {}, None
    for w, (a, b) in windows.items():
        if w == "holdout" and not passed:
            break
        tvc[w] = run([(tvc_ind, -1)], K_TVC, a, b)[0]
        for name, (parts, K) in books.items():
            if w == "discovery" and name != "C":
                continue
            for cm in (1.0, 2.0, 3.0):
                n, g, c = run(parts, K, a, b, cm)
                rows.append({"book": name, "K": K, "window": w, "cmult": cm, "gross_bp_day": float(g.mean() * 1e4),
                             "cost_bp_day": float(c.mean() * 1e4), **window_stats(n, tvc[w])})
        c1 = next(r for r in rows if r["book"] == "C" and r["window"] == w and r["cmult"] == 1.0)
        log(f"C {w}: mean {c1['mean_bp_day']:+.1f} bp/day t {c1['t_nw10']:+.2f}")
        if w == "validation":
            passed = c1["mean_bp_day"] > 0 and c1["t_nw10"] >= 1.5
        elif w == "holdout":
            confirmed = c1["mean_bp_day"] > 0 and c1["t_nw10"] >= 2
    df = pd.DataFrame(rows)
    df.to_csv(out / "books.csv", index=False)
    verdict = {"validation_passed": bool(passed), "confirmed": bool(passed and confirmed)}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log(verdict)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", default="posfam_v1", choices=("posfam_v1", "posfam_v2"))
    (v1 if ap.parse_args().lane == "posfam_v1" else v2)()
