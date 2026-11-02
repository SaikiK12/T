"""R383 presence_v1: does R282's oi_mcap book depend on whether a row has Binance metrics?

R282 (`scripts/pitfac_factors.py`, frozen) ranks the top-150 Binance perps by 30-day volume on six factors and
oi_mcap = ln(oi_usd / mcap_est). On `data/daily/panel.parquet` a row holds oi_usd only if the coin was among the 100
most traded within 35 days (R332), so oi_mcap has about 56 names a day, and having a value is itself a forward signal.
`data/daily_v2/panel.parquet` holds the metrics for every top-150 row. This lane builds R282's factor table from both
panels with R282's own `factors()`, adds a presence control, and runs R282's engine (`qx factors`, unchanged) on one
table of five books:

| book | values |
|---|---|
| oi_mcap_v1 | R282's oi_mcap on data/daily (must reproduce R282's frozen table and report) |
| oi_mcap_v2 | the same construction on data/daily_v2 |
| oi_mcap_v2_on_v1 | v2's oi_mcap kept only where v1 has a value (same rows as v1) |
| presence_v1 | 1 + u where the row holds oi_usd on data/daily, else u; u ~ U(0,1), seed 383 |
| presence_v2 | the same on data/daily_v2 |

The engine's top-minus-bottom fifth of presence is a random fifth of the rows with metrics against a random fifth of
the rows without (R332's presence book, on R282's universe, hold and cost). Decision: see PREREG.md.

usage: python scripts/run_presence.py [--plumbing]       (--plumbing builds and compares tables; no return is read)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts.pitfac_factors import H, NEED, factors  # noqa: E402
from scripts.qx_run_verified import _manifest_snapshot  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "presence_v1"
PANEL1 = ROOT / "data" / "daily" / "panel.parquet"
PANEL2 = ROOT / "data" / "daily_v2" / "panel.parquet"
FROZEN = ROOT / "experiments" / "pitfac_v1" / "factors.parquet"
R282 = ROOT / "experiments" / "pitfac_v1" / "results" / "report.json"
QX = ROOT / "engine" / "target" / "release" / "qx"
TABLE = LANE / "results" / "table.parquet"
SEED = 383
BOOKS = ["oi_mcap_v1", "oi_mcap_v2", "oi_mcap_v2_on_v1", "presence_v1", "presence_v2"]
RUNS = ["all_1x", "all_2x", "all_3x", "d_1x", "v_1x"]                 # specs spec_<run>.toml; decision reads all_1x
T_BAR = 2.0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def same(a, b):
    """NaN-aware exact equality of two float arrays."""
    return bool(((a == b) | (np.isnan(a) & np.isnan(b))).all())


def has_oi(panel, keys):
    """1.0 where the panel row (day, perp) holds oi_usd, for the factor table's (t, sym) keys."""
    p = panel[["day", "perp", "oi_usd"]].assign(day=lambda d: pd.to_datetime(d.day), perp=lambda d: d.perp.astype(str))
    p = p.assign(has=p.oi_usd.notna().astype(float)).set_index(["day", "perp"]).has
    day = pd.to_datetime(keys.t.to_numpy() + H, unit="ms")
    idx = pd.MultiIndex.from_arrays([day, keys.sym.to_numpy()])
    return p.reindex(idx).to_numpy()


