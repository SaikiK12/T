"""R304 mlrank_v2: R299's rankers again, without the three features whose coverage leaks survival.

R299 (`scripts/run_mlrank.py`, frozen) passed its rule with a GBM ranker, and its audit found why. KuCoin, Kraken,
MEXC, Hyperliquid, Upbit and Bithumb histories were fetched for the markets live at download time. A coin Binance later
delisted has almost none of them. Among the top 150 in 2021-24, KuCoin funding covers 53-95% of the survivors' rows
and 2-5% of the later-delisted coins'. `n_venues`, `fund_gap7` and `kimchi7` therefore tell a model which coins will
die. This lane drops them and runs the same family, code and decision rule. It also runs one diagnostic: the GBM
on those three features alone.

Everything except the feature lists comes unchanged from `scripts/run_mlrank.py`.

usage: python scripts/run_mlrank2.py [--plumbing]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, prereg  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_lotcap import weekly_grid  # noqa: E402
from scripts.run_mlrank import (DAY, HOLDS, MODELS, PIT, SPA_BLOCK, SPA_BOOT, WINDOWS, book,  # noqa: E402
                                daily_ic, decide, legs, load_panel, month_starts, prepare, rank_target, report,
                                stack, targets, universe, walk_forward, window_mask)

LANE = ROOT / "experiments" / "mlrank_v2"
LEAKY = ["n_venues", "fund_gap7", "kimchi7"]
CLEAN = [f for f in PIT if f not in LEAKY]
FEATURES = {"clean": CLEAN, "leak": LEAKY}
STRATS = [(m, h, "clean") for m in MODELS for h in HOLDS]            # the family: decided on
DIAG = [("gbm", 7, "leak")]                                          # reported, not decided on
TRIALS = len(STRATS) + len(DIAG)
SEED = 304
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def label(k):
    m, h, s = k
    return f"{m} h{h} {s}"


def dead_perps(w, margin=30):
    """Perps whose last close is more than `margin` days before the panel's last day: delisted (or stopped trading)
    inside the panel. Reporting only."""
    last = w["close"].apply(lambda s: s.last_valid_index())
    return set(last[last < w["close"].index.max() - pd.Timedelta(days=margin)].index)


def dead_share(rows, dead, hold, win):
    """Mean share of each leg's names that later stop trading, over the window's rebalances."""
    ts = np.array([r["t"] for r in rows], np.int64)
    m = window_mask(ts, hold, win)
    out = {}
    for side, sign in (("long", 1), ("short", -1)):
        sh = [np.mean([p in dead for p, x in r["w"].items() if np.sign(x) == sign]) for r, k in zip(rows, m) if k]
        out[side] = float(np.mean(sh)) if sh else None
    return out


def build(df, keys=STRATS + DIAG):
    w, f, uni = prepare(df)
    X = {s: stack(f, FEATURES[s], uni) for s in {k[2] for k in keys}}
    res, ics = {}, {}
    for h in HOLDS:
        if not any(k[1] == h for k in keys):
            continue
        ret, fund = targets(w, h)
        y = rank_target(ret - fund, uni).stack(future_stack=True)
        for k in keys:
            m, hk, s = k
            if hk != h:
                continue
            log(f"fit {label(k)}")
            yl = y.reindex(X[s].index)
            pred, _ = walk_forward(X[s], yl, m, h, FEATURES[s])
            res[k] = book(legs(pred, h), ret, fund)
            ics[k] = daily_ic(pred, yl)
    return w, res, ics


def analyze(w, res, ics):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = report(rows, k[1], ics[k])
        series[k] = (ts, net1)
    pick, ok, checks = decide({k: reports[k] for k in STRATS if k in reports})
    dead = dead_perps(w)
    legs_dead = {label(k): {win: dead_share(res[k], dead, k[1], win) for win in WINDOWS} for k in res}
    uni = universe(w)
    base = uni[[c for c in uni.columns if c in dead]].sum(axis=1) / uni.sum(axis=1).where(uni.sum(axis=1) > 0)
    day_ms = np.array([d.value // 10**6 for d in base.index], np.int64)
    base_dead = {win: float(base[window_mask(day_ms, 1, win)].mean()) for win in WINDOWS}
    flag = None
    if pick:
        flag = {win: (legs_dead[label(pick)][win]["short"] or 0) > 2 * base_dead[win] for win in WINDOWS}
    # reported: SPA / reality check over the family's books on a weekly grid from the first prediction day
    spa = {}
    ks = [k for k in STRATS if k in series]
    t0 = min(int(series[k][0].min()) for k in ks)
    anchors = np.arange(t0, max(int(series[k][0].max()) for k in ks) + 1, 7 * DAY, dtype=np.int64)
    for win in WINDOWS:
        an = anchors[window_mask(anchors, 7, win)]
        cols = []
        for k in ks:
            ts, net = series[k]
            mk = window_mask(ts, k[1], win)
            cols.append(weekly_grid(ts[mk], net[mk], an))
        spa[win] = inference.spa(np.column_stack(cols), n_boot=SPA_BOOT, block=SPA_BLOCK,
                                 rng=np.random.default_rng(SEED))
        spa[win]["best"] = label(ks[spa[win]["best"]])
        spa[win]["weeks"] = int(len(an))
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL", "spa": spa,
            "dead_share": legs_dead, "dead_perps": len(dead), "universe_dead_share": base_dead,
            "survivor_flag": flag}


def plumbing(df):
    """Counts only (no return read): how often each feature is present for perps that later stop trading."""
    w, f, uni = prepare(df.drop(columns=["ret"]).assign(ret=np.nan))
    dead = dead_perps(w)
    is_dead = pd.DataFrame(False, index=uni.index, columns=uni.columns)
    is_dead.loc[:, [c for c in uni.columns if c in dead]] = True
    out = {"dead_perps": len(dead), "features": len(CLEAN), "dropped": LEAKY, "coverage": {}}
    years = uni.index.year
    for k in CLEAN + LEAKY:
        x = f[k].where(uni).notna()
        cov = {}
        for y in sorted(set(years)):
            r = years == y
            u_live, u_dead = (uni & ~is_dead)[r], (uni & is_dead)[r]
            cov[str(y)] = [round(float(x[r][u_live].sum().sum() / max(u_live.sum().sum(), 1)), 2),
                           round(float(x[r][u_dead].sum().sum() / max(u_dead.sum().sum(), 1)), 2)]
        out["coverage"][k] = cov
    out["prediction_months"] = len(month_starts(uni.index))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="coverage counts only, no return read")
    a = ap.parse_args()
    df = load_panel()
    if a.plumbing:
        print(json.dumps(plumbing(df), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    w, res, ics = build(df)
    out = analyze(w, res, ics)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}; rank IC disc {v['disc']['rank_ic']['mean']} "
            f"valid {v['valid']['rank_ic']['mean']}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "n_long": r["n_long"], "n_short": r["n_short"]} for k, rs in res.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    pd.DataFrame({label(k): v for k, v in ics.items()}).to_csv(res_dir / "rank_ic.csv", float_format="%.5f")
    import sklearn
    summary = {"rid": "R304", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "sklearn": sklearn.__version__, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
