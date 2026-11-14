"""tradesize_v1 (R226): trade count and mean print size as 72 h spread books, tested for information beyond quote
volume, as set out in experiments/tradesize_v1/PREREG.md.

usage: python scripts/run_tradesize.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, features, flowfeat, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "tradesize_v1"
START, VAL, HOLD_OUT, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
HOLD = 72
TESTED = {"size_lvl": "qv_lvl", "size_chg": "qv_chg", "count_chg": "qv_chg"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def build(u):
    k = flowfeat.load("klines", u.p.t, u.p.symbols, ("quote_volume", "count"))
    lq = {n: flowfeat._log(features.roll(k["quote_volume"], n, "sum")) for n in (24, 720)}
    ln = {n: flowfeat._log(features.roll(k["count"], n, "sum")) for n in (24, 720)}
    del k
    return {"size_lvl": lq[24] - ln[24], "size_chg": (lq[24] - ln[24]) - (lq[720] - ln[720]),
            "count_chg": ln[24] - (ln[720] - np.log(30)), "qv_lvl": lq[24],
            "qv_chg": lq[24] - (lq[720] - np.log(30))}


def coverage(u, feats, a, b):
    """Share of eligible coin-hours with a finite feature, by liquidity tier and listing age, over rows [a, b)."""
    e = u.elig[a:b]
    first = np.argmax(np.isfinite(u.p["close"]), axis=0)
    age = (np.arange(a, b)[:, None] - first[None, :]) < 180 * 24
    rank = u.rank[a:b]
    groups = {"rank_1_20": e & (rank <= 20), "rank_21_50": e & (rank > 20), "age_lt_180d": e & age,
              "age_ge_180d": e & ~age, "all": e}
    return {f: {g: float(np.isfinite(x[a:b])[m].mean()) if m.any() else None for g, m in groups.items()}
            for f, x in feats.items()}


def window_stats(n, ref, days):
    s = events.summary(n)
    X = np.column_stack([np.ones(len(n)), ref])
    beta = np.linalg.lstsq(X, n, rcond=None)[0]
    resid = n - beta[1] * ref
    year = pd.to_datetime(days, unit="ms", utc=True).year
    return {"days": len(n), "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
            "t_nw10": float(stats.newey_west_t(n, 10)[2]), "sharpe": s.get("sharpe", np.nan),
            "max_dd": s.get("max_dd", np.nan), "corr_ref": float(np.corrcoef(n, ref)[0, 1]),
            "beta_ref": float(beta[1]), "resid_bp_day": float(resid.mean() * 1e4),
            "resid_t_nw10": float(stats.newey_west_t(resid, 10)[2]),
            "by_year_bp_day": {int(y): float(n[year == y].mean() * 1e4) for y in np.unique(year)}}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    feats = build(u)
    cov = coverage(u, feats, t0, th)
    log("coverage (discovery + validation):", json.dumps(cov))
    bins = {f: features.bins_xs(x, u.elig, 8) for f, x in feats.items()}
    del feats
    kof = lambda ind: float(ind[t0:tv].sum(axis=1).mean())

    def run(parts, K, a, b, cm=1.0):
        """parts: [(ind, side)] summed before costs; rows [a, b) warmed up from a - HOLD."""
        w = max(a - HOLD, 0)
        P = sum(slices.positions(ind, HOLD, w, b, 1.0 / (HOLD * K), side) for ind, side in parts)
        o = slices.run(P, u.ret, u.elig, u.cmat, w, b, cmult=cm)
        D = (b - a) // 24
        day = lambda x: x[(a - w): (a - w) + D * 24].reshape(D, 24).sum(1)
        return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"])

    def spread(f):
        lo, hi = (bins[f] == 0) & u.elig, (bins[f] == 7) & u.elig
        K = kof(lo) + kof(hi)
        return {"H": ([(hi, 1), (lo, -1)], K), "L": ([(lo, 1), (hi, -1)], K)}

    windows = {"discovery": (t0, tv), "validation": (tv, th), "holdout": (th, t1 - (t1 - th) % 24)}
    refs = {r: spread(r)["H"] for r in set(TESTED.values())}
    ref_net = {}
    rows, stage = [], {}
    for f, r in TESTED.items():
        for direction, (parts, K) in spread(f).items():
            name = f"{f}/{direction}"
            passed = True
            for w, (a, b) in windows.items():
                if not passed:
                    break
                if (r, w) not in ref_net:                  # a reference's holdout only if a book reaches it
                    ref_net[(r, w)] = run(*refs[r], a, b)[0]
                    rn = ref_net[(r, w)]
                    log(f"reference {r} {w}: mean {rn.mean() * 1e4:+.1f} bp/day "
                        f"t {stats.newey_west_t(rn, 10)[2]:+.2f}")
                days = u.p.t[a:a + (b - a) // 24 * 24:24]
                res = {}
                for cm in (1.0, 2.0, 3.0):
                    n, g, c = run(parts, K, a, b, cm)
                    res[cm] = n
                    rows.append({"book": name, "reference": r, "K": K, "window": w, "cmult": cm,
                                 "gross_bp_day": float(g.mean() * 1e4), "cost_bp_day": float(c.mean() * 1e4),
                                 **window_stats(n, ref_net[(r, w)], days)})
                r1 = rows[-3]
                if w == "discovery":
                    passed = r1["t_nw10"] >= 2 and res[2.0].mean() > 0 and r1["resid_t_nw10"] >= 2
                elif w == "validation":
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5 and r1["resid_bp_day"] > 0
                else:
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2
                stage[name] = {"reached": w, "passed": bool(passed)}
                log(name, w, f"mean {r1['mean_bp_day']:+.1f} bp/day t {r1['t_nw10']:+.2f}",
                    f"resid {r1['resid_bp_day']:+.1f} t {r1['resid_t_nw10']:+.2f}", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "coverage": cov,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "confirmed": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "confirmed")}, indent=1))


if __name__ == "__main__":
    main()
