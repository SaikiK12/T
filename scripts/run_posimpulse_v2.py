"""posimpulse_v2 (R240): imp24/H and imp72/H from R234 tested on validation only, with K fixed on 2023, as set out
in experiments/posimpulse_v2/PREREG.md. The holdout is not read.

usage: python scripts/run_posimpulse_v2.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import features, prereg, research, screen  # noqa: E402
from run_posimpulse import build, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "posimpulse_v2"
WINDOWS = (("discovery", "2023-01-01", "2024-01-01"), ("validation", "2024-01-01", "2025-07-01"))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def rule(w, r, n2):
    if w == "discovery":                                       # 2023: seen, reported only
        return True
    return r["mean_bp_day"] > 0 and r["t_nw10"] >= 2 and n2.mean() > 0


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u, windows=WINDOWS)
    feats = build(u)
    lb = features.bins_xs(feats.pop("tvc"), u.elig, 8)
    lo = (lb == 0) & u.elig
    ref = ([(lo, -1)], float(lo[s.t0:s.tv].sum(axis=1).mean()))
    log(f"level book K {ref[1]:.3f}")
    rows, stage = [], {}
    for f in ("imp24", "imp72"):
        parts, K = s.spread(feats.pop(f))["H"]
        name = f"{f}/H"
        log(name, f"K {K:.3f}")
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
