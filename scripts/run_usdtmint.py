"""R460 usdtmint_v1 runner, frozen in experiments/usdtmint_v1/PREREG.md: does BTC (and, reported, ETH) rise after a
Tether USDT mint by more than at random times and by more than a Hyperliquid taker round trip plus funding?

Reads experiments/usdtmint_v1/events.csv (a copy of data/usdt_mints/events.csv from scripts/fetch_usdt_mints.py),
Binance USD-M 1-minute bars (data/klines_1m, rows from 2021-01-01 only: 2020 is a reserved sample) and Binance funding
(data/fundingRate), scores every cell of scripts/usdtmint_rule.py once and writes experiments/usdtmint_v1/results/.

usage: python scripts/run_usdtmint.py              the frozen run (verifies the PREREG and every input it lists)
       python scripts/run_usdtmint.py --plumbing   event and trade counts per cell and split; no price is read
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
from lab.config import split_of  # noqa: E402
import usdtmint_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "usdtmint_v1"
REGISTRY = "R460"
BARS = ROOT / "data" / "klines_1m"
FUND = ROOT / "data" / "fundingRate"
FIRST_ROW_MS = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)   # no 2020 row is read
CIRCLE_LO = int(datetime(2021, 1, 2, tzinfo=timezone.utc).timestamp() * 1000)
DATA_END = int(datetime(2026, 9, 30, tzinfo=timezone.utc).timestamp() * 1000)     # last day of the bars
SPLITS = ("disc", "val", "hold")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    rows = [ln.split() for ln in block.strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


def verify_data():
    for folder in (BARS, FUND):
        man = json.loads((folder / "manifest.json").read_text())
        for sym in rule.ASSETS:
            got = prereg.sha256_file(folder / f"{sym}.parquet")
            if got != man["symbols"][sym]["sha256"]:
                raise prereg.PreregError(f"{folder.name}/{sym}.parquet: sha256 {got} != manifest")


def load_bars(sym):
    t = pq.read_table(BARS / f"{sym}.parquet", columns=["t", "open"], filters=[("t", ">=", FIRST_ROW_MS)])
    df = t.to_pandas().sort_values("t")
    assert df.t.min() >= FIRST_ROW_MS
    return df.t.to_numpy("int64"), df.open.to_numpy("float64")


def load_funding(sym):
    t = pq.read_table(FUND / f"{sym}.parquet", columns=["t", "rate"], filters=[("t", ">=", FIRST_ROW_MS)])
    df = t.to_pandas().sort_values("t")
    return df.t.to_numpy("int64"), df.rate.to_numpy("float64")


def split_name(ms):
    return split_of(datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date())


def events_table(lane=LANE):
    ev = pd.read_csv(lane / "events.csv")
    ev = ev[ev.amount_usdt >= rule.MIN_MINT].copy()
    ev["entry"] = rule.entry_time(ev.ts_ms.to_numpy())
    return ev.sort_values("entry").reset_index(drop=True)


def circle_hi(hold_ms):
    return DATA_END - hold_ms


def cell_entries(ev, subset, hold_ms, down_mask=None):
    m = (ev.entry >= CIRCLE_LO) & (ev.entry < circle_hi(hold_ms))
    if subset == "big":
        m &= ev.amount_usdt >= rule.BIG_MINT
    elif subset in ("tron", "ethereum"):
        m &= ev.chain == subset
    elif subset == "down":
        m &= down_mask
    e = ev.entry[m].to_numpy("int64")
    return e[rule.non_overlapping(e, hold_ms)]


def plumbing(lane=LANE):
    ev = events_table(lane)
    rows = []
    for subset in rule.SUBSETS:
        if subset == "down":
            continue   # needs prices
        for h in rule.HORIZONS_H:
            e = cell_entries(ev, subset, h * rule.HOUR_MS)
            sp = pd.Series([split_name(x) for x in e]).value_counts().to_dict()
            rows.append({"subset": subset, "h": h, "trades": len(e), **{s: sp.get(s, 0) for s in SPLITS}})
    out = pd.DataFrame(rows)
    log("\n" + out.to_string(index=False))
    return out


def split_means(tb, ob, hold_ms):
    """Mean H-return over every hourly start in each split (the unconditional benchmark)."""
    starts = np.arange(CIRCLE_LO, circle_hi(hold_ms), rule.HOUR_MS, dtype="int64")
    r = rule.log_return_bp(tb, ob, starts, hold_ms)
    sp = np.array([split_name(x) for x in starts])
    return {s: float(np.nanmean(r[sp == s])) for s in SPLITS}


def score(lane=LANE, rng=None):
    rng = rng or np.random.default_rng(rule.SEED)
    ev = events_table(lane)
    cells, trades = [], []
    for sym in rule.ASSETS:
        tb, ob = load_bars(sym)
        ft, fr = load_funding(sym)
        prior = rule.log_return_bp(tb, ob, ev.entry.to_numpy("int64") - rule.DAY_MS, rule.DAY_MS)
        down = pd.Series(prior < 0, index=ev.index)
        for h in rule.HORIZONS_H:
            hold = h * rule.HOUR_MS
            mu = split_means(tb, ob, hold)
            for subset in rule.SUBSETS:
                e = cell_entries(ev, subset, hold, down)
                r = rule.log_return_bp(tb, ob, e, hold)
                f = rule.funding_bp(ft, fr, e, hold)
                ok = np.isfinite(r)
                e, r, f = e[ok], r[ok], f[ok]
                sp = np.array([split_name(x) for x in e])
                n = len(r)
                p, plac, obs = rule.shift_p(tb, ob, e, hold, CIRCLE_LO, circle_hi(hold), rng) if n else (np.nan,) * 3
                sd = float(np.std(r, ddof=1)) if n > 1 else np.nan
                row = {"asset": sym, "subset": subset, "h": h, "n": n, "mean": float(np.mean(r)) if n else np.nan,
                       "sd": sd, "t": float(np.mean(r) / sd * np.sqrt(n)) if n > 1 and sd > 0 else np.nan,
                       "hit": float(np.mean(r > 0)) if n else np.nan, "mde80": rule.mde80(sd, n),
                       "placebo_mean": plac, "excess": obs - plac if n else np.nan, "p": p,
                       "funding_mean": float(np.mean(f)) if n else np.nan,
                       "decision": (sym, subset, h) in rule.DECISIONS}
                for s in SPLITS:
                    k = sp == s
                    row[f"n_{s}"] = int(k.sum())
                    row[f"excess_{s}"] = float(np.mean(r[k]) - mu[s]) if k.any() else np.nan
                for c in rule.COST_MULTS:
                    row[f"net_{c}x"] = float(np.mean(r - c * rule.UNIT_COST_BP - f)) if n else np.nan
                cells.append(row)
                for x, rr, ff, ss in zip(e, r, f, sp):
                    trades.append({"asset": sym, "subset": subset, "h": h, "entry_ms": int(x), "split": ss,
                                   "ret_bp": float(rr), "funding_bp": float(ff)})
            log(f"{sym} {h}h done")
    out = pd.DataFrame(cells)
    dec = out.decision
    out["p_holm"] = np.nan
    out.loc[dec, "p_holm"] = rule.holm(out.loc[dec, "p"].to_numpy())
    return out, pd.DataFrame(trades)


def run(plumb=False, lane=LANE, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        verify_data()
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match; bar and funding parquet match manifests")
    if plumb:
        plumbing(lane)
        log("PLUMBING counts only")
        return "PLUMBING"
    out, trades = score(lane)
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    out.to_csv(res / "cells.csv", index=False)
    trades.to_csv(res / "trades.csv", index=False)
    dec = out[out.decision].set_index(["asset", "subset", "h"]).loc[list(rule.DECISIONS)].reset_index()
    state, text = rule.verdict(dec.to_dict("records"))
    (res / "summary.json").write_text(json.dumps({
        "registry": REGISTRY, "state": state, "text": text, "cells": len(out), "cost_unit_bp": rule.UNIT_COST_BP,
        "decisions": json.loads(dec.to_json(orient="records"))}, indent=1) + "\n")
    log(state, text)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    run(plumb=a.plumbing)


if __name__ == "__main__":
    main()
