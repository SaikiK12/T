"""fundxs_v1 (R302): the Binance funding level as a cross-sectional signal, net of the funding each leg pays (M263).
As set out in experiments/fundxs_v1/PREREG.md.

Each day the perps in the universe (the top 150 or top 50 by trailing 30-day quote volume) are ranked by the funding
they settled over the last 3 or 30 days. The book goes long the bottom fifth (lowest funding) and short the top fifth,
in equal weights, held 1 day (rebalanced daily) or 7 days (weekly), at API costs. Longs pay the funding and shorts
receive it.

The family: signal {fund3, fund30} x hold {1, 7 days} x universe {top 150, top 50} = 8 books, one side (R276's
direction, written into M263). The best discovery book (2021-01..2023-12) by net t goes to validation (2024-01..
2026-09), once.

Also reported, not decided on: each book's price and funding parts (the reconciliation with R190's carry), R276's
reference at its own 7 bp cost, the ties at the base funding rate, and the legs' volume ranks.

Timing: row D of data/daily/panel.parquet is the decision at 00:00 UTC of day D. Signals use rows up to D; entry is
row D's close; a hold of h days exits at the last close in rows D+1..D+h and pays the funding settled in those rows
(R299's `targets`). The panel holds no row before 2021-01-02 or after 2026-09-30 (reserved).

usage: python scripts/run_fundxs.py [--plumbing]
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
from scripts.run_lotcap import costed, turnover, weekly_grid  # noqa: E402
from scripts.run_mlrank import book, decide, targets  # noqa: E402
from scripts.run_qbasis import report, window_mask, years  # noqa: E402

LANE = ROOT / "experiments" / "fundxs_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
DAY = 86_400_000
SIGNALS = {"fund3": 3, "fund30": 30}             # days of funding summed
HOLDS = (1, 7)                                   # days
TOPS = (150, 50)                                 # universe: top n by trailing 30-day quote volume
STRATS = [(s, h, u) for s in SIGNALS for h in HOLDS for u in TOPS]
TRIALS = len(STRATS)
Q, MIN_NAMES = 5, 30
COST = 8.5e-4                                    # API, per side, 1x
R276_COST = 7e-4                                 # R276's cost per side, for the parity line only
WINDOWS = {"disc": ("2021-01-01", "2023-12-31"), "valid": ("2024-01-01", "2026-09-30")}   # R301's: its `report`,
# `window_mask` and `years` (gross and net 1x/2x/3x per window, at 8.5 bp per side) are reused unchanged
SPA_BOOT, SPA_BLOCK, SEED = 2000, 4, 302
COLS = ["close", "fund", "rank_qvol30"]
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- panel
def wide(df):
    """{column: DataFrame day x perp} on a full calendar of days."""
    days = pd.date_range(df.day.min(), df.day.max(), freq="D")
    perps = sorted(df.perp.unique())
    df = df.assign(day=pd.to_datetime(df.day))
    return {c: df.pivot(index="day", columns="perp", values=c).reindex(index=days, columns=perps) for c in COLS}


def signal(w, name):
    """The funding settled over the last n days (rows D-n+1..D), only where the perp has a close on row D and on row
    D-n+1, so the window is inside its history."""
    n = SIGNALS[name]
    c = w["close"]
    s = w["fund"].fillna(0.0).rolling(n, min_periods=n).sum()
    return s.where(c.notna() & c.shift(n - 1).notna())


def universe(w, top):
    return (w["rank_qvol30"] <= top) & w["close"].notna()


def legs(sig, uni, hold, seed=SEED):
    """{day: (longs, shorts)}: long the bottom fifth of the signal (the lowest funding), short the top fifth, floor(n / 5)
    each, among the universe's perps with a signal. Every day (hold 1), or every 7th day from the panel's first day
    (hold 7). Fewer than MIN_NAMES perps: no book. Ties break by a seeded random order, never by symbol."""
    rng = np.random.default_rng(seed)
    ok = sig.notna() & uni
    first = sig.index[0]
    out = {}
    for d in sig.index:
        if hold == 7 and (d - first).days % 7:
            continue
        row = sig.loc[d][ok.loc[d]]
        n = len(row)
        if n < MIN_NAMES:
            continue
        order = np.lexsort((rng.random(n), row.to_numpy()))
        s = row.index.to_numpy()[order]
        k = n // Q
        out[d] = (tuple(s[:k]), tuple(s[-k:]))
    return out


# ------------------------------------------------------------------------------------------------------------ stats
def parts(rows, price_rows, hold):
    """Per window and year: the book's gross split into price (the same legs with no funding) and funding (the rest:
    funding received by the short leg minus funding paid by the long leg), in bp/day."""
    df = pd.DataFrame({"t": [r["t"] for r in rows], "gross": [r["gross"] for r in rows],
                       "price": [r["gross"] for r in price_rows],
                       "fund_long": [r["long"] - p["long"] for r, p in zip(rows, price_rows)],
                       "fund_short": [r["short"] - p["short"] for r, p in zip(rows, price_rows)]})
    df["funding"] = df.gross - df.price
    cols = ["gross", "price", "funding", "fund_long", "fund_short"]
    bp = lambda x: {c: float(x[c].mean() / hold * 1e4) for c in cols}
    out = {}
    for win in WINDOWS:
        m = window_mask(df.t.to_numpy(), hold, win)
        out[win] = bp(df[m]) if m.any() else None
    y = pd.to_datetime(df.t, unit="ms").dt.year
    out["years"] = {int(k): bp(v) for k, v in df.groupby(y)}
    return out


def r276_parity(rows):
    """The daily fund3 top-150 book over every period, at R276's 7 bp per side: gross and net bp/day."""
    net = costed(rows, R276_COST)
    return {"periods": len(rows), "gross_bp_day": float(np.mean([r["gross"] for r in rows]) * 1e4),
            "net_bp_day": float(net.mean() * 1e4), "turnover_per_day": float(turnover(rows).mean()),
            "r276_net_bp_day": 10.43}


