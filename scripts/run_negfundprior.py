"""negfundprior_v1 (R381): R273's negative-funding onsets split by the coin's prior 30-day direction (M458), as set out in
experiments/negfundprior_v1/PREREG.md. The events are R273's rows of kind neg0.3 as they are; the prior direction is the
sign of the close-to-close move over the 30 days that end at the settlement; the long leg, its holding rule and its costs
are R273's, priced by the same qx engine; the up-state validation cell also gets the engine's matched-date null.

usage: .venv/bin/python scripts/run_negfundprior.py [--register]
       .venv/bin/python scripts/run_negfundprior.py --decoy KIND OUTDIR   (code test on another R273 kind; never writes
                                                                         into the lane or the registry)
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, registry  # noqa: E402

LANE = ROOT / "experiments" / "negfundprior_v1"
SRC = ROOT / "experiments" / "fundext_v1"
QX = ROOT / "engine" / "target" / "release" / "qx"
KLINES = ROOT / "data" / "klines_1h"
HOUR, DAY = 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
LOOK = 30 * DAY                                                     # the prior window
STALE = 24                                                          # a prior price may be at most 24 h stale
KIND = "neg0.3"                                                     # the family; neg1 and neg2 are reported, not counted
OTHER = ("neg1", "neg2")
SHORT = {"neg0.3": "n03", "neg1": "n1", "neg2": "n2", "pos0.3": "p03"}
H = (24, 72)
COSTS = (0.004, 0.008, 0.012)                                       # R273's round trip at 1x / 2x / 3x
MIN_CLUSTERS = 30                                                   # an up-state validation cell below this fails
TRIM = 10
T_MIN = 2.0
ALPHA = 0.05
TRIALS = 6
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------ prior direction
def prior_close(ts, cl, x):
    """Close of the last valid bar that opens in [x - (STALE + 1) h, x - 1 h]: the price at x, no later than x."""
    x = (int(x) // HOUR) * HOUR
    i = int(np.searchsorted(ts, x - HOUR, side="right")) - 1
    if i < 0 or ts[i] < x - (STALE + 1) * HOUR:
        return math.nan
    return float(cl[i])


def prior_return(ts, cl, t0):
    """Close-to-close move over the 30 days that end at the settlement t0; NaN if either end has no price."""
    p1, p0 = prior_close(ts, cl, t0), prior_close(ts, cl, t0 - LOOK)
    return p1 / p0 - 1.0 if p1 == p1 and p0 == p0 and p0 > 0 else math.nan


def load_klines(sym, klines=KLINES):
    """Valid bars from 2021-01-01 only: the filter drops 2020 rows before any use."""
    k = pd.read_parquet(Path(klines) / f"{sym}.parquet", columns=["t", "close", "count"], filters=[("t", ">=", T0)])
    k = k[(k["count"] > 0) & (k.close > 0)].drop_duplicates("t").sort_values("t")
    return k.t.values.astype(np.int64), k.close.values.astype(float)


def add_prior(legs, klines=KLINES):
    legs = legs.copy()
    legs["ret30"] = math.nan
    for sym, idx in legs.groupby("perp").groups.items():
        ts, cl = load_klines(sym, klines)
        legs.loc[idx, "ret30"] = [prior_return(ts, cl, t) for t in legs.loc[idx, "release_ms"]]
    return legs


def assign(legs, kind):
    """state (up if the prior 30-day move is > 0, else dn) and part (val = the later half by settlement time of the
    eligible legs of `kind`, dev = the earlier half). Returns the legs with ret30, state, part and the split time."""
    legs = legs[legs.ret30.notna()].copy()
    legs["state"] = np.where(legs.ret30 > 0, "up", "dn")
    ts = np.sort(legs.loc[legs.kind == kind, "release_ms"].values)
    split = int(ts[len(ts) // 2])
    legs["part"] = np.where(legs.release_ms >= split, "val", "dev")
    return legs, split


def label(kind, state, part):
    return f"{SHORT[kind]}_{state}_{part}"


# ------------------------------------------------------------------------------------------------------ statistics
def tstat(x):
    x = np.asarray(x, float)
    if len(x) < 2:
        return math.nan
    sd = x.std(ddof=1)
    return float(x.mean() / (sd / math.sqrt(len(x)))) if sd > 0 else math.nan


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return math.nan
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float((a.mean() - b.mean()) / se) if se > 0 else math.nan


def obs(d, net):
    """One observation per cluster (same label, same r0 hour): the equal-weight mean net of its legs."""
    return pd.Series(net.values, index=d.r0.values).groupby(level=0).mean()


def cell(d, h, null_p=math.nan):
    """R273's long leg at horizon h on the legs `d`: net = -(sg + cost); the mean over cluster observations."""
    d = d[d[f"sg_{h}"].notna()]
    if d.empty:
        return {"h": h, "legs": 0, "n": 0, "mean1": math.nan, "mean2": math.nan, "mean3": math.nan, "median1": math.nan,
                "hit1": math.nan, "t1": math.nan, "trim1": math.nan, "null_p": null_p}
    n1 = -d[f"sg_{h}"] - COSTS[0]
    o = [obs(d, -d[f"sg_{h}"] - c) for c in COSTS]
    keep = n1.sort_values(ascending=False, kind="stable").index[TRIM:]           # without its 10 best legs
    dt = d.loc[keep]
    trim = float(obs(dt, -dt[f"sg_{h}"] - COSTS[0]).mean()) if len(dt) else math.nan
    return {"h": h, "legs": int(len(d)), "n": int(len(o[0])), "mean1": float(o[0].mean()), "mean2": float(o[1].mean()),
            "mean3": float(o[2].mean()), "median1": float(o[0].median()), "hit1": float((o[0] > 0).mean()),
            "t1": tstat(o[0].values), "trim1": trim, "null_p": null_p}


