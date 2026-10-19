"""propfirm_v1 (R202): the lab's return streams under prop-firm rule sets, as set out in
experiments/propfirm_v1/PREREG.md.

usage: python scripts/run_propfirm.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, prereg, propfirm  # noqa: E402

LANE = ROOT / "experiments" / "propfirm_v1"
OUT = LANE / "results"
EXP = ROOT / "experiments"
SCALES = (0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 0.75, 1, 1.5, 2)
CRYPTO = ("hyro_2step", "hyro_1step", "ftmo_2step", "ftmo_1step", "cft_1phase", "cft_2phase", "breakout_pro")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def streams():
    v2 = np.load(EXP / "flow72_v2" / "results" / "daily.npz")
    ho = np.load(EXP / "flow72_holdout" / "results" / "daily.npz")
    carry = np.load(EXP / "carry_v1" / "results" / "primary_daily.npz")
    s = {"flowA_hold": ho["holdout_combined_universe"], "flowA_hold_top10": ho["holdout_combined_top10"],
         "tvc_hold": ho["holdout_top_vs_crowd/xs8_universe"], "flowA_ins": v2["combined_h1_c1"],
         "tvc_ins": v2["top_vs_crowd/xs8_h1_c1"],
         "carry_ins": np.concatenate([carry["discovery"], carry["validation"]])}
    s = {k: np.nan_to_num(np.asarray(v, float)) for k, v in s.items()}
    for k in ("flowA_hold", "tvc_hold"):
        s[f"zero_{k}"] = s[k] - s[k].mean()
    return s


def own_capital(r):
    st = events.summary(r)
    dd = st.get("max_dd", np.nan)
    mu, var = r.mean(), r.var()
    kelly = mu / var if var > 0 else np.nan
    scale_dd10 = 0.10 / dd if dd and dd > 0 else np.nan     # scale at which the historical max drawdown is 10%
    return {"ann": st.get("ann"), "sharpe": st.get("sharpe"), "max_dd": dd, "kelly_scale": kelly,
            "scale_dd10": scale_dd10, "kelly_frac_at_dd10": scale_dd10 / kelly if kelly and kelly > 0 else np.nan,
            "ann_at_dd10": mu * 365 * scale_dd10}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    S = streams()
    own = {k: own_capital(v) for k, v in S.items()}
    pd.DataFrame(own).T.to_csv(OUT / "own_capital.csv")
    log("own capital\n" + pd.DataFrame(own).T.round(4).to_string())
    rows, grid = [], []
    for name, r in S.items():
        firms = CRYPTO + (("topstep_50k",) if name.startswith("zero_") else ())
        for firm in firms:
            rules = propfirm.PRESETS[firm]
            allrows, best = propfirm.optimize(r, rules, SCALES, n=4000, horizon=365, funded_days=180, block=5,
                                              seed=0)
            for x in allrows:
                grid.append({"stream": name, "firm": firm, **x})
            rows.append({"stream": name, "firm": firm, "fee": rules.fee, **best})
            log(f"{name:18s} {firm:13s} scale {best['scale']:<5} pass {best['p_pass']:.3f} paid {best['p_paid']:.3f}"
                f" payout {best['exp_payout']:9.0f} ev {best['ev']:9.0f} breakeven fee {best['breakeven_fee']:9.0f}")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "best.csv", index=False)
    pd.DataFrame(grid).to_csv(OUT / "grid.csv", index=False)
    log("\n" + df.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