def ties(sig, uni):
    """Per window: the median share of the universe sitting at the day's most common signal value (the base funding
    rate), and the share of days where that tie is larger than a fifth of the universe (so a leg holds tied perps
    picked at random)."""
    out = {}
    for win, (a, z) in WINDOWS.items():
        sh = []
        for d in sig.loc[a:z].index:
            row = sig.loc[d][uni.loc[d] & sig.loc[d].notna()]
            if len(row) >= MIN_NAMES:
                sh.append(row.round(10).value_counts().iloc[0] / len(row))
        sh = np.array(sh)
        out[win] = {"days": int(len(sh)), "median_modal_share": float(np.median(sh)) if len(sh) else None,
                    "days_tie_over_fifth": float((sh > 1 / Q).mean()) if len(sh) else None}
    return out


def leg_ranks(lg, rank, hold):
    """Per window: the mean trailing volume rank of the long and the short leg's perps (1 = the most traded)."""
    ts = np.array([d.value // 10**6 for d in lg], np.int64)
    out = {}
    for win in WINDOWS:
        m = window_mask(ts, hold, win)
        days = [d for d, k in zip(lg, m) if k]
        if not days:
            out[win] = None
            continue
        out[win] = {side: float(np.mean([rank.loc[d, list(lg[d][i])].mean() for d in days]))
                    for side, i in (("long", 0), ("short", 1))}
    return out


def label(k):
    s, h, u = k
    return f"{s} h{h} top{u}"


def build(w):
    res, price, lgs = {}, {}, {}
    for s in SIGNALS:
        sig = signal(w, s)
        for h in HOLDS:
            ret, fund = targets(w, h)
            for u in TOPS:
                lg = legs(sig, universe(w, u), h)
                lgs[(s, h, u)] = lg
                res[(s, h, u)] = book(lg, ret, fund)
                price[(s, h, u)] = book(lg, ret, fund * 0.0)
    return res, price, lgs


def analyze(w, res, price, lgs):
    reports, series = {}, {}
    for k, rows in res.items():
        reports[k], ts, net1 = report(rows, k[1])
        series[k] = (ts, net1)
    pick, ok, checks = decide(reports)
    spa = {}
    first = w["close"].index[0].value // 10**6
    end = w["close"].index[-1].value // 10**6
    anchors = np.arange(first, end + 1, 7 * DAY, dtype=np.int64)
    for win in WINDOWS:
        an = anchors[window_mask(anchors, 7, win)]
        cols = []
        for k in STRATS:
            ts, net = series[k]
            m = window_mask(ts, k[1], win)
            cols.append(weekly_grid(ts[m], net[m], an))
        r = inference.spa(np.column_stack(cols), n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        r["best"] = label(STRATS[r["best"]])
        r["weeks"] = int(len(an))
        spa[win] = r
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL", "spa": spa,
            "years": {label(k): years(res[k], k[1]) for k in STRATS},
            "parts": {label(k): parts(res[k], price[k], k[1]) for k in STRATS},
            "r276_parity": r276_parity(res[("fund3", 1, 150)]),
            "ties": {f"{s} top{u}": ties(signal(w, s), universe(w, u)) for s in SIGNALS for u in TOPS},
            "leg_ranks": {label(k): leg_ranks(lgs[k], w["rank_qvol30"], k[1]) for k in STRATS}}


# ------------------------------------------------------------------------------------------------------------- main
def load_panel():
    return pd.read_parquet(PANEL, columns=["day", "perp", *COLS])


def plumbing(df):
    """Counts only: decision days and names per signal, universe and window. No funding value or return is read."""
    w = wide(df)
    c = w["close"]
    out = {"panel_days": int(len(c)), "perps": int(c.notna().any().sum())}
    for s, n in SIGNALS.items():
        have = c.notna() & c.shift(n - 1).notna()
        for u in TOPS:
            k = (have & universe(w, u)).sum(axis=1)
            days = k.index[k >= MIN_NAMES]
            ts = np.array([d.value // 10**6 for d in days], np.int64)
            out[f"{s} top{u}"] = {"days": int(len(days)), **{wn: int(window_mask(ts, 1, wn).sum()) for wn in WINDOWS},
                                  "names_min": int(k[k >= MIN_NAMES].min()),
                                  "names_median": float(k[k >= MIN_NAMES].median())}
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
    res, price, lgs = build(w)
    out = analyze(w, res, price, lgs)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    rows = [{"strategy": label(k), "t": r["t"], "gross": r["gross"], "price": p["gross"], "long": r["long"],
             "short": r["short"], "n_long": r["n_long"], "n_short": r["n_short"]}
            for k in STRATS for r, p in zip(res[k], price[k])]
    pd.DataFrame(rows).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    summary = {"rid": "R302", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
