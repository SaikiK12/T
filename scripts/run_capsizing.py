"""capsizing_v1 (R496, M545): does entry-spread sizing beat fixed size on UNSEEN trades?

Fits two numbers on discovery (entry < 2024), then reads validation once. Size uses only the
entry-time spread; realised PnL never chooses a size. Costs are measured per venue, and each trade
is charged the WORSE of its own two venues.

usage: python scripts/run_capsizing.py
"""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import capacity, prereg, registry  # noqa: E402

LANE = ROOT / "experiments/capsizing_v1"
TRADES = ROOT / "experiments/xfund_kd_v1/results/trades.csv"
BG = ROOT / "experiments/bgcosts_v1/results/books.csv"
KD = LANE / "results/books_kd.csv"
SPLIT = "2024-01-01"
SIZES = (1_000, 5_000, 10_000)
BASE_N = 10_000
MIN_N = 1_000
CAP = 10_000
MULT = (1, 2, 3)
N_BOOT = 2000
BLOCK = 20
SEED = 20261115


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_inputs():
    block = re.search(r"```inputs\n(.*?)```", (LANE / "PREREG.md").read_text(), re.S).group(1)
    n = 0
    for line in block.strip().splitlines():
        want, rel = line.split()
        if sha(ROOT / rel) != want:
            raise SystemExit(f"{rel}: sha256 differs from the frozen inputs block")
        n += 1
    return n


def curves():
    """(a_bp, beta, depth_usd) per venue, fitted on that venue's own measured median costs."""
    out = {}
    for frame in (pd.read_csv(BG), pd.read_csv(KD)):
        for v, g in frame.groupby("venue"):
            ys = [g[f"side_{n//1000}k_bp"].median() for n in SIZES]
            a, b, r2 = capacity.fit_cost_curve(SIZES, ys)
            out[v] = {"a_bp": a, "beta": b, "r2": r2,
                      "depth_usd": float(g.usd_ask_1pct.median())}
    return out


def worse(v1, v2, cv, n):
    """The conservative leg: whichever of the trade's two venues costs more at this size."""
    a = capacity.cost_bp(n, cv[v1]["a_bp"], cv[v1]["beta"]) if v1 in cv else np.nan
    b = capacity.cost_bp(n, cv[v2]["a_bp"], cv[v2]["beta"]) if v2 in cv else np.nan
    if np.isfinite(a) and np.isfinite(b):
        return max(a, b)
    return a if np.isfinite(a) else b


def load():
    t = pd.read_csv(TRADES)
    t["gross"] = t.price_pnl + t.funding_pnl
    t["hold"] = (pd.to_datetime(t.exit) - pd.to_datetime(t.entry)).dt.days.clip(lower=1)
    t["x"] = t.spread_in_ann * t.hold / 365.0     # ex-ante: entry spread x the hold it will run
    return t.sort_values("entry").reset_index(drop=True)


def fit_discovery(d):
    """OLS through the origin of realised gross on the ex-ante spread-time product. Two numbers."""
    x, y = d.x.to_numpy(), d.gross.to_numpy()
    k = float((x @ y) / (x @ x))
    return k, float(d.hold.median())


def size_of(row, k, cv):
    g_hat = k * row.spread_in_ann * row.hold / 365.0
    if not np.isfinite(g_hat) or g_hat <= 0:
        return MIN_N, "nonpositive_forecast", g_hat
    v1, v2 = row.long, row.short
    use = [v for v in (v1, v2) if v in cv]
    if not use:
        return MIN_N, "no_curve", g_hat
    v = max(use, key=lambda z: capacity.cost_bp(BASE_N, cv[z]["a_bp"], cv[z]["beta"]))
    c = cv[v]
    r = capacity.constrained_notional(g_hat, c["a_bp"], c["beta"],
                                      depth_usd=c["depth_usd"], fit_range=SIZES, capital_cap=CAP)
    return max(MIN_N, r["n"]), r["binding"], g_hat


def net_dollars(t, ns, cv, mult):
    n = np.asarray(ns, dtype=float)
    cost = np.array([worse(r.long, r.short, cv, ni) for r, ni in zip(t.itertuples(), n)])
    return n * (t.gross.to_numpy() - mult * cost / 1e4)


def block_bootstrap_diff(diff, n_boot=N_BOOT, block=BLOCK, seed=SEED):
    x = np.asarray(diff, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < block * 2:
        return float("nan"), float("nan"), float("nan")
    z = x - x.mean()
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(len(z) / block))
    means = np.empty(n_boot)
    for b in range(n_boot):
        st = rng.integers(0, len(z) - block + 1, size=nb)
        means[b] = np.concatenate([z[s:s + block] for s in st])[:len(z)].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo + x.mean()), float(hi + x.mean()), float((means + x.mean() <= 0).mean())


def main():
    frozen = prereg.verify(LANE / "PREREG.md")
    n_in = check_inputs()
    cv = curves()
    t = load()
    disc = t[t.entry < SPLIT]
    val = t[t.entry >= SPLIT].reset_index(drop=True)
    k, hold_med = fit_discovery(disc)

    ns, binds, gh = [], [], []
    for r in val.itertuples():
        n, b, g = size_of(r, k, cv)
        ns.append(n); binds.append(b); gh.append(g)
    res = {}
    for m in MULT:
        rule = net_dollars(val, ns, cv, m)
        base = net_dollars(val, [BASE_N] * len(val), cv, m)
        diff = rule - base
        lo, hi, p = block_bootstrap_diff(diff)
        res[str(m)] = {"rule_total": float(np.nansum(rule)), "base_total": float(np.nansum(base)),
                       "diff_total": float(np.nansum(diff)),
                       "diff_mean_per_trade": float(np.nanmean(diff)),
                       "ci95_low": lo, "ci95_high": hi, "p_diff_le_zero": p,
                       "rule_hit": float((rule > 0).mean()), "base_hit": float((base > 0).mean())}
    d1, d2 = res["1"], res["2"]
    passed = (d1["diff_total"] > 0 and np.isfinite(d1["ci95_low"]) and d1["ci95_low"] > 0
              and d2["diff_total"] > 0)
    rep = {
        "round": "R496", "method": "M545", "lane": "capsizing_v1",
        "prereg_sha256": frozen, "inputs_checked": n_in,
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "program_trials_before": registry.program_trials(ROOT / "registry/rounds.csv"),
        "trials": 1,
        "discovery_trades": len(disc), "validation_trades": len(val),
        "fitted_on_discovery_only": {"k": k, "median_hold_days": hold_med},
        "curves": cv,
        "sizing_bindings": pd.Series(binds).value_counts().to_dict(),
        "chosen_size_median": float(np.median(ns)),
        "validation": res,
        "verdict": "PASS" if passed else "NULL",
        "limits": [
            "gate 0: a split of R277's already-published archive, not a fresh sample",
            "one cost snapshot per venue; delisted contracts scored at their venue median curve",
            "size uses the ENTRY spread only; realised PnL never selects a size",
            "tests sizing WITHIN R277's frozen entry rule, not a new entry signal",
        ],
    }
    out = LANE / "results"
    out.mkdir(exist_ok=True)
    (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n")
    val.assign(n_chosen=ns, binding=binds, g_hat=gh).to_csv(out / "validation_scored.csv", index=False)
    check_inputs()
    print(json.dumps({"verdict": rep["verdict"], "k": k,
                      "validation": {m: {kk: round(vv, 2) if isinstance(vv, float) else vv
                                         for kk, vv in r.items()} for m, r in res.items()}}, indent=1))


if __name__ == "__main__":
    main()
