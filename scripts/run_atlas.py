"""atlas_v1 (R185): the gross-edge atlas, as set out in experiments/atlas_v1/PREREG.md.

usage: python scripts/run_atlas.py discovery [--tensors main,clock,flow] [--groupings session,tier,regime]
       python scripts/run_atlas.py validation
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

LANE = ROOT / "experiments" / "atlas_v1"
OUT = LANE / "results"
RD = data.ROOT / "research"
VAL_START, VAL_END = "2024-01-01", "2025-07-01"
Q, MIN_REAL, MIN_SUPPORT, MIN_DAYS, MIN_DAYS_GROUP = 0.10, 5, 0.01, 200, 100
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def tensors(which):
    out = {}
    for name in which:
        if name == "main":
            meta = json.loads((RD / "meta.json").read_text())
            out[name] = (np.load(RD / "bins.npy", mmap_mode="r"), meta["names"])
        else:
            path = RD / f"bins_{name}.npy"
            if not path.exists():
                log(f"tensor {name} missing, skipped")
                continue
            names = json.loads((RD / f"meta_{name}.json").read_text())["names"]
            out[name] = (np.load(path, mmap_mode="r"), [f"{name}:{n}" if name == "clock" else n for n in names])
    return out


def groupings(u, which, t0, t1):
    T, S = u.ret.shape
    g = {}
    if "session" in which:
        g["session"] = (np.broadcast_to(atlas.session_groups(u.p.t)[:, None], (T, S)), atlas.SESSION_NAMES)
    if "tier" in which:
        g["tier"] = (atlas.tier_groups(u.rank), atlas.TIER_NAMES)
    if "regime" in which:
        btc = u.p.symbols.index("BTCUSDT")
        g["regime"] = (np.broadcast_to(atlas.regime_groups(u.p["close"][:, btc])[:, None], (T, S)), atlas.REGIME_NAMES)
    return {k: (np.ascontiguousarray(v), n) for k, (v, n) in g.items()}


def one_pass(u, tens, ret, group, gnames, t0, t1, eras):
    F, X = atlas.forward(ret, u.elig, t0, t1)
    frames = []
    for tname, (bins, names) in tens.items():
        views = np.arange(bins.shape[0], dtype=np.int64)
        acc = atlas.run(bins, views, F, X, u.cmat, u.index, group, len(gnames), t0, t1)
        to = atlas._time_only(bins, views, *u.index, t0, t1, 7)
        df = atlas.stats(acc, names, atlas.HORIZONS, eras, gnames, to)
        df.insert(0, "tensor", tname)
        frames.append(df)
        del acc
    return pd.concat(frames, ignore_index=True)


def eligible(df, group_level=False):
    ok = (df["support"] >= MIN_SUPPORT) & (df["days"] >= (MIN_DAYS_GROUP if group_level else MIN_DAYS))
    return ok & ~((df["measure"] == "excess") & df["time_only"]) & df["t"].notna()


def taus(real, nulls, group_level):
    """{(tensor, measure, h): tau} from the real and placebo tables of one grouping."""
    sel = (lambda d: d[d.group != "all"]) if group_level else (lambda d: d[d.group == "all"])
    r = sel(real)
    r = r[eligible(r, group_level)]
    ns = [sel(n) for n in nulls]
    ns = [n[eligible(n, group_level)] for n in ns]
    out = {}
    for key, rr in r.groupby(["tensor", "measure", "h"]):
        nn = [n[(n.tensor == key[0]) & (n.measure == key[1]) & (n.h == key[2])].t.values for n in ns]
        out[key] = atlas.threshold(rr.t.values, nn, Q, MIN_REAL)
    return out


def flag(df, tau, group_level):
    key = list(zip(df.tensor, df.measure, df.h))
    th = np.array([tau.get(k, np.inf) for k in key])
    need = 4 if group_level else 5
    ok = eligible(df, group_level) & (df.t.abs() >= th) & (df.eras_same_sign >= need)
    if not group_level:
        ok &= df.breadth >= 0.6
    return ok, th


def discovery(a):
    u, _, _ = research.load_universe()
    t0, t1 = 0, research.row_of(u.p, research.DISC_END)
    eras = search.half_year_edges(u.p, t0, t1)
    tens = tensors(a.tensors.split(","))
    tag = "+".join(tens)
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"tensors": list(tens), "eras": eras.tolist(), "groupings": {}}
    for gname, (group, names) in groupings(u, a.groupings.split(","), t0, t1).items():
        log(f"{gname}: real pass")
        real = one_pass(u, tens, u.ret, group, names, t0, t1, eras)
        rng = np.random.default_rng(sum(map(ord, gname)))
        nulls = []
        for k in range(2):
            shift = 24 * int(rng.integers(120, 976)) + 12
            log(f"{gname}: placebo {k} (shift {shift} h)")
            nulls.append(one_pass(u, tens, search.shifted_returns(u, shift, t1), group, names, t0, t1, eras))
        tau_all, tau_grp = taus(real, nulls, False), taus(real, nulls, True)
        real["cge"], real["tau"] = flag(real, tau_all, False)
        gl = real.group != "all"
        okg, thg = flag(real[gl], tau_grp, True)
        real.loc[gl, "cge"], real.loc[gl, "tau"] = okg.values, thg
        for k, n in enumerate(nulls):
            n["cge"], n["tau"] = flag(n, tau_all, False)
            n.to_parquet(OUT / f"disc_{tag}_{gname}_placebo{k}.parquet")
        real.to_parquet(OUT / f"disc_{tag}_{gname}_real.parquet")
        trials = int(((real.group != "all") | (gname == "session")).sum())
        summary["groupings"][gname] = {
            "trials": trials, "tau_all": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in tau_all.items()},
            "tau_group": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in tau_grp.items()},
            "cge_all": int(real[real.group == "all"].cge.sum()), "conditional": int(real[gl].cge.sum()),
            "placebo_cge_all": [int(n[n.group == "all"].cge.sum()) for n in nulls]}
        log(f"{gname}: tau(all) {summary['groupings'][gname]['tau_all']}")
        log(f"{gname}: confident edges {summary['groupings'][gname]['cge_all']} (placebo "
            f"{summary['groupings'][gname]['placebo_cge_all']}), conditional {summary['groupings'][gname]['conditional']}")
    (OUT / f"disc_{tag}_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    log("done")


def validation(a):
    """Freeze the discovery lists, then score them once on 2024-01-01..2025-06-30."""
    u, _, _ = research.load_universe()
    t0, t1 = research.row_of(u.p, VAL_START), research.row_of(u.p, VAL_END)
    assert t1 <= u.holdout_row
    eras = search.half_year_edges(u.p, t0, t1)
    tag = "+".join(a.tensors.split(","))
    lists, hashes = [], {}
    for f in sorted(OUT.glob(f"disc_{tag}_*_real.parquet")):
        d = pd.read_parquet(f)
        d = d[d.cge]
        lists.append(d.assign(source=f.stem))
    for f in sorted(OUT.glob(f"disc_{tag}_*_placebo*.parquet")):
        d = pd.read_parquet(f)
        lists.append(d[d.cge & (d.group == "all")].assign(source=f.stem))
    found = pd.concat(lists, ignore_index=True)
    path = OUT / f"discovery_lists_{tag}.csv"
    found.to_csv(path, index=False)
    hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    log("frozen discovery lists", hashes)
    tens = tensors(sorted(set(found.tensor)))
    frames = []
    for gname, (group, names) in groupings(u, sorted({s.split("_")[-2] for s in found.source}), t0, t1).items():
        log(f"validation pass: {gname}")
        v = one_pass(u, tens, u.ret, group, names, t0, t1, eras)
        frames.append(v.assign(grouping=gname))
    val = pd.concat(frames, ignore_index=True)
    val.to_parquet(OUT / f"validation_{tag}_real.parquet")
    (OUT / f"validation_{tag}_hashes.json").write_text(json.dumps(hashes, indent=1))
    log("done")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["discovery", "validation"])
    ap.add_argument("--tensors", default="main,clock")
    ap.add_argument("--groupings", default="session,tier,regime")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    discovery(a) if a.step == "discovery" else validation(a)
