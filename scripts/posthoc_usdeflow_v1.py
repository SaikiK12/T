"""Post hoc for usdeflow_v1 (R488): rank correlations of the USDe weekly supply change with this week's and next
week's Hyperliquid funding, and the partial rank correlation of w(t) with f(t+1) given f(t). Decides nothing.

Written after the run, in answer to review 2026-11-13-122155. Reads experiments/usdeflow_v1/results/weekly.csv only
(the frozen runner's output) and writes experiments/usdeflow_v1/results/posthoc.json. No null is computed: the
numbers are descriptive and untested. A residualized target (w against f(t+1) given f(t)) would be a new lane with a
new id.

usage: python scripts/posthoc_usdeflow_v1.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LANE = ROOT / "experiments" / "usdeflow_v1"


def rank_corr(x, y):
    return float(np.corrcoef(pd.Series(x).rank().to_numpy(float), pd.Series(y).rank().to_numpy(float))[0, 1])


def partial(r_xy, r_xz, r_yz):
    """Partial correlation of x and y given z from the three pairwise correlations."""
    return (r_xy - r_xz * r_yz) / np.sqrt((1.0 - r_xz ** 2) * (1.0 - r_yz ** 2))


def coin_report(p, coin):
    q = p[["w", f"f_{coin}", f"f_next_{coin}"]].dropna()
    w, f0, f1 = q.w, q[f"f_{coin}"], q[f"f_next_{coin}"]
    r_w0, r_w1, r_01 = rank_corr(w, f0), rank_corr(w, f1), rank_corr(f0, f1)
    return {"n": int(len(q)), "rho_w_f_t": r_w0, "rho_w_f_t1": r_w1, "rho_f_t_f_t1": r_01,
            "partial_rho_w_f_t1_given_f_t": float(partial(r_w1, r_w0, r_01)),
            "rho_w_f_t1_minus_rho_w_f_t": r_w1 - r_w0}


def main():
    p = pd.read_csv(LANE / "results" / "weekly.csv")
    out = {"label": "post hoc, decides nothing, no null computed", "source": "results/weekly.csv",
           "coins": {c: coin_report(p, c) for c in ("BTC", "ETH")}}
    (LANE / "results" / "posthoc.json").write_text(json.dumps(out, indent=1) + "\n")
    for c, r in out["coins"].items():
        print(c, " ".join(f"{k} {v:+.3f}" if isinstance(v, float) else f"{k} {v}" for k, v in r.items()))


if __name__ == "__main__":
    main()
