"""R385 dvolbeta_v1 (M456, the sort half): each coin's trailing 90-day return beta to daily Deribit DVOL changes as a
cross-sectional sort on the top-150 Binance perps, held 7 days, as set out in experiments/dvolbeta_v1/PREREG.md.

Four books: {BTC DVOL, ETH DVOL} x {long the low-beta fifth / short the high-beta fifth, and the reverse}. Panel,
universe, entry, exit, funding, legs (top/bottom fifth, seeded random ties), weekly grid, windows, costs, the three
checks and the pick rule come unchanged from `scripts/run_mlrank.py` (frozen). The gamma-weighted option inventory half
of M456 needs chain-priced data and is not tested.

usage: python scripts/run_dvolbeta.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402
from scripts.run_mlrank import (FIRST_PRED, WINDOWS, book, daily_ic, decide, legs, rank_target,  # noqa: E402
                                report, targets, universe, wide)

LANE = ROOT / "experiments" / "dvolbeta_v1"
PANEL = ROOT / "data" / "daily" / "panel.parquet"
DVOL = {"BTC": ROOT / "data" / "deribit" / "dvol_BTC.parquet", "ETH": ROOT / "data" / "deribit" / "dvol_ETH.parquet"}
PANEL_COLS = ["close", "ret", "fund", "rank_qvol30"]
WIN, MIN_OBS, HOLD = 90, 60, 7
DAY_MS, HOUR_MS = 86_400_000, 3_600_000
SIDES = {"LH": "long low beta / short high beta", "HL": "long high beta / short low beta"}
BOOKS = [(c, s) for c in DVOL for s in SIDES]                  # 4
TRIALS = len(BOOKS)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def dvol_daily(path, days):
    """DVOL known at 00:00 UTC of each row: the close of the last hourly bar of the day before (panel timing: an
    hourly bar opening at t goes on row ceil((t + 1 h) / 1 day))."""
    d = pd.read_parquet(path, columns=["t", "close"]).drop_duplicates("t").sort_values("t")
    row = -((-(d.t.to_numpy(np.int64) + HOUR_MS)) // DAY_MS)    # ceil
    s = pd.Series(d.close.to_numpy(float), index=pd.to_datetime(row * DAY_MS, unit="ms")).groupby(level=0).last()
    return s.reindex(days)


def dvol_change(level):
    """Daily log change of DVOL on the calendar of rows; NaN where either row is missing."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(level).diff()


def rolling_beta(R, x, win=WIN, min_obs=MIN_OBS):
    """Day x perp OLS slope of the return on x over rows D-win+1..D (row D included: it holds day D-1, known at 00:00
    of D). Only rows where both exist count; fewer than min_obs pairs, or a zero variance, give NaN."""
    ok = R.notna() & x.notna().to_numpy()[:, None]
    X = pd.DataFrame(np.broadcast_to(x.to_numpy(float)[:, None], R.shape), index=R.index, columns=R.columns)
    Xz, Rz = X.where(ok, 0.0), R.where(ok, 0.0)
    roll = lambda f: f.rolling(win).sum()
    n, sx, sy = roll(ok.astype(float)), roll(Xz), roll(Rz)
    sxy, sxx = roll(Xz * Rz), roll(Xz * Xz)
    with np.errstate(divide="ignore", invalid="ignore"):
        cov = sxy - sx * sy / n
        var = sxx - sx * sx / n
        beta = cov / var
    return beta.where((n >= min_obs) & (var > 1e-18))


def scores(beta, uni, side, first=FIRST_PRED):
    """(day, perp) -> score for universe rows from `first` on. The top fifth of the score is the long leg."""
    s = (-beta if side == "LH" else beta).where(uni).stack(future_stack=True).dropna()
    return s[s.index.get_level_values(0) >= pd.Timestamp(first)]


def market_corr(rows, ret, uni):
    """Descriptive only: the book's gross against the equal-weight top-150 return over the same hold."""
    ts = [pd.Timestamp(r["t"], unit="ms") for r in rows]
    mk = np.array([float(ret.loc[d][uni.loc[d]].mean()) for d in ts])
    g = np.array([r["gross"] for r in rows])
    ok = np.isfinite(mk) & np.isfinite(g)
    return float(np.corrcoef(g[ok], mk[ok])[0, 1]), float(np.polyfit(mk[ok], g[ok], 1)[0])


def analyze(df, x_of):
    """The four books on a panel; `x_of(days)` returns {coin: DVOL log change on the calendar of rows}."""
    w = wide(df)
    ret1, uni = w["ret"], universe(w)
    ret, fund = targets(w, HOLD)
    y = rank_target(ret - fund, uni).stack(future_stack=True)
    x = x_of(ret1.index)
    betas = {c: rolling_beta(ret1, x[c]) for c in DVOL}
    for c in DVOL:
        log(f"{c} DVOL: {int(x[c].notna().sum())} daily changes, first {x[c].first_valid_index():%Y-%m-%d}, "
            f"last {x[c].last_valid_index():%Y-%m-%d}")
    res, ics, reps, desc = {}, {}, {}, {}
    for k in BOOKS:
        c, side = k
        pred = scores(betas[c], uni, side)
        rows = book(legs(pred, HOLD), ret, fund)
        ic = daily_ic(pred, y.reindex(pred.index))
        rep = report(rows, HOLD, ic)[0]
        res[k], ics[k], reps[k] = rows, ic, rep
        corr, slope = market_corr(rows, ret, uni)
        bm = betas[c].where(uni).stack(future_stack=True).dropna()
        desc[k] = {"corr_ew_market": corr, "slope_ew_market": slope, "beta_median": float(bm.median()),
                   "beta_share_negative": float((bm < 0).mean()),
                   "scored_names_median": int(pred.groupby(level=0).size().median())}
        for win in WINDOWS:
            r = rep[win]["1x"]
            log(f"{c} {side} {win}: gross {rep[win]['gross'].get('bp_day', float('nan')):+.2f} net1x "
                f"{r.get('bp_day', float('nan')):+.2f} bp/day t {r.get('t')} periods {r.get('periods')}")
    pick, passes, checks = decide({f"{c} {s}": reps[(c, s)] for c, s in BOOKS})
    return res, ics, reps, desc, pick, passes, checks


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    df = pd.read_parquet(PANEL, columns=["day", "perp", *PANEL_COLS])
    x_of = lambda days: {c: dvol_change(dvol_daily(p, days)) for c, p in DVOL.items()}
    res, ics, reps, desc, pick, passes, checks = analyze(df, x_of)
    verdict = "PARTIAL" if passes else "NULL"
    log(f"pick {pick}, passes {passes} {checks}; verdict {verdict}")
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"book": f"{k[0]} {k[1]}", "t": r["t"], "gross": r["gross"], "long": r["long"], "short": r["short"],
                   "n_long": r["n_long"], "n_short": r["n_short"]} for k, rs in res.items() for r in rs]
                 ).to_csv(res_dir / "periods.csv", index=False, float_format="%.8g")
    pd.DataFrame({f"{k[0]} {k[1]}": v for k, v in ics.items()}).to_csv(res_dir / "rank_ic.csv", float_format="%.5f")
    summary = {"rid": "R385", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha, "inputs": shas,
               "pick": pick, "pick_passes": passes, "checks": checks,
               "books": {f"{k[0]} {k[1]}": {"report": reps[k], "descriptive": desc[k]} for k in BOOKS}}
    (res_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
