"""hvrev_v1 (R380): weekly reversal at an 8-10 week lookback inside the high-volatility tercile, with and without the
high-volatility / winner tilt removed. As set out in experiments/hvrev_v1/PREREG.md (M457).

Daily point-in-time panel, rows up to D only (prices, volume rank and funding; no metrics column is read). On every 7th
day from 2022-01-01 the universe is row D's top 150 perps by rank_qvol30 with a close; names missing any of the four
inputs (vol30, mom7, max7, the lookback return) drop out. The gate keeps the top tercile by vol30 (n // 3 names). The
score is the lookback return times -1 (long the losers), ranked inside the group; the residualised book regresses that
rank on the ranks of vol30, mom7 and max7 and uses the residual. Long the top fifth, short the bottom fifth, equal
weights, seeded random ties, a 7 day hold, funding over the hold, API costs on turnover. Helpers are R299's and lotcap's,
imported unchanged.

usage: python scripts/run_hvrev.py [--plumbing]      (plumbing: counts only, no return is read)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import inference, prereg  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_lotcap import costed, series_stats, turnover, weekly_grid  # noqa: E402
from scripts.run_mlrank import (COST, FIRST_PRED, MIN_NAMES, SEED, SPA_BLOCK, SPA_BOOT, WINDOWS, book,  # noqa: E402
                                decide, legs, log, targets, universe, wide, window_mask)

LANE = ROOT / "experiments" / "hvrev_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
LOAD = ["day", "perp", "close", "ret", "fund", "rank_qvol30"]
HOLD = 7                                                  # days
LOOKBACKS = (8, 9, 10)                                    # weeks
FAMILY = [(L, "hv", r) for L in LOOKBACKS for r in (False, True)]
CONTROLS = [(9, "all", False), (9, "all", True)]          # reported and counted, never picked
STRATS = FAMILY + CONTROLS
TRIALS = len(STRATS)


def label(k):
    L, gate, r = k
    return f"L{L}w {gate} {'resid' if r else 'raw'}"


# ---------------------------------------------------------------------------------------------------------- signals
def roll(x, n):
    return x.rolling(n, min_periods=max(2, int(0.7 * n)))


def signals(w):
    """{name: day x perp} from rows up to each day only."""
    lr = np.log1p(w["ret"])
    s = {"vol30": roll(lr, 30).std(), "mom7": roll(lr, 7).sum(), "max7": roll(w["ret"], 7).max()}
    for L in LOOKBACKS:
        s[f"mom{7 * L}"] = roll(lr, 7 * L).sum()
    return {k: v.replace([np.inf, -np.inf], np.nan) for k, v in s.items()}


def rk(v):
    """Ranks into (-0.5, 0.5), average ties."""
    return (pd.Series(v).rank().to_numpy() - 0.5) / len(v) - 0.5


def day_pred(sig, uni, d, L, gate, resid, rng):
    """(perps index, prediction, R2 of the tilt regression or NaN, group size) for decision row d. High = long."""
    X = np.column_stack([sig[c].loc[d].to_numpy() for c in ("vol30", "mom7", "max7", f"mom{7 * L}")])
    ok = uni.loc[d].to_numpy() & np.isfinite(X).all(axis=1)
    idx = np.flatnonzero(ok)
    X, n = X[idx], len(idx)
    if gate == "hv":
        order = np.lexsort((rng.random(n), -X[:, 0]))         # vol30 descending, ties by the seeded order
        keep = np.sort(order[: n // 3])
        idx, X = idx[keep], X[keep]
    if len(idx) < 5:
        return None
    y = rk(-X[:, 3])                                           # losers high
    if not resid:
        return idx, y, np.nan, len(idx)
    A = np.column_stack([np.ones(len(idx)), rk(X[:, 0]), rk(X[:, 1]), rk(X[:, 2])])
    e = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
    return idx, e, float(1.0 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()), len(idx)


def predictions(sig, uni, perps, days, k):
    L, gate, r = k
    rng = np.random.default_rng(SEED)
    idx_d, idx_p, vals, r2, size = [], [], [], {}, {}
    for d in days:
        out = day_pred(sig, uni, d, L, gate, r, rng)
        if out is None:
            continue
        ix, p, q, n = out
        idx_d += [d] * len(ix)
        idx_p += list(perps[ix])
        vals += list(p)
        r2[d], size[d] = q, n
    pred = pd.Series(vals, index=pd.MultiIndex.from_arrays([idx_d, idx_p]))
    return pred, r2, size


# ---------------------------------------------------------------------------------------------------------- books
def zero_exit(w):
    """Rows whose exit close is missing for the whole hold: the book credits them 0 (targets()). Reported."""
    c = w["close"]
    return c.notna() & c.ffill(limit=HOLD - 1).shift(-HOLD).isna()


def build(df):
    w = wide(df)
    uni, sig = universe(w), signals(w)
    ret, fund = targets(w, HOLD)
    zx = zero_exit(w)
    perps = np.array(w["close"].columns)
    days = pd.date_range(FIRST_PRED, w["close"].index.max(), freq=f"{HOLD}D")
    res, extra = {}, {}
    for k in STRATS:
        pred, r2, size = predictions(sig, uni, perps, days, k)
        lg = legs(pred, HOLD)
        res[k] = book(lg, ret, fund)
        extra[k] = {"r2": r2, "size": size,
                    "zero_exit": {d: (sum(bool(zx.loc[d, s]) for s in lg[d][0]), sum(bool(zx.loc[d, s]) for s in lg[d][1]))
                                  for d in lg}}
    return res, extra


def window_extra(k, extra, win):
    a, b = (pd.Timestamp(x) for x in WINDOWS[win])
    sel = lambda m: {d: v for d, v in m.items() if a <= d <= b - pd.Timedelta(days=HOLD)}
    ex = extra[k]
    r2 = [v for v in sel(ex["r2"]).values() if np.isfinite(v)]
    zx = list(sel(ex["zero_exit"]).values())
    return {"mean_r2": float(np.mean(r2)) if r2 else None,
            "group_size_mean": float(np.mean(list(sel(ex["size"]).values()))) if ex["size"] else None,
            "zero_exit_per_period_long": float(np.mean([z[0] for z in zx])) if zx else None,
            "zero_exit_per_period_short": float(np.mean([z[1] for z in zx])) if zx else None}


def report(rows):
    ts = np.array([r["t"] for r in rows], np.int64)
    nets = {m: costed(rows, x * COST) for m, x in (("1x", 1), ("2x", 2), ("3x", 3))}
    gross = np.array([r["gross"] for r in rows])
    turn = turnover(rows)
    rep = {}
    for w in WINDOWS:
        m = window_mask(ts, HOLD, w)
        rep[w] = {"gross": series_stats(gross[m], ts[m], HOLD * 24),
                  **{x: series_stats(v[m], ts[m], HOLD * 24) for x, v in nets.items()},
                  "long_bp": float(np.mean([r["long"] for r, q in zip(rows, m) if q]) * 1e4) if m.any() else None,
                  "short_bp": float(np.mean([r["short"] for r, q in zip(rows, m) if q]) * 1e4) if m.any() else None,
                  "names_per_leg": float(np.mean([r["n_short"] for r, q in zip(rows, m) if q])) if m.any() else None,
                  "turnover_per_period": float(turn[m].mean()) if m.any() else None}
    inw = window_mask(ts, HOLD, "disc") | window_mask(ts, HOLD, "valid")
    yrs = pd.to_datetime(ts, unit="ms").year
    rep["net1x_bp_day_by_year"] = {int(y): float(nets["1x"][inw & (yrs == y)].mean() / HOLD * 1e4)
                                   for y in sorted(set(yrs[inw]))}
    return rep, ts, nets["1x"]


def analyze(res, extra):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = report(rows)
        series[k] = (ts, net1)
        for w in WINDOWS:
            reports[k][w].update(window_extra(k, extra, w))
    pick, ok, checks = decide({k: reports[k] for k in FAMILY})
    paired, corr = {}, {}
    for w in WINDOWS:
        for r in (False, True):
            ta, xa = series[(9, "hv", r)]
            tb, xb = series[(9, "all", r)]
            common, ia, ib = np.intersect1d(ta, tb, return_indices=True)
            mk = window_mask(common, HOLD, w)
            paired[f"{w} L9w hv minus all {'resid' if r else 'raw'}"] = series_stats((xa[ia] - xb[ib])[mk], common[mk], HOLD * 24)
        for L in LOOKBACKS:
            ta, xa = series[(L, "hv", False)]
            tb, xb = series[(L, "hv", True)]
            common, ia, ib = np.intersect1d(ta, tb, return_indices=True)
            mk = window_mask(common, HOLD, w)
            corr[f"{w} L{L}w hv raw vs resid"] = float(np.corrcoef(xa[ia][mk], xb[ib][mk])[0, 1])
    spa = {}
    anchors = np.sort(np.unique(np.concatenate([series[k][0] for k in FAMILY])))
    for w in WINDOWS:
        an = anchors[window_mask(anchors, HOLD, w)]
        D = np.column_stack([weekly_grid(series[k][0][window_mask(series[k][0], HOLD, w)],
                                         series[k][1][window_mask(series[k][0], HOLD, w)], an) for k in FAMILY])
        spa[w] = inference.spa(D, n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        spa[w]["best"] = label(FAMILY[spa[w]["best"]])
        spa[w]["weeks"] = int(len(an))
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL",
            "paired_hv_minus_all": paired, "corr_raw_resid": corr, "spa": spa}


# ------------------------------------------------------------------------------------------------------------ main
def load_panel():
    return pd.read_parquet(PANEL, columns=LOAD)


def plumbing(df):
    """Counts only. Returns are replaced by 0 where a day exists, so only which names have inputs is read."""
    w = wide(df.assign(ret=df.ret.notna().astype(float).where(df.ret.notna())))
    uni, sig = universe(w), signals(w)
    days = pd.date_range(FIRST_PRED, w["close"].index.max(), freq=f"{HOLD}D")
    out = {"first_row": str(w["close"].index.min().date()), "last_row": str(w["close"].index.max().date()),
           "rebalance_days": int(len(days))}
    for L in LOOKBACKS:
        n_all = [int((uni.loc[d].to_numpy() & np.isfinite(np.column_stack(
            [sig[c].loc[d].to_numpy() for c in ("vol30", "mom7", "max7", f"mom{7 * L}")])).all(axis=1)).sum())
                 for d in days]
        n_all = np.array(n_all)
        out[f"L{L}w"] = {"eligible_min": int(n_all.min()), "eligible_median": float(np.median(n_all)),
                         "hv_group_min": int((n_all // 3).min()), "days_hv_group_below_30": int(((n_all // 3) < MIN_NAMES).sum())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    df = load_panel()
    if a.plumbing:
        print(json.dumps(plumbing(df), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    res, extra = build(df)
    out = analyze(res, extra)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "n_long": r["n_long"], "n_short": r["n_short"]} for k, rs in res.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    summary = {"rid": "R380", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
