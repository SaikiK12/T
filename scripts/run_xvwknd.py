"""R466 xvwknd_v1 runner, frozen in experiments/xvwknd_v1/PREREG.md: the Sunday-evening gap between trade.xyz's and
Lighter's perp on the same US stock, traded as a pair (sell the dearer venue, buy the cheaper) from Sunday 19:00 to
Monday 10:00 New York (decision) or Sunday 22:00 (reported).

Inputs are two frozen fetches, each re-hashed against its own manifest:
- data/xyz_wknd (R462's trade.xyz candles and funding; columns t, c, v and time, rate)
- data/lighter_wknd (R465's Lighter candles and funding; columns t, close, volume and t, rate)
Samples: A (decides) Fridays 2026-05-01 .. 2026-09-25; B (confirms) Fridays 2026-10-02 .. 2026-11-06. The xyz
candles start on 2026-04-17, so the earlier weekends of R465's sample C are not covered.

usage: python scripts/run_xvwknd.py universe     write experiments/xvwknd_v1/universe.csv (before the freeze)
       python scripts/run_xvwknd.py              the frozen run
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
import xyzwknd_rule as base  # noqa: E402  (frozen in R462)
import xvwknd_rule as rule  # noqa: E402
from earnperp_rule import cluster_flip_p, mde80  # noqa: E402
from run_xyzwknd import frozen_inputs  # noqa: E402

LANE = ROOT / "experiments" / "xvwknd_v1"
XYZ = ROOT / "data" / "xyz_wknd"
LT = ROOT / "data" / "lighter_wknd"
REGISTRY = "R466"
SPANS = {"A": (date(2026, 5, 1), date(2026, 9, 25)), "B": (date(2026, 10, 2), date(2026, 11, 6))}
LISTED_MS = 7 * 86_400_000
DECISION = (25, "x2")
MIN_A, MIN_WEEKENDS_A = 100, 10
MIN_B, MIN_WEEKENDS_B = 30, 4
ALPHA = 0.05
SEED = 466
COLS = ["coin", "lt_market_id", "etf", "growth", "ipo_424b4"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def write_universe(lane=LANE):
    """The 50 markets of R465's frozen universe, with R462's xyz growth flag."""
    with open(ROOT / "experiments" / "xyzwknd_v1" / "universe.csv", newline="") as f:
        xyz = {r["coin"]: r for r in csv.DictReader(f)}
    with open(ROOT / "experiments" / "ltwknd_v1" / "universe.csv", newline="") as f:
        lt = list(csv.DictReader(f))
    lane.mkdir(parents=True, exist_ok=True)
    with open(lane / "universe.csv", "w", newline="") as f:
        w = csv.DictWriter(f, COLS, lineterminator="\n")
        w.writeheader()
        for r in lt:
            w.writerow({"coin": r["coin"], "lt_market_id": r["market_id"], "etf": r["etf"],
                        "growth": xyz[r["coin"]]["growth"], "ipo_424b4": r["ipo_424b4"]})
    print(len(lt), "markets")


def verify_bars(data):
    man = json.loads((data / "manifest.json").read_text())["files"]
    for rel, v in man.items():
        if prereg.sha256_file(data / rel) != v["sha256"]:
            raise prereg.PreregError(f"{data / rel}: sha256 differs from its fetch manifest")
    return len(man)


def load_universe(lane=LANE):
    with open(lane / "universe.csv", newline="") as f:
        return list(csv.DictReader(f))


def _xyz(xyz, coin):
    pk, pf = xyz / "klines_1h" / f"{coin}.parquet", xyz / "funding" / f"{coin}.parquet"
    if not pk.exists():
        return None
    k = pd.read_parquet(pk, columns=["t", "c", "v"])
    f = pd.read_parquet(pf, columns=["time", "rate"]) if pf.exists() else pd.DataFrame(columns=["time", "rate"])
    return ((k.t.to_numpy("int64"), pd.to_numeric(k.c).to_numpy("float64"), pd.to_numeric(k.v).to_numpy("float64")),
            (f.time.to_numpy("int64"), pd.to_numeric(f.rate).to_numpy("float64")))


def _lt(lt, coin):
    pk, pf = lt / "klines_1h" / f"{coin}.parquet", lt / "funding" / f"{coin}.parquet"
    if not pk.exists():
        return None
    k = pd.read_parquet(pk, columns=["t", "close", "volume"])
    f = pd.read_parquet(pf, columns=["t", "rate"]) if pf.exists() else pd.DataFrame(columns=["t", "rate"])
    return ((k.t.to_numpy("int64"), k.close.to_numpy("float64"), k.volume.to_numpy("float64")),
            (f.t.to_numpy("int64"), f.rate.to_numpy("float64")))


def build(lane=LANE, xyz=XYZ, lt=LT):
    """One row per (market, weekend) that is eligible and has a fresh trade on both venues at E."""
    weekends = [dict(w, sample=s) for s, span in SPANS.items() for w in base.fridays(*span)]
    rows, skipped = [], {"no_file": 0, "not_listed": 0, "pre_ipo": 0, "unpriced": 0}
    for u in load_universe(lane):
        a, b = _xyz(xyz, u["coin"]), _lt(lt, u["coin"])
        if a is None or b is None:
            skipped["no_file"] += len(weekends)
            continue
        listed = max(int(a[0][0][0]) if len(a[0][0]) else 2**62, int(b[0][0][0]) if len(b[0][0]) else 2**62)
        unit = rule.unit_cost(u["growth"].strip().lower() == "enabled")
        for w in weekends:
            if listed > w["R"] - LISTED_MS:
                skipped["not_listed"] += 1
                continue
            if u["ipo_424b4"] and w["F"] <= u["ipo_424b4"]:
                skipped["pre_ipo"] += 1
                continue
            x = rule.event_row(a[0], b[0], a[1], b[1], w)
            if x["d"] == 0:
                skipped["unpriced"] += 1
                continue
            rows.append({"coin": u["coin"], "etf": int(u["etf"]), "F": w["F"], "sample": w["sample"],
                         "unit": unit, **x})
    return pd.DataFrame(rows), skipped


def score(per, rng):
    cells = []
    for theta in rule.THETAS:
        for x in rule.EXITS:
            row = {"theta": theta, "exit": x, "decision": (theta, x) == DECISION}
            for smp in SPANS:
                s = smp.lower()
                sub = per[per["sample"] == smp] if len(per) else per
                d = sub[(sub.G.abs() >= theta) & np.isfinite(sub[f"g_{x}"])] if len(sub) else sub
                v = d[f"g_{x}"].to_numpy(float) if len(d) else np.array([])
                n = len(v)
                sd = float(np.std(v, ddof=1)) if n > 1 else math.nan
                row.update({f"n_{s}": n, f"wk_{s}": int(d.F.nunique()) if n else 0,
                            f"mean_{s}": float(np.mean(v)) if n else math.nan, f"sd_{s}": sd,
                            f"hit_{s}": float(np.mean(v > 0)) if n else math.nan,
                            f"gap_{s}": float(np.mean(d.G.abs())) if n else math.nan,
                            f"unit_{s}": float(d["unit"].mean()) if n else math.nan,
                            f"mde80_{s}": mde80(sd, n),
                            f"p_{s}": cluster_flip_p(v, d.F.to_numpy(), rng) if n else math.nan})
            for k in (1, 2, 3):
                row[f"net_{k}x_a"] = row["mean_a"] - k * row["unit_a"]
            cells.append(row)
    return pd.DataFrame(cells)


def persistence(per):
    """Reported only. Over A's decision-cell events with a fresh gap an hour before E: the correlation of G(E - 1 h)
    with G(E), and the decision cell's mean return when the earlier gap had the same sign and |G(E - 1 h)| >= theta."""
    theta, x = DECISION
    d = per[(per["sample"] == "A") & (per.G.abs() >= theta) & np.isfinite(per[f"g_{x}"])] if len(per) else per
    d = d[np.isfinite(d.G_prev)] if len(d) else d
    if len(d) < 3:
        return {"n": int(len(d))}
    same = d[(np.sign(d.G_prev) == np.sign(d.G)) & (d.G_prev.abs() >= theta)]
    return {"n": int(len(d)), "corr": float(np.corrcoef(d.G_prev, d.G)[0, 1]), "n_same": int(len(same)),
            "mean_same": float(same[f"g_{x}"].mean()) if len(same) else None,
            "mean_other": float(d.drop(same.index)[f"g_{x}"].mean()) if len(d) > len(same) else None}


