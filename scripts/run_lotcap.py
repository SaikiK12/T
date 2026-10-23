"""lotcap_v1 (R298): harvest R282's lottery-cluster median while capping the squeezes. As set out in
experiments/lotcap_v1/PREREG.md (M276, queued by R282's FINDINGS).

R282 found that young, small, heavily traded coins (age, size, vol_mcap) do worse than the rest on a typical day
(rank IC t 10-16), but its quintile books earned nothing: a few squeezes in the short leg cancel the median. Here the
same quintile books (long the least lottery-like fifth of the top 150, short the most) get a close-based protective
cover on each short leg (qx `leg_stop` semantics, R274): a short is closed at the first traded hourly close that is
`cover` or more above its entry, and stays flat until the next rebalance.

The family: score {age, cluster} x cover {none, 10%, 20%, 35%} x hold {24 h rebalanced daily, 168 h rebalanced
weekly} = 16 books, API costs. The best book in discovery (2021-01..2023-12) by net t goes to validation
(2024-01..2026-09), once.

Timing: R282's factor rows (experiments/pitfac_v1/factors.parquet, frozen with R282) put each value on the hourly bar
t that ends at 00:00 UTC; entry is that bar's close. Bars and funding before 2021-01-01 (reserved) and from
2026-10-01 (post-archive, reserved) are dropped on load and never read.

usage: python scripts/run_lotcap.py [--plumbing]
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, inference, prereg, stats  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "lotcap_v1"
FACTORS = ROOT / "experiments" / "pitfac_v1" / "factors.parquet"
H, DAY = 3_600_000, 86_400_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)        # 2020 is reserved
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)        # exclusive: post-archive is reserved
SCORES = ("age", "cluster")
COVERS = (0.0, 0.10, 0.20, 0.35)
HOLDS = (24, 168)
STRATS = [(s, h, c) for s in SCORES for h in HOLDS for c in COVERS]
TRIALS = len(STRATS)
Q, MIN_NAMES = 5, 30
COST = 8.5e-4                                # API, per side, 1x (2x and 3x reported)
NW_LAG = {24: 5, 168: 2}                     # periods
T_MIN, BEST_DROP = 2.0, 10
DISC = ("2021-01-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
WINDOWS = {"disc": DISC, "valid": VALID}
SPA_BOOT, SPA_BLOCK, SEED = 2000, 4, 298
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------------------ score
def _pct(v):
    """Cross-sectional percentile rank in (0, 1], ties averaged; NaN stays NaN."""
    return v.rank(pct=True)


def scores(fx):
    """Per row (t, sym): lot_age = the percentile rank of -age; lot_cluster = the mean percentile rank of -age, -size
    and +vol_mcap among the coins with all three. Higher is more lottery-like."""
    fx = fx[["t", "sym", "age", "size", "vol_mcap"]].copy()
    g = fx.groupby("t")
    fx["lot_age"] = g.age.transform(lambda v: _pct(-v))
    full = fx[fx[["age", "size", "vol_mcap"]].notna().all(axis=1)]
    gf = full.groupby("t")
    cl = (gf.age.transform(lambda v: _pct(-v)) + gf["size"].transform(lambda v: _pct(-v))
          + gf.vol_mcap.transform(lambda v: _pct(v))) / 3.0
    fx["lot_cluster"] = cl.reindex(fx.index)
    return fx[["t", "sym", "lot_age", "lot_cluster"]]


def rebalance_times(ts, hold):
    """Decision times of a book: every decision for 24 h; every 7th day from the first decision for 168 h."""
    ts = np.sort(np.unique(ts))
    if hold == 24:
        return ts
    return ts[((ts - ts[0]) // DAY) % 7 == 0]


def legs(sc, score, times):
    """{t: (long syms, short syms)}: the bottom and top fifth (floor(n / Q) names each) of lot_<score> among the coins
    scored at t, with at least MIN_NAMES of them. Ties break by symbol."""
    col = f"lot_{score}"
    d = sc[sc.t.isin(times) & sc[col].notna()].sort_values(["t", col, "sym"])
    out = {}
    for t, g in d.groupby("t"):
        n = len(g)
        if n < MIN_NAMES:
            continue
        k = n // Q
        s = g.sym.to_numpy()
        out[int(t)] = (tuple(s[:k]), tuple(s[-k:]))
    return out


# ------------------------------------------------------------------------------------------------------------- bars
class Bars:
    """One coin's hourly closes on the grid T0 + r H, r = 0 .. (T1 - T0) / H - 1, and its funding settlements; rows
    outside [T0, T1) are dropped on load. A bar is traded when its close is finite and its volume positive."""

    def __init__(self, t, close, volume, f_t, f_rate):
        n = (T1 - T0) // H
        keep = (t >= T0) & (t < T1)
        r = (t[keep] - T0) // H
        self.close = np.full(n, np.nan)
        self.close[r] = close[keep]
        vol = np.zeros(n)
        vol[r] = volume[keep]
        self.traded = np.isfinite(self.close) & (vol > 0)
        fk = (f_t >= T0) & (f_t < T1)
        self.f_t, self.f_cum = f_t[fk], np.concatenate([[0.0], np.cumsum(f_rate[fk])])

    @classmethod
    def load(cls, sym, root=None):
        root = Path(root or data.ROOT)
        k = pd.read_parquet(root / "klines_1h" / f"{sym}.parquet", columns=["t", "close", "volume"])
        k = k[(k.t >= T0) & (k.t < T1)].drop_duplicates("t")
        fp = root / "fundingRate" / f"{sym}.parquet"
        f = pd.read_parquet(fp, columns=["t", "rate"]) if fp.exists() else pd.DataFrame({"t": [], "rate": []})
        f = f[(f.t >= T0) & (f.t < T1)].sort_values("t").drop_duplicates("t")
        ft = (np.rint(f.t.to_numpy(np.float64) / 60_000).astype(np.int64) * 60_000)
        return cls(k.t.to_numpy(np.int64), k.close.to_numpy(np.float64), k.volume.to_numpy(np.float64), ft,
                   f.rate.to_numpy(np.float64))

    def funding(self, a, b):
        """Sum of the rates settled in (a, b] (ms)."""
        return float(self.f_cum[np.searchsorted(self.f_t, b, "right")] - self.f_cum[np.searchsorted(self.f_t, a, "right")])

    def leg(self, t, hold, short, cover):
        """The leg entered at the close of the bar opening at t and held `hold` hours: (price return close/entry - 1,
        funding over the hold, covered?). The exit is the last traded close at or before the end, or the first traded
        close in the hold `cover` or more above the entry for a short (cover 0: none). None when the entry bar is
        not traded or the hold would end at or after T1."""
        r0 = (t - T0) // H
        end = r0 + hold
        if r0 < 0 or end >= len(self.close) or not self.traded[r0]:
            return None
        entry = self.close[r0]
        path = np.arange(r0 + 1, end + 1)
        tr = path[self.traded[path]]
        xr, covered = (tr[-1] if len(tr) else r0), False
        if short and cover > 0 and len(tr):
            hit = np.nonzero(self.close[tr] / entry - 1.0 >= cover)[0]
            if len(hit):
                xr, covered = tr[hit[0]], True
        ret = self.close[xr] / entry - 1.0
        return ret, self.funding(T0 + (r0 + 1) * H, T0 + (xr + 1) * H), covered


# ------------------------------------------------------------------------------------------------------------ books
def book(lg, bars, hold, cover):
    """Per decision t: gross = mean long (ret - funding) + mean short (-ret + funding), price = the same without
    funding, the weights entered, and which shorts were covered. Coins whose entry bar is not traded are left out
    of their leg."""
    rows = []
    for t in sorted(lg):
        longs, shorts = lg[t]
        lr = [(s, bars[s].leg(t, hold, False, 0.0)) for s in longs if s in bars]
        sr = [(s, bars[s].leg(t, hold, True, cover)) for s in shorts if s in bars]
        lr, sr = [(s, x) for s, x in lr if x], [(s, x) for s, x in sr if x]
        if not lr or not sr:
            continue
        lg_ret = np.mean([x[0] - x[1] for _, x in lr])
        sh_ret = np.mean([-x[0] + x[1] for _, x in sr])
        price = np.mean([x[0] for _, x in lr]) - np.mean([x[0] for _, x in sr])
        rows.append({"t": t, "gross": lg_ret + sh_ret, "price": price, "long": lg_ret, "short": sh_ret,
                     "n_long": len(lr),
                     "n_short": len(sr), "covered": [s for s, x in sr if x[2]],
                     "w": {**{s: 1.0 / len(lr) for s, _ in lr}, **{s: -1.0 / len(sr) for s, _ in sr}}})
    return rows


def costed(rows, cost):
    """Net per period at `cost` per side: turnover from the previous period's end weights (covered shorts end at 0,
    their exit charged when covered) to this period's, plus the covers. Weight drift inside a period is ignored."""
    prev, out = {}, []
    for r in rows:
        w = r["w"]
        turn = sum(abs(w.get(s, 0.0) - prev.get(s, 0.0)) for s in set(w) | set(prev))
        cov = sum(abs(w[s]) for s in r["covered"])
        out.append(r["gross"] - cost * (turn + cov))
        prev = {s: v for s, v in w.items() if s not in r["covered"]}
    return np.array(out)


