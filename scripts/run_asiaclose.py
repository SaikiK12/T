"""R468 asiaclose_v1 runner, frozen in experiments/asiaclose_v1/PREREG.md: Asian single-stock perps on trade.xyz and
Lighter across the daily closure of their local exchange (M526). scripts/asiaclose_rule.py gives the openings, the
instants, W, the fade side and the returns; this file feeds it each venue's traded 1 h candles and hourly funding and
scores two samples:
- A (decides): local opening days 2026-04-27 .. 2026-08-31;
- B (confirms): local opening days 2026-09-01 .. 2026-11-10.
One decision cell: both venues, weekday nights, |W| >= 50 bp, exit X1. The side is not fixed in advance: A's mean picks
it (fade if positive, follow if negative) and B must agree.

usage: python scripts/run_asiaclose.py      the frozen run (verifies the PREREG, every input it lists and every bar file)
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
import asiaclose_rule as rule  # noqa: E402
from earnperp_rule import cluster_flip_p, mde80  # noqa: E402  (frozen in R461)
from run_xyzwknd import frozen_inputs  # noqa: E402  (frozen in R462)

LANE = ROOT / "experiments" / "asiaclose_v1"
DATA = ROOT / "data" / "asiaclose"
REGISTRY = "R468"
SPANS = {"A": (date(2026, 4, 27), date(2026, 8, 31)), "B": (date(2026, 9, 1), date(2026, 11, 10))}
LISTED_MS = 7 * 86_400_000
SLIPPAGE_BP = 4.0                 # round trip, both fills: R462's assumption
UNIT_BP = {"xyz": 2 * 0.9 + SLIPPAGE_BP, "lighter": 0.0 + SLIPPAGE_BP}
VENUES = ("both", "xyz", "lighter")
KINDS = ("night", "gap")
THETAS = (0, 50, 100, 200)
EXCHANGES = ("KRX", "TSE", "HKEX", "SSE")
DECISION = ("both", "night", 50, "x1")
# Kioxia's 3-for-1 split (xyz settled and reopened KIOXIA at about 06:35 UTC on 2026-09-28): openings on these days
# straddle it and are dropped on both venues.
CORPORATE = {"285A": {date(2026, 9, 28), date(2026, 9, 29)}}
MIN_A, MIN_DAYS_A = 150, 40
MIN_B, MIN_DAYS_B = 50, 15
ALPHA = 0.05
SEED = 468
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
    """One row per (market, opening) that is eligible and priced."""
    opens = {x: [dict(o, sample=s) for s, span in SPANS.items() for o in rule.openings(x, *span)] for x in EXCHANGES}
    rows, skipped = [], {"no_file": 0, "not_listed": 0, "corporate": 0, "unpriced": 0}
    for u in load_universe(lane):
        ops = opens[u["exchange"]]
        pk = data / u["venue"] / "klines_1h" / f"{u['coin']}.parquet"
        pf = data / u["venue"] / "funding" / f"{u['coin']}.parquet"
        if not pk.exists():
            skipped["no_file"] += len(ops)
            continue
        k = pd.read_parquet(pk, columns=["t", "close", "volume"])
        listed = int(k.t.min()) if len(k) else None
        k = k[(k.volume > 0) & (k.close > 0)]
        f = pd.read_parquet(pf, columns=["t", "rate"]) if pf.exists() else pd.DataFrame(columns=["t", "rate"])
        t, c = k.t.to_numpy("int64"), k.close.to_numpy("float64")
        ft, fr = f.t.to_numpy("int64"), f.rate.to_numpy("float64")
        for o in ops:
            if listed is None or listed > o["R"] - LISTED_MS:
                skipped["not_listed"] += 1
                continue
            if date.fromisoformat(o["D"]) in CORPORATE.get(u["local"], set()):
                skipped["corporate"] += 1
                continue
            x = rule.event_row(t, c, ft, fr, o)
            if x["s"] == 0:
                skipped["unpriced"] += 1
                continue
            rows.append({"venue": u["venue"], "coin": u["coin"], "exchange": u["exchange"], "D": o["D"],
                         "kind": o["kind"], "sample": o["sample"], "unit": UNIT_BP[u["venue"]], **x})
    return pd.DataFrame(rows), skipped


def cells_spec():
    """(name, venue, kind, theta, exit, exchange) for every cell: 48 grid cells, then 4 exchange diagnostics."""
    out = [(f"{v}/{k}/{th}/{x}", v, k, th, x, "all") for v in VENUES for k in KINDS for th in THETAS
           for x in rule.EXITS]
    out += [(f"both/night/50/x1/{e}", "both", "night", 50, "x1", e) for e in EXCHANGES]
    return out


def cell_frame(per, venue, kind, theta, exit_key, exchange):
    d = per[(per.kind == kind) & (per.W.abs() >= theta) & np.isfinite(per[f"g_{exit_key}"])]
    if venue != "both":
        d = d[d.venue == venue]
    if exchange != "all":
        d = d[d.exchange == exchange]
    return d.rename(columns={f"g_{exit_key}": "v"})


def score(per, rng):
    cells = []
    for name, venue, kind, theta, x, exch in cells_spec():
        row = {"cell": name, "venue": venue, "kind": kind, "theta": theta, "exit": x, "exchange": exch,
               "decision": (venue, kind, theta, x) == DECISION and exch == "all"}
        for smp in SPANS:
            s = smp.lower()
            sub = per[per["sample"] == smp] if len(per) else per
            d = cell_frame(sub, venue, kind, theta, x, exch) if len(sub) else pd.DataFrame(
                columns=["D", "v", "unit"])
            v = d["v"].to_numpy(float) if len(d) else np.array([])
            n = len(v)
            sd = float(np.std(v, ddof=1)) if n > 1 else math.nan
            row.update({f"n_{s}": n, f"days_{s}": int(d.D.nunique()) if n else 0,
                        f"mean_{s}": float(np.mean(v)) if n else math.nan, f"sd_{s}": sd,
                        f"hit_{s}": float(np.mean(v > 0)) if n else math.nan,
                        f"unit_{s}": float(d["unit"].mean()) if n else math.nan, f"mde80_{s}": mde80(sd, n),
                        f"p_{s}": cluster_flip_p(v, d.D.to_numpy(), rng) if n else math.nan})
        for k in (1, 2, 3):
            row[f"net_{k}x_a"] = abs(row["mean_a"]) - k * row["unit_a"]
        cells.append(row)
    return pd.DataFrame(cells)


def verdict(c):
    """c: the decision cell's row (dict). Two-sided: A's sign picks the side (+ fade, - follow); B must agree."""
    if c["n_a"] < MIN_A or c["days_a"] < MIN_DAYS_A:
        return "INCONCLUSIVE", "A below its sample sizes"
    side = np.sign(c["mean_a"]) if np.isfinite(c["mean_a"]) else 0
    b_ok = (c["n_b"] >= MIN_B and c["days_b"] >= MIN_DAYS_B and side != 0 and np.isfinite(c["mean_b"])
            and np.sign(c["mean_b"]) == side)
    a_sig = c["p_a"] <= ALPHA and side != 0
    if a_sig and abs(c["mean_a"]) > 2 * c["unit_a"] and b_ok and abs(c["mean_b"]) > c["unit_b"]:
        state = "PASS"
    elif a_sig and abs(c["mean_a"]) > c["unit_a"] and b_ok:
        state = "PARTIAL"
    else:
        state = "NULL"
    word = "fade" if side > 0 else "follow" if side < 0 else "none"
    text = (f"side {word}; A mean {c['mean_a']:.1f} bp p {c['p_a']:.4f} n {c['n_a']} days {c['days_a']}; "
            f"B mean {c['mean_b']:.1f} bp n {c['n_b']} days {c['days_b']}")
    return state, text


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
        log(f"bar files verified: {verify_bars(data)}")
    per, skipped = build(lane, data)
    log("events:", per.groupby(["sample", "kind"]).size().to_dict() if len(per) else {}, "skipped:", skipped)
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
