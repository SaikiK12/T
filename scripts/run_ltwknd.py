"""R465 ltwknd_v1 runner, frozen in experiments/ltwknd_v1/PREREG.md: R462's frozen trade.xyz weekend fade (M515), run
unchanged on Lighter's prices, funding and fees for the 50 of R462's US-stock markets that Lighter lists.

R462's rule module (scripts/xyzwknd_rule.py) gives the weekends, instants, W, the fade side and the returns; this file
only feeds it Lighter's hourly candles (those with volume, so P(T) is a trade) and hourly funding, and scores three
samples:
- A (decides): Fridays 2026-05-01 .. 2026-09-25, R462's sample A (a venue replication on the same weekends);
- B (confirms): Fridays 2026-10-02 .. 2026-11-06, R462's sample B;
- C (confirms when large enough): Fridays 2026-02-27 .. 2026-04-24, weekends no lane has read.
One decision cell: R462's D2 (all markets, |W| >= 50 bp, exit X1 = Sunday 22:00 New York).

usage: python scripts/run_ltwknd.py      the frozen run (verifies the PREREG, every input it lists and every bar file)
"""
import csv
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import xyzwknd_rule as rule  # noqa: E402  (frozen in R462)
from earnperp_rule import cluster_flip_p, mde80  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402

LANE = ROOT / "experiments" / "ltwknd_v1"
DATA = ROOT / "data" / "lighter_wknd"
REGISTRY = "R465"
SPANS = {"A": (date(2026, 5, 1), date(2026, 9, 25)), "B": (date(2026, 10, 2), date(2026, 11, 6)),
         "C": (date(2026, 2, 27), date(2026, 4, 24))}
LISTED_MS = 7 * 86_400_000
TAKER_BP = 0.0                    # Lighter Standard account: 0 maker / 0 taker (orderBookDetails, 2026-11-11)
SLIPPAGE_BP = 4.0                 # round trip, both fills: R462's assumption
UNIT_BP = 2 * TAKER_BP + SLIPPAGE_BP
DECISION = ("all", 50, "x1")
MIN_A, MIN_WEEKENDS_A = 100, 10
MIN_BC, MIN_WEEKENDS_BC = 30, 4
ALPHA = 0.05
SEED = 465
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def verify_bars(data=DATA):
    man = json.loads((data / "manifest.json").read_text())["files"]
    for rel, v in man.items():
        if prereg.sha256_file(data / rel) != v["sha256"]:
            raise prereg.PreregError(f"{data / rel}: sha256 differs from its fetch manifest")
    return len(man)


def load_universe(lane=LANE):
    with open(lane / "universe.csv", newline="") as f:
        return list(csv.DictReader(f))


def build(lane=LANE, data=DATA):
    """One row per (market, weekend) that is eligible and priced."""
    weekends = [dict(w, sample=s) for s, span in SPANS.items() for w in rule.fridays(*span)]
    rows, skipped = [], {"no_file": 0, "not_listed": 0, "pre_ipo": 0, "unpriced": 0}
    for u in load_universe(lane):
        pk, pf = data / "klines_1h" / f"{u['coin']}.parquet", data / "funding" / f"{u['coin']}.parquet"
        if not pk.exists():
            skipped["no_file"] += len(weekends)
            continue
        k = pd.read_parquet(pk, columns=["t", "close", "volume"])
        listed = int(k.t.min()) if len(k) else None
        k = k[(k.volume > 0) & (k.close > 0)]
        f = pd.read_parquet(pf, columns=["t", "rate"]) if pf.exists() else pd.DataFrame(columns=["t", "rate"])
        t, c = k.t.to_numpy("int64"), k.close.to_numpy("float64")
        ft, fr = f.t.to_numpy("int64"), f.rate.to_numpy("float64")
        for w in weekends:
            if listed is None or listed > w["R"] - LISTED_MS:
                skipped["not_listed"] += 1
                continue
            if u["ipo_424b4"] and w["F"] <= u["ipo_424b4"]:
                skipped["pre_ipo"] += 1
                continue
            x = rule.event_row(t, c, ft, fr, w)
            if x["s"] == 0:
                skipped["unpriced"] += 1
                continue
            rows.append({"coin": u["coin"], "etf": int(u["etf"]), "F": w["F"], "sample": w["sample"],
                         "unit": UNIT_BP, **x})
    return pd.DataFrame(rows), skipped


