"""Run the battery_v1 lane for one walk-forward fold, as set out in experiments/battery_v1/PREREG.md.

usage: python scripts/run_battery.py F2 [--placebos 2] [--out experiments/battery_v1/results]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, policy, prereg, research, search  # noqa: E402

# (discovery start, discovery end = test start, test end); the test end never passes 2025-07-01
FOLDS = {"F1": ("2021-01-01", "2023-01-01", "2024-01-01"),
         "F2": ("2021-01-01", "2024-01-01", "2025-01-01"),
         "F3": ("2021-01-01", "2025-01-01", "2025-07-01")}
CFG = {"n_conds": 250, "per_view": 6, "pair_holds": (24, 72), "triple_pairs": 400, "fdr_q": 0.25, "min_real": 30,
       "rho": 0.7, "cap": 2000, "era_lag": 3,
       "policy_L": (30, 60, 120), "policy_K": (5, 10, 20), "policy_H": (7, 14), "primary": (60, 10, 7),
       "persist": {"L": 40, "H": 14, "far_gap": 100, "block": 14, "n_perm": 500}, "n_rep": 500, "episode": (60, 2.0, 30)}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def pipeline(u, bins, t0, t1, edges, ret_override=None, tag=""):
    cat = search.condition_catalog(bins, u.elig, t0, t1)
    out = []
    S1 = search.score_rules(u, bins, search.singles(cat), t0, t1, edges, CFG["era_lag"], ret_override)
    log(f"{tag} stage 1: {len(S1.rules)} single rules; peak t quantiles 50/99/max =",
        np.round(np.quantile(S1.peak, [.5, .99, 1]), 2))
    conds = search.top_conditions(S1, cat, CFG["n_conds"], CFG["per_view"])
    S2 = search.score_rules(u, bins, search.pairs(conds, holds=CFG["pair_holds"]), t0, t1, edges, CFG["era_lag"], ret_override)
    log(f"{tag} stage 2: {len(S2.rules)} pairs; peak max {S2.peak.max():.2f}")
    S3 = search.score_rules(u, bins, search.triples(S2, conds, CFG["triple_pairs"]), t0, t1, edges, CFG["era_lag"], ret_override)
    log(f"{tag} stage 3: {len(S3.rules)} triples; peak max {S3.peak.max():.2f}")
    return [S1, S2, S3]


def pooled(stages):
    rules = [r for s in stages for r in s.rules]
    return rules, np.vstack([s.ret for s in stages]), np.concatenate([s.peak for s in stages])


def library(stages, tau=None, top=None):
    rules, ret, peak = pooled(stages)
    ok = np.flatnonzero(peak >= tau) if tau is not None else np.argsort(-peak)[: top * 5]
    order = ok[np.argsort(-peak[ok])]
    kept = search.dedupe(ret, order, CFG["rho"], cap=CFG["cap"] if top is None else top)
    return [rules[i] for i in kept], ret[kept], peak[kept]


def analyse(R, rng):
    """Locality, persistence and the policy grid on a frozen library's test-period daily returns."""
    w, th, md = CFG["episode"]
    eps = policy.episodes(policy.rolling_t(R, w), th, md)
    out = {"n_strategies": int(R.shape[1]), "n_days": int(R.shape[0]),
           "share_with_episode": float(np.mean([len(e) > 0 for e in eps])),
           "persistence": {k: v for k, v in policy.persistence_test(R, rng=rng, **CFG["persist"]).items()}}
    grid, series = {}, {}
    for L in CFG["policy_L"]:
        for K in CFG["policy_K"]:
            for H in CFG["policy_H"]:
                if K >= R.shape[1]:
                    continue
                res = policy.policy_vs_random(R, L, K, H, True, n_rep=CFG["n_rep"], rng=rng)
                series[(L, K, H)] = res.pop("series")
                grid[f"L{L}_K{K}_H{H}"] = res
    out["policy"] = grid
    srs = np.array([np.nanmean(s) / np.nanstd(s, ddof=1) for s in series.values() if np.isfinite(s).sum() > 30])
    if len(srs) > 2:
        best = max(series, key=lambda k: np.nanmean(series[k]) / np.nanstd(series[k], ddof=1))
        s = series[best][np.isfinite(series[best])]
        out["dsr_best_of_grid"] = {"config": list(best), "dsr": inference.dsr(s, srs, len(srs))}
    p = CFG["primary"]
    out["primary"] = grid.get(f"L{p[0]}_K{p[1]}_H{p[2]}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fold", choices=FOLDS)
    ap.add_argument("--placebos", type=int, default=2)
    ap.add_argument("--out", default=str(ROOT / "experiments" / "battery_v1" / "results"))
    ap.add_argument("--no-prereg", action="store_true", help="smoke runs only: skip the frozen-spec check")
    a = ap.parse_args()
    if not a.no_prereg:
        log("prereg sha", prereg.verify(ROOT / "experiments" / "battery_v1" / "PREREG.md")[:12])
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    u, bins, names = research.load_universe()
    d0, d1, d2 = (research.row_of(u.p, d) for d in FOLDS[a.fold])
    assert d2 <= u.holdout_row, "a fold may not reach the holdout"
    edges = search.half_year_edges(u.p, d0, d1)
    log(f"{a.fold}: discovery rows {d0}-{d1} ({(d1 - d0) // 24} days, {len(edges) - 1} eras), test rows {d1}-{d2}")

    t = time.time()
    real = pipeline(u, bins, d0, d1, edges, None, "real")
    n_trials = sum(len(s.rules) for s in real)
    log(f"real search done: {n_trials} trials in {(time.time() - t) / 60:.1f} min")
    rng = np.random.default_rng(sum(map(ord, a.fold)))
    plac = []
    for k in range(a.placebos):
        shift = int(rng.integers(24 * 120, (d1 - d0) - 24 * 120))
        # Keep the phase random.  Rounding to whole days leaves hour/session/
        # funding-clock features aligned with the returns in the placebo.
        plac.append(pipeline(u, bins, d0, d1, edges, search.shifted_returns(u, shift, d1), f"placebo{k}"))
        n_trials += sum(len(s.rules) for s in plac[-1])

    rules_r, ret_r, peak_r = pooled(real)
    null_peaks = [pooled(p)[2] for p in plac]
    grid, fdr, counts = search.empirical_fdr(peak_r, null_peaks)
    table = [{"t": float(g), "fdr": None if np.isnan(f) else float(f), "real": int(c),
              "placebo": float(np.mean([(n >= g).sum() for n in null_peaks]))} for g, f, c in zip(grid, fdr, counts)]
    ok = np.flatnonzero((fdr <= CFG["fdr_q"]) & (counts >= CFG["min_real"]))
    tau = float(grid[ok.min()]) if len(ok) else None
    log("threshold tau =", tau)
    result = {"fold": a.fold, "n_trials": n_trials, "tau": tau, "fdr_table": table, "cfg": {k: str(v) for k, v in CFG.items()}}

    if tau is not None:
        lib, lib_disc, lib_peak = library(real, tau)
        log(f"library: {len(lib)} diverse rules at peak t >= {tau}")
        ret_t, cost_t, _ = research.eval_rules(u, bins, lib, d1, d2)
        R = ret_t.T.astype(np.float64)
        result["library"] = {"n": len(lib), "mean_peak": float(lib_peak.mean())}
        result["real"] = analyse(R, np.random.default_rng(1))
        np.savez_compressed(out_dir / f"{a.fold}_library.npz", test=ret_t, disc=lib_disc,
                            rules=np.array([repr(r) for r in lib]))
        pn = []
        for k, p in enumerate(plac):
            plib, _, _ = library(p, top=len(lib))
            pr, _, _ = research.eval_rules(u, bins, plib, d1, d2)
            pn.append(analyse(pr.T.astype(np.float64), np.random.default_rng(10 + k)))
        result["placebo"] = pn
    (out_dir / f"{a.fold}.json").write_text(json.dumps(result, indent=1, default=float))
    log("wrote", out_dir / f"{a.fold}.json")


if __name__ == "__main__":
    main()
