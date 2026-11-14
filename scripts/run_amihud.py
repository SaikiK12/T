"""amihud_v1 (R236): 30-day Amihud illiquidity as one-week spread books, as set out in experiments/amihud_v1/PREREG.md.
The holdout is not read.

usage: python scripts/run_amihud.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import features, flowfeat, prereg, research, screen  # noqa: E402

LANE = ROOT / "experiments" / "amihud_v1"
HOLD, W = 168, 720
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def trimmed(n, k=10):
    s = np.sort(n)
    return float(s[k:-k].mean() * 1e4) if len(s) > 2 * k else np.nan


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u, hold=HOLD)
    qv = flowfeat.load("klines", u.p.t, u.p.symbols, ("quote_volume",))["quote_volume"]
    absr = np.abs(np.asarray(u.ret, np.float64))
    illiq = features.roll(absr, W, "mean") / features.roll(qv, W, "mean")
    with np.errstate(divide="ignore", invalid="ignore"):
        illiq = np.where(np.isfinite(illiq) & (illiq > 0), np.log(illiq), np.nan).astype(np.float32)
    qv_lvl = flowfeat._log(features.roll(qv, 24, "sum"))
    del qv, absr
    a, b = s.rows["discovery"][0], s.rows["validation"][1]
    log("finite share of eligible coin-hours (2021-2025H1):",
        round(float(np.isfinite(illiq[a:b])[u.elig[a:b]].mean()), 4))
    ref = s.spread(qv_lvl)["H"]
    rule = lambda w, r, n2: (r["t_nw10"] >= 2 and n2.mean() > 0) if w == "discovery" else \
        (r["mean_bp_day"] > 0 and r["t_nw10"] >= 1.5)
    rows, stage = [], {}
    for d, (parts, K) in s.spread(illiq).items():
        name = f"illiq/{d}"
        r, st = s.staged(name, parts, K, ref_book=ref, rule=rule, holdout=False, log=log)
        for x in r:
            if x["cmult"] == 1.0:
                x["trimmed_bp_day"] = trimmed(s.run(parts, K, *s.rows[x["window"]])[0])
        rows += r
        stage[name] = st
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
