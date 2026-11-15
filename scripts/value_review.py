"""Recompute every number in research/VALUE_REVIEW_20261115.md from committed files.

Reads only experiments/unlocks_v1/results/events_priced.csv (R265's committed per-event table).
No network, no new data, no statistic that R265 did not already publish is used to select anything:
this is a risk/robustness description of an existing lane, not a new signal search.

usage: python scripts/value_review.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "experiments/unlocks_v1/results/events_priced.csv"
HOLD_DAYS = 7          # R265: short at the close of D-7, cover at the close of D
CAPS = (0.02, 0.038, 0.05)
N_BOOT = 4000
SEED = 7


def robustness(net):
    pos, n = int((net > 0).sum()), len(net)
    return {
        "n": n,
        "mean_pct": 100 * float(net.mean()),
        "median_pct": 100 * float(np.median(net)),
        "sd_pct": 100 * float(net.std()),
        "skew": float(stats.skew(net)),
        "kurtosis": float(stats.kurtosis(net)),
        "hit_pct": 100 * pos / n,
        "sign_test_p": float(stats.binomtest(pos, n, 0.5, alternative="greater").pvalue),
        "trimmed_mean_10pct": 100 * float(stats.trim_mean(net, 0.1)),
    }


def week_bootstrap(df, col="net1x"):
    x, wk = df[col].to_numpy(), df.week.to_numpy()
    uw = np.unique(wk)
    groups = {w: x[wk == w] for w in uw}
    rng = np.random.default_rng(SEED)
    means = np.empty(N_BOOT)
    for b in range(N_BOOT):
        pick = rng.choice(uw, size=len(uw), replace=True)
        means[b] = np.concatenate([groups[w] for w in pick]).mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"reps": N_BOOT, "seed": SEED, "ci95_low_pct": 100 * float(lo),
            "ci95_high_pct": 100 * float(hi), "p_mean_le_zero": float((means <= 0).mean())}


def tail_vs_adv(df):
    d = df.dropna(subset=["V"])
    bad, hi = d.gross < -0.40, d.V >= 0.82
    tab = [[int((bad & ~hi).sum()), int((~bad & ~hi).sum())],
           [int((bad & hi).sum()), int((~bad & hi).sum())]]
    return {"n_with_V": len(d), "n_worse_than_-40pct": int(bad.sum()),
            "all_worse_are_low_adv": bool((d[bad].V < 0.82).all()),
            "contingency_low_high_x_bad_ok": tab,
            "fisher_one_sided_p": float(stats.fisher_exact(tab, alternative="greater")[1]),
            "high_adv_worst_pct": 100 * float(d[hi].gross.min()),
            "low_adv_worst_pct": 100 * float(d[~hi].gross.min()),
            "note": "the tail/ADV association was seen AFTER R265 ran; p>0.05, so it is not a filter"}


def sizing(df):
    tot = (df.gross + df.funding).to_numpy()
    out = {}
    for cap in CAPS:
        eq, peak, mdd = 1.0, 1.0, 0.0
        for r in tot:
            eq *= 1.0 + cap * r
            peak = max(peak, eq)
            mdd = min(mdd, eq / peak - 1.0)
        out[f"{cap:.3f}"] = {"terminal_equity_x": eq, "max_drawdown_pct": 100 * mdd,
                             "worst_single_event_equity_pct": 100 * cap * float(tot.min())}
    return out


def concurrency(df):
    d = df.copy()
    d["day"] = pd.to_datetime(d.day)
    d["entry"] = d.day - pd.Timedelta(days=HOLD_DAYS)
    d["tot"] = d.gross + d.funding
    days = pd.date_range(d.entry.min(), d.day.max(), freq="D")
    conc, worst, worst_day = [], float("inf"), None
    for t in days:
        open_ev = d[(d.entry <= t) & (d.day > t)]
        conc.append(len(open_ev))
        if len(open_ev):
            s = float(open_ev.tot.sum())
            if s < worst:
                worst, worst_day = s, str(t.date())
    conc = np.array(conc)
    wk = d.groupby("week").net1x.agg(["sum", "size"])
    return {"mean_open": float(conc.mean()), "max_open": int(conc.max()),
            "days_ge5_open": int((conc >= 5).sum()), "calendar_days": len(days),
            "worst_cluster_sum_pct": 100 * worst, "worst_cluster_day": worst_day,
            "worst_week_sum_pct": 100 * float(wk["sum"].min()),
            "worst_week_events": int(wk.loc[wk["sum"].idxmin(), "size"]),
            "peak_gross_pct_at_cap": {f"{c:.3f}": 100 * c * int(conc.max()) for c in CAPS},
            "cluster_equity_hit_pct_at_cap": {f"{c:.3f}": 100 * c * worst for c in CAPS}}


def cluster_stress(df, cap=0.02, gross=0.10):
    """The worst concurrent cluster with an EXTRA shock beyond anything archived.

    Suggested by a worker (qwen3.8-max) so the archived maximum is not trusted as a bound. This is
    a description of R494's frozen rule, not a new gate; it lives here rather than in the frozen
    runner so the lane's input hash stays valid.
    """
    d = df.copy()
    d["day"] = pd.to_datetime(d.day)
    d["entry"] = d.day - pd.Timedelta(days=HOLD_DAYS)
    d["tot"] = d.gross + d.funding
    worst, n_at = 0.0, 1
    for t in pd.date_range(d.entry.min(), d.day.max(), freq="D"):
        op = d[(d.entry <= t) & (d.day > t)]
        if len(op):
            s = float(op.tot.sum())
            if s < worst:
                worst, n_at = s, len(op)
    w = min(cap, gross / n_at)
    return {"cap": cap, "gross_cap": gross, "worst_open_positions": n_at, "sized_weight": w,
            "scenarios": {label: {"cluster_return": worst + shock, "equity_hit": (worst + shock) * w}
                          for label, shock in (("as_archived", 0.0),
                                               ("plus_one_river_funding_shock", -0.45),
                                               ("plus_100pt_stress", -1.0))}}


def cluster_bootstrap(df, col="net1x"):
    """The mean's CI under several dependence structures, not just calendar weeks.

    A referee (qwen4-max-preview) objected that unlocks cluster by token, sector and date, so a
    week bootstrap may understate dependence. Recomputed under month, quarter and per-token
    clusters as well; the edge must survive all of them, not the friendliest one.
    """
    x = df[col].to_numpy()
    keys = {
        "week": df.week.to_numpy(),
        "month": df.day.str[:7].to_numpy(),
        "quarter": (df.day.str[:4] + "Q"
                    + ((df.day.str[5:7].astype(int) - 1) // 3 + 1).astype(str)).to_numpy(),
        "perp": df.perp.to_numpy(),
    }
    rng = np.random.default_rng(SEED + 4)
    out = {}
    for name, k in keys.items():
        groups = {u: x[k == u] for u in np.unique(k)}
        uk = np.unique(k)
        means = np.empty(N_BOOT)
        for b in range(N_BOOT):
            pick = rng.choice(uk, size=len(uk), replace=True)
            means[b] = np.concatenate([groups[u] for u in pick]).mean()
        lo, hi = np.percentile(means, [2.5, 97.5])
        out[name] = {"clusters": int(len(uk)), "ci95_low_pct": 100 * float(lo),
                     "ci95_high_pct": 100 * float(hi), "p_mean_le_zero": float((means <= 0).mean())}
    return out


def main():
    df = pd.read_csv(EVENTS)
    rep = {
        "source": str(EVENTS.relative_to(ROOT)),
        "source_sha256": __import__("hashlib").sha256(EVENTS.read_bytes()).hexdigest(),
        "robustness_net1x": robustness(df.net1x.to_numpy()),
        "week_bootstrap": week_bootstrap(df),
        "cluster_bootstrap_by_dependence": cluster_bootstrap(df),
        "tail_vs_adv": tail_vs_adv(df),
        "sizing_sequential_no_stop": sizing(df),
        "concurrency": concurrency(df),
        "cluster_stress_beyond_archive": cluster_stress(df),
        "events_per_year": {k: int(v) for k, v in df.groupby(df.day.str[:4]).size().items()},
        "has_intrabar_path": any(c in df.columns for c in ("high", "low", "mfe", "mae")),
        "limits": [
            "gate 0 description of an existing lane; no new signal, no selection",
            "sequential sizing assumes one event resolves at a time; see concurrency for the cluster bound",
            "no stop is simulated: the committed file has no intrabar path",
            "the ADV tail filter is post-hoc and is NOT adopted",
        ],
    }
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main()
