"""nagel_v1 (R308): the 1-day cross-sectional reversal only after market stress (M325), as set out in
experiments/nagel_v1/PREREG.md.

Nagel (2012, RFS, "Evaporating Liquidity") reads short-term reversal returns as the pay of liquidity providers, and
finds them highest when the VIX is high. The owner's reel DbIlAc1g0LM (Tom Costello) says crypto market makers run a
short-volatility book and pull quotes when volatility jumps. Turned around: the few who still provide liquidity after
a stress day should be paid. R245 found the unconditional 1-day reversal on the top 50 losing before costs.

The book on decision row D (data/daily/panel.parquet; signals use rows up to D, entry at row D's close, exit at row
D+1's close, R299's `targets`): long the fifth of the universe that fell most on row D, short the fifth that rose
most, equal weight, net of the funding each leg pays. It trades only when row D is a stress day:
- mvol: the top 50's mean absolute return on row D;
- disp: the top 50's cross-sectional standard deviation of returns on row D;
- oi: the change in the top 50's summed open interest from row D-1 to row D (R303's cascade measure; a fall is stress);
each against its own previous 365 rows (at least 180): at or above the 90th percentile (oi: at or below the 10th).

Family: universe {top 50, top 150} x stress {mvol, disp, oi} = 6 decided books, plus the same reversal on every day
for each universe (reported, counted): 8 trials.

usage: python scripts/run_nagel.py [--plumbing]   (--plumbing: stress-day and book-size counts only, no return read)
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
from lab import prereg, stress  # noqa: E402
from scripts.run_capit import WINDOWS, cascade, event_stats, wide  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_mlrank import targets  # noqa: E402
from scripts.run_qbasis import window_mask  # noqa: E402

LANE = ROOT / "experiments" / "nagel_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
COLS = ["close", "ret", "fund", "oi_usd", "rank_qvol30"]
DAY = 86_400_000
TOPS = (50, 150)
MEASURES = ("mvol", "disp", "oi")
BOOKS = [(top, s) for top in TOPS for s in MEASURES]           # decided
BASE = [(top, "all") for top in TOPS]                           # reported, counted
TRIALS = len(BOOKS) + len(BASE)                                 # 8
STRESS_TOP, MIN_NAMES = 50, 30                                  # the stress measures read the top 50, 30+ names
Q, LOOK, MIN_LOOK = 0.90, 365, 180
FIFTH, MIN_LEG = 0.2, 5
TIERS = ((20, 6e-4), (50, 8e-4), (100, 12e-4), (np.inf, 20e-4))   # API cost per side by volume rank (R306's tiers)
T_MIN = 2.0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- stress
def measures(w):
    """{name: Series per row} of the three stress measures (NaN with fewer than 30 top-50 names)."""
    top = (w["rank_qvol30"] <= STRESS_TOP) & w["close"].notna() & w["ret"].notna()
    r = w["ret"].where(top)
    n = top.sum(axis=1)
    return {"mvol": r.abs().mean(axis=1).where(n >= MIN_NAMES),
            "disp": r.std(axis=1, ddof=1).where(n >= MIN_NAMES),
            "oi": cascade(w)[0]}


def trigger(x, name, q=Q, look=LOOK, min_look=MIN_LOOK):
    """Row D is a stress day when its measure is at or above the q-quantile of the previous `look` rows (at least
    `min_look` defined), or for oi at or below the (1 - q)-quantile."""
    prev = x.shift(1).rolling(look, min_periods=min_look)
    if name == "oi":
        return (x <= prev.quantile(1.0 - q)) & x.notna()
    return (x >= prev.quantile(q)) & x.notna()


# ------------------------------------------------------------------------------------------------------------ books
def tier_cost(rank):
    """API cost per side for a volume rank."""
    rank = np.asarray(rank, float)
    out = np.full(rank.shape, TIERS[-1][1])
    for hi, c in reversed(TIERS):
        out = np.where(rank <= hi, c, out)
    return out


def rev_rows(w, top, days=None):
    """One row per decision day (all days, or those in `days`): long the fifth of row D's top-`top` perps with the
    lowest return on row D, short the fifth with the highest (at least 5 each), held to row D+1's close.
    gross = mean long (ret - funding) - mean short (ret - funding); cost = each leg's mean round-trip tier cost."""
    ret, fund = targets(w, 1)
    uni = (w["rank_qvol30"] <= top) & w["close"].notna() & w["ret"].notna() & ret.notna()
    rows = []
    idx = w["close"].index if days is None else days
    for d in idx:
        u = uni.loc[d].to_numpy()
        if np.floor(u.sum() * FIFTH) < MIN_LEG:
            continue
        names = w["close"].columns[u]
        sig = w["ret"].loc[d, names].to_numpy(float)
        k = int(np.floor(len(names) * FIFTH))
        order = np.argsort(sig, kind="stable")
        lo, hi = names[order[:k]], names[order[-k:]]
        net = (ret.loc[d] - fund.loc[d])
        cl = tier_cost(w["rank_qvol30"].loc[d, lo]).mean() * 2
        ch = tier_cost(w["rank_qvol30"].loc[d, hi]).mean() * 2
        rows.append({"t": int(d.value // 10**6), "long": float(net[lo].mean()), "short": float(net[hi].mean()),
                     "gross": float(net[lo].mean() - net[hi].mean()), "cost": float(cl + ch), "n": int(len(names))})
    return rows


def costed(rows, m):
    return np.array([r["gross"] - m * r["cost"] for r in rows])


def report(rows):
    ts = np.array([r["t"] for r in rows], np.int64)
    rep = {}
    for win in WINDOWS:
        msk = window_mask(ts, 1, win)
        sel = [r for r, z in zip(rows, msk) if z]
        if not sel:
            rep[win] = {"1x": {"events": 0}}
            continue
        out = {f"{k}x": event_stats(costed(sel, k), ts[msk], 1) for k in (1, 2, 3)}
        out["gross"] = event_stats([r["gross"] for r in sel], ts[msk], 1)
        out["long_bp"] = float(np.mean([r["long"] for r in sel]) * 1e4)
        out["short_bp"] = float(np.mean([r["short"] for r in sel]) * 1e4)
        out["cost_bp"] = float(np.mean([r["cost"] for r in sel]) * 1e4)
        rep[win] = out
    return rep


def decide(reports):
    """The discovery pick among the six stress books and its validation verdict (R298-R307's rule)."""
    cand = [(k, r["disc"]["1x"]) for k, r in reports.items() if k[1] != "all"
            and r["disc"]["1x"].get("t") is not None and r["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = reports[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": (v.get("2x", {}).get("mean_bp") or -1) > 0,
              "wo_best": (v["1x"].get("mean_wo_best_bp") or -1) > 0}
    return pick, all(checks.values()), checks


def label(k):
    return f"top{k[0]} {k[1]}"


# ------------------------------------------------------------------------------------------------------------- main
def load_panel():
    return pd.read_parquet(PANEL, columns=["day", "perp", *COLS])


def stress_days(w):
    ms_ = measures(w)
    return {s: ms_[s].index[trigger(ms_[s], s).to_numpy()] for s in MEASURES}


def plumbing(df):
    """Counts only: stress days per measure and window, their overlap, and the book's names per leg. The counts read
    rows up to D only; no exit is read."""
    w = wide(df)
    sd = stress_days(w)
    out = {"panel_days": int(len(w["close"]))}
    for s, days in sd.items():
        ts = np.array([d.value // 10**6 for d in days], np.int64)
        out[s] = {win: int(window_mask(ts, 1, win).sum()) for win in WINDOWS}
    out["overlap"] = {f"{a}&{b}": len(set(sd[a]) & set(sd[b])) for i, a in enumerate(MEASURES)
                      for b in MEASURES[i + 1:]}
    for top in TOPS:
        n = ((w["rank_qvol30"] <= top) & w["close"].notna() & w["ret"].notna()).sum(axis=1)
        out[f"top{top}_leg_median"] = int(np.floor(n.median() * FIFTH))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no return read (before the freeze)")
    a = ap.parse_args()
    if a.plumbing:
        print(json.dumps(plumbing(load_panel()), indent=1, default=str))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    w = wide(load_panel())
    sd = stress_days(w)
    res, reports = {}, {}
    for top in TOPS:
        res[(top, "all")] = rev_rows(w, top)
        for s in MEASURES:
            res[(top, s)] = rev_rows(w, top, sd[s])
    for k, rows in res.items():
        reports[k] = report(rows)
        d, va = reports[k]["disc"]["1x"], reports[k]["valid"]["1x"]
        log(f"{label(k)}: disc {d.get('events')} days net {d.get('mean_bp')} bp t {d.get('t')}; valid "
            f"{va.get('events')} days net {va.get('mean_bp')} bp t {va.get('t')}")
    pick, ok, checks = decide(reports)
    log(f"pick {label(pick) if pick else None}, passes {ok} {checks}")
    # Nagel's contrast, reported: the same universe's book on the other days
    other = {}
    for top, s in BOOKS:
        stress_t = {r["t"] for r in res[(top, s)]}
        other[label((top, s))] = report([r for r in res[(top, "all")] if r["t"] not in stress_t])
    st = {}
    if pick:
        rows = res[pick]
        pnl = pd.Series(costed(rows, 1) * 1e4, index=pd.to_datetime([r["t"] for r in rows], unit="ms"))
        st = stress.report(pnl)
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"book": label(k), **r} for k, rows in res.items() for r in rows]).to_csv(
        res_dir / "days.csv", index=False, float_format="%.6g")
    summary = {"rid": "R308", "verdict": "PARTIAL" if ok else "NULL", "trials": TRIALS, "prereg_sha256": sha,
               "inputs": shas, "pick": label(pick) if pick else None, "pick_passes": bool(ok), "checks": checks,
               "books": {label(k): v for k, v in reports.items()}, "other_days": other, "pick_stress": st,
               "stress_days": {s: [d.strftime("%Y-%m-%d") for d in v] for s, v in sd.items()}}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
