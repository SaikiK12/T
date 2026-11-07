"""R414 famswitch_v1: can a blind switch between the lab's strategy streams beat holding them all equally? As set out
in experiments/famswitch_v1/PREREG.md. Gate 0: every stream is an archive result its own lane already read.

Streams (daily net returns at each lane's 1x cost, one unit of capital each), rebuilt by scripts/xbook_archive.py's
functions over 2023-06-01..2026-09-30:
- carry: R278 A, R278 B, R279 A, R279 B (cross-venue funding spreads);
- flow: R215 A, R215 B, R218 X2 (altcoin flow books);
- events: R266 unlocks, R268 delist, R270 montag, R272 FF, R272 PL (each lane's legs by exit day, over 10 slots).

Allocators (weights for day d use returns up to d - LAG only):
- EQ: equal capital over the streams available on d (the baseline);
- HEDGE: exponential weights on each stream's discounted past return (half-life 30 days, eta 20);
- FTL: on the first day of each month, all capital in the stream with the best return over the previous 90 days;
- ORACLE (reference only, uses the future): each month, all capital in that month's best stream.
Switching costs m x 0.20% per unit of capital moved, m = 1, 2, 3.

usage: python scripts/run_famswitch.py [--plumbing]
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
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg, stats  # noqa: E402
import xbook_archive as xa  # noqa: E402

LANE = ROOT / "experiments" / "famswitch_v1"
LAG = 2                          # weights for d use returns through d - 2 (one day of reporting slack)
WARM = 90                        # a stream joins after 90 days with data
HALF = 30                        # HEDGE discount half-life (days)
ETA = 20.0                       # HEDGE learning rate on discounted return (a 5% lead weighs e^1 = 2.7x)
LOOK = 90                        # FTL trailing window (days)
SWITCH_COST = 0.002              # per unit of capital moved, at m = 1
MS = (1, 2, 3)
NW = 10
HALVES = (("2023-09-01", "2025-01-01"), ("2025-01-01", "2026-10-01"))
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def streams():
    days = pd.date_range(*xa.WINDOW, freq="D")
    carry, flow, t = xa.carry_sleeves(), xa.flow_sleeves(), xa.event_tickets()
    ev = {lane: (g.groupby("day").net.sum() / xa.SLOTS).reindex(days).fillna(0.0) for lane, g in t.groupby("lane")}
    S = pd.concat([carry.reindex(days), flow.reindex(days), pd.DataFrame(ev, index=days)], axis=1)
    return S


def available(S):
    """True where a stream has at least WARM days of data before d - LAG (and data on d)."""
    seen = S.notna().cumsum().shift(LAG).fillna(0)
    return (seen >= WARM) & S.notna()


def w_eq(S, A):
    return A.div(A.sum(axis=1), axis=0).fillna(0.0)


def w_hedge(S, A, half=HALF, eta=ETA):
    lam = 0.5 ** (1 / half)
    R = S.fillna(0.0).to_numpy()
    disc = np.zeros_like(R)
    acc = np.zeros(R.shape[1])
    for i in range(len(R)):
        acc = acc * lam + R[i]
        disc[i] = acc
    score = pd.DataFrame(disc, index=S.index, columns=S.columns).shift(LAG)
    z = np.exp(eta * (score - score.where(A).max(axis=1).values[:, None])).where(A, 0.0)
    return z.div(z.sum(axis=1), axis=0).fillna(0.0)


def w_ftl(S, A, look=LOOK):
    trail = S.fillna(0.0).rolling(look, min_periods=look).sum().shift(LAG)
    W = pd.DataFrame(0.0, index=S.index, columns=S.columns)
    pick = None
    for d in S.index:
        if d.day == 1 or pick is None:
            row = trail.loc[d].where(A.loc[d])
            pick = row.idxmax() if row.notna().any() else None
        if pick is not None and A.loc[d, pick]:
            W.loc[d, pick] = 1.0
    return W


def w_oracle(S, A):
    """Reference only: uses each month's own returns."""
    W = pd.DataFrame(0.0, index=S.index, columns=S.columns)
    for _, g in S.where(A).groupby(S.index.to_period("M")):
        tot = g.sum(min_count=1)
        if tot.notna().any():
            W.loc[g.index, tot.idxmax()] = 1.0
    return W.where(A, 0.0)


