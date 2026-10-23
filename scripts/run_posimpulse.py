"""posimpulse_v1 (R234): the 24 h and 72 h change in top-vs-crowd positioning as 72 h spread books, tested for
information beyond the level book, as set out in experiments/posimpulse_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_posimpulse.py
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

LANE = ROOT / "experiments" / "posimpulse_v1"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def build(u):
    m = flowfeat.load("metrics", u.p.t, u.p.symbols, ("top_ls_sum", "ls_count"))
    tvc = flowfeat._log(m["top_ls_sum"]) - flowfeat._log(m["ls_count"])
    del m
    out = {"tvc": tvc}
    for n in (24, 72):
        x = np.full_like(tvc, np.nan)
        x[n:] = tvc[n:] - tvc[:-n]
        out[f"imp{n}"] = x
    return out


def coverage(u, feats, a, b):
    """Share of eligible coin-hours with a finite feature, per year, over rows [a, b)."""
    year = pd.to_datetime(u.p.t[a:b], unit="ms", utc=True).year
    e = u.elig[a:b]
    return {f: {int(y): float(np.isfinite(x[a:b][year == y])[e[year == y]].mean()) for y in np.unique(year)}
            for f, x in feats.items()}


def trimmed(n, k=10):
    s = np.sort(n)
    return float(s[k:-k].mean() * 1e4) if len(s) > 2 * k else np.nan


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u)
    feats = build(u)
    cov = coverage(u, feats, *s.rows["discovery"][:1], s.rows["validation"][1])
    log("coverage by year:", json.dumps(cov))
    lb = features.bins_xs(feats.pop("tvc"), u.elig, 8)
    lo = (lb == 0) & u.elig
    ref = ([(lo, -1)], float(lo[s.t0:s.tv].sum(axis=1).mean()))
    log(f"level book K {ref[1]:.3f}")
    rows, stage = [], {}
    for f in ("imp24", "imp72"):
        books = s.spread(feats.pop(f))
        for d, (parts, K) in books.items():
            name = f"{f}/{d}"
            r, st = s.staged(name, parts, K, ref_book=ref, holdout=False, log=log)
            for x in r:
                if x["cmult"] == 1.0:
                    a, b = s.rows[x["window"]]
                    x["trimmed_bp_day"] = trimmed(s.run(parts, K, a, b)[0])
            rows += r
            stage[name] = st
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "coverage": cov,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
