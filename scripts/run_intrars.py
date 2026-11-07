"""intrars_v1 (R300): intraday cross-sectional relative strength among the top 50 perps (M318, from Linda Raschke on
Better System Trader 124). As set out in experiments/intrars_v1/PREREG.md.

At a fixed hour of the UTC day, rank the top 50 perps by their move since 00:00 UTC; long the n strongest and short
the n weakest (follow), or the reverse (fade); flat at 24:00 UTC. Raschke on stocks: the day's relative-strength
leaders keep leading into the close, an edge that "might only last one day".

The family: decision k in {1, 2, 4, 8, 12 h after 00:00 UTC, 10:00 New York on NYSE days} x names per leg n in {3, 5}
x {follow, fade} = 24 books at API costs (8.5 bp per side at 1x; the book is entered and closed every day, 4 units of
turnover on 1 long and 1 short). The best discovery book (2021-01..2023-12) by net t goes to validation
(2024-01..2026-09), once. Eight placebo clocks (the same rules with the day starting at a random hour) are reported,
not decided on.

Timing: hourly bars on the grid T0 + r H; row r opens at T0 + r H and closes an hour later. A day of clock o starts at
the close of row 24 i + o - 1; the decision and entry are at the close of row sp + k; the exit is at the last traded
close at or before the close of row sp + 24. The universe at a decision is the top 50 by trailing 30-day quote volume
at the decision row (data/research/rank.npy, built from bars through that row). Bars and funding before 2021-01-01
(reserved) and from 2026-10-01 (post-archive, reserved) are never read.

usage: python scripts/run_intrars.py [--plumbing]
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
from lab import data, inference, prereg, sessions  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_lotcap import (DAY, H, T0, T1, WINDOWS, bars_digest, decide, load_bars,  # noqa: E402
                                series_stats)

LANE = ROOT / "experiments" / "intrars_v1"
VIEW = ROOT / "data" / "research"
ANCHORS = (1, 2, 4, 8, 12, "us10")
NAMES = (3, 5)
SIDES = ("follow", "fade")
STRATS = [(a, n, s) for a in ANCHORS for n in NAMES for s in SIDES]
TRIALS = len(STRATS)
TOP, MIN_NAMES = 50, 30
COST, TURN = 8.5e-4, 4.0                     # API, per side, 1x; entry 2 + exit 2 units a day
TIE = 1e-12                                  # random tie-break, below any real difference in a price ratio
PLACEBOS, SEED = 8, 300
SPA_BOOT, SPA_BLOCK = 2000, 10
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ------------------------------------------------------------------------------------------------------------- grid
class Grid:
    """Hourly closes C [n, S] (NaN where the bar did not trade), the last traded row at or before each row L (-1
    before the first), funding settled up to each bar's close G (cumulative) and the liquidity rank R."""

    def __init__(self, syms, C, G, R):
        self.syms, self.C, self.G, self.R = list(syms), C, G, R
        rows = np.arange(C.shape[0])
        self.L = np.maximum.accumulate(np.where(np.isfinite(C), rows[:, None], -1), axis=0)

    @classmethod
    def from_bars(cls, syms, bars, rank):
        n = (T1 - T0) // H
        close_t = T0 + (np.arange(n) + 1) * H
        C, G = np.full((n, len(syms)), np.nan), np.zeros((n, len(syms)))
        for j, s in enumerate(syms):
            b = bars[s]
            C[:, j] = np.where(b.traded, b.close, np.nan)
            G[:, j] = b.f_cum[np.searchsorted(b.f_t, close_t, "right")]
        return cls(syms, C, G, rank)


def rows_for(nd, o, k):
    """Start, entry and end rows for each day i of clock o, decision k hours in (k may vary by day)."""
    sp = 24 * np.arange(nd) + o - 1
    return sp, sp + np.asarray(k), sp + 24


def us_hours(nd):
    """Hours from 00:00 UTC to 10:00 New York on each day (14 in EDT, 15 in EST); 0 when the NYSE is closed."""
    noon = T0 + np.arange(nd, dtype=np.int64) * DAY + 12 * H
    trading, _ = sessions._nyse_open_day(sessions._local(noon, "America/New_York"))
    return np.where(trading, np.where(sessions.us_dst(noon) == 1, 14, 15), 0)


