"""xsbattery_v1 (R238): eight cross-sectional features as one-week spread books, as set out in
experiments/xsbattery_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_xsbattery.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, features, flowfeat, prereg, research, screen  # noqa: E402

LANE = ROOT / "experiments" / "xsbattery_v1"
HOLD, W = 168, 720
HOUR = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def funding(t, symbols):
    """Hourly array: each settlement's rate at its hour, 0 between settlements, NaN before the first record."""
    out = np.full((len(t), len(symbols)), np.nan, np.float32)
    for j, s in enumerate(symbols):
        p = data.ROOT / "fundingRate" / f"{s}.parquet"
        if not p.exists():
            continue
        d = pd.read_parquet(p)
        i = (d["t"].values // HOUR * HOUR - t[0]) // HOUR
        ok = (i >= 0) & (i < len(t))
        if not ok.any():
            continue
        first = max(int(i[ok].min()), 0)
        out[first:, j] = 0.0
        np.add.at(out[:, j], i[ok], d["rate"].values[ok].astype(np.float32))
    return out


def build(u):
    c = np.asarray(u.p["close"], np.float64)
    lc = np.where(c > 0, np.log(np.where(c > 0, c, 1)), np.nan)
    r = np.asarray(u.ret, np.float64)
    f = {}
    lag = lambda x, n: np.vstack([np.full((n, x.shape[1]), np.nan), x[:-n]])
    f["mom7"] = lc - lag(lc, 168)
    f["rev28"] = lc - lag(lc, 672)
    f["maxd"] = features.roll(lc - lag(lc, 24), W, "max")
    e = u.elig
    with np.errstate(invalid="ignore"):
        mkt = np.nanmean(np.where(e, r, np.nan), axis=1)
    f["ivol"] = features.roll(r - mkt[:, None], W, "std")
    f["skew"] = features.roll(r, W, "skew")
    f["hi52"] = lc - np.log(features.roll(c, 8760, "max"))
    fr = funding(u.p.t, u.p.symbols)
    f["fslope"] = features.roll(fr, 168, "sum") / 7 - features.roll(fr, 720, "sum") / 30
    k = flowfeat.load("klines", u.p.t, u.p.symbols, ("high", "low"))
    with np.errstate(divide="ignore", invalid="ignore"):
        eta = (np.log(k["high"].astype(np.float64)) + np.log(k["low"].astype(np.float64))) / 2
    del k
    lc1, eta1 = lag(lc, 1), lag(eta, 1)
    term = 4 * (lc1 - eta1) * (lc1 - eta)
    f["arspread"] = np.sqrt(np.maximum(features.roll(term, W, "mean"), 0)).astype(np.float32)
    f["arspread"][~np.isfinite(features.roll(term, W, "mean"))] = np.nan
    return {k: np.asarray(v, np.float32) for k, v in f.items()}


def trimmed(n, k=10):
    s = np.sort(n)
    return float(s[k:-k].mean() * 1e4) if len(s) > 2 * k else np.nan


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u, hold=HOLD)
    feats = build(u)
    a, b = s.rows["discovery"][0], s.rows["validation"][1]
    cov = {n: round(float(np.isfinite(x[a:b])[u.elig[a:b]].mean()), 4) for n, x in feats.items()}
    log("coverage (2021-2025H1):", json.dumps(cov))
    rule = lambda w, r, n2: (r["t_nw10"] >= 2 and n2.mean() > 0) if w == "discovery" else \
        (r["mean_bp_day"] > 0 and r["t_nw10"] >= 1.5)
    rows, stage, hdisc = [], {}, {}
    for name in list(feats):
        books = s.spread(feats.pop(name))
        for d, (parts, K) in books.items():
            bk = f"{name}/{d}"
            r, st = s.staged(bk, parts, K, rule=rule, holdout=False, log=log)
            for x in r:
                if x["cmult"] == 1.0:
                    n = s.run(parts, K, *s.rows[x["window"]])[0]
                    x["trimmed_bp_day"] = trimmed(n)
                    if d == "H" and x["window"] == "discovery":
                        hdisc[name] = n
            rows += r
            stage[bk] = st
    corr = pd.DataFrame(hdisc).corr().round(2)
    log("discovery correlation of H books:\n" + corr.to_string())
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    corr.to_csv(out / "h_corr_discovery.csv")
    verdict = {"stages": stage, "coverage": cov,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "discovery_passers": [k for k, v in stage.items() if v["reached"] != "discovery" or v["passed"]],
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("discovery_passers", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
