"""xsrev_v1 (R245): 1-day and 7-day reversal books inside the most and least liquid terciles of the top-50, as set out
in experiments/xsrev_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_xsrev.py
"""
import dataclasses
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, research, screen  # noqa: E402

LANE = ROOT / "experiments" / "xsrev_v1"
TERCILES = {"LIQ": (1, 17), "ILLIQ": (34, 50)}
FEATURES = {"r1d": (24, 24), "r7d": (168, 168)}          # lookback, hold
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def trimmed(n, k=10):
    s = np.sort(n)
    return float(s[k:-k].mean() * 1e4) if len(s) > 2 * k else np.nan


def rule(w, r, n2):
    return (r["t_nw10"] >= 2 and n2.mean() > 0) if w == "discovery" else (r["mean_bp_day"] > 0 and r["t_nw10"] >= 1.5)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    c = np.asarray(u.p["close"], np.float64)
    lc = np.where(c > 0, np.log(np.where(c > 0, c, 1)), np.nan)
    rank = np.asarray(u.rank)
    rows, stage = [], {}
    for tname, (lo, hi) in TERCILES.items():
        sub = dataclasses.replace(u, elig=np.asarray(u.elig) & (rank >= lo) & (rank <= hi), index=None)
        for fname, (lb, hold) in FEATURES.items():
            x = np.full_like(lc, np.nan)
            x[lb:] = lc[lb:] - lc[:-lb]
            s = screen.Screen(sub, hold=hold, nbins=4)
            parts, K = s.spread(x)["L"]
            name = f"{fname}/{tname}"
            r, st = s.staged(name, parts, K, rule=rule, holdout=False, log=log)
            for row in r:
                if row["cmult"] == 1.0:
                    row["trimmed_bp_day"] = trimmed(s.run(parts, K, *s.rows[row["window"]])[0])
            rows += r
            stage[name] = st
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    d1 = df[(df.cmult == 1.0) & (df.window == "discovery")].set_index("book")
    diff = {f: float(d1.loc[f"{f}/ILLIQ", "mean_bp_day"] - d1.loc[f"{f}/LIQ", "mean_bp_day"]) for f in FEATURES}
    verdict = {"stages": stage, "illiq_minus_liq_discovery_bp_day": diff,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers", "illiq_minus_liq_discovery_bp_day")},
                   indent=1))


if __name__ == "__main__":
    main()