def cell_frame(per, group, theta, exit_key):
    if group == "rel":
        d = rule.relative(per, exit_key)
        return d[d.W.abs() >= theta].rename(columns={"g": "v"}) if len(d) else d
    d = per if group == "all" else per[per.etf == (1 if group == "etf" else 0)]
    d = d[(d.W.abs() >= theta) & np.isfinite(d[f"g_{exit_key}"])]
    return d.rename(columns={f"g_{exit_key}": "v"})


def score(per, rng):
    cells = []
    for group in rule.GROUPS:
        for theta in rule.THETAS:
            for x in rule.EXITS:
                row = {"group": group, "theta": theta, "exit": x, "decision": (group, theta, x) == DECISION}
                for smp in SPANS:
                    s = smp.lower()
                    sub = per[per["sample"] == smp] if len(per) else per
                    d = cell_frame(sub, group, theta, x) if len(sub) else pd.DataFrame(columns=["F", "v", "unit"])
                    v = d["v"].to_numpy(float) if len(d) else np.array([])
                    n = len(v)
                    sd = float(np.std(v, ddof=1)) if n > 1 else math.nan
                    row.update({f"n_{s}": n, f"wk_{s}": int(d.F.nunique()) if n else 0,
                                f"mean_{s}": float(np.mean(v)) if n else math.nan, f"sd_{s}": sd,
                                f"hit_{s}": float(np.mean(v > 0)) if n else math.nan,
                                f"unit_{s}": float(d["unit"].mean()) if n else math.nan,
                                f"mde80_{s}": mde80(sd, n),
                                f"p_{s}": cluster_flip_p(v, d.F.to_numpy(), rng) if n else math.nan})
                for k in (1, 2, 3):
                    row[f"net_{k}x_a"] = row["mean_a"] - k * row["unit_a"]
                cells.append(row)
    return pd.DataFrame(cells)


def verdict(c):
    """c: the decision cell's row (dict). The fade side is fixed by R462, so a mean must be positive."""
    def ok_sizes(n, wk, n_min, wk_min):
        return n >= n_min and wk >= wk_min
    if not ok_sizes(c["n_a"], c["wk_a"], MIN_A, MIN_WEEKENDS_A):
        return "INCONCLUSIVE", "A below its sample sizes"
    b_ok = ok_sizes(c["n_b"], c["wk_b"], MIN_BC, MIN_WEEKENDS_BC) and c["mean_b"] > 0
    c_big = ok_sizes(c["n_c"], c["wk_c"], MIN_BC, MIN_WEEKENDS_BC)
    c_ok = (not c_big) or c["mean_c"] > 0
    a_sig = c["p_a"] <= ALPHA and c["mean_a"] > 0
    if a_sig and c["mean_a"] > 2 * c["unit_a"] and b_ok and c["mean_b"] > c["unit_b"] and c_ok:
        state = "PASS"
    elif a_sig and c["mean_a"] > c["unit_a"] and b_ok:
        state = "PARTIAL"
    else:
        state = "NULL"
    text = (f"A mean {c['mean_a']:.1f} bp p {c['p_a']:.4f}; B mean {c['mean_b']:.1f} bp; "
            f"C mean {c['mean_c']:.1f} bp ({'sized' if c_big else 'below sizes'})")
    return state, text


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
        log(f"bar files verified: {verify_bars(data)}")
    per, skipped = build(lane, data)
    log("events:", per.groupby("sample").size().to_dict() if len(per) else {}, "skipped:", skipped)
    out = score(per, np.random.default_rng(SEED))
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    per.to_csv(res / "events.csv", index=False)
    out.to_csv(res / "cells.csv", index=False)
    dec = out[out.decision].iloc[0].to_dict()
    state, text = verdict(dec)
    (res / "summary.json").write_text(json.dumps({
        "registry": REGISTRY, "state": state, "text": text, "cells": len(out), "skipped": skipped,
        "decision": json.loads(pd.Series(dec).to_json())}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