def build():
    df1 = pd.read_parquet(PANEL1, columns=NEED)
    df2 = pd.read_parquet(PANEL2, columns=NEED)
    f1, f2 = factors(df1), factors(df2)
    frozen = pd.read_parquet(FROZEN)
    other = [c for c in f1.columns[2:] if c != "oi_mcap"]
    chk = {"rows": len(f1),
           "v1_equals_R282_table": bool(list(f1.columns) == list(frozen.columns) and len(f1) == len(frozen)
                                        and (f1.t.to_numpy() == frozen.t.to_numpy()).all()
                                        and (f1.sym.to_numpy() == frozen.sym.to_numpy()).all()
                                        and all(same(f1[c].to_numpy(), frozen[c].to_numpy()) for c in f1.columns[2:])),
           "v2_same_rows": bool(len(f1) == len(f2) and (f1.t.to_numpy() == f2.t.to_numpy()).all()
                                and (f1.sym.to_numpy() == f2.sym.to_numpy()).all()),
           "other_factors_identical_v1_v2": {c: same(f1[c].to_numpy(), f2[c].to_numpy()) for c in other}}
    has1, has2 = has_oi(df1, f1), has_oi(df2, f2)
    u = np.random.default_rng(SEED).random(len(f1))
    tab = f1[["t", "sym"]].copy()
    tab["oi_mcap_v1"] = f1.oi_mcap.to_numpy()
    tab["oi_mcap_v2"] = f2.oi_mcap.to_numpy()
    tab["oi_mcap_v2_on_v1"] = np.where(f1.oi_mcap.notna().to_numpy(), f2.oi_mcap.to_numpy(), np.nan)
    tab["presence_v1"] = has1 + u
    tab["presence_v2"] = has2 + u
    day = pd.to_datetime(f1.t.to_numpy() + H, unit="ms")
    g = pd.DataFrame({"year": day.year, "has1": has1, "has2": has2,
                      "m1": f1.oi_mcap.notna().to_numpy(), "m2": f2.oi_mcap.notna().to_numpy()})
    chk["share_with_oi_usd_by_year"] = {int(y): [round(float(x.has1.mean()), 3), round(float(x.has2.mean()), 3)]
                                        for y, x in g.groupby("year")}
    names = pd.DataFrame({"d": day, "m1": g.m1, "m2": g.m2, "has1": has1, "has2": has2})
    per = names.groupby("d").agg(m1=("m1", "sum"), m2=("m2", "sum"), n=("m1", "size"), s1=("has1", "mean"),
                                 s2=("has2", "mean"))
    chk["oi_mcap_names_per_day"] = {"v1_mean": round(float(per.m1.mean()), 1), "v2_mean": round(float(per.m2.mean()), 1),
                                    "v1_days_ge30": int((per.m1 >= 30).sum()), "v2_days_ge30": int((per.m2 >= 30).sum()),
                                    "universe_mean": round(float(per.n.mean()), 1), "days": len(per)}
    chk["days_with_share_between_20_and_80pct"] = {"v1": int(((per.s1 >= .2) & (per.s1 <= .8)).sum()),
                                                  "v2": int(((per.s2 >= .2) & (per.s2 <= .8)).sum())}
    chk["oi_mcap_values_v1_vs_v2_where_both"] = {
        "rows_both": int((f1.oi_mcap.notna() & f2.oi_mcap.notna()).sum()),
        "rows_differ": int((f1.oi_mcap.notna() & f2.oi_mcap.notna()
                            & ~np.isclose(f1.oi_mcap, f2.oi_mcap, rtol=0, atol=1e-9)).sum()),
        "rows_v1_only": int((f1.oi_mcap.notna() & f2.oi_mcap.isna()).sum()),
        "rows_v2_only": int((f1.oi_mcap.isna() & f2.oi_mcap.notna()).sum())}
    return tab, chk


def run_engine(name):
    spec = LANE / f"spec_{name}.toml"
    out = LANE / "results" / name
    with open(LANE / "run.log", "a") as f:
        subprocess.run([str(QX), "factors", str(spec)], cwd=ROOT, check=True, stderr=f,
                       env={**os.environ, "QX_DATA": str(ROOT / "data")})
    return json.loads((out / "report.json").read_text()), pd.read_csv(out / "ic.csv")


def pick(rep, factor, h=24):
    return next(r for r in rep["results"] if r["factor"] == factor and r["horizon_h"] == h)


def book_row(rep, factor):
    """Top-minus-bottom fifth, h = 24: gross, net at the run's cost, the NW t of that net, the rank IC."""
    r = pick(rep, factor)
    paid = r["ls_bp"] - r["ls_net_bp"]
    return {"dates": r["dates"], "names": round(r["mean_names"], 1), "gross_bp_day": r["ls_bp"], "gross_t": r["ls_t"],
            "net_bp_day": r["ls_net_bp"], "net_t": r["ls_net_t"], "paid_bp_day": paid, "rank_ic": r["rank_ic"],
            "turnover_top": r["turnover_top"], "turnover_bottom": r["turnover_bottom"],
            "gross_by_h_bp": {h: pick(rep, factor, h)["ls_bp"] for h in (24, 72, 168)}}


def reproduction(rep):
    """oi_mcap_v1 against R282's report, h = 24, 72, 168: rank IC, gross spread and (h = 24) net and its t."""
    old = json.loads(R282.read_text())
    worst = 0.0
    for h in (24, 72, 168):
        a = next(r for r in old["results"] if r["factor"] == "oi_mcap" and r["horizon_h"] == h)
        b = pick(rep, "oi_mcap_v1", h)
        keys = ["rank_ic", "ls_bp", "ic", "dates"] + (["ls_net_bp", "ls_net_t"] if h == 24 else [])
        for k in keys:
            worst = max(worst, abs(a[k] - b[k]) / max(1e-12, abs(a[k])))
    return {"max_relative_difference": worst, "match": worst < 1e-6}