def decide(up, dn, h):
    """The frozen pass rule at one horizon, on the validation part."""
    diff = up["mean1"] - dn["mean1"]
    c = {"up_n>=30": up["n"] >= MIN_CLUSTERS, "up_t1>=2": up["t1"] >= T_MIN, "up_mean2x>0": up["mean2"] > 0,
         "up_trim10>0": up["trim1"] > 0, "diff_up_minus_dn>0": diff > 0, "dn_t1<2": dn["t1"] < T_MIN,
         "null_p<0.05": up["null_p"] < ALPHA}
    return {"h": h, "conditions": {k: bool(v) for k, v in c.items()}, "pass": bool(all(c.values()))}


# ----------------------------------------------------------------------------------------------------- the engine
def engine_spec(frozen_text, events, out):
    """The frozen spec with this run's events and output paths (the real run changes nothing)."""
    return frozen_text.replace('events = "experiments/negfundprior_v1/events.csv"', f'events = "{events}"').replace(
        'out = "experiments/negfundprior_v1/results"', f'out = "{out}"')


def run_engine(spec_path, logfile):
    with open(logfile, "a") as f:
        subprocess.run([str(QX), "events", str(spec_path)], cwd=ROOT, check=True, stderr=f,
                       env={**os.environ, "QX_DATA": str(ROOT / "data")})


