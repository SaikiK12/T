"""R462 xyzwknd_v1 runner, frozen in experiments/xyzwknd_v1/PREREG.md: fade the weekend move of trade.xyz US-equity
perps (Hyperliquid HIP-3) from Sunday 19:00 New York to Sunday 22:00 (X1) or Monday 10:00 (X2).

Sample A (decides): weekends whose Friday is 2026-05-01 .. 2026-09-25 (after trade.xyz cut the closed-market oracle
time constant to 30 minutes on 2026-04-30). Sample B (confirms): Fridays 2026-10-02 .. 2026-11-06. Prices and funding
are Hyperliquid's public candleSnapshot and fundingHistory, fetched after the freeze by scripts/fetch_xyz_wknd.py into
data/xyz_wknd.

usage: python scripts/run_xyzwknd.py      the frozen run (verifies the PREREG, every input it lists and every bar file)
"""
import csv
import json
import math
import re
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
import xyzwknd_rule as rule  # noqa: E402
from earnperp_rule import cluster_flip_p, holm, mde80  # noqa: E402

LANE = ROOT / "experiments" / "xyzwknd_v1"
DATA = ROOT / "data" / "xyz_wknd"
REGISTRY = "R462"
A_SPAN = (date(2026, 5, 1), date(2026, 9, 25))
B_SPAN = (date(2026, 10, 2), date(2026, 11, 6))
LISTED_MS = 7 * 86_400_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    rows = [ln.split() for ln in block.strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


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
    weekends = [dict(w, sample="A") for w in rule.fridays(*A_SPAN)] + \
               [dict(w, sample="B") for w in rule.fridays(*B_SPAN)]
    rows, skipped = [], {"no_file": 0, "not_listed": 0, "pre_ipo": 0, "unpriced": 0}
    for u in load_universe(lane):
        pk, pf = data / "klines_1h" / f"{u['coin']}.parquet", data / "funding" / f"{u['coin']}.parquet"
        if not pk.exists():
            skipped["no_file"] += len(weekends)
            continue
        k = pd.read_parquet(pk, columns=["t", "c"])
        f = pd.read_parquet(pf, columns=["time", "rate"]) if pf.exists() else pd.DataFrame(columns=["time", "rate"])
        t, c = k.t.to_numpy("int64"), k.c.to_numpy("float64")
        ft, fr = f.time.to_numpy("int64"), f.rate.to_numpy("float64")
        unit = rule.unit_cost(u["growth"].strip().lower() == "enabled")
        for w in weekends:
            if not len(t) or t[0] > w["R"] - LISTED_MS:
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
                         "unit": unit, **x})
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
                row = {"group": group, "theta": theta, "exit": x,
                       "decision": (group, theta, x) in rule.DECISIONS}
                for smp in ("A", "B"):
                    s = smp.lower()
                    sub = per[per["sample"] == smp]
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
                for k in rule.COST_MULTS:
                    row[f"net_{k}x_a"] = abs(row["mean_a"]) - k * row["unit_a"]
                cells.append(row)
    out = pd.DataFrame(cells)
    dec = out.decision
    out["p_holm"] = np.nan
    out.loc[dec, "p_holm"] = holm(out.loc[dec, "p_a"].to_numpy())
    return out


def run(lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
        log(f"bar files verified: {verify_bars(data)}")
    per, skipped = build(lane, data)
    log("events:", per.groupby("sample").size().to_dict() if len(per) else {}, "skipped:", skipped)
    out = score(per, np.random.default_rng(rule.SEED))
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    per.to_csv(res / "events.csv", index=False)
    out.to_csv(res / "cells.csv", index=False)
    dec = out[out.decision].set_index(["group", "theta", "exit"]).loc[list(rule.DECISIONS)].reset_index()
    state, text = rule.verdict(dec.to_dict("records"))
    (res / "summary.json").write_text(json.dumps({
        "registry": REGISTRY, "state": state, "text": text, "cells": len(out), "skipped": skipped,
        "decisions": json.loads(dec.to_json(orient="records"))}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    run()
