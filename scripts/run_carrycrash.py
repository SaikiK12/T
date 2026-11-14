"""carrycrash_v1 (R207): high market-wide carry as a BTC crash signal, as set out in experiments/carrycrash_v1/PREREG.md."""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import carry, engine, events, panel, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "carrycrash_v1"
INS, HOLD_OUT, END = "2021-01-01", "2025-07-01", "2026-10-01"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def signal_days(M, q):
    """S_d = M_d > the q-quantile of M over days d-365..d-1 (at least 180 finite days)."""
    s = pd.Series(M)
    thr = s.shift(1).rolling(365, min_periods=180).quantile(q).values
    with np.errstate(invalid="ignore"):
        return (M > thr) & np.isfinite(thr), thr


def overlay(S, hold_days, ret, cost, day_row0, T):
    """Hourly weight: -1 from a signal day's 00:00 row through hold_days x 24 rows after the last signal day."""
    w = np.zeros(T)
    for d in np.flatnonzero(S):
        a = day_row0 + d * 24
        w[a:min(a + hold_days * 24, T)] = -1.0
    pnl = w * np.nan_to_num(ret)
    dw = np.abs(np.diff(np.concatenate([[0.0], w])))
    return w, pnl, dw * cost


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = panel.load_panel()
    keep = np.flatnonzero(np.isfinite(p["close"]).any(axis=0))
    p = p.columns(keep)
    rank = panel.liquidity_rank(p, 24 * 30)
    elig = rank <= 50
    cmat = engine.cost_matrix(rank).astype(np.float64)
    fund = p["fund_event"].astype(np.float64)
    close = p["close"].astype(np.float64)
    ret = engine.forward_returns(close, fund)
    apr = carry.trailing_apr(fund, 72)
    b = p.symbols.index("BTCUSDT")
    hours = pd.to_datetime(p.t, unit="ms", utc=True)
    r0 = int(np.flatnonzero(hours.hour == 0)[0])
    T = len(p.t)
    D = (T - r0) // 24
    rows = r0 + 24 * np.arange(D)
    days = hours[rows]
    with np.errstate(invalid="ignore"):
        a = np.where(elig[rows], apr[rows], np.nan)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # days before any funding: all-NaN rows
        M = np.nanmedian(a, axis=1)
    log(f"days {D}, first {days[0].date()}, market carry median {np.nanmedian(M):.3f}")
    btc = close[rows, b]
    fwd_min = np.full(D, np.nan)
    for d in range(D - 30):
        fwd_min[d] = np.nanmin(close[rows[d] + 1:rows[d] + 30 * 24 + 1, b]) / btc[d] - 1
    d_ins, d_ho, d_end = (int(np.searchsorted(days, pd.Timestamp(x, tz="UTC"))) for x in (INS, HOLD_OUT, END))
    res, keep_series = [], {}
    for q in (0.90, 0.80):
        S, thr = signal_days(M, q)
        for h in (7, 30):
            for cm in (1.0, 2.0, 3.0):
                w, pnl, c = overlay(S, h, ret[:, b], cmat[:, b] * cm, r0, T)
                net = (pnl - c)[r0:r0 + D * 24].reshape(D, 24).sum(1)
                gross = pnl[r0:r0 + D * 24].reshape(D, 24).sum(1)
                inpos = (w[r0:r0 + D * 24].reshape(D, 24) != 0).any(1)
                for name, (x0, x1) in (("insample", (d_ins, d_ho)), ("holdout", (d_ho, d_end))):
                    n = net[x0:x1]
                    sig = np.flatnonzero(S[x0:x1])
                    ep = int(len(sig) and 1 + (np.diff(sig) > h).sum())
                    res.append({"q": q, "hold": h, "cmult": cm, "window": name, "days": x1 - x0,
                                "days_in_pos": int(inpos[x0:x1].sum()), "signal_days": int(S[x0:x1].sum()),
                                "episodes": ep, "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
                                "gross_total": float(gross[x0:x1].sum()), "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                                **{k: v for k, v in events.summary(n).items() if k != "t_nw"}})
                if cm == 1.0:
                    keep_series[f"q{int(q * 100)}_h{h}"] = net[d_ins:d_end]
        # crash frequency, by window
        for name, (x0, x1) in (("insample", (d_ins, d_ho)), ("holdout", (d_ho, d_end)), ("all", (d_ins, d_end))):
            f = fwd_min[x0:x1]
            s = S[x0:x1] & np.isfinite(f)
            ok = np.isfinite(f)
            for lvl in (-0.20, -0.10):
                res.append({"q": q, "window": name, "crash_level": lvl, "signal_days": int(s.sum()),
                            "p_crash_signal": float((f[s] <= lvl).mean()) if s.any() else np.nan,
                            "p_crash_all": float((f[ok] <= lvl).mean())})
    df = pd.DataFrame(res)
    df.to_csv(out / "results.csv", index=False)
    np.savez_compressed(out / "daily.npz", days=np.asarray(days[d_ins:d_end].astype(np.int64)), **keep_series)
    pd.DataFrame({"day": days.date, "market_carry": M, "thr90": signal_days(M, 0.9)[1],
                  "btc_close": btc, "btc_fwd30_min": fwd_min}).to_csv(out / "market_carry.csv.gz", index=False)
    books = df[df.crash_level.isna()] if "crash_level" in df else df
    p1 = books[(books.q == 0.9) & (books.hold == 7) & (books.cmult == 1.0)].set_index("window")
    yr = pd.Series(keep_series["q90_h7"], index=days[d_ins:d_end]).groupby(days[d_ins:d_end].year).sum()
    verdict = {"insample_mean_bp_day": float(p1.loc["insample", "mean_bp_day"]),
               "insample_t_nw10": float(p1.loc["insample", "t_nw10"]),
               "holdout_mean_bp_day": float(p1.loc["holdout", "mean_bp_day"]),
               "confirmed": bool(p1.loc["insample", "mean_bp_day"] > 0 and p1.loc["insample", "t_nw10"] >= 2
                                 and p1.loc["holdout", "mean_bp_day"] > 0),
               "per_year_q90_h7": {int(k): float(v) for k, v in yr.items()}}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 220)
    log("\n" + books.drop(columns=[c for c in ("crash_level", "p_crash_signal", "p_crash_all") if c in books])
        .round(4).to_string(index=False))
    log("\n" + df[df.crash_level.notna()][["q", "window", "crash_level", "signal_days", "p_crash_signal",
                                           "p_crash_all"]].round(3).to_string(index=False))
    log(verdict)


if __name__ == "__main__":
    main()