def formula_check():
    """R273's frozen priced legs and the net formula reproduce R273's own table (long, 24 h and 72 h, 1x)."""
    pl = pd.read_csv(SRC / "results" / "legs_priced.csv")
    st = pd.read_csv(SRC / "results" / "strategies.csv")
    worst = 0.0
    for _, r in st[(st.dir == "long") & st.h.isin(H)].iterrows():
        c = cell(pl[pl.kind == r.kind], int(r.h))
        worst = max(worst, abs(c["mean1"] * 100 - r.mean_1x_pct), abs(c["mean2"] * 100 - r.mean_2x_pct),
                    abs(c["t1"] - r.t), abs(c["n"] - r.n))
    if worst > 1e-6:
        raise SystemExit(f"net formula does not reproduce R273's table: worst difference {worst:g}")
    return worst


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--register", action="store_true")
    ap.add_argument("--decoy", nargs=2, metavar=("KIND", "OUTDIR"))
    a = ap.parse_args(argv)
    if a.register:
        return register()
    decoy = a.decoy is not None
    kind = a.decoy[0] if decoy else KIND
    pre = LANE / "PREREG.md"
    if decoy:
        out = Path(a.decoy[1]).resolve()
        if ROOT in out.parents or out == ROOT:
            raise SystemExit("--decoy output must be outside the repository")
        events_path = out / "events.csv"
        psha, shas = "decoy", {}
    else:
        psha = prereg.verify(pre)
        from scripts.run_clockflow import check_inputs
        shas = check_inputs(pre)
        out, events_path = LANE / "results", LANE / "events.csv"
    out.mkdir(parents=True, exist_ok=True)
    logfile = out / "run.log" if decoy else LANE / "run.log"
    log("prereg", psha[:12], f"{len(shas)} inputs match" if shas else "(decoy: nothing frozen is checked)")
    t0 = time.time()
    log("net formula reproduces R273's long 24 h / 72 h table; worst difference", f"{formula_check():.2e}")

    # 1. the events as they are, and each one's prior 30-day direction
    legs = pd.read_csv(SRC / "legs.csv")
    kinds = [kind] if decoy else [kind, *OTHER]
    legs = legs[legs.kind.isin(kinds)].copy()
    if (legs.release_ms < T0).any():
        raise SystemExit("an event before 2021-01-01")
    n_before = legs.groupby("kind").size().to_dict()
    legs = add_prior(legs)
    legs, split = assign(legs, kind)
    n_after = legs.groupby("kind").size().to_dict()
    log("events by kind", n_before, "with a prior 30-day price", n_after, "split at", pd.Timestamp(split, unit="ms"))
    legs["lab"] = [label(k, s, p) for k, s, p in zip(legs.kind, legs.state, legs.part)]
    legs[["notice", "kind", "ticker", "perp", "window", "release_ms", "rate", "ret30", "state", "part", "lab"]].to_csv(
        out / "states.csv", index=False)
    ev = legs.assign(kind=legs.lab)[["notice", "kind", "ticker", "perp", "window", "release_ms", "rate"]]
    ev.to_csv(events_path, index=False)
    log("events file", events_path.name, f"{len(ev)} rows")

    # 2. R273's pricing, on the labelled events: the engine, with the matched-date null for every cell
    frozen = (LANE / "spec.toml").read_text()
    spec = engine_spec(frozen, str(events_path), str(out)) if decoy else frozen
    spec_path = out / "spec_run.toml" if decoy else LANE / "spec.toml"
    if decoy:
        spec_path.write_text(spec)
    run_engine(spec_path, logfile)
    rep = json.loads((out / "report.json").read_text())
    pl = pd.read_csv(out / "legs_priced.csv")
    eng = {(r["strat"]["kind"], r["strat"]["h"]): r for r in rep["strategies"]}

    # 3. the engine's pricing is R273's: compare every leg with R273's frozen priced legs
    r273 = pd.read_csv(SRC / "results" / "legs_priced.csv").set_index("notice")
    pk = pl.drop_duplicates("notice").set_index("notice")
    same = pk.index.intersection(r273.index)
    bad = 0
    for h in H:
        x, y = pk.loc[same, f"sg_{h}"].values, r273.loc[same, f"sg_{h}"].values
        bad += int((~((np.isnan(x) & np.isnan(y)) | (np.abs(np.nan_to_num(x) - np.nan_to_num(y)) < 1e-8))).sum())
    log(f"priced legs {len(pl)}; {len(same)} in R273's frozen priced legs; {bad} leg-horizons differ from R273's pricing")

    # 4. cells
    pl = pl.merge(legs[["notice", "kind", "state", "part", "lab"]].rename(columns={"kind": "k0"}), on="notice")
    rows, match = [], []

    def get(k, st, part, h, counted):
        lab = label(k, st, part)
        if part == "all":
            d = pl[(pl.k0 == k) & (pl.state == st)] if st != "pool" else pl[pl.k0 == k]
            npv = math.nan
        else:
            d = pl[(pl.k0 == k) & (pl.part == part) & ((pl.state == st) if st != "pool" else True)]
            e = eng.get((lab, h))
            npv = (e.get("null") or {}).get("p", math.nan) if e else math.nan
            if e and st != "pool":
                c = cell(d, h)
                m = e["stats"][0]
                ok = abs(c["mean1"] * 100 - m["mean_pct"]) < 1e-6 and c["n"] == m["n"] and abs(c["t1"] - m["t"]) < 1e-6
                match.append(bool(ok))
        c = cell(d, h, npv)
        c.update({"set": "counted" if counted else "reported", "kind": k, "state": st, "part": part})
        rows.append(c)
        return c

    res = {}
    for h in H:
        for st in ("up", "dn"):
            res[st, h] = get(KIND if not decoy else kind, st, "val", h, True)
        du = obs(pl[(pl.k0 == (kind)) & (pl.part == "val") & (pl.state == "up") & pl[f"sg_{h}"].notna()],
                 -pl[f"sg_{h}"] - COSTS[0])
        dd = obs(pl[(pl.k0 == (kind)) & (pl.part == "val") & (pl.state == "dn") & pl[f"sg_{h}"].notna()],
                 -pl[f"sg_{h}"] - COSTS[0])
        rows.append({"set": "counted", "kind": kind, "state": "up-dn", "part": "val", "h": h, "legs": math.nan,
                     "n": f"{len(du)}/{len(dd)}", "mean1": res["up", h]["mean1"] - res["dn", h]["mean1"],
                     "mean2": res["up", h]["mean2"] - res["dn", h]["mean2"],
                     "mean3": res["up", h]["mean3"] - res["dn", h]["mean3"], "median1": math.nan, "hit1": math.nan,
                     "t1": welch(du.values, dd.values), "trim1": math.nan, "null_p": math.nan})
        for st in ("pool",):
            get(kind, st, "val", h, False)
        for part in ("dev", "all"):
            for st in ("up", "dn", "pool"):
                get(kind, st, part, h, False)
        if not decoy:
            for k in OTHER:
                for part in ("val", "all"):
                    for st in ("up", "dn"):
                        get(k, st, part, h, False)
    cells = pd.DataFrame(rows)
    cells.to_csv(out / "cells.csv", index=False)

    # 5. the frozen rule
    dec = [decide(res["up", h], res["dn", h], h) for h in H]
    diff_t = {int(r["h"]): r["t1"] for r in rows if r["state"] == "up-dn"}
    verdict = "PARTIAL" if any(d["pass"] for d in dec) else "NULL"
    best = max(H, key=lambda h: res["up", h]["t1"] if res["up", h]["t1"] == res["up", h]["t1"] else -9)
    v = {"lane": "negfundprior_v1", "decoy": decoy, "kind": kind, "verdict": verdict, "trials": TRIALS,
         "prereg_sha": psha, "split_ms": split, "split_time": str(pd.Timestamp(split, unit="ms")),
         "events_in": {k: int(x) for k, x in n_before.items()}, "events_with_prior": {k: int(x) for k, x in n_after.items()},
         "engine_pricing_differences_vs_R273": bad, "engine_stats_match_python": bool(all(match)) and len(match) > 0,
         "decisions": dec, "diff_welch_t_val": diff_t, "best_up_h": best,
         "best_up": {k: res["up", best][k] for k in ("n", "mean1", "mean2", "mean3", "t1", "trim1", "null_p")},
         "events_sha256": prereg.sha256_file(events_path), "run_seconds": round(time.time() - t0, 1)}
    (out / "verdict.json").write_text(json.dumps(v, indent=1, default=str))
    table(cells, out / "TABLE.md")
    log("engine stats match python:", v["engine_stats_match_python"], "| VERDICT", verdict, "(decoy)" if decoy else "")
    return 0


