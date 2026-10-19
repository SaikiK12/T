"""Lanes on Gate.io contract stats, traded on Binance returns: xvenue_v1 (R205, top traders vs the crowd measured on
Gate) and liq_v1 (R206, liquidation cascades), as set out in their PREREGs.

usage: python scripts/run_gate_lanes.py xvenue|liq
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
from lab import data, events, features, prereg, research, slices, stats  # noqa: E402

HOUR = 3_600_000
HOLD, K = 72, 9.316
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def gate_grid(u, cols):
    """{col: [T, S] float32} on the research clock from data/gate_1h; NaN where Gate has no row."""
    T, S = u.ret.shape
    out = {c: np.full((T, S), np.nan, np.float32) for c in cols}
    t0 = int(u.p.t[0])
    n = 0
    for j, s in enumerate(u.p.symbols):
        path = data.ROOT / "gate_1h" / f"{s}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        i = (df["t"].values - t0) // HOUR
        ok = (i >= 0) & (i < T)
        for c in cols:
            if c in df:
                out[c][i[ok], j] = df[c].values[ok]
        n += 1
    log(f"Gate data for {n} research columns")
    return out


def book_row(name, o, extra=None):
    n = o["daily"]
    return {"book": name, "days": len(n), "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
            **events.summary(n), "gross_exposure": float(o["gross_exposure"].mean()), **(extra or {})}


def nw(n, lag):
    return float(stats.newey_west_t(np.asarray(n, float), lag)[2]) if len(n) > 10 else np.nan


def xvenue(u):
    lane = ROOT / "experiments" / "xvenue_v1"
    log("prereg sha", prereg.verify(lane / "PREREG.md")[:12])
    out = lane / "results"
    out.mkdir(parents=True, exist_ok=True)
    g = gate_grid(u, ["top_lsr_size", "lsr_account"])
    with np.errstate(divide="ignore", invalid="ignore"):
        gtvc = np.log(g["top_lsr_size"]) - np.log(g["lsr_account"])
    gtvc[~np.isfinite(gtvc)] = np.nan
    have = np.isfinite(gtvc)
    first = int(np.flatnonzero(have.any(axis=1))[0])
    t0 = (first + HOLD) // 24 * 24 + 24
    t1 = research.row_of(u.p, "2026-10-01")
    t1 -= (t1 - t0) % 24
    elig = u.elig & have
    gb = features.bins_xs(gtvc, elig, 8)
    rd = data.ROOT / "research"
    fb = np.load(rd / "bins_flow.npy", mmap_mode="r")
    fn = json.loads((rd / "meta_flow.json").read_text())["names"]
    bb = np.asarray(fb[fn.index("flow:top_vs_crowd/xs8")])
    inds = {"G": (gb == 0) & elig, "B": (bb == 0) & elig, "G_only": (gb == 0) & (bb != 0) & elig}
    rows, keep = [], {}
    for name, ind in inds.items():
        for cm in (1.0, 2.0, 3.0):
            o = slices.book(ind, u.ret, u.elig, u.cmat, HOLD, 1.0 / (HOLD * K), t0, t1, side=-1, cmult=cm)
            rows.append(book_row(name, o, {"cmult": cm, "t_nw10": nw(o["daily"], 10)}))
            if cm == 1.0:
                keep[name] = o["daily"]
    # signal agreement
    rho, overlap = [], []
    for t in range(t0, t1):
        e = elig[t] & np.isfinite(gtvc[t])
        if e.sum() < 10:
            continue
        x = pd.Series(gtvc[t, e]).rank().values
        b = bb[t, e]
        ok = b >= 0
        if ok.sum() >= 10:
            rho.append(np.corrcoef(x[ok], b[ok])[0, 1])
        g0, b0 = gb[t, e] == 0, bb[t, e] == 0
        if g0.any() or b0.any():
            overlap.append((g0 & b0).sum() / max((g0 | b0).sum(), 1))
    df = pd.DataFrame(rows)
    p = df[(df.book == "G") & (df.cmult == 1.0)].iloc[0]
    q = df[(df.book == "G_only") & (df.cmult == 1.0)].iloc[0]
    verdict = {"window": [str(pd.Timestamp(int(u.p.t[t0]), unit="ms").date()),
                          str(pd.Timestamp(int(u.p.t[t1 - 1]), unit="ms").date())],
               "replicates": bool(p.mean_bp_day > 0 and p.t_nw10 >= 2),
               "adds": bool(q.mean_bp_day > 0 and q.t_nw10 >= 2),
               "spearman_mean": float(np.nanmean(rho)), "spearman_q10_q90": [float(np.nanquantile(rho, 0.1)),
                                                                             float(np.nanquantile(rho, 0.9))],
               "bin0_jaccard_mean": float(np.mean(overlap)) if overlap else None}
    df.to_csv(out / "books.csv", index=False)
    np.savez_compressed(out / "daily.npz", **keep)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    days = pd.to_datetime(u.p.t[t0:t1:24], unit="ms", utc=True)
    monthly = pd.DataFrame({k: pd.Series(v, index=days[:len(v)]).groupby(days[:len(v)].strftime("%Y-%m")).sum()
                            for k, v in keep.items()})
    monthly.to_csv(out / "monthly.csv")
    log("\n" + df.round(4).to_string(index=False))
    log("monthly\n" + monthly.round(4).to_string())
    log(verdict)


def liq(u):
    lane = ROOT / "experiments" / "liq_v1"
    log("prereg sha", prereg.verify(lane / "PREREG.md")[:12])
    out = lane / "results"
    out.mkdir(parents=True, exist_ok=True)
    g = gate_grid(u, ["long_liq_usd", "short_liq_usd", "open_interest_usd"])
    with np.errstate(divide="ignore", invalid="ignore"):
        L = (g["long_liq_usd"] - g["short_liq_usd"]) / g["open_interest_usd"]
    L[~np.isfinite(L)] = np.nan
    df_L = pd.DataFrame(L)
    q95 = df_L.rolling(720, min_periods=360).quantile(0.95).shift(1).values
    q05 = df_L.rolling(720, min_periods=360).quantile(0.05).shift(1).values
    ready = np.isfinite(q95)
    first = int(np.flatnonzero(ready.any(axis=1))[0])
    t0 = first // 24 * 24 + 24
    t1 = research.row_of(u.p, "2026-10-01")
    t1 -= (t1 - t0) % 24
    with np.errstate(invalid="ignore"):
        up = (L >= q95) & (L > 0) & u.elig & ready           # longs liquidated: buy the bounce
        dn = (L <= q05) & (L < 0) & u.elig & ready           # shorts squeezed: sell the spike
    rows, keep = [], {}
    for h in (4, 12, 24, 72):
        k_l = (up[t0:t1].sum() + dn[t0:t1].sum()) / (t1 - t0)
        unit = 1.0 / (h * max(k_l, 1e-9))
        for name, parts in (("both", ((up, 1), (dn, -1))), ("long_leg", ((up, 1),)), ("short_leg", ((dn, -1),))):
            for cm in ((1.0, 2.0, 3.0) if name == "both" else (1.0,)):
                P = sum(slices.positions(ind, h, t0, t1, unit, side) for ind, side in parts)
                o = slices.run(P, u.ret, u.elig, u.cmat, t0, t1, hedge=True, cmult=cm)
                rows.append(book_row(name, o, {"h": h, "cmult": cm, "K_L": float(k_l), "t_nw5": nw(o["daily"], 5),
                                               "turnover_day": float(o["turnover"].sum() / max(len(o["daily"]), 1))}))
                if cm == 1.0 and name == "both":
                    keep[f"h{h}"] = o["daily"]
    df = pd.DataFrame(rows)
    p = df[(df.book == "both") & (df.h == 12) & (df.cmult == 1.0)].iloc[0]
    verdict = {"window": [str(pd.Timestamp(int(u.p.t[t0]), unit="ms").date()),
                          str(pd.Timestamp(int(u.p.t[t1 - 1]), unit="ms").date())],
               "confirmed_discovery": bool(p.mean_bp_day > 0 and p.t_nw5 >= 2),
               "events_up": int(up[t0:t1].sum()), "events_dn": int(dn[t0:t1].sum())}
    df.to_csv(out / "books.csv", index=False)
    np.savez_compressed(out / "daily.npz", **keep)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    log("\n" + df.round(4).to_string(index=False))
    log(verdict)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lane", choices=("xvenue", "liq"))
    a = ap.parse_args()
    u, _, _ = research.load_universe()
    (xvenue if a.lane == "xvenue" else liq)(u)


if __name__ == "__main__":
    main()