def run(S, W, m):
    gross = (W * S.fillna(0.0)).sum(axis=1)
    turn = W.diff().abs().sum(axis=1, min_count=1).fillna(W.abs().sum(axis=1))   # day 1: the initial entry
    return gross - m * SWITCH_COST * turn, turn


def describe(x, turn=None):
    x = x.dropna()
    eq = (1 + x).cumprod()
    out = {"days": len(x), "mean_bp_day": float(x.mean() * 1e4), "ann_pct": float(x.mean() * 365 * 100),
           "sharpe": float(x.mean() / x.std(ddof=1) * np.sqrt(365)) if x.std() > 0 else None,
           "nw_t": float(stats.newey_west_t(x.values, NW)[2]), "max_dd_pct": float((eq / eq.cummax() - 1).min() * 100),
           "worst_month_pct": float(x.groupby(x.index.to_period("M")).sum().min() * 100),
           "halves_bp_day": [float(x[a:b].mean() * 1e4) if len(x[a:b]) else None for a, b in HALVES]}
    if turn is not None:
        out["turnover_per_day"] = float(turn.loc[x.index].mean())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only")
    a = ap.parse_args()
    if not a.plumbing:
        sha = prereg.verify(LANE / "PREREG.md")
        from scripts.run_clockflow import check_inputs
        log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match")
    S = streams()
    A = available(S)
    start = A.any(axis=1).idxmax()
    if a.plumbing:
        log(f"{S.shape[1]} streams, {len(S)} days {S.index[0].date()}..{S.index[-1].date()}; first allocatable "
            f"{start.date()}; streams available per day min {int(A[start:].sum(axis=1).min())} max "
            f"{int(A[start:].sum(axis=1).max())}")
        for c in S:
            log(f"  {c}: {int(S[c].notna().sum())} days with data, first allocatable "
                f"{A[c].idxmax().date() if A[c].any() else None}")
        return
    S, A = S[start:], A[start:]
    Ws = {"EQ": w_eq(S, A), "HEDGE": w_hedge(S, A), "FTL": w_ftl(S, A), "ORACLE": w_oracle(S, A)}
    res = {"prereg_sha256": sha, "window": [str(S.index[0].date()), str(S.index[-1].date())],
           "streams": list(S.columns), "methods": {}, "vs_eq": {}, "decision": {}}
    net = {}
    for k, W in Ws.items():
        res["methods"][k] = {}
        for m in MS:
            x, turn = run(S, W, m)
            net[(k, m)] = x
            res["methods"][k][f"{m}x"] = describe(x, turn)
        res["methods"][k]["mean_weight"] = {c: round(float(v), 4) for c, v in W.mean().items()}
    res["streams_alone"] = {c: describe(S[c].where(A[c])) for c in S}
    for k in ("HEDGE", "FTL"):
        d1, d2 = net[(k, 1)] - net[("EQ", 1)], net[(k, 2)] - net[("EQ", 2)]
        t = float(stats.newey_west_t(d1.values, NW)[2])
        halves = [float(d1[a:b].mean()) for a, b in HALVES]
        checks = {"diff_1x_mean_gt0": bool(d1.mean() > 0), "diff_1x_nw_t_ge_2.24": t >= 2.24,
                  "diff_2x_mean_gt0": bool(d2.mean() > 0), "diff_1x_each_half_gt0": all(h > 0 for h in halves)}
        res["vs_eq"][k] = {"diff_bp_day_1x": float(d1.mean() * 1e4), "nw_t_1x": t,
                           "diff_bp_day_2x": float(d2.mean() * 1e4), "halves_bp_day": [h * 1e4 for h in halves]}
        res["decision"][k] = {"checks": checks, "verdict": "SWITCH_ADDS" if all(checks.values()) else "NULL"}
        log(f"{k}: {res['decision'][k]['verdict']} {json.dumps(checks)}")
    pick_best = (Ws["FTL"].groupby(S.index.to_period("M")).first().idxmax(axis=1)
                 == Ws["ORACLE"].groupby(S.index.to_period("M")).first().idxmax(axis=1))
    res["ftl_picked_month_best_share"] = float(pick_best.mean())
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
    pd.DataFrame({f"{k}_{m}x": v for (k, m), v in net.items()}).to_csv(LANE / "results" / "daily.csv")
    log("done")


if __name__ == "__main__":
    main()
