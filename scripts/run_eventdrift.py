"""R368 eventdrift_v1 runner, frozen in experiments/eventdrift_v1/PREREG.md: do Binance's crude-oil and natural-gas
perpetuals keep moving the way their first minute after an EIA release moved, far enough to pay a taker round trip?

Reads the 60 releases of experiments/eventdrift_v1/events.csv, the 1-minute bars of data/tradfi_perps/klines_1m/ and
scores the cells of scripts/eventdrift_rule.py once, writing experiments/eventdrift_v1/results/.

usage: python scripts/run_eventdrift.py              the frozen run (verifies the PREREG and every input it lists)
       python scripts/run_eventdrift.py --plumbing   bar coverage per event only; no return, reaction or test is computed
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import eventdrift_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "eventdrift_v1"
REGISTRY = "R368"
DATA = ROOT / "data" / "tradfi_perps" / "klines_1m"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    """Every file in the PREREG's inputs block must still hash to its frozen sha256."""
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    shas = {}
    for line in block.strip().splitlines():
        want, rel = line.split()
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
        shas[rel] = got
    return shas


def verify_data(data=DATA):
    """Each symbol's parquet must match the sha256 its manifest recorded when the archive was fetched."""
    manifest = json.loads((data / "manifest.json").read_text())
    for sym in set(rule.EVENT_SYMBOL.values()):
        want = manifest["symbols"][sym]["sha256"]
        got = prereg.sha256_file(data / f"{sym}.parquet")
        if got != want:
            raise prereg.PreregError(f"{sym}.parquet: sha256 {got} != manifest {want}")
    return manifest["sha256"]


def load_bars(sym, data=DATA):
    return pd.read_parquet(data / f"{sym}.parquet", columns=["t", "open", "close"]).sort_values("t")


def coverage(events, bars_by_symbol):
    """Per event, how many of the bars T-1 .. T+10 exist. Counts only: no price is read into the result."""
    rows = []
    for e in events.itertuples():
        sym = rule.EVENT_SYMBOL[e.event]
        offsets = np.arange(-rule.BARS_BEFORE, rule.BARS_AFTER + 1)
        o, c = rule.lookup(bars_by_symbol[sym], e.release_ms + offsets * rule.MINUTE_MS)
        rows.append({"event": e.event, "release_utc": e.release_utc, "symbol": sym, "bars": int(np.isfinite(c).sum()),
                     "needed": len(offsets), "usable": bool(np.isfinite(o).all() and np.isfinite(c).all())})
    return pd.DataFrame(rows)


def score(events, bars_by_symbol, rng):
    """Every (event type, subset, horizon) cell, plus the late-entry variant of the two decision cells."""
    rows = {e: [] for e in rule.EVENT_SYMBOL}
    for e in events.itertuples():
        rows[e.event].append({"release_utc": e.release_utc,
                              **rule.event_row(bars_by_symbol[rule.EVENT_SYMBOL[e.event]], e.release_ms)})
    per_event = {k: pd.DataFrame(v) for k, v in rows.items()}
    cells = []
    for etype, sym in rule.EVENT_SYMBOL.items():
        df = per_event[etype]
        df = df[df.usable]
        for subset in rule.SUBSETS:
            for h in rule.HORIZONS:
                x = rule.continuation(df.r0, df[f"move{h}"], subset)
                cells.append({"event": etype, "symbol": sym, "subset": subset, "h": h, "entry": "open",
                              "decision": h == rule.DECISION_H and (etype, sym, subset) in rule.DECISIONS,
                              **rule.summarize(x), "p": rule.sign_flip_p(x, rng)})
        for subset in (s for (e, _, s) in rule.DECISIONS if e == etype):
            x = rule.continuation(df.r0, df.late5, subset)
            cells.append({"event": etype, "symbol": sym, "subset": subset, "h": rule.DECISION_H, "entry": "late",
                          "decision": False, **rule.summarize(x), "p": rule.sign_flip_p(x, rng)})
    out = pd.DataFrame(cells)
    dec = out[out.decision].copy()
    out["p_holm"] = np.nan
    out.loc[dec.index, "p_holm"] = rule.holm(dec.p.to_numpy())
    for k in rule.COST_MULTS:
        out[f"net_{k}x"] = out["mean"] - k * rule.UNIT_COST_BP
    return out, per_event


def run(plumbing=False, lane=LANE, data=DATA, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match; data manifest {verify_data(data)[:12]}")
    events = pd.read_csv(lane / "events.csv")
    bars = {sym: load_bars(sym, data) for sym in set(rule.EVENT_SYMBOL.values())}
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    cov = coverage(events, bars)
    cov.to_csv(res / "coverage.csv", index=False)
    by = cov.groupby("event").usable.agg(["sum", "count"])
    log("usable events:", {k: f"{int(v['sum'])}/{int(v['count'])}" for k, v in by.iterrows()})
    if plumbing:
        log("PLUMBING counts only")
        return "PLUMBING"
    out, per_event = score(events, bars, np.random.default_rng(rule.SEED))
    for etype, df in per_event.items():
        df.to_csv(res / f"events_{etype}.csv", index=False)
    out.to_csv(res / "cells.csv", index=False)
    dec = out[out.decision]
    state, text = rule.verdict(dec.to_dict("records"))
    (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text,
                                                  "decisions": json.loads(dec.to_json(orient="records")),
                                                  "cells": len(out), "cost_unit_bp": rule.UNIT_COST_BP}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    run(plumbing=a.plumbing)