def by_year(ic, factor):
    d = ic[(ic.factor == factor) & (ic.horizon_h == 24)].copy()
    d["year"] = pd.to_datetime(d.t + H, unit="ms").dt.year
    out = {int(y): round(float(x.ls.mean() * 1e4), 1) for y, x in d.groupby("year")}
    s = np.sort(d.ls.to_numpy())[::-1]
    out["gross_without_best_10_days"] = round(float(s[10:].mean() * 1e4), 1)
    out["gross_median"] = round(float(d.ls.median() * 1e4), 1)
    out["best_10_share_of_sum"] = round(float(s[:10].sum() / s.sum()), 2) if s.sum() > 0 else None
    return out


def decide(t1, t2, tp, repro):
    """The frozen rule (PREREG): signed net 1x t of the long-top book, window ALL, h = 24."""
    if not repro:
        return "INVALID", "NULL", "oi_mcap_v1 does not reproduce R282; no label"
    if t1 < T_BAR:
        return "INVALID", "NULL", "R282's book has t < 2 here; premise failed"
    if t2 >= T_BAR:
        return "survives", "PARTIAL", "v2 t >= 2" + ("; presence t >= 2 too" if tp >= T_BAR else "")
    if tp >= T_BAR:
        return "metrics-leak", "NULL", "presence t >= 2 and v2 t < 2"
    return "not-reproduced", "NULL", "v2 t < 2 and presence t < 2: not attributed to presence"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    if a.plumbing:
        tab, chk = build()
        print(json.dumps(chk, indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    for n in RUNS:
        tomllib.loads((LANE / f"spec_{n}.toml").read_text())
    prov = {f: ROOT / "docs" / "provenance" / f"{f}.json" for f in ("klines_1h", "fundingRate")}
    data_before = {f: _manifest_snapshot(ROOT, p, json.loads(p.read_text())) for f, p in prov.items()}
    log("data folders match their provenance: " + ", ".join(f"{f} {v['files']} files" for f, v in data_before.items()))
    tab, chk = build()
    log(f"table built: {chk['rows']} rows; v1 equals R282's frozen table {chk['v1_equals_R282_table']}; v2 same rows "
        f"{chk['v2_same_rows']}; other factors identical {all(chk['other_factors_identical_v1_v2'].values())}")
    (LANE / "results").mkdir(exist_ok=True)
    tab.to_parquet(TABLE, index=False)
    reps, ics = {}, {}
    for n in RUNS:
        reps[n], ics[n] = run_engine(n)
        log(f"engine run {n} done")
    data_after = {f: _manifest_snapshot(ROOT, p, json.loads(p.read_text())) for f, p in prov.items()}
    if data_after != data_before:
        raise SystemExit("a data folder changed during the run")
    log("data folders unchanged after the run")
    out = {"rid": "R383", "prereg_sha256": sha, "inputs": shas, "plumbing": chk,
           "reproduction_R282": reproduction(reps["all_1x"]), "books": {}, "by_year_gross_bp": {}}
    for n in RUNS:
        out["books"][n] = {b: book_row(reps[n], b) for b in BOOKS}
    for b in BOOKS:
        out["by_year_gross_bp"][b] = by_year(ics["all_1x"], b)
    all1 = out["books"]["all_1x"]
    # R282's frozen direction (long low oi_mcap) from the same engine output: -gross - paid
    out["long_low_net_bp_day"] = {b: {f"{k}x": -r["gross_bp_day"] - k * r["paid_bp_day"] for k in (1, 2, 3)}
                                  for b, r in all1.items() if b.startswith("oi_mcap")}
    t1, t2, tp = (all1[b]["net_t"] for b in ("oi_mcap_v1", "oi_mcap_v2", "presence_v1"))
    label, verdict, why = decide(t1, t2, tp, out["reproduction_R282"]["match"])
    out["decision"] = {"t_oi_mcap_v1": t1, "t_oi_mcap_v2": t2, "t_presence_v1": tp, "label": label, "verdict": verdict,
                       "why": why, "trials": len(BOOKS)}
    (LANE / "results" / "summary.json").write_text(json.dumps(out, indent=1, default=str))
    log(f"t net 1x: oi_mcap v1 {t1:+.2f}, v2 {t2:+.2f}, presence v1 {tp:+.2f}; label {label}; verdict {verdict} ({why})")
    return out


if __name__ == "__main__":
    main()