def verdict(c):
    """c: the decision cell's row (dict). The pair sells the dearer venue, so a pass needs a positive mean."""
    if not (c["n_a"] >= MIN_A and c["wk_a"] >= MIN_WEEKENDS_A):
        return "INCONCLUSIVE", "A below its sample sizes"
    b_ok = c["n_b"] >= MIN_B and c["wk_b"] >= MIN_WEEKENDS_B and c["mean_b"] > 0
    a_sig = c["p_a"] <= ALPHA and c["mean_a"] > 0
    if a_sig and c["mean_a"] > 2 * c["unit_a"] and b_ok and c["mean_b"] > c["unit_b"]:
        state = "PASS"
    elif a_sig and c["mean_a"] > c["unit_a"] and b_ok:
        state = "PARTIAL"
    else:
        state = "NULL"
    return state, (f"A mean {c['mean_a']:.1f} bp p {c['p_a']:.4f} unit {c['unit_a']:.1f}; "
                   f"B mean {c['mean_b']:.1f} bp (n {c['n_b']})")


def run(lane=LANE, xyz=XYZ, lt=LT, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
        log(f"bar files verified: xyz {verify_bars(xyz)}, lighter {verify_bars(lt)}")
    per, skipped = build(lane, xyz, lt)
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
        "decision": json.loads(pd.Series(dec).to_json()), "persistence": persistence(per)}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    if sys.argv[1:] == ["universe"]:
        write_universe()
    else:
        run()
