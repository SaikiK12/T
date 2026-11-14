"""Recover only missing Lighter page seams into a new copy; never edit R310 inputs.

Every added row must come from a public query with that timestamp strictly inside
the request. No interpolation, zero fill or changes to already observed rates.
The inherited counters enforce the original combined 8,000-request/250-MiB budget.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.fetch_equation_history import PublicPages, START, END, H, lighter_rows, unique  # noqa: E402
from scripts.run_equations import sha, write_json, verify_inputs  # noqa: E402

PARENT = ROOT/"data/equations_v1"
OUT = ROOT/"data/equations_v2"


def targets(folder):
    result = []
    for path in sorted((Path(folder)/"lighter/funding").glob("*.parquet")):
        frame = pd.read_parquet(path)
        if not len(frame):
            continue
        grid = np.arange(max(START+H, int(frame.t.min())), min(END, int(frame.t.max()))+H, H)
        missing = np.setdiff1d(grid, frame.t.to_numpy(np.int64))
        for timestamp in missing:
            if (int(timestamp)-START) % (700*H) != 0:
                raise ValueError("non-seam absence: this repair must not invent its explanation")
            result.append([path.stem, int(timestamp)])
    return result


def add_observed(frame, rows, timestamp):
    hit = rows[rows.t.eq(timestamp)]
    if len(hit) != 1 or frame.t.eq(timestamp).any():
        raise ValueError("expected exactly one previously absent source event")
    overlap = frame.merge(rows, on="t", suffixes=("_old", "_new"))
    for key in ("rate", "cycle_h"):
        if len(overlap) and not np.array_equal(overlap[key+"_old"], overlap[key+"_new"]):
            raise ValueError("provider revised an existing neighboring event; do not silently overwrite")
    return unique(pd.concat([frame, hit], ignore_index=True))


def collect(out=OUT):
    verify_inputs()  # prove the old frozen source/implementation remains intact
    out = Path(out)
    if not out.exists():
        shutil.copytree(PARENT, out)
    # The first public seam probe is retained outside the model's parquet inventory.
    probe = out/"boundary_probe_BTC.parquet"
    if probe.exists():
        dest = ROOT.parent/"equation_boundary_probe.parquet"
        if dest.exists():
            if sha(dest) != sha(probe):
                raise ValueError("conflicting retained seam probe")
        else:
            probe.rename(dest)
    plan = {"version": 1, "parent_inputs_sha256": sha(ROOT/"experiments/equations_v1/inputs.json"),
            "repair_code_sha256": sha(__file__), "targets": targets(PARENT),
            "scope": "exact same 117 pairs and analysis dates; source events at 700h page seams only"}
    p = out/"repair_plan.json"
    if p.exists() and json.loads(p.read_text()) != plan:
        raise ValueError("repair plan or code changed during acquisition")
    write_json(p, plan)
    client = PublicPages(out)
    client.state["complete"] = False
    client.save()
    ids = {r["symbol"]: int(r["market_id"]) for r in json.loads((out/"lighter_contracts_current.json").read_text())}
    done = set(client.state.get("repaired_seams", []))
    for number, (symbol, timestamp) in enumerate(plan["targets"], 1):
        key = symbol+"/"+str(timestamp)
        path = out/"lighter/funding"/(symbol+".parquet")
        frame = pd.read_parquet(path)
        if key in done:
            if not frame.t.eq(timestamp).any():
                raise ValueError("repair receipt does not match data")
            continue
        rows = lighter_rows(client, ids[symbol], "funding", start=timestamp-H, end=timestamp+H)
        frame = add_observed(frame, rows, timestamp)
        temp = path.with_suffix(".repair.parquet")
        frame.to_parquet(temp, index=False)
        temp.replace(path)
        done.add(key)
        client.state["repaired_seams"] = sorted(done)
        client.save()
        if number % 25 == 0:
            print(f"recovered {number}/{len(plan['targets'])}; total requests {client.state['requests']}; "
                  f"total response MiB {client.state['wire_bytes']/2**20:.2f}", flush=True)
    remaining = targets(out)
    if remaining:
        raise ValueError("public source did not repair every registered seam")
    verify_inputs()
    client.state["complete"] = True
    client.save()
    write_json(out/"repair_receipt.json", {"plan_sha256": sha(p), "recovered_events": len(done),
               "parent_unchanged": True, "global_requests": client.state["requests"],
               "global_response_bytes": client.state["wire_bytes"], "interpolated_events": 0})
    print("source repair complete; no strategy outcomes computed", flush=True)


if __name__ == "__main__":
    collect()