def turnover(rows):
    prev, out = {}, []
    for r in rows:
        w = r["w"]
        out.append(sum(abs(w.get(s, 0.0) - prev.get(s, 0.0)) for s in set(w) | set(prev)))
        prev = {s: v for s, v in w.items() if s not in r["covered"]}
    return np.array(out)


# ------------------------------------------------------------------------------------------------------------ stats
def window_mask(ts, hold, win):
    """Periods whose decision falls in the window and whose hold ends inside it."""
    a, b = WINDOWS[win]
    lo = pd.Timestamp(a, tz="UTC").value // 10**6
    hi = (pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1)).value // 10**6
    ts = np.asarray(ts, np.int64)
    return (ts >= lo) & (ts + (hold + 1) * H <= hi)


def series_stats(x, ts, hold):
    """Period stats of a net series x at decision times ts. The NW t runs over a calendar grid of periods, missing
    periods as gaps."""
    x, ts = np.asarray(x, float), np.asarray(ts, np.int64)
    if len(x) < 10:
        return {"periods": int(len(x))}
    step = hold * H if hold == 168 else DAY
    grid = np.full(int((ts[-1] - ts[0]) // step) + 1, np.nan)
    grid[(ts - ts[0]) // step] = x
    _, _, t = stats.newey_west_t(grid, NW_LAG[hold])
    per_day = hold / 24.0
    best = np.sort(x)[::-1]
    return {"periods": int(len(x)), "mean_bp": float(x.mean() * 1e4), "bp_day": float(x.mean() / per_day * 1e4),
            "ann_pct": float(x.mean() / per_day * 365 * 100), "t": float(t) if np.isfinite(t) else None,
            "median_bp": float(np.median(x) * 1e4), "hit": float((x > 0).mean()),
            "mean_wo_best_bp": float(best[BEST_DROP:].mean() * 1e4),
            "best_share": float(best[:BEST_DROP].sum() / x.sum()) if x.sum() > 0 else None,
            "sharpe": float(x.mean() / x.std() * np.sqrt(365 / per_day)) if x.std() > 0 else None}


def strategy_report(rows, hold):
    ts = np.array([r["t"] for r in rows], np.int64)
    nets = {k: costed(rows, m * COST) for k, m in (("1x", 1), ("2x", 2), ("3x", 3))}
    gross = np.array([r["gross"] for r in rows])
    turn = turnover(rows)
    rep = {}
    for w in WINDOWS:
        m = window_mask(ts, hold, w)
        rep[w] = {"gross": series_stats(gross[m], ts[m], hold), **{k: series_stats(v[m], ts[m], hold)
                                                                   for k, v in nets.items()},
                  "long_bp": float(np.mean([r["long"] for r, k in zip(rows, m) if k]) * 1e4) if m.any() else None,
                  "short_bp": float(np.mean([r["short"] for r, k in zip(rows, m) if k]) * 1e4) if m.any() else None,
                  "price_bp": float(np.mean([r["price"] for r, k in zip(rows, m) if k]) * 1e4) if m.any() else None,
                  "names_per_leg": float(np.mean([r["n_short"] for r, k in zip(rows, m) if k])) if m.any() else None,
                  "covers_per_period": float(np.mean([len(r["covered"]) for r, k in zip(rows, m) if k]))
                  if m.any() else None,
                  "turnover_per_period": float(turn[m].mean()) if m.any() else None}
    return rep, ts, nets["1x"]


def weekly_grid(ts, net, anchors):
    """A book's net summed onto the weekly rebalance anchors (each anchor collects the periods decided in its week)."""
    i = np.searchsorted(anchors, ts, "right") - 1
    out = np.zeros(len(anchors))
    ok = i >= 0
    np.add.at(out, i[ok], net[ok])
    return out


# ------------------------------------------------------------------------------------------------------------- main
def build(fx, bars):
    sc = scores(fx)
    res = {}
    for s, h, c in STRATS:
        lg = legs(sc, s, rebalance_times(sc.t.to_numpy(), h))
        res[(s, h, c)] = book(lg, bars, h, c)
    return sc, res


def decide(reports):
    """The discovery pick (highest net 1x t with a positive mean) and its validation verdict."""
    cand = [(k, r["disc"]["1x"]) for k, r in reports.items() if r["disc"]["1x"].get("t") is not None
            and r["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = reports[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": v["2x"].get("mean_bp", -1) > 0,
              "wo_best": v["1x"].get("mean_wo_best_bp", -1) > 0}
    return pick, all(checks.values()), checks


def label(k):
    s, h, c = k
    return f"{s} h{h} cover{int(round(c * 100))}"


def analyze(res):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = strategy_report(rows, k[1])
        series[k] = (ts, net1)
    pick, ok, checks = decide(reports)
    # reported: parity with R282's age book (24 h, gross, price only, all decisions: +4.35 bp/day)
    rows = res[("age", 24, 0.0)]
    parity = {"age_h24_cover0_price_bp_day": float(np.mean([r["price"] for r in rows]) * 1e4) if rows else None,
              "r282_age_gross_bp_day": 4.35}
    # reported: covered minus uncovered, per score and hold (paired on decision times)
    paired = {}
    for s, h, c in STRATS:
        if c == 0:
            continue
        ta, xa = series[(s, h, c)]
        tb, xb = series[(s, h, 0.0)]
        common, ia, ib = np.intersect1d(ta, tb, return_indices=True)
        d = xa[ia] - xb[ib]
        paired[label((s, h, c))] = {w: series_stats(d[m], common[m], h) for w in WINDOWS
                                    for m in [window_mask(common, h, w)]}
    # reported: Hansen SPA / White RC over the 16 books on a common weekly grid, per window
    spa = {}
    anchors_all = np.sort(np.unique(np.concatenate([series[k][0] for k in STRATS if k[1] == 168])))
    for w in WINDOWS:
        an = anchors_all[window_mask(anchors_all, 168, w)]
        cols = []
        for k in STRATS:
            ts, net = series[k]
            m = window_mask(ts, k[1], w)
            cols.append(weekly_grid(ts[m], net[m], an))
        D = np.column_stack(cols)
        spa[w] = inference.spa(D, n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        spa[w]["best"] = label(STRATS[spa[w]["best"]])
        spa[w]["weeks"] = int(len(an))
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL",
            "covered_minus_uncovered": paired, "spa": spa, "parity": parity}


def load_bars(syms, root=None):
    out = {}
    for s in sorted(syms):
        try:
            out[s] = Bars.load(s, root)
        except FileNotFoundError:
            pass
    return out


def bars_digest(bars):
    """sha256 over every loaded coin's grid closes, traded flags and funding: a record of the bars read."""
    h = hashlib.sha256()
    for s in sorted(bars):
        b = bars[s]
        h.update(s.encode())
        for a in (b.close, b.traded, b.f_t, b.f_cum):
            h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def plumbing(fx, sc):
    """Counts only: decisions, names, coins needed. No return is read."""
    out = {"factor_rows": int(len(fx)), "decisions": int(sc.t.nunique()),
           "first": str(pd.to_datetime(sc.t.min(), unit="ms")), "last": str(pd.to_datetime(sc.t.max(), unit="ms"))}
    for s in SCORES:
        for h in HOLDS:
            lg = legs(sc, s, rebalance_times(sc.t.to_numpy(), h))
            ts = np.array(sorted(lg), np.int64)
            names = [len(v[1]) for v in lg.values()]
            out[f"{s} h{h}"] = {"rebalances": len(lg), **{w: int(window_mask(ts, h, w).sum()) for w in WINDOWS},
                                "median_names_per_leg": float(np.median(names)) if names else None,
                                "coins": len({x for v in lg.values() for side in v for x in side})}
    return out


def needed_syms(sc):
    syms = set()
    for s in SCORES:
        for h in HOLDS:
            for longs, shorts in legs(sc, s, rebalance_times(sc.t.to_numpy(), h)).values():
                syms |= set(longs) | set(shorts)
    return syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    fx = pd.read_parquet(FACTORS)
    fx = fx[(fx.t >= T0) & (fx.t < T1)]
    if a.plumbing:
        sc = scores(fx)
        print(json.dumps(plumbing(fx, sc), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    sc = scores(fx)
    syms = needed_syms(sc)
    bars = load_bars(syms)
    log(f"{len(bars)} of {len(syms)} coins' bars loaded, digest {bars_digest(bars)[:12]}")
    _, res = build(fx, bars)
    out = analyze(res)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "n_long": r["n_long"], "n_short": r["n_short"], "covered": len(r["covered"])}
            for k, rs in res.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    summary = {"rid": "R298", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "coins_loaded": len(bars), "bars_digest": bars_digest(bars), **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