# ------------------------------------------------------------------------------------------------------------ books
def day_books(g, sp, e, x, ok, n, seed):
    """Per day: the follow book, long the n eligible coins that rose most from the close of sp to the close of e and
    short the n that rose least, entered at the close of e and closed at the last traded close in (e, x] (at entry
    when none). Eligible: top TOP by rank at e, traded at sp and at e. Days with fewer than MIN_NAMES are skipped.
    Columns: day, gross (long leg net of the funding it pays, short leg plus the funding it earns), price, long,
    short, basket (equal-weight eligible, long side), names, and the symbols in the top and bottom legs."""
    nrow = g.C.shape[0]
    ok = np.asarray(ok, bool) & (sp >= 0) & (x < nrow)
    i = np.flatnonzero(ok)
    sp, e, x = sp[i], e[i], x[i]
    c1 = g.C[e]
    sig = c1 / g.C[sp] - 1.0
    with np.errstate(invalid="ignore"):
        elig = (g.R[e] <= TOP) & np.isfinite(sig)
    m = elig.sum(1)
    keep = m >= MIN_NAMES
    i, sp, e, x, c1, sig, elig, m = i[keep], sp[keep], e[keep], x[keep], c1[keep], sig[keep], elig[keep], m[keep]
    cols = np.arange(g.C.shape[1])
    xr = g.L[x]
    xr = np.where(xr > e[:, None], xr, e[:, None])
    ret = g.C[xr, cols] / c1 - 1.0
    lr = ret - (g.G[xr, cols] - g.G[e])
    key = np.where(elig, sig + TIE * np.random.default_rng(seed).random(sig.shape), np.inf)
    order = np.argsort(key, axis=1)
    bot = order[:, :n]
    top = np.take_along_axis(order, np.clip(m[:, None] - n + np.arange(n), 0, None), 1)
    pick = lambda a, idx: np.take_along_axis(a, idx, 1).mean(1)
    long, short = pick(lr, top), -pick(lr, bot)
    basket = np.where(elig, lr, 0.0).sum(1) / m
    names = lambda idx: ["|".join(g.syms[j] for j in row) for row in idx]
    return pd.DataFrame({"day": i, "gross": long + short, "price": pick(ret, top) - pick(ret, bot), "long": long,
                         "short": short, "basket": basket, "names": m, "top": names(top), "bot": names(bot)})


def flip(df):
    """The fade book on the same legs: long the weakest n, short the strongest."""
    return df.assign(gross=-df.gross, price=-df.price, long=-df.short, short=-df.long, top=df.bot, bot=df.top)


def family(g, o, anchors):
    nd = g.C.shape[0] // 24
    res = {}
    for a in anchors:
        k = us_hours(nd) if a == "us10" else np.full(nd, a)
        sp, e, x = rows_for(nd, o, k)
        for n in NAMES:
            df = day_books(g, sp, e, x, k > 0, n, seed=(SEED, o, 10 if a == "us10" else a, n))
            res[(a, n, "follow")], res[(a, n, "fade")] = df, flip(df)
    return res


# ------------------------------------------------------------------------------------------------------------ stats
def in_window(day, o, win):
    """Days whose clock starts in the window and whose hold ends inside it."""
    a, b = WINDOWS[win]
    lo = pd.Timestamp(a, tz="UTC").value // 10**6
    hi = (pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1)).value // 10**6
    start = T0 + np.asarray(day, np.int64) * DAY + o * H
    return (start >= lo) & (start + DAY <= hi)


def report(df, o=0):
    ts = T0 + df.day.to_numpy(np.int64) * DAY + o * H
    rep = {}
    for w in WINDOWS:
        m = in_window(df.day, o, w)
        x, t = df[m], ts[m]
        g = x.gross.to_numpy()
        if not len(x):
            rep[w] = {"gross": {"periods": 0}, "1x": {"periods": 0}, "2x": {"periods": 0}, "3x": {"periods": 0}}
            continue
        bp = lambda v: float(v.mean() * 1e4)
        rep[w] = {"gross": series_stats(g, t, 24),
                  **{f"{c}x": series_stats(g - c * COST * TURN, t, 24) for c in (1, 2, 3)},
                  "price_bp": bp(x.price), "long_bp": bp(x.long), "short_bp": bp(x.short), "basket_bp": bp(x.basket),
                  "long_excess_bp": bp(x.long - x.basket), "short_excess_bp": bp(x.short + x.basket),
                  "names_median": float(x.names.median()), "breakeven_bp_side": bp(x.gross) / TURN}
    return rep


def label(k):
    a, n, s = k
    return f"{a if a == 'us10' else f'k{a}'} n{n} {s}"


def years(df):
    y = pd.to_datetime(T0 + df.day.to_numpy(np.int64) * DAY, unit="ms").year
    return {int(k): {"gross_bp": float(v.gross.mean() * 1e4), "net1x_bp": float((v.gross - COST * TURN).mean() * 1e4),
                     "days": int(len(v))} for k, v in df.groupby(y)}


def clock_summary(reps):
    """The family pick on one clock (decide's rule) and how it fared in validation."""
    pick, ok, _ = decide(reps)
    ts = [r["disc"]["1x"].get("t") for r in reps.values() if r["disc"]["1x"].get("t") is not None]
    out = {"max_disc_t": float(max(ts)) if ts else None, "pick": label(pick) if pick else None, "passes": bool(ok)}
    if pick:
        v = reps[pick]["valid"]["1x"]
        out.update({"pick_valid_t": v.get("t"), "pick_valid_bp_day": v.get("bp_day")})
    return out


