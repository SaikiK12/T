"""anytime_monitor_v1 (R489, M479, gate 0 diagnostic): can a forward paper lane be read every day at a
fixed level without inflating the type-I error, and what does the e-process monitor say about the lab's
already-recorded forward-lane series?

Reads only repository-committed CSV files (no network, no market data). For each series and cost column it
runs the monitor in three modes (bet, block, mixture) from `lab.sequential`, after first checking on two
fixed-seed synthetic nulls that the monitor's size is at most alpha. Writes results.json, a receipt and a
log next to the PREREG. Freeze PREREG.md before running; `verify()` runs first.

usage: python scripts/run_anytime_monitor.py [--no-check]
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab import registry  # noqa: E402
from lab.sequential import lane_monitor  # noqa: E402

REGISTRY = "R489"
LANE = ROOT / "experiments" / "anytime_monitor_v1"
PREREG = LANE / "PREREG.md"

ALPHA = 0.05
LO, HI = -0.30, 0.30
BLOCK = 5
MODES = ("bet", "block", "mixture")
SEEDS = 400
DAYS = 365

# (relative path, kind, grouping columns, cost columns)
SERIES = [
    ("experiments/carry_v2_audit_v1/results/daily.csv", "carry_audit", ("book", "engine"),
     ("net_1x", "net_2x", "net_3x")),
    ("experiments/carry_v2_audit_kc_v1/results/daily.csv", "carry_audit", ("book", "engine"),
     ("net_1x", "net_2x", "net_3x")),
    ("experiments/carry_fwd/journal/tickets.csv", "forward", ("book",), ("net", "net_2x", "net_3x")),
    ("experiments/mexc_fwd/journal/tickets.csv", "forward", ("book",), ("net", "net_2x", "net_3x")),
    ("experiments/xfund_fwd/journal/tickets.csv", "forward", None, ()),
]


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_daily_series(path, key_cols, cost_cols):
    """Return {series_name: {cost_col: [values in date order]}} for one committed CSV.

    Groups rows by `key_cols` (a tuple, or None for one pooled series) and sorts each group by
    its `date`/`day` column so the series is in time order. Files that carry several engines or
    books must be split, or the interleaved streams corrupt the monitor.
    """
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    cols = rows[0].keys()
    date_col = "date" if "date" in cols else ("day" if "day" in cols else None)
    groups = {}
    for r in rows:
        if key_cols and all(k in cols for k in key_cols):
            key = "|".join(r[k] for k in key_cols)
        else:
            key = "all"
        groups.setdefault(key, []).append(r)
    out = {}
    for key, sub in groups.items():
        if date_col:
            sub = sorted(sub, key=lambda r: r[date_col])
        for c in cost_cols:
            if c not in cols:
                continue
            vals = []
            for r in sub:
                try:
                    vals.append(float(r[c]))
                except (TypeError, ValueError):
                    vals.append(float("nan"))
            if any(np.isfinite(vals)):
                out.setdefault(key, {})[c] = vals
    return out


def _synthetic_size(mode, block, phi, seed):
    rng = np.random.default_rng(seed)
    false = 0
    for _ in range(SEEDS):
        e = rng.normal(0.0, 0.006, DAYS)
        if phi == 0.0:
            r = e
        else:
            r = np.empty(DAYS)
            r[0] = e[0]
            for i in range(1, DAYS):
                r[i] = phi * r[i - 1] + e[i]
        r = np.clip(r, LO, HI)
        false += lane_monitor(r, LO, HI, alpha=ALPHA, mode=mode, block=block)["reject"]
    return false / SEEDS


def run():
    prereg.verify(PREREG)
    started = time.time()
    receipts = []
    cells = []
    reads = []

    for rel, kind, key_cols, cost_cols in SERIES:
        path = ROOT / rel
        if not path.exists():
            receipts.append({"path": rel, "present": False})
            continue
        receipts.append({"path": rel, "present": True, "sha256": sha256_file(path)})
        series = _read_daily_series(path, key_cols, cost_cols)
        for name, per_cost in series.items():
            for cost, vals in per_cost.items():
                x = np.asarray(vals, dtype=float)
                if not np.isfinite(x).any():
                    continue
                if np.any(np.isfinite(x) & ((x < LO) | (x > HI))):
                    reads.append({"file": rel, "series": name, "cost": cost, "state": "OUT_OF_BOUND"})
                    continue
                row = {"file": rel, "series": name, "cost": cost, "n": int(np.isfinite(x).sum())}
                for mode in MODES:
                    out = lane_monitor(x, LO, HI, alpha=ALPHA, mode=mode, block=BLOCK)
                    row[mode] = {"e_value": out["e_value"], "reject": out["reject"],
                                 "p_anytime": out["p_anytime"], "first_reject_index": out["first_reject_index"]}
                    cells.append({"series": name, "cost": cost, "mode": mode, "e_value": out["e_value"],
                                  "reject": out["reject"]})
                # a rejection is read as evidence only when the dependence-robust block mode agrees
                if row["block"]["reject"]:
                    row["state"] = "MONITOR_REJECTS"
                elif row["bet"]["reject"] or row["mixture"]["reject"]:
                    row["state"] = "MONITOR_BET_ONLY"
                else:
                    row["state"] = "NULL"
                reads.append(row)

    slack = 3.0 * (ALPHA * (1 - ALPHA) / SEEDS) ** 0.5
    calibration = {}
    for mode in MODES:
        for phi, label in ((0.0, "iid"), (0.7, "ar1_phi0.7")):
            size = _synthetic_size(mode, BLOCK, phi, 20261114 + int(phi * 1000) + MODES.index(mode))
            calibration[f"{mode}|{label}"] = {"size": size, "slack": slack, "ok": size <= ALPHA + slack}
    # the method is valid if every mode holds on the i.i.d. null and the block mode holds under AR(1)
    valid = all(v["ok"] for v in calibration.values())
    verdict = "METHOD_VALID" if valid else "METHOD_INVALID"

    n_reject = sum(1 for r in reads if r.get("state") == "MONITOR_REJECTS")
    n_bet_only = sum(1 for r in reads if r.get("state") == "MONITOR_BET_ONLY")
    n_null = sum(1 for r in reads if r.get("state") == "NULL")
    program_trials = registry.program_trials(ROOT / "registry" / "rounds.csv")

    results = {
        "registry": REGISTRY, "lane": "anytime_monitor_v1", "method": "M479",
        "alpha": ALPHA, "bounds": [LO, HI], "block": BLOCK, "modes": list(MODES),
        "verdict": verdict, "calibration": calibration,
        "n_series_cells": len(reads), "n_reject": n_reject, "n_bet_only": n_bet_only, "n_null": n_null,
        "program_trials_before": program_trials, "strategy_trials_added": 0,
        "reads": reads, "cells": cells, "receipts": receipts,
        "runtime_s": round(time.time() - started, 3),
    }
    (LANE / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (LANE / "receipt.json").write_text(json.dumps({
        "prereg_sha256": prereg.sha256_file(PREREG), "inputs": receipts, "verdict": verdict,
    }, indent=2, sort_keys=True) + "\n")
    print(f"{verdict}: {n_reject} MONITOR_REJECTS, {n_bet_only} MONITOR_BET_ONLY, {n_null} NULL "
          f"over {len(reads)} series-cost cells")
    for k, v in calibration.items():
        print(f"  size {k}: {v['size']:.3f} (limit {ALPHA + v['slack']:.3f}) {'ok' if v['ok'] else 'FAIL'}")
    return 0 if valid else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-check", action="store_true")
    ap.parse_args()
    raise SystemExit(run())


if __name__ == "__main__":
    main()
