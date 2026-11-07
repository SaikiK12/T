"""R411 dvolvrp_v1 (M477, item 41): Deribit's 30-day implied volatility index (DVOL) against the realized volatility of
the next 30 days, BTC and ETH, as set out in experiments/dvolvrp_v1/PREREG.md. A measurement, not a trade: no costs and
no decision.

Each UTC day d: DVOL at d 00:00 (the close of the hourly bar opening at d - 1 h, `data/deribit/dvol_<CUR>.parquet`)
and the realized volatility of the 720 hourly log returns of the Binance USDT perp over [d, d + 30 d)
(`data/klines_1m`, closes on the hour), annualized with 8,760 hours, zero mean. Days with any missing hour are skipped.

usage: python scripts/run_dvolvrp.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs  # noqa: E402
from scripts.run_optflow import COINS, hourly_prices  # noqa: E402

LANE = ROOT / "experiments" / "dvolvrp_v1"
HOUR, DAY = 3_600_000, 86_400_000
N = 720                                           # hours in 30 days
NW_LAG = 30                                       # the daily windows overlap by 29 days
HALVES = (("2021-01-01", "2024-01-01"), ("2024-01-01", "2026-10-01"))
log_ = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def dvol_at(path):
    """{instant ms: DVOL} where instant = bar open + 1 h (the bar's close), for bars inside [T0, T1)."""
    d = pd.read_parquet(path, columns=["t", "close"])
    d = d[(d.t >= T0) & (d.t < T1) & (d.close > 0)].drop_duplicates("t")
    return dict(zip((d.t + HOUR).astype(np.int64), d.close.astype(float)))


def days(PH, DV):
    """Rows (day, dvol, rv) for every day with DVOL at 00:00 and 720 complete hourly returns after it."""
    out = []
    d = T0
    while d + 30 * DAY <= T1:
        k = (d - T0) // HOUR
        seg = PH[k: k + N + 1]
        if d in DV and len(seg) == N + 1 and np.all(np.isfinite(seg)):
            rv = float(np.sqrt(np.sum(np.diff(np.log(seg)) ** 2) * 8760.0 / N) * 100.0)
            out.append((d, DV[d], rv))
        d += DAY
    return pd.DataFrame(out, columns=["d", "dvol", "rv"])


def describe(x, dates):
    x = np.asarray(x, float)
    dt = pd.to_datetime(dates, unit="ms")
    halves = [float(x[(dt >= a) & (dt < b)].mean()) if ((dt >= a) & (dt < b)).any() else None for a, b in HALVES]
    return {"days": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)),
            "t_nw": float(stats.newey_west_t(x, NW_LAG)[2]), "share_positive": float((x > 0).mean()),
            "p05": float(np.percentile(x, 5)), "min": float(x.min()), "halves": halves}


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log_(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    res, frames = {"registry": "R411", "prereg_sha": sha, "coins": {}}, []
    for cur in COINS:
        PH = hourly_prices(data.ROOT / "klines_1m" / f"{COINS[cur]}.parquet")
        f = days(PH, dvol_at(data.ROOT / "deribit" / f"dvol_{cur}.parquet"))
        f["gap"] = f.dvol - f.rv                                   # vol points
        f["varswap"] = (f.dvol ** 2 - f.rv ** 2) / (2.0 * f.dvol)  # vega-normalized variance-swap P&L, vol points
        by_year = f.groupby(pd.to_datetime(f.d, unit="ms").dt.year)
        res["coins"][cur] = {
            "first_day": pd.Timestamp(f.d.min(), unit="ms").date().isoformat(),
            "last_day": pd.Timestamp(f.d.max(), unit="ms").date().isoformat(),
            "mean_dvol": float(f.dvol.mean()), "mean_rv": float(f.rv.mean()),
            "gap_volpts": describe(f.gap, f.d), "varswap_volpts": describe(f.varswap, f.d),
            "by_year_gap_mean": {int(y): float(g.gap.mean()) for y, g in by_year},
            "by_year_share_positive": {int(y): float((g.gap > 0).mean()) for y, g in by_year},
        }
        frames.append(f.assign(coin=cur))
        g = res["coins"][cur]["gap_volpts"]
        log_(f"{cur}: {g['days']} days, DVOL - RV30 mean {g['mean']:+.2f} vol pts (NW t {g['t_nw']:.2f}), "
             f"median {g['median']:+.2f}, positive {g['share_positive']:.0%}")
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1))
    out = pd.concat(frames)
    out["day"] = pd.to_datetime(out.d, unit="ms").dt.date
    out[["coin", "day", "dvol", "rv", "gap", "varswap"]].to_csv(LANE / "results" / "days.csv", index=False)


if __name__ == "__main__":
    main()