def table(cells, path):
    def f(x, nd=2, pct=True):
        return "n/a" if not isinstance(x, (int, float)) or x != x else (f"{x * 100:+.{nd}f}%" if pct else f"{x:.{nd}f}")
    L = ["| Set | Kind | State | Part | h | Legs | Clusters | 1x mean | Median | Hit | t | 2x mean | 3x mean | "
         "Mean w/o 10 best | Null p |", "|" + "---|" * 15]
    for _, r in cells.iterrows():
        L.append(f"| {r['set']} | {r['kind']} | {r['state']} | {r['part']} | {r['h']} | "
                 f"{'' if r['legs'] != r['legs'] else int(r['legs'])} | {r['n']} | {f(r['mean1'])} | {f(r['median1'])} | "
                 f"{f(r['hit1'], 0)} | {f(r['t1'], 2, False)} | {f(r['mean2'])} | {f(r['mean3'])} | {f(r['trim1'])} | "
                 f"{f(r['null_p'], 4, False)} |")
    path.write_text("\n".join(L) + "\n")


def register():
    """Append the lane's one registry row from results/verdict.json. Refuses to run twice."""
    v = json.loads((LANE / "results" / "verdict.json").read_text())
    if v["decoy"]:
        raise SystemExit("a decoy run is never registered")
    psha = prereg.verify(LANE / "PREREG.md")
    path = str(ROOT / "registry" / "rounds.csv")
    if any(r["id"] == "R381" for r in registry.rows(path)):
        raise SystemExit("R381 is already registered")
    b = v["best_up"]
    note = (f"qx long leg of R273 neg0.3 onsets split by prior 30-day direction; validation (from {v['split_time'][:10]}); "
            f"best up-state {v['best_up_h']}h 1x {b['mean1'] * 100:+.2f}% t {b['t1']:.2f} 2x {b['mean2'] * 100:+.2f}% "
            f"n {b['n']}; passes {[d['h'] for d in v['decisions'] if d['pass']] or 'none'}")
    rid = registry.append(path, id="R381", date="2026-11-02", lane="negfundprior_v1",
                          title="R273 neg0.3 onsets split by the coin's prior 30-day direction: long 24 h / 72 h, "
                                "up vs down state on the validation half (M458)",
                          status="DONE", verdict=v["verdict"], trials=v["trials"], prereg_sha=psha,
                          path="experiments/negfundprior_v1", notes=note)
    log(f"registered {rid} {v['verdict']}, {v['trials']} trials; program {registry.program_trials(path):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
