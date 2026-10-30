"""qbasis_v1 (R301): the dated-futures basis as a cross-sectional signal on Binance perps (M170, from Chi, Hao, Hu and
Ran, J. Futures Markets 2023). As set out in experiments/qbasis_v1/PREREG.md.

Each day the coins with a Binance COIN-M quarterly are ranked. There are 5-10 at a time: BTC, ETH, BNB, XRP, ADA, LINK,
LTC, DOT, BCH, and SOL from 2024-08. The rank is by either:
- the annualized basis of the nearest quarterly (7+ days left) over the COIN-M perp (the daily panel's qtr_basis_ann);
- or that basis's change over 7 days.

The books go long the k highest and short the k lowest, or the reverse, in the matching USD-M perps. They are held
1 day (rebalanced daily) or 7 days (weekly), at API costs with funding.

The family: signal {level, chg7} x side {long high, long low} x hold {1, 7 days} x k {1, 2} = 16 books. The best
discovery book (2021-01..2023-12) by net t goes to validation (2024-01..2026-09), once.

Timing: row D of data/daily/panel.parquet is the decision at 00:00 UTC of day D. Signals use rows up to D; entry is
row D's close; a hold of h days exits at the last close in rows D+1..D+h and pays the funding settled in those rows
(R299's `targets`). The panel holds no row before 2021-01-02 or after 2026-09-30 (reserved).

usage: python scripts/run_qbasis.py [--plumbing]
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
from scripts.run_lotcap import costed, series_stats, turnover, weekly_grid  # noqa: E402
from scripts.run_mlrank import book, decide, targets  # noqa: E402

LANE = ROOT / "experiments" / "qbasis_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
DAY = 86_400_000
SIGNALS = ("level", "chg7")
SIDES = ("high", "low")                          # long the highest signal (short the lowest), or the reverse
HOLDS = (1, 7)                                   # days
KS = (1, 2)                                      # names per leg
STRATS = [(s, d, h, k) for s in SIGNALS for d in SIDES for h in HOLDS for k in KS]
TRIALS = len(STRATS)
MIN_NAMES = 5
COST = 8.5e-4                                    # API, per side, 1x
DISC = ("2021-01-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
WINDOWS = {"disc": DISC, "valid": VALID}
SPA_BOOT, SPA_BLOCK, SEED = 2000, 4, 301
COLS = ["close", "fund", "qtr_basis_ann", "qtr_days"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- panel
def wide(df):
    """{column: DataFrame day x perp} on a full calendar of days."""
    days = pd.date_range(df.day.min(), df.day.max(), freq="D")
    perps = sorted(df.perp.unique())
    df = df.assign(day=pd.to_datetime(df.day))
    return {c: df.pivot(index="day", columns="perp", values=c).reindex(index=days, columns=perps) for c in COLS}


def signal(w, name):
    """level: the annualized basis on row D; chg7: its change since row D-7 (across a roll this compares two
    contracts' annualized basis)."""
    b = w["qtr_basis_ann"]
    return b if name == "level" else b - b.shift(7)


def legs(sig, close, hold, k, side, seed=SEED):
    """{day: (longs, shorts)} among the coins with a signal and a close on day D: long the k highest and short the k
    lowest (side "high"), or the reverse ("low"). Every day (hold 1), or every 7th day from the panel's first day
    (hold 7). Fewer than MIN_NAMES coins: no book. Ties break by a seeded random order, never by symbol."""
    rng = np.random.default_rng(seed)
    ok = sig.notna() & close.notna()
    first = sig.index[0]
    out = {}
    for d in sig.index:
        if hold == 7 and (d - first).days % 7:
            continue
        row = sig.loc[d][ok.loc[d]]
        if len(row) < MIN_NAMES:
            continue
        order = np.lexsort((rng.random(len(row)), row.to_numpy()))
        s = row.index.to_numpy()[order]
        hi, lo = tuple(s[-k:]), tuple(s[:k])
        out[d] = (hi, lo) if side == "high" else (lo, hi)
    return out


# ------------------------------------------------------------------------------------------------------------ stats
def window_mask(ts, hold, win):
    """Rebalances decided in the window whose hold ends inside it (row D + hold <= the window's last row)."""
    a, b = WINDOWS[win]
    lo, hi = pd.Timestamp(a).value // 10**6, pd.Timestamp(b).value // 10**6
    ts = np.asarray(ts, np.int64)
    return (ts >= lo) & (ts + hold * DAY <= hi)


def report(rows, hold):
    ts = np.array([r["t"] for r in rows], np.int64)
    nets = {k: costed(rows, m * COST) for k, m in (("1x", 1), ("2x", 2), ("3x", 3))}
    gross = np.array([r["gross"] for r in rows])
    turn = turnover(rows)
    rep = {}
    for w in WINDOWS:
        m = window_mask(ts, hold, w)
        sel = [r for r, k in zip(rows, m) if k]
        rep[w] = {"gross": series_stats(gross[m], ts[m], hold * 24),
                  **{k: series_stats(v[m], ts[m], hold * 24) for k, v in nets.items()},
                  "long_bp": float(np.mean([r["long"] for r in sel]) * 1e4) if sel else None,
                  "short_bp": float(np.mean([r["short"] for r in sel]) * 1e4) if sel else None,
                  "turnover_per_period": float(turn[m].mean()) if sel else None}
    return rep, ts, nets["1x"]


def label(k):
    s, d, h, n = k
    return f"{s} {d} h{h} k{n}"


def years(rows, hold):
    """Gross and net 1x per calendar year (bp/day)."""
    net = costed(rows, COST)
    y = pd.to_datetime([r["t"] for r in rows], unit="ms").year
    df = pd.DataFrame({"y": y, "g": [r["gross"] for r in rows], "n": net})
    return {int(k): {"gross_bp_day": float(v.g.mean() / hold * 1e4), "net1x_bp_day": float(v.n.mean() / hold * 1e4),
                     "periods": int(len(v))} for k, v in df.groupby("y")}


def membership(lg):
    """Share of rebalances each coin sits in the long and in the short leg."""
    n = len(lg)
    out = {}
    for side, i in (("long", 0), ("short", 1)):
        c = pd.Series([s for v in lg.values() for s in v[i]]).value_counts() / max(n, 1)
        out[side] = {k: round(float(v), 3) for k, v in c.items()}
    return out


def basis_vs_funding(w):
    """Per window: the median across days of the cross-sectional rank correlation between the basis level and the
    perp's last 3 days of funding (is the quarterly basis just funding?), and the mean annualized basis by year."""
    b = w["qtr_basis_ann"]
    f3 = w["fund"].rolling(3, min_periods=3).sum()
    out = {}
    for win, (a, z) in WINDOWS.items():
        bb, ff = b.loc[a:z], f3.loc[a:z]
        cs = [bb.loc[d].rank().corr(ff.loc[d].rank()) for d in bb.index
              if (bb.loc[d].notna() & ff.loc[d].notna()).sum() >= MIN_NAMES]
        out[win] = {"median_rank_corr": float(np.nanmedian(cs)) if cs else None, "days": len(cs)}
    out["mean_basis_ann_by_year"] = {int(y): float(v) for y, v in b.stack().groupby(level=0).mean()
                                     .groupby(lambda d: d.year).mean().items()}
    return out


def build(w):
    res, lgs = {}, {}
    for s in SIGNALS:
        sig = signal(w, s)
        for h in HOLDS:
            ret, fund = targets(w, h)
            for k in KS:
                for d in SIDES:
                    lg = legs(sig, w["close"], h, k, d)
                    lgs[(s, d, h, k)] = lg
                    res[(s, d, h, k)] = book(lg, ret, fund)
    return res, lgs


def analyze(w, res, lgs):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = report(rows, k[2])
        series[k] = (ts, net1)
    pick, ok, checks = decide(reports)
    spa = {}
    anchors = np.sort(np.unique(np.concatenate([series[k][0] for k in STRATS if k[2] == 7])))
    for win in WINDOWS:
        an = anchors[window_mask(anchors, 7, win)]
        cols = []
        for k in STRATS:
            ts, net = series[k]
            m = window_mask(ts, k[2], win)
            cols.append(weekly_grid(ts[m], net[m], an))
        r = inference.spa(np.column_stack(cols), n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        r["best"] = label(STRATS[r["best"]])
        r["weeks"] = int(len(an))
        spa[win] = r
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL", "spa": spa,
            "years": {label(k): years(res[k], k[2]) for k in STRATS},
            "membership": {label(k): membership(lgs[k]) for k in STRATS if k[1] == "high" and k[3] == 1},
            "basis_vs_funding": basis_vs_funding(w)}


# ------------------------------------------------------------------------------------------------------------- main
def load_panel():
    return pd.read_parquet(PANEL, columns=["day", "perp", *COLS])


def plumbing(df):
    """Counts only: decision days, names and coins per signal and window. No signal value or return is read."""
    w = wide(df)
    have = w["qtr_basis_ann"].notna() & w["close"].notna()
    out = {"panel_days": int(len(w["close"])), "coins": sorted(have.columns[have.any()].tolist())}
    for s in SIGNALS:
        ok = have & (have.shift(7, fill_value=False) if s == "chg7" else True)
        n = ok.sum(axis=1)
        days = n.index[n >= MIN_NAMES]
        ts = np.array([d.value // 10**6 for d in days], np.int64)
        out[s] = {"days": int(len(days)), **{wn: int(window_mask(ts, 1, wn).sum()) for wn in WINDOWS},
                  "names_min": int(n[n >= MIN_NAMES].min()), "names_median": float(n[n >= MIN_NAMES].median())}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no signal or return read (before the freeze)")
    a = ap.parse_args()
    if a.plumbing:
        print(json.dumps(plumbing(load_panel()), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    w = wide(load_panel())
    res, lgs = build(w)
    out = analyze(w, res, lgs)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
             "longs": "|".join(s for s, v in r["w"].items() if v > 0),
             "shorts": "|".join(s for s, v in r["w"].items() if v < 0)} for k, rs in res.items() for r in rs]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    summary = {"rid": "R301", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
