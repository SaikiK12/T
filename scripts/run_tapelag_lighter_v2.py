"""R348 tapelag_lighter_v2: R347's frozen rule, rerun after R347's runner crashed before any statistic.

R347 (`scripts/run_tapelag_lighter.py`, frozen) stopped in its summary: under pandas 3, a coin-day with no trade gave
an empty trade table of untyped (object) columns, the concatenated net column stayed object, and `nlargest` refused
it. No statistic had been computed or printed. That file stays unchanged. This runner imports every R347 function
and constant, and changes one thing: each coin-day's trade table is cast to numbers before it is concatenated
(`typed`). The rule, trials, costs, test and decision are R347's.

usage: python scripts/run_tapelag_lighter_v2.py --run    verifies the frozen PREREG and its inputs, then runs
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts import run_tapelag_lighter as v1  # noqa: E402

LANE = ROOT / "experiments" / "tapelag_lighter_v2"
SESSIONS = "experiments/tapelag_lighter_v1/inputs/sessions.csv"
REGISTRY = "R348"
INTS = ("s", "e", "x", "side")


def typed(t):
    """A trade table with numeric columns, also when it has no row (the one change from R347)."""
    return t.astype({c: (np.int64 if c in INTS else float) for c in t.columns})


def run_days(days, sessions, walk, root=ROOT, delays=(v1.DELAY,)):
    """R347's run_days, with each coin-day's trades typed before the concatenation."""
    trades = {(th, h, dl): [] for th in v1.THETAS for h in v1.HOLDS for dl in delays}
    skips = {key: {} for key in trades}
    buckets = set()
    for day in days:
        d0, books, sids = v1.load_day(day, sessions, root)
        for c in v1.COINS:
            gb, gl, d, dev = v1.coin_day(day, c, d0, books, sids)
            obs = np.flatnonzero(np.isfinite(dev))
            buckets.update((day, int(b)) for b in np.unique((obs + 1) // v1.BUCKET))
            for key in trades:
                th, h, dl = key
                tr, sk = v1.simulate(dev, gl[0], gl[1], gl[2], gl[3], th, h, walk[c], delay=dl)
                tr = typed(tr)
                tr["coin"], tr["day"] = c, day
                tr["bucket"] = (tr.s + 1) // v1.BUCKET
                trades[key].append(tr)
                for name, v in sk.items():
                    skips[key][name] = skips[key].get(name, 0) + v
    trades = {k: pd.concat(v, ignore_index=True) for k, v in trades.items()}
    return trades, skips, sorted(buckets)


def evaluate(days, sessions, walk, root=ROOT):
    """The summary R347's main would have written, and the primary trades."""
    trades, skips, buckets = run_days(days, sessions, walk, root, delays=(1, 2, 3))
    keys = [(th, h) for th in v1.THETAS for h in v1.HOLDS]
    trials = {k: v1.summarize(trades[(*k, v1.DELAY)], buckets) for k in keys}
    X = np.column_stack([v1.bucket_series(trades[(*k, v1.DELAY)], "net1", buckets) for k in keys])
    tb, p, pfw = v1.block_bootstrap(X)
    fam = dict(t={k: float(tb[i]) for i, k in enumerate(keys)}, p={k: float(p[i]) for i, k in enumerate(keys)},
               p_family={k: float(pfw[i]) for i, k in enumerate(keys)})
    verdict = v1.decide(v1.PRIMARY, fam, trials)
    name = {k: f"theta{k[0]:g}_h{k[1]}" for k in keys}
    delay = {name[k]: {f"delay_{dl}s_1x_bp": (round(float(trades[(*k, dl)].net1.mean()), 3)
                                              if len(trades[(*k, dl)]) else None) for dl in (1, 2, 3)} for k in keys}
    out = dict(lane=LANE.name, registry=REGISTRY, trials=v1.TRIALS, days=list(days),
               observable_buckets=len(buckets), observable_hours=round(len(buckets) * v1.BUCKET / 3600, 2),
               primary=name[v1.PRIMARY], verdict=verdict,
               trials_detail={name[k]: dict(**trials[k], boot_t=round(fam["t"][k], 2), boot_p=round(fam["p"][k], 4),
                                            boot_p_family=round(fam["p_family"][k], 4), skips=skips[(*k, v1.DELAY)])
                              for k in keys},
               delay_sensitivity=delay, walk_cost_bp=walk)
    return out, {name[k]: trades[(*k, v1.DELAY)] for k in keys}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    if not ap.parse_args().run:
        ap.error("use --run once the PREREG is frozen")
    prereg.verify(LANE / "PREREG.md")
    shas = v1.frozen_inputs(LANE / "PREREG.md")
    v1.log(f"PREREG verified; {len(shas)} inputs match")
    walk = v1.walk_costs(v1.book_rows([f for f in shas if f.startswith(v1.BOOKS)]))
    v1.log("walk cost bp a side: " + ", ".join(f"{c} {v:.2f}" for c, v in walk.items()))
    out, trades = evaluate(v1.DAYS, pd.read_csv(ROOT / SESSIONS), walk)
    out["inputs"] = shas
    (LANE / "results").mkdir(exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    for k, t in trades.items():
        t.to_csv(LANE / "results" / f"trades_{k}.csv.gz", index=False)
    v1.log(f"{out['observable_buckets']} observable buckets; verdict {out['verdict']}; "
           f"primary 1x {out['trials_detail'][out['primary']].get('1x')}")


if __name__ == "__main__":
    main()
