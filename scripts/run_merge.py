"""merge_v1 (R186): walk-forward merge of many signals into one forecast, traded only where it clears costs, as set
out in experiments/merge_v1/PREREG.md.

usage: python scripts/run_merge.py --tag M1 [--tensors main,clock] [--train-days 365] [--placebo]
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
from lab import atlas, inference, merge, prereg, research, search, stats  # noqa: E402
from run_atlas import tensors as load_tensors  # noqa: E402

LANE = ROOT / "experiments" / "merge_v1"
START, END = "2022-01-01", "2025-07-01"
HORIZONS = [4, 24, 72]
GRID = [1, 3, 10, 30, 100, 200]
K_IN = [0.0, 0.5, 1.0, 1.5, 2.0]
CMULT = [0.0, 0.25, 0.5, 1.0, 2.0]
PRIMARY = {"h": 24, "measure": "excess", "N": 30, "k_in": 1.0, "cmult": 1.0}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def month_starts(p, a, b):
    days = pd.date_range(a, b, freq="MS", tz="UTC")
    return [research.row_of(p, d.strftime("%Y-%m-%d")) for d in days]


def summarize(daily, years):
    d = daily[np.isfinite(daily)]
    if len(d) < 30 or d.std() == 0:
        return {}
    eq = np.cumsum(d)
    out = {"ann": d.mean() * 365, "sharpe": d.mean() / d.std(ddof=1) * np.sqrt(365),
           "t_nw": stats.newey_west_t(d, 5)[2],
           "max_dd": float(np.max(np.maximum.accumulate(eq) - eq)), "hit": float((d > 0).mean())}
    for y, idx in years.items():
        out[f"y{y}"] = float(daily[idx].sum())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--tensors", default="main,clock")
    ap.add_argument("--train-days", type=int, default=365)
    ap.add_argument("--placebo", action="store_true")
    a = ap.parse_args()
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out_dir = LANE / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = a.tag + ("_placebo" if a.placebo else "")

    u, _, _ = research.load_universe()
    hold = u.holdout_row
    tens = {}
    for name, (bins, names) in load_tensors(a.tensors.split(",")).items():
        to = atlas._time_only(bins, np.arange(bins.shape[0], dtype=np.int64), *u.index, 0, hold, 7)
        tens[name] = (bins, names, to.astype(bool))
    ret = u.ret
    if a.placebo:
        rng = np.random.default_rng(sum(map(ord, a.tag)))
        shift = 24 * int(rng.integers(120, hold // 24 - 120)) + 12
        log("placebo shift", shift, "hours")
        ret = search.shifted_returns(u, shift, hold)
    refits = month_starts(u.p, START, END)
    assert refits[-1] <= hold
    log(f"{tag}: {len(refits) - 1} monthly refits, tensors {list(tens)}, train {a.train_days} days")
    fc, picks = merge.walk_forward(tens, ret, u.elig, u.cmat, u.index, refits, a.train_days, 72, HORIZONS, GRID,
                                   log=log)

    r0, r1 = refits[0], refits[-1]
    D = (r1 - r0) // 24
    day_year = pd.to_datetime(u.p.t[r0:r1:24], unit="ms", utc=True).year.values
    years = {y: np.flatnonzero(day_year == y) for y in np.unique(day_year)}
    rows, series = [], {}
    for (h, m), f in fc.items():
        ls = m == "excess"
        for ni, N in enumerate(GRID):
            for k in K_IN:
                variants = [(c, k, "fixed") for c in CMULT] + [(c, k * c, "fee_aware") for c in (0.25, 0.5) if k > 0]
                for cm, k_eff, kind in variants:
                    o = merge.trade(f[ni], ret, u.elig, u.index, u.cmat, r0, r1, k_in=k_eff, k_out=0.0, slots=10,
                                    min_hold=4, cmult=cm, ls=ls)
                    day = o[: D * 24].reshape(D, 24, 6)
                    net, gross, cost = day[..., 0].sum(1), day[..., 2].sum(1), day[..., 1].sum(1)
                    row = {"h": h, "measure": m, "N": N, "k_in": k, "cmult": cm, "threshold": kind,
                           "gross_ann": gross.mean() * 365, "cost_ann": cost.mean() * 365,
                           "turnover_day": day[..., 5].sum(1).mean(), "n_long": day[..., 3].mean(),
                           "n_short": day[..., 4].mean()}
                    row.update(summarize(net, years))
                    rows.append(row)
                    series[f"{h}|{m}|{N}|{k}|{cm}|{kind}"] = net.astype(np.float32)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / f"{tag}_grid.csv", index=False)
    np.savez_compressed(out_dir / f"{tag}_daily.npz", **series)

    names_of = {t: v[1] for t, v in tens.items()}
    sel = []
    for (h, m), per in picks.items():
        for r, cells in zip(refits[:-1], per):
            day = pd.to_datetime(u.p.t[r], unit="ms", utc=True).strftime("%Y-%m")
            for rank, (tn, v, b, mean, t) in enumerate(cells[:30]):
                sel.append({"month": day, "h": h, "measure": m, "rank": rank, "tensor": tn, "name": names_of[tn][v],
                            "bin": b, "mean_bp": mean * 1e4, "t": t})
    pd.DataFrame(sel).to_csv(out_dir / f"{tag}_selections.csv", index=False)

    fixed = df[(df.threshold == "fixed") & (df.cmult == 1.0)].dropna(subset=["sharpe"])
    srs = fixed.sharpe.values / np.sqrt(365)
    best = fixed.sort_values("sharpe").iloc[-1]
    key = f"{best.h}|{best.measure}|{best.N}|{best.k_in}|1.0|fixed"
    p = PRIMARY
    prim = df[(df.h == p["h"]) & (df.measure == p["measure"]) & (df.N == p["N"]) & (df.k_in == p["k_in"])
              & (df.threshold == "fixed")].set_index("cmult")
    summary = {"tag": tag, "configs_at_1x": int(len(fixed)), "trials_total": int(len(df)),
               "primary": prim.to_dict(orient="index"),
               "best_at_1x": {"config": key, "sharpe": float(best.sharpe),
                              "dsr": inference.dsr(series[key].astype(np.float64), srs, len(srs))}}
    (out_dir / f"{tag}_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    log("done", tag)


if __name__ == "__main__":
    main()
