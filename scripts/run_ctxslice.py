"""ctxslice_v1 (R201): the replicated excess context edges of atlas_ctx (R192) and atlas_mtf (R195) as one slice book,
as set out in experiments/ctxslice_v1/PREREG.md.

usage: python scripts/run_ctxslice.py list        write and hash the cell list (no statistic)
       python scripts/run_ctxslice.py insample    stage 1, 2021-01-01..2025-06-30 (selection-biased filter)
       python scripts/run_ctxslice.py holdout     stage 2, one shot, only if stage 1 passed its gate
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
sys.path.insert(0, str(ROOT / "scripts"))
from lab import events, prereg, slices  # noqa: E402
import run_context_atlas as rca  # noqa: E402

LANE = ROOT / "experiments" / "ctxslice_v1"
OUT = LANE / "results"
SOURCES = {"ctx": ROOT / "experiments" / "atlas_ctx" / "results" / "replication.csv",
           "mtf": ROOT / "experiments" / "atlas_mtf" / "results" / "replication.csv"}
GROUPS = ("all", "ctx", "mtf", "h1_4", "h12_24", "h72")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def make_list():
    frames = []
    for src, path in SOURCES.items():
        m = pd.read_csv(path)
        x = m[(m.kind == "real") & (m.measure == "excess") & (m.cce_rep_2x == True)]  # noqa: E712
        frames.append(x.assign(source=src)[["source", "family", "context", "code", "view", "name", "bin", "h",
                                            "cond_bp", "cond_bp_v", "share"]])
    cells = pd.concat(frames, ignore_index=True)
    cells["side"] = np.sign(cells.cond_bp).astype(int)
    path = OUT / "cells.csv"
    OUT.mkdir(parents=True, exist_ok=True)
    cells.to_csv(path, index=False)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    (OUT / "cells.sha256").write_text(sha + "\n")
    log(f"{len(cells)} cells ({cells.source.value_counts().to_dict()}), sha {sha[:12]}")


def load_cells():
    path = OUT / "cells.csv"
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert sha == (OUT / "cells.sha256").read_text().strip(), "cells.csv changed after it was hashed"
    return pd.read_csv(path)


def groups_of(c):
    g = ["all", c.source]
    g.append("h1_4" if c.h <= 4 else "h12_24" if c.h <= 24 else "h72")
    return g


def build_positions(cells, u, bins, names, to, t0, t1, M=None):
    """Summed positions per group over [t0, t1); M (the size normalizer) is computed on [0, holdout_row) if None."""
    fams = sorted(set(cells.family))
    ctxs = {ctx: load for fam, ctx, load in rca.contexts(bins, names, to, fams)}
    P = {g: np.zeros((t1 - t0, u.elig.shape[1])) for g in GROUPS} if M is not None else None
    counts = {}
    ho = u.holdout_row
    for ctx, sub in cells.groupby("context", sort=True):
        code_arr = ctxs[ctx]()
        for i, c in sub.iterrows():
            ind = (np.asarray(bins[c.view]) == c.bin) & (code_arr == c.code) & u.elig
            counts[i] = float(ind[:ho].sum()) / ho
            if M is not None:
                pos = slices.positions(ind, int(c.h), t0, t1, 1.0 / (int(c.h) * M), int(c.side))
                for g in groups_of(c):
                    P[g] += pos
        log(f"context {ctx}: {len(sub)} cells")
    return P, counts


def run_books(P, u, t0, t1, period):
    btc = u.p.symbols.index("BTCUSDT")
    top10 = u.rank <= 10
    only_btc = np.zeros_like(u.elig)
    only_btc[:, btc] = True
    c_btc = u.p["close"][t0:t1 + 1:24, btc].astype(np.float64)
    r_btc = np.full((t1 - t0) // 24, np.nan)
    r_btc[:len(c_btc) - 1] = c_btc[1:] / c_btc[:-1] - 1
    days = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True)
    rows, keep = [], {}
    variants = [("all", "universe", (True, None), cm) for cm in (1.0, 2.0, 3.0)]
    variants += [("all", "top10", (True, top10), 1.0), ("all", "btc", (True, only_btc), 1.0),
                 ("all", "none", (False, None), 1.0)]
    variants += [(g, "universe", (True, None), 1.0) for g in GROUPS[1:]]
    for g, hname, (hedge, basket), cm in variants:
        o = slices.run(P[g], u.ret, u.elig, u.cmat, t0, t1, hedge=hedge, cmult=cm, basket=basket)
        n = o["daily"]
        D = len(n)
        ok = np.isfinite(r_btc[:D])
        r = {"period": period, "book": g, "hedge": hname, "cmult": cm, "days": D, "total": float(n.sum()),
             "mean_bp_day": float(n.mean() * 1e4), **events.summary(n),
             "beta_btc": float(np.polyfit(r_btc[:D][ok], n[ok], 1)[0]) if ok.sum() > 2 else np.nan,
             "gross_exposure": float(o["gross_exposure"].mean()), "net_exposure": float(o["net_exposure"].mean()),
             "turnover_day": float(o["turnover"].sum() / max(D, 1)),
             "gross_day_bp": float(o["gross"].sum() / max(D, 1) * 1e4),
             "cost_day_bp": float(o["cost"].sum() / max(D, 1) * 1e4)}
        rows.append(r)
        if cm == 1.0:
            keep[f"{g}_{hname}"] = n
    df = pd.DataFrame(rows)
    prim = keep["all_universe"]
    s = pd.Series(prim, index=days[:len(prim)])
    by = s.groupby(days[:len(prim)].year if period == "insample" else days[:len(prim)].strftime("%Y-%m")).sum()
    return df, keep, by


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=("list", "insample", "holdout"))
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    if a.stage == "list":
        return make_list()
    cells = load_cells()
    u, bins, names, to, _, _ = rca.setup("all")
    ho = u.holdout_row
    if a.stage == "insample":
        _, counts = build_positions(cells, u, bins, names, to, 0, ho, M=None)
        M = float(sum(counts.values()))
        log(f"M = {M:.3f} coin-states per hour (sum over cells, 2021-2025H1)")
        P, _ = build_positions(cells, u, bins, names, to, 0, ho, M=M)
        df, keep, by = run_books(P, u, 0, ho, "insample")
        p = df[(df.book == "all") & (df.hedge == "universe") & (df.cmult == 1.0)].iloc[0]
        gate = bool(p.mean_bp_day > 0 and p.t_nw >= 2)
        (OUT / "insample.json").write_text(json.dumps({"M": M, "gate_pass": gate, "t_nw": p.t_nw, "ann": p.ann},
                                                      indent=1, default=float))
        name = "insample"
    else:
        ins = json.loads((OUT / "insample.json").read_text())
        if not ins["gate_pass"]:
            raise SystemExit("stage 1 did not pass its gate: the holdout is not read")
        assert not (OUT / "holdout.csv").exists(), "the holdout was already run once"
        t1 = len(u.p.t) - len(u.p.t) % 24
        P, _ = build_positions(cells, u, bins, names, to, ho, t1, M=ins["M"])
        df, keep, by = run_books(P, u, ho, t1, "holdout")
        p = df[(df.book == "all") & (df.hedge == "universe") & (df.cmult == 1.0)].iloc[0]
        confirmed = bool(p.mean_bp_day > 0 and p.t_nw >= 2)
        (OUT / "verdict.json").write_text(json.dumps({"confirmed": confirmed, "t_nw": p.t_nw, "ann": p.ann,
                                                      "total": p.total, "days": int(p.days)}, indent=1, default=float))
        log("CONFIRMED" if confirmed else "NOT CONFIRMED")
        name = "holdout"
    df.to_csv(OUT / f"{name}.csv", index=False)
    np.savez_compressed(OUT / f"{name}_daily.npz", **keep)
    by.to_csv(OUT / f"{name}_by_period.csv", header=["net"])
    log("\n" + df.round(4).to_string(index=False))
    log("by period:\n" + by.round(4).to_string())


if __name__ == "__main__":
    main()
