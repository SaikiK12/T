"""R461 earnperp_v1 runner, frozen in experiments/earnperp_v1/PREREG.md: after an out-of-hours earnings release (SEC 8-K
Item 2.02), does a 24/7 stock perp keep moving the way it first moved, or turn back, by the next cash open and close?

Sample A: releases accepted before 2026-10-21 00:00 UTC, priced on data/mexc_tradfi/klines_1h (held before the freeze).
Sample B: releases accepted 2026-10-21 .. 2026-11-09, priced on data/mexc_stock_post/klines_1h, fetched after the
freeze by scripts/fetch_mexc_stock_1h.py. The market hedge (diagnostic) is MEXC's SPX500_USDT perp in both.

usage: python scripts/run_earnperp.py              the frozen run (verifies the PREREG and every input it lists)
       python scripts/run_earnperp.py --plumbing   event counts per sample and session, and the symbol list for sample
                                                   B; reads bar times only, no price
"""
import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import earnperp_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "earnperp_v1"
REGISTRY = "R461"
A_DIR = ROOT / "data" / "mexc_tradfi" / "klines_1h"
B_DIR = ROOT / "data" / "mexc_stock_post" / "klines_1h"
NAMED = {"NVDA": "NVIDIA", "TSLA": "TESLA", "COIN": "COINBASE", "HOOD": "ROBINHOOD"}
B_START = pd.Timestamp("2026-10-21", tz="UTC")
B_END = pd.Timestamp("2026-11-10", tz="UTC")
LISTED_MS = 2 * 86_400_000
HEDGE = "SPX500_USDT"
SUBSETS = ("all", "pos", "neg", "big")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)  # noqa: E731


