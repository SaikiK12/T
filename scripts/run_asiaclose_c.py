"""R469 asiaclose_c, frozen in experiments/asiaclose_c/PREREG.md: R468's frozen rule (scripts/asiaclose_rule.py) and
universe (experiments/asiaclose_v1/universe.csv) read once on openings that no lane has seen, D in 2026-11-12 ..
2027-01-29 (sample C). R468's decision cell decides (both venues, weekday nights, |W| >= 50 bp, exit X1) with R468's
side fixed: fade. Run once by .github/workflows/claude-asiaclose-c.yml on or after 2027-02-01 00:00 UTC; it refuses to
run earlier and does nothing once results/summary.json exists.

Bars are fetched by R468's frozen fetcher (scripts/fetch_asiaclose.py) into data/asiaclose_c, with its manifest.

usage: python scripts/run_asiaclose_c.py      the frozen run (verifies the PREREG and every input it lists)
"""
import json
import math
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import fetch_asiaclose as fetch  # noqa: E402  (frozen in R468)
import asiaclose_rule as rule  # noqa: E402  (frozen in R468)
import run_asiaclose as base  # noqa: E402  (frozen in R468)
from earnperp_rule import cluster_flip_p, mde80  # noqa: E402  (frozen in R461)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "asiaclose_c"
UNIVERSE_LANE = ROOT / "experiments" / "asiaclose_v1"
DATA = ROOT / "data" / "asiaclose_c"
REGISTRY = "R469"
SPAN = (date(2026, 11, 12), date(2027, 1, 29))
RUN_AFTER_MS = int(datetime(2027, 2, 1, tzinfo=timezone.utc).timestamp() * 1000)
FETCH = ("2026-10-15T00:00:00Z", "2027-02-01T00:00:00Z")
# R468's holiday table stops at 2026. The 2027 full-day closures inside C: New Year's Day on all four exchanges and
# Coming of Age Day (2nd Monday of January) on the TSE. Added to the frozen table at run time, never removed.
HOLIDAYS_2027 = {"KRX": {date(2027, 1, 1)}, "TSE": {date(2027, 1, 1), date(2027, 1, 11)},
                 "HKEX": {date(2027, 1, 1)}, "SSE": {date(2027, 1, 1)}}
MIN_N, MIN_DAYS = 150, 30
ALPHA = 0.05
SEED = 469
# The decision cell, then reports (counted as trials): each venue, each exchange.
CELLS = ([("decision", "both", "all")] + [(f"venue {v}", v, "all") for v in ("xyz", "lighter")]
         + [(f"exchange {e}", "both", e) for e in base.EXCHANGES])
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def read(per, rng):
    rows = []
    for name, venue, exch in CELLS:
        d = base.cell_frame(per, venue, "night", 50, "x1", exch) if len(per) else pd.DataFrame(columns=["D", "v"])
        v = d["v"].to_numpy(float) if len(d) else np.array([])
        n = len(v)
        sd = float(np.std(v, ddof=1)) if n > 1 else math.nan
        mean = float(np.mean(v)) if n else math.nan
        unit = float(d["unit"].mean()) if n else math.nan
        p2 = cluster_flip_p(v, d.D.to_numpy(), rng) if n else math.nan
        p1 = p2 / 2 if n and mean > 0 else (1 - p2 / 2 if n else math.nan)
        rows.append({"cell": name, "n": n, "days": int(d.D.nunique()) if n else 0, "mean": mean, "sd": sd,
                     "median": float(np.median(v)) if n else math.nan,
                     "hit": float(np.mean(v > 0)) if n else math.nan, "unit": unit, "p_one_sided": p1,
                     "mde80": mde80(sd, n), **{f"net_{k}x": mean - k * unit for k in (1, 2, 3)}})
    return pd.DataFrame(rows)


def verdict(c):
    """c: the decision row. The side is R468's (fade), so the mean must be positive."""
    if c["n"] < MIN_N or c["days"] < MIN_DAYS:
        return "INCONCLUSIVE", "C below its sample sizes"
    if c["p_one_sided"] <= ALPHA and c["mean"] > 2 * c["unit"]:
        state = "PASS"
    else:
        state = "NULL"
    return state, (f"C mean {c['mean']:.1f} bp (median {c['median']:.1f}) p {c['p_one_sided']:.4f} n {c['n']} "
                   f"days {c['days']} unit {c['unit']:.2f}")


def run(lane=LANE, data=DATA, now_ms=None, check=True, do_fetch=True):
    res = lane / "results"
    if (res / "summary.json").exists():
        log("already read:", json.loads((res / "summary.json").read_text())["state"])
        return None
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if now_ms < RUN_AFTER_MS:
        log("not before 2027-02-01 00:00 UTC; nothing read")
        return None
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(frozen_inputs(lane / 'PREREG.md'))} inputs match")
    if do_fetch:
        fetch.OUT = data
        fetch.bars(*FETCH)
    log(f"bar files verified: {base.verify_bars(data)}")
    base.SPANS = {"C": SPAN}
    for x, days in HOLIDAYS_2027.items():
        rule.HOLIDAYS[x] = rule.HOLIDAYS[x] | days
    per, skipped = base.build(UNIVERSE_LANE, data)
    log("events:", per.groupby("kind").size().to_dict() if len(per) else {}, "skipped:", skipped)
    out = read(per, np.random.default_rng(SEED))
    res.mkdir(parents=True, exist_ok=True)
    per.to_csv(res / "events.csv", index=False)
    out.to_csv(res / "cells.csv", index=False)
    dec = out.iloc[0].to_dict()
    state, text = verdict(dec)
    (res / "summary.json").write_text(json.dumps({
        "registry": REGISTRY, "state": state, "text": text, "skipped": skipped,
        "decision": json.loads(pd.Series(dec).to_json())}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
