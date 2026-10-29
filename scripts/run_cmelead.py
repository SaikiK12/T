"""R370 cmelead_v1 runner, frozen in experiments/cmelead_v1/PREREG.md: after an EIA release moves CME's crude or gas future,
does Binance's TradFi perp lag it long enough for a taker to earn the catch-up?

Reads experiments/cmelead_v1/windows.csv (60 releases and their placebo days), the CME trades of data/databento/cmelead/ and
the Binance aggregated trades of data/cmelead/binance/, scores scripts/cmelead_rule.py once and writes
experiments/cmelead_v1/results/.

usage: python scripts/run_cmelead.py              the frozen run (verifies the PREREG, its inputs and the data hashes)
       python scripts/run_cmelead.py --plumbing   trade counts and reference availability per window; no price change, state
                                                  or test is computed
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.csv as pc

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import prereg  # noqa: E402
import cmelead_rule as rule  # noqa: E402

LANE = ROOT / "experiments" / "cmelead_v1"
REGISTRY = "R370"
PROV = ROOT / "docs" / "provenance" / "cmelead.json"
BN = ROOT / "data" / "cmelead" / "binance"
CME = ROOT / "data" / "databento" / "cmelead"
US = rule.US
CELL_COLS = ["event", "kind", "release_ms", "anchor_ms", "lag_s", "status", "s", "t_star_s", "D", "c", "lag_ok", "entry", "exit",
             "entry_wait_s", "gross"]
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


def verify_data(prov=PROV, root=ROOT):
    """Every file the provenance note lists must exist and hash to its recorded sha256; the digest is returned."""
    body = json.loads(Path(prov).read_text())
    for h in body["file_hashes"]:
        got = prereg.sha256_file(root / h["path"])
        if got != h["sha256"]:
            raise prereg.PreregError(f"{h['path']}: sha256 {got} != provenance {h['sha256']}")
    return body["combined_sha256"]


def cme_path(w):
    stem = "_".join(["GLBX.MDP3", w.cme, "trades", iso(w.lo_ms), iso(w.hi_ms)]).replace(":", "")
    return CME / f"{stem}.csv.zst"


def iso(ms):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ms / 1000))


def load_cme(path):
    """Trades only (action T) with a positive price: dict of t (UTC microseconds, the exchange's event time) and price."""
    tab = pc.read_csv(pa.input_stream(str(path), compression="zstd"))
    t_ns = np.asarray(tab["ts_event"].cast(pa.timestamp("ns", "UTC")).cast(pa.int64()))
    act = np.asarray(tab["action"].to_pylist())
    price = np.asarray(tab["price"].cast(pa.float64()))
    keep = (act == "T") & np.isfinite(price) & (price > 0)
    order = np.argsort(t_ns[keep], kind="stable")
    return {"t": (t_ns[keep] // 1000)[order], "price": price[keep][order]}


def load_binance(sym, anchor_ms):
    path = BN / sym / f"{anchor_ms}.parquet"
    if not path.exists():                                   # a placebo day before the archive begins: counted as no_ref
        return {"t": np.array([], dtype=np.int64), "price": np.array([]), "buyer_maker": np.array([], dtype=bool)}
    df = pd.read_parquet(path).sort_values(["t", "agg_id"], kind="stable")
    return {"t": df.t.to_numpy(dtype=np.int64) * 1000, "price": df.price.to_numpy(dtype=float),
            "buyer_maker": df.buyer_maker.to_numpy(dtype=bool)}


def counts(w, lead, fol):
    T_us = int(w.anchor_ms) * US // 1000
    near = lambda a: int(((a["t"] >= T_us) & (a["t"] <= T_us + 60 * US)).sum())  # noqa: E731
    return {"cme_trades": len(lead["t"]), "binance_prints": len(fol["t"]), "cme_after": near(lead), "binance_after": near(fol),
            "ref_cme": bool(np.isfinite(rule.reference(lead, T_us))), "ref_binance": bool(np.isfinite(rule.reference(fol, T_us)))}


def invalid(c):
    """Why a window cannot be scored (a recording hole, never a lost trade), or ''."""
    if not (c["ref_cme"] and c["ref_binance"]):
        return "no_ref"
    if c["cme_after"] == 0 or c["binance_after"] == 0:
        return "no_trades_after"
    return ""


def score_window(w, lead, fol):
    T_us = int(w.anchor_ms) * US // 1000
    rows = []
    for L in rule.LAGS:
        r = rule.evaluate(lead, fol, T_us, w.event, L)
        rows.append({"event": w.event, "kind": w.kind, "release_ms": int(w.release_ms), "anchor_ms": int(w.anchor_ms),
                     "lag_s": L, **r})
    return rows


def cell_stats(g, k_rng):
    x = g.gross.to_numpy(dtype=float)
    s = rule.summarize(x)
    out = {**s, "p": rule.sign_flip_p(x, k_rng)}
    out["mde80"] = 2.8 * s["sd"] / np.sqrt(s["n"]) if s["n"] > 1 and np.isfinite(s["sd"]) else np.nan
    for k in rule.COST_MULTS:
        out[f"net_{k}x"] = s["mean"] - k * 2 * rule.FEE_SIDE_BP if s["n"] else np.nan
    return out


def summarize(cells, windows_valid):
    """One row per (event type, latency, subset) for the release windows, with Holm over the two decision cells."""
    rng = np.random.default_rng(rule.SEED)
    rows = []
    ev = cells[cells.kind == "event"]
    for etype in sorted(windows_valid):
        for L in rule.LAGS:
            g = ev[(ev.event == etype) & (ev.lag_s == L) & (ev.status == "ok")]
            for subset, sel in (("filtered", g[g.lag_ok.astype(bool)]), ("all", g)):
                rows.append({"event": etype, "lag_s": L, "subset": subset,
                             "decision": bool(L == rule.DECISION_L and subset == "filtered"),
                             "valid": windows_valid[etype], **cell_stats(sel, rng)})
    out = pd.DataFrame(rows)
    dec = out[out.decision]
    out["p_holm"] = np.nan
    out.loc[dec.index, "p_holm"] = rule.holm(dec.p.to_numpy())
    return out


def placebo_table(cells):
    """Fire counts and mean gross on the placebo days, the decision latency, filtered and not. Reported, not decided on."""
    pl = cells[(cells.kind != "event") & (cells.lag_s == rule.DECISION_L)]
    rows = []
    for (etype, kind), g in pl.groupby(["event", "kind"]):
        ok = g[g.status == "ok"]
        rows.append({"event": etype, "kind": kind, "windows": len(g), "crossed": int((g.status != "no_cross").sum()),
                     "ok": len(ok), "filtered": int(ok.lag_ok.astype(bool).sum()),
                     "mean_gross_all": float(ok.gross.mean()) if len(ok) else np.nan,
                     "mean_gross_filtered": float(ok[ok.lag_ok.astype(bool)].gross.mean()) if ok.lag_ok.astype(bool).any() else np.nan})
    return pd.DataFrame(rows)


def run(plumbing=False, lane=LANE, check=True):
    if check:
        digest = prereg.verify(lane / "PREREG.md")
        inputs = frozen_inputs(lane / "PREREG.md")
        log(f"PREREG verified {digest[:12]}; {len(inputs)} inputs match; data digest {verify_data()[:12]}")
    windows = pd.read_csv(lane / "windows.csv")
    res = lane / "results"
    res.mkdir(parents=True, exist_ok=True)
    cov, cells = [], []
    for w in windows.itertuples():
        lead, fol = load_cme(cme_path(w)), load_binance(w.binance, w.anchor_ms)
        c = counts(w, lead, fol)
        why = invalid(c)
        cov.append({"event": w.event, "kind": w.kind, "release_ms": w.release_ms, "anchor_ms": w.anchor_ms, **c, "invalid": why})
        if not plumbing and not why:
            cells += score_window(w, lead, fol)
    cov = pd.DataFrame(cov)
    cov.to_csv(res / "coverage.csv", index=False)
    ev = cov[cov.kind == "event"]
    valid = ev[ev.invalid == ""].groupby("event").size().to_dict()
    log("valid release windows:", {e: f"{valid.get(e, 0)}/{(ev.event == e).sum()}" for e in sorted(ev.event.unique())},
        "| placebo windows valid:", int(((cov.kind != "event") & (cov.invalid == "")).sum()), "of", int((cov.kind != "event").sum()))
    if plumbing:
        log("PLUMBING counts only")
        return "PLUMBING"
    cells = pd.DataFrame(cells, columns=CELL_COLS)
    cells.to_csv(res / "windows_scored.csv", index=False)
    out = summarize(cells, {e: int(valid.get(e, 0)) for e in sorted(ev.event.unique())})
    out.to_csv(res / "cells.csv", index=False)
    placebo_table(cells).to_csv(res / "placebo.csv", index=False)
    status = (cells[cells.kind == "event"].groupby(["event", "lag_s", "status"]).size().rename("n").reset_index())
    status.to_csv(res / "status_counts.csv", index=False)
    dec = out[out.decision]
    state, text = rule.verdict(dec.to_dict("records"))
    (res / "summary.json").write_text(json.dumps({"registry": REGISTRY, "state": state, "text": text, "valid": valid,
                                                  "decisions": json.loads(dec.to_json(orient="records")),
                                                  "cells": len(out), "cost_unit_bp": 2 * rule.FEE_SIDE_BP}, indent=1) + "\n")
    log(state, text)
    return state


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    run(plumbing=a.plumbing)