def frozen_inputs(prereg_path, root=ROOT):
    block = re.search(r"```inputs\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    rows = [ln.split() for ln in block.strip().splitlines() if ln.strip()]
    for want, rel in rows:
        got = prereg.sha256_file(root / rel)
        if got != want:
            raise prereg.PreregError(f"{rel}: sha256 {got} != frozen {want}")
    return rows


def verify_bars(syms):
    """Sample A files must match docs/provenance/mexc_tradfi.json; sample B files their fetch manifest."""
    a = {h["path"]: h["sha256"] for h in json.loads((ROOT / "docs/provenance/mexc_tradfi.json").read_text())
         ["file_hashes"]}
    bman = B_DIR.parent / "manifest.json"
    b = json.loads(bman.read_text())["symbols"] if bman.exists() else {}
    n = 0
    for s in syms:
        pa, pb = A_DIR / f"{s}.parquet", B_DIR / f"{s}.parquet"
        if pa.exists():
            if prereg.sha256_file(pa) != a.get(f"klines_1h/{s}.parquet"):
                raise prereg.PreregError(f"{pa}: sha256 differs from docs/provenance/mexc_tradfi.json")
            n += 1
        if pb.exists():
            if prereg.sha256_file(pb) != b.get(s, {}).get("sha256"):
                raise prereg.PreregError(f"{pb}: sha256 differs from its fetch manifest")
            n += 1
    return n


def symbol(ticker):
    return NAMED.get(ticker, ticker + "STOCK") + "_USDT"


def bars(sym, cols=("t", "open")):
    parts = []
    for d in (A_DIR, B_DIR):
        p = d / f"{sym}.parquet"
        if p.exists():
            parts.append(pq.read_table(p, columns=list(cols)).to_pandas())
    if not parts:
        return None
    df = pd.concat(parts).drop_duplicates("t", keep="first").sort_values("t")
    return df


def events(lane=LANE):
    ev = pd.read_csv(lane / "events.csv")
    ev["acc"] = pd.to_datetime(ev.acceptance_utc, utc=True)
    ev["acc_ms"] = [int(x.timestamp() * 1000) for x in ev.acc]
    ev["sample"] = np.where(ev.acc < B_START, "A", np.where(ev.acc < B_END, "B", ""))
    ev = ev[ev["sample"] != ""].copy()
    inst = [rule.instants(int(x)) for x in ev.acc_ms]
    ev["session"] = [i["session"] for i in inst]
    for k in ("R", "E", "X1", "X2"):
        ev[k] = [i.get(k) for i in inst]
    ev["N"] = [i.get("N") for i in inst]
    ev["sym"] = [symbol(t) for t in ev.ticker]
    return ev.reset_index(drop=True)


def usable(ev):
    """Keep events whose perp has bars from at least two days before the filing; drop a repeated ticker-day."""
    first = {}
    for s in ev.sym.unique():
        b = bars(s, ("t",))
        first[s] = int(b.t.min()) if b is not None and len(b) else None
    ok = [first[s] is not None and first[s] <= a - LISTED_MS for s, a in zip(ev.sym, ev.acc_ms)]
    ev = ev[np.array(ok) & ev.session.notna()].copy()
    return ev.drop_duplicates(["ticker", "N", "session"]).reset_index(drop=True)


def plumbing(lane=LANE):
    ev = events(lane)
    log("filings by sample and session:", ev.groupby(["sample", ev.session.fillna("other")]).size().to_dict())
    ok = usable(ev)
    log("usable:", ok.groupby(["sample", "session"]).size().to_dict())
    b_syms = sorted(set(ev[ev["sample"] == "B"].sym) | {HEDGE})
    (lane / "sample_b_symbols.txt").write_text("\n".join(b_syms) + "\n")
    log(f"{len(b_syms)} symbols written for sample B")
    return ok


def compute(ev):
    rows = []
    hedge = bars(HEDGE)
    ht, ho = hedge.t.to_numpy("int64"), hedge.open.to_numpy("float64")
    cache = {}
    for r in ev.itertuples():
        if r.sym not in cache:
            b = bars(r.sym)
            cache[r.sym] = (b.t.to_numpy("int64"), b.open.to_numpy("float64"))
        t, o = cache[r.sym]
        inst = {"R": r.R, "E": r.E, "X1": r.X1, "X2": r.X2}
        x = rule.event_row(t, o, inst)
        if x["s"] == 0:
            continue
        pe = rule.price_at(ht, ho, r.E)
        for k in ("x1", "x2"):
            px = rule.price_at(ht, ho, inst[k.upper()])
            mk = 1e4 * math.log(px / pe) if pe > 0 and px > 0 and inst[k.upper()] > r.E else math.nan
            x[f"h{k}"] = x[k] - x["s"] * mk if np.isfinite(x[k]) else math.nan
        rows.append({"ticker": r.ticker, "sample": r.sample, "session": r.session, "acc": r.acceptance_utc,
                     "N": r.N, **x})
    return pd.DataFrame(rows)


def subset(df, name, cut):
    if name == "pos":
        return df[df.s > 0]
    if name == "neg":
        return df[df.s < 0]
    if name == "big":
        return df[df.r0.abs() >= cut]
    return df


def score(per, rng):
    cells = []
    for sess in ("amc", "bmo"):
        a_sess = per[(per["sample"] == "A") & (per.session == sess)]
        cut = float(a_sess.r0.abs().quantile(2 / 3)) if len(a_sess) else math.nan
        for sub in SUBSETS:
            for h in ("x1", "x2"):
                for hedged in (False, True):
                    col = ("h" if hedged else "") + h
                    row = {"session": sess, "subset": sub, "h": h, "hedged": hedged,
                           "decision": (sess, h) in rule.DECISIONS and sub == "all" and not hedged}
                    for smp in ("A", "B"):
                        d = subset(per[(per["sample"] == smp) & (per.session == sess)], sub, cut)
                        v = d[col].to_numpy(float)
                        keep = np.isfinite(v)
                        v, cl = v[keep], d.N.to_numpy()[keep]
                        n = len(v)
                        sd = float(np.std(v, ddof=1)) if n > 1 else math.nan
                        row.update({f"n_{smp.lower()}": n, f"mean_{smp.lower()}": float(np.mean(v)) if n else math.nan,
                                    f"sd_{smp.lower()}": sd, f"days_{smp.lower()}": len(set(cl)),
                                    f"hit_{smp.lower()}": float(np.mean(v > 0)) if n else math.nan,
                                    f"mde80_{smp.lower()}": rule.mde80(sd, n),
                                    f"p_{smp.lower()}": rule.cluster_flip_p(v, cl, rng) if n else math.nan})
                    for c in rule.COST_MULTS:
                        row[f"net_{c}x_a"] = abs(row["mean_a"]) - c * rule.UNIT_COST_BP
                    cells.append(row)
    out = pd.DataFrame(cells)
    dec = out.decision
    out["p_holm"] = np.nan
    out.loc[dec, "p_holm"] = rule.holm(out.loc[dec, "p_a"].to_numpy())
    return out


def run(plumb=False, lane=LANE, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match")
    if plumb:
        plumbing(lane)
        return "PLUMBING"
    ev = usable(events(lane))
    if check:
        log(f"bar files verified: {verify_bars(set(ev.sym) | {HEDGE})}")
    per = compute(ev)
    out = score(per, np.random.default_rng(rule.SEED))
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    per.to_csv(res / "events.csv", index=False)
    out.to_csv(res / "cells.csv", index=False)
    dec = out[out.decision].set_index(["session", "h"]).loc[list(rule.DECISIONS)].reset_index()
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
