"""atlas_ctx (R192): context lifts of the atlas signals, as set out in experiments/atlas_ctx/PREREG.md.

usage: python scripts/run_context_atlas.py discovery [--families clock,crowd,market,flow]   (resumable, per context)
       python scripts/run_context_atlas.py flag          thresholds and the discovery lists
       python scripts/run_context_atlas.py validation    freeze the lists, then one pass per listed context
       python scripts/run_context_atlas.py report        replication tables
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import atlas, data, prereg, research, search  # noqa: E402

LANE = ROOT / "experiments" / "atlas_ctx"
OUT = LANE / "results"
RD = data.ROOT / "research"
VAL_START, VAL_END = "2024-01-01", "2025-07-01"
Q, MIN_REAL, MIN_SUPPORT, MIN_SHARE, MIN_DAYS, MIN_ERAS = 0.10, 5, 0.01, 0.02, 100, 4
MARKET = ("btc_ret[", "disp[", "breadth[", "funding_clock[")
KEEP = ["view", "name", "bin", "h", "code", "measure", "base_bp", "cond_bp", "cond_t", "cond_days", "lift_bp", "lift_t",
        "lift_days", "lift_eras_same_sign", "lift_eras", "share", "cells", "support", "cost_rt_bp", "amplifies",
        "cond_edge_cost"]
KEY = ["context", "view", "bin", "h", "code", "measure"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def setup():
    u, bins, names = research.load_universe()
    t_end = research.row_of(u.p, VAL_END)
    assert t_end <= u.holdout_row
    to = atlas._time_only(bins, np.arange(bins.shape[0], dtype=np.int64), *u.index, 0, t_end, 7)
    base = np.flatnonzero(to == 0).astype(np.int64)
    nb = atlas.max_bins(bins, base, *u.index, 0, t_end) + 1
    return u, bins, names, to, base, nb


def contexts(bins, names, to, families):
    """[(family, context name, loader)] in a fixed order; loader() -> contiguous int8 [T, S] codes (-1 = no code)."""
    out = []
    if "clock" in families:
        c = np.load(RD / "bins_clock.npy", mmap_mode="r")
        for i, n in enumerate(json.loads((RD / "meta_clock.json").read_text())["names"]):
            out.append(("clock", f"clock:{n}", lambda i=i, c=c: np.ascontiguousarray(c[i])))
    if "crowd" in families:
        c = np.load(RD / "bins_ctx.npy", mmap_mode="r")
        for i, n in enumerate(json.loads((RD / "meta_ctx.json").read_text())["names"]):
            out.append(("crowd", n, lambda i=i, c=c: np.ascontiguousarray(c[i])))
    if "market" in families:
        for i, n in enumerate(names):
            if to[i] and n.startswith(MARKET):
                out.append(("market", n, lambda i=i: np.ascontiguousarray(bins[i])))
    if "flow" in families:
        path = RD / "bins_flow.npy"
        if path.exists():
            c = np.load(path, mmap_mode="r")
            for i, n in enumerate(json.loads((RD / "meta_flow.json").read_text())["names"]):
                out.append(("flow", n, lambda i=i, c=c: np.ascontiguousarray(c[i])))
        else:
            log("flow tensor missing, flow family skipped")
    return out


def fname(ctx, kind):
    return OUT / f"{kind}_{ctx.replace(':', '_').replace('/', '_').replace('[', '(').replace(']', ')')}.parquet"


def lift_pass(u, bins, names, base, nb, group, F, X, t0, t1, eras):
    G = int(group[t0:t1].max()) + 1
    if G <= 1:
        return None
    acc = atlas.run(bins, base, F, X, u.cmat, u.index, group, G, t0, t1, nb=nb)
    df = atlas.lift_stats(acc, names, atlas.HORIZONS, eras, [str(k) for k in range(G)])
    return df[KEEP]


def passes_filters(df):
    return (df.support >= MIN_SUPPORT) & (df.share >= MIN_SHARE) & (df.lift_days >= MIN_DAYS) & df.lift_t.notna()


def discovery(a):
    u, bins, names, to, base, nb = setup()
    t0, t1 = 0, research.row_of(u.p, research.DISC_END)
    eras = search.half_year_edges(u.p, t0, t1)
    OUT.mkdir(parents=True, exist_ok=True)
    ctxs = contexts(bins, names, to, a.families.split(","))
    log(f"{len(base)} base views, {int(nb.sum())} cells, {len(ctxs)} contexts")
    F, X = atlas.forward(u.ret, u.elig, t0, t1)
    for i, (fam, ctx, load) in enumerate(ctxs):
        if fname(ctx, "real").exists() and fname(ctx, "placebo").exists():
            continue
        group = load()
        real = lift_pass(u, bins, names, base, nb, group, F, X, t0, t1, eras)
        if real is None:
            log(f"{ctx}: one code only, skipped")
            continue
        rng = np.random.default_rng(sum(map(ord, ctx)))
        shift = 24 * int(rng.integers(120, 976)) + 12
        Fp, Xp = atlas.forward(search.shifted_returns(u, shift, t1), u.elig, t0, t1)
        null = lift_pass(u, bins, names, base, nb, group, Fp, Xp, t0, t1, eras)
        del Fp, Xp
        for kind, df in (("real", real), ("placebo", null)):
            df = df[passes_filters(df)].assign(family=fam, context=ctx)
            df.to_parquet(fname(ctx, kind))
        log(f"{i + 1}/{len(ctxs)} {ctx}: {int(passes_filters(real).sum())} cells")
    log("done")


def load(kind):
    frames = [pd.read_parquet(f) for f in sorted(OUT.glob(f"{kind}_*.parquet"))]
    return pd.concat(frames, ignore_index=True)


def flag(a):
    real, null = load("real"), load("placebo")
    summary = {"trials": int(len(real)), "families": {}}
    for d in (real, null):
        d["cl"], d["cce"], d["tau"], d["tau_cond"] = False, False, np.inf, np.inf
    for (fam, meas, h), r in real.groupby(["family", "measure", "h"]):
        n = null[(null.family == fam) & (null.measure == meas) & (null.h == h)]
        tau = atlas.threshold(r.lift_t.values, [n.lift_t.values], Q, MIN_REAL)
        tau_c = atlas.threshold(r.cond_t.values, [n.cond_t.values], Q, MIN_REAL)
        for d, idx in ((real, r.index), (null, n.index)):
            x = d.loc[idx]
            cl = (x.lift_t.abs() >= tau) & (x.lift_eras_same_sign >= MIN_ERAS)
            d.loc[idx, "cl"] = cl
            d.loc[idx, "cce"] = cl & x.amplifies & (x.cond_t.abs() >= tau_c) & (x.cond_edge_cost >= 1)
            d.loc[idx, "tau"], d.loc[idx, "tau_cond"] = tau, tau_c
        summary["families"].setdefault(fam, {})[f"{meas}|{h}"] = {
            "tau": tau, "tau_cond": tau_c, "cells": int(len(r)), "cl": int(real.loc[r.index, "cl"].sum()),
            "cl_placebo": int(null.loc[n.index, "cl"].sum()), "cce": int(real.loc[r.index, "cce"].sum()),
            "cce_placebo": int(null.loc[n.index, "cce"].sum())}
    for d in (real, null):
        d[["cl", "cce"]] = d[["cl", "cce"]].astype(bool)
    lists = pd.concat([real[real.cl].assign(kind="real"), null[null.cl].assign(kind="placebo")], ignore_index=True)
    lists.to_csv(OUT / "discovery_lists.csv", index=False)
    (OUT / "discovery_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    for fam, v in summary["families"].items():
        log(fam, {k: (x["cl"], x["cl_placebo"], x["cce"], x["cce_placebo"]) for k, x in v.items()})
    log("trials", summary["trials"], "lists", lists.groupby("kind").size().to_dict())


def validation(a):
    path = OUT / "discovery_lists.csv"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT / "validation_hashes.json").write_text(json.dumps({path.name: sha}, indent=1))
    log("frozen discovery lists", sha[:12])
    lists = pd.read_csv(path)
    u, bins, names, to, base, nb = setup()
    t0, t1 = research.row_of(u.p, VAL_START), research.row_of(u.p, VAL_END)
    eras = search.half_year_edges(u.p, t0, t1)
    F, X = atlas.forward(u.ret, u.elig, t0, t1)
    want = set(lists.context)
    frames = []
    for fam, ctx, load_ctx in contexts(bins, names, to, sorted(set(lists.family))):
        if ctx not in want:
            continue
        group = load_ctx()
        G = int(group[:t1].max()) + 1
        acc = atlas.run(bins, base, F, X, u.cmat, u.index, group, G, t0, t1, nb=nb)
        v = atlas.lift_stats(acc, names, atlas.HORIZONS, eras, [str(k) for k in range(G)])[KEEP]
        keys = lists[lists.context == ctx][KEY[1:]].drop_duplicates()
        frames.append(v.merge(keys, on=KEY[1:]).assign(context=ctx, family=fam))
        log(f"validation {ctx}")
    pd.concat(frames, ignore_index=True).to_parquet(OUT / "validation_real.parquet")
    log("done")


def report(a):
    lists = pd.read_csv(OUT / "discovery_lists.csv")
    val = pd.read_parquet(OUT / "validation_real.parquet")
    m = lists.merge(val[KEY + ["cond_bp", "cond_t", "lift_bp", "lift_t", "cond_edge_cost", "cost_rt_bp"]], on=KEY,
                    how="left", suffixes=("", "_v"))
    m["rep"] = (np.sign(m.lift_bp_v) == np.sign(m.lift_bp)) & (m.lift_t_v.abs() >= 2)
    m["cce_rep"] = m.cce & m.rep & (np.sign(m.cond_bp_v) == np.sign(m.cond_bp))
    for k in (1, 2, 3):
        m[f"cce_rep_{k}x"] = m.cce_rep & (m.cond_bp_v.abs() >= k * m.cost_rt_bp_v)
    m.to_csv(OUT / "replication.csv", index=False)
    g = m.groupby(["family", "kind"]).agg(cl=("rep", "size"), rep=("rep", "sum"), rate=("rep", "mean"),
                                          cce=("cce", "sum"), cce_rep_1x=("cce_rep_1x", "sum"),
                                          cce_rep_2x=("cce_rep_2x", "sum"), cce_rep_3x=("cce_rep_3x", "sum"))
    log("\n" + g.to_string())
    r = m[m.kind == "real"]
    log("\n" + r.groupby(["family", "h", "measure"]).rep.agg(["size", "sum", "mean"]).to_string())
    log("\n" + r.groupby(["family", "amplifies"]).rep.agg(["size", "sum", "mean"]).to_string())
    verdict = {}
    for fam in sorted(set(m.family)):
        rr, pp = m[(m.family == fam) & (m.kind == "real")], m[(m.family == fam) & (m.kind == "placebo")]
        base_rate = pp.rep.mean() if len(pp) else 0.0
        ok = rr.rep.sum() >= 20 and rr.rep.mean() >= 0.25 and rr.rep.mean() >= 2 * base_rate
        verdict[fam] = {"cl": int(len(rr)), "rep": int(rr.rep.sum()), "rate": float(rr.rep.mean()) if len(rr) else 0.0,
                        "baseline": float(base_rate), "placebo_cl": int(len(pp)), "signal": bool(ok)}
    (OUT / "report.json").write_text(json.dumps(verdict, indent=1))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["discovery", "flag", "validation", "report"])
    ap.add_argument("--families", default="clock,crowd,market,flow")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    {"discovery": discovery, "flag": flag, "validation": validation, "report": report}[a.step](a)
