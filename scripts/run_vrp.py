"""vrp_v1 (R209): implied minus realized volatility as a BTC/ETH timing signal, as set out in
experiments/vrp_v1/PREREG.md."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, events, prereg, research, stats  # noqa: E402

LANE = ROOT / "experiments" / "vrp_v1"
HOLD_OUT, END = "2025-07-01", "2026-10-01"
COINS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
HOUR = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = u.p.t
    hours = pd.to_datetime(t, unit="ms", utc=True)
    r0 = int(np.flatnonzero(hours.hour == 0)[0])
    t_end = research.row_of(u.p, END)
    D = (t_end - r0) // 24
    rows = r0 + 24 * np.arange(D)
    days = hours[rows]
    d_ho = int(np.searchsorted(days, pd.Timestamp(HOLD_OUT, tz="UTC")))
    res, keep, extra = [], {}, {}
    for cur, sym in COINS.items():
        j = u.p.symbols.index(sym)
        close = u.p["close"][:, j].astype(np.float64)
        ret = np.nan_to_num(u.ret[:, j].astype(np.float64))
        cost = u.cmat[:, j].astype(np.float64)
        lr = np.diff(np.log(close), prepend=np.nan)
        sq = pd.Series(lr ** 2).rolling(720, min_periods=600).mean().shift(1).values   # rows d-720..d-1
        rv = 100 * np.sqrt(8760 * sq[rows])
        dv = pd.read_parquet(data.ROOT / "deribit" / f"dvol_{cur}.parquet")
        iv_map = pd.Series(dv["close"].values, index=dv["t"].values)
        iv = iv_map.reindex(t[rows] - HOUR).values                                       # the 23:00 bar of d-1
        vrp = iv - rv
        s = pd.Series(vrp).shift(1).rolling(365, min_periods=180)
        med, lo, hi = s.median().values, s.quantile(1 / 3).values, s.quantile(2 / 3).values
        ok = np.isfinite(vrp) & np.isfinite(med)
        first = int(np.flatnonzero(ok)[0])
        day_ret = ret[r0:r0 + D * 24].reshape(D, 24).sum(1)
        mom30 = pd.Series(np.log(close[rows])).diff(30).values
        with np.errstate(invalid="ignore"):
            extra[cur] = {"first_day": str(days[first].date()),
                          "vrp_mean": float(np.nanmean(vrp[first:d_ho])), "share_iv_above_rv": float(np.nanmean(
                              (vrp[first:d_ho] > 0))),
                          "corr_vrp_past30d_ret": float(pd.Series(vrp[first:d_ho]).corr(pd.Series(mom30[first:d_ho])))}
        for split in ("median", "tercile"):
            with np.errstate(invalid="ignore"):
                if split == "median":
                    wd = np.where(vrp > med, 1.0, -1.0)
                else:
                    wd = np.where(vrp > hi, 1.0, np.where(vrp < lo, -1.0, 0.0))
            wd[~ok] = 0.0
            for reb in ("daily", "weekly"):
                w = wd.copy()
                if reb == "weekly":
                    mon = np.asarray(days.dayofweek == 0)
                    last = 0.0
                    for d in range(D):
                        if mon[d]:
                            last = wd[d]
                        w[d] = last if ok[d] or not mon[d] else 0.0
                    w[:first] = 0.0
                wh = np.repeat(w, 24)
                dw = np.abs(np.diff(np.concatenate([[0.0], wh])))
                for cm in (1.0, 2.0, 3.0):
                    net_h = wh * ret[r0:r0 + D * 24] - cm * dw * cost[r0:r0 + D * 24]
                    net = net_h.reshape(D, 24).sum(1)
                    for win, (a, b) in (("insample", (first, d_ho)), ("holdout", (d_ho, D))):
                        n = net[a:b]
                        hi_d, lo_d = w[a:b] > 0, w[a:b] < 0
                        res.append({"coin": cur, "split": split, "rebalance": reb, "cmult": cm, "window": win,
                                    "days": b - a, "share_long": float(hi_d.mean()), "share_short": float(lo_d.mean()),
                                    "total": float(n.sum()), "mean_bp_day": float(n.mean() * 1e4),
                                    "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                                    "ret_bp_long_days": float(day_ret[a:b][hi_d].mean() * 1e4) if hi_d.any() else np.nan,
                                    "ret_bp_short_days": float(day_ret[a:b][lo_d].mean() * 1e4) if lo_d.any() else np.nan,
                                    **{k: v for k, v in events.summary(n).items() if k != "t_nw"}})
                    if cm == 1.0:
                        keep[f"{cur}_{split}_{reb}"] = net
    df = pd.DataFrame(res)
    df.to_csv(out / "results.csv", index=False)
    np.savez_compressed(out / "daily.npz", days=np.asarray(t[rows]), **keep)
    p = df[(df.coin == "BTC") & (df.split == "median") & (df.rebalance == "daily") & (df.cmult == 1.0)].set_index("window")
    n = keep["BTC_median_daily"]
    yr = pd.Series(n, index=days).groupby(days.year).sum()
    verdict = {"insample_mean_bp_day": float(p.loc["insample", "mean_bp_day"]),
               "insample_t_nw10": float(p.loc["insample", "t_nw10"]),
               "holdout_mean_bp_day": float(p.loc["holdout", "mean_bp_day"]),
               "confirmed": bool(p.loc["insample", "mean_bp_day"] > 0 and p.loc["insample", "t_nw10"] >= 2
                                 and p.loc["holdout", "mean_bp_day"] > 0),
               "per_year_primary": {int(k): float(v) for k, v in yr.items()}, "descriptive": extra}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df[df.cmult == 1.0].round(4).to_string(index=False))
    log("\n" + df[df.cmult > 1.0][["coin", "split", "rebalance", "cmult", "window", "mean_bp_day", "t_nw10"]]
        .round(3).to_string(index=False))
    log(verdict)


if __name__ == "__main__":
    main()