def spa(res):
    out = {}
    for w in WINDOWS:
        days = np.unique(np.concatenate([df.day[in_window(df.day, 0, w)].to_numpy() for df in res.values()]))
        cols = []
        for k in STRATS:
            df = res[k][in_window(res[k].day, 0, w)]
            v = pd.Series(0.0, index=days)
            v.loc[df.day.to_numpy()] = (df.gross - COST * TURN).to_numpy()
            cols.append(v.to_numpy())
        r = inference.spa(np.column_stack(cols), n_boot=SPA_BOOT, block=SPA_BLOCK, rng=np.random.default_rng(SEED))
        r["best"] = label(STRATS[r["best"]])
        r["days"] = int(len(days))
        out[w] = r
    return out


def placebo_offsets():
    return sorted(int(o) for o in np.random.default_rng(SEED).choice(np.arange(1, 24), PLACEBOS, replace=False))


def analyze(g, res):
    reports = {k: report(df) for k, df in res.items()}
    pick, ok, checks = decide(reports)
    clocks = {0: clock_summary({k: v for k, v in reports.items() if k[0] != "us10"})}
    for o in placebo_offsets():
        clocks[o] = clock_summary({k: report(df, o) for k, df in family(g, o, ANCHORS[:-1]).items()})
    real = clocks[0]
    rank = {f: 1 + sum((c.get(f) or -np.inf) > (real.get(f) or -np.inf) for o, c in clocks.items() if o)
            for f in ("max_disc_t", "pick_valid_t")}
    return {"strategies": {label(k): v for k, v in reports.items()}, "pick": label(pick) if pick else None,
            "pick_passes": bool(ok), "checks": checks, "verdict": "PARTIAL" if ok else "NULL",
            "years": {label(k): years(res[k]) for k in STRATS if k[2] == "follow"}, "spa": spa(res),
            "clocks": {str(o): c for o, c in clocks.items()}, "real_clock_rank_of_9": rank}


# ------------------------------------------------------------------------------------------------------------- main
def load_grid():
    meta = json.loads((VIEW / "meta.json").read_text())
    rank = np.load(VIEW / "rank.npy")
    t = np.load(VIEW / "t.npy")
    assert t[0] == T0 and len(t) == (T1 - T0) // H, "research view grid differs from [T0, T1)"
    with np.errstate(invalid="ignore"):
        ever = np.nanmin(np.where(np.isnan(rank), np.inf, rank), axis=0) <= TOP
    syms = [s for s, e in zip(meta["symbols"], ever) if e]
    bars = load_bars(syms)
    syms = [s for s in syms if s in bars]
    idx = [meta["symbols"].index(s) for s in syms]
    return Grid.from_bars(syms, bars, rank[:, idx]), bars


def plumbing(g):
    """Counts only: days and eligible names per anchor and window. No return is read."""
    nd = g.C.shape[0] // 24
    tr = np.isfinite(g.C)
    out = {"symbols": len(g.syms), "days": nd, "placebo_offsets": placebo_offsets()}
    for a in ANCHORS:
        k = us_hours(nd) if a == "us10" else np.full(nd, a)
        sp, e, x = rows_for(nd, 0, k)
        ok = (k > 0) & (sp >= 0) & (x < g.C.shape[0])
        i = np.flatnonzero(ok)
        with np.errstate(invalid="ignore"):
            m = ((g.R[e[i]] <= TOP) & tr[sp[i]] & tr[e[i]]).sum(1)
        days = i[m >= MIN_NAMES]
        out[label((a, 0, "")).split()[0]] = {"days": int(len(days)), "median_names": float(np.median(m)),
                                  **{w: int(in_window(days, 0, w).sum()) for w in WINDOWS}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    if a.plumbing:
        g, _ = load_grid()
        print(json.dumps(plumbing(g), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    g, bars = load_grid()
    digest = bars_digest(bars)
    log(f"{len(g.syms)} coins' bars loaded, digest {digest[:12]}")
    res = family(g, 0, ANCHORS)
    out = analyze(g, res)
    for k, v in out["strategies"].items():
        d, va = v["disc"]["1x"], v["valid"]["1x"]
        log(f"{k}: disc net {d.get('bp_day', float('nan')):+.2f} bp/day t {d.get('t')}, valid net "
            f"{va.get('bp_day', float('nan')):+.2f} t {va.get('t')}")
    log(f"pick {out['pick']}, passes {out['pick_passes']} {out['checks']}; verdict {out['verdict']}")
    log(f"clocks: {out['clocks']}; real clock rank {out['real_clock_rank_of_9']}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    pd.concat([df.assign(strategy=label(k)) for k, df in res.items() if k[2] == "follow"]).to_csv(
        res_dir / "days.csv", index=False, float_format="%.8g")
    summary = {"rid": "R300", "verdict": out["verdict"], "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "coins_loaded": len(g.syms), "bars_digest": digest, **out}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
