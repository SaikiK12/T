"""Factors for qx factors (R282 pitfac_v1) from the daily point-in-time panel (lab/daily.py): what the panel's new
sources say about a Binance perp at 00:00 UTC.

One row per decision day and coin: t = the open of the hourly bar ending at 00:00 UTC (entry at its close), sym = the
Binance perp. A coin is eligible on day d when the panel has its row d (it traded in the 24 h before) and it ranks in
the top `TOP` by 30-day Binance quote volume (`rank_qvol30`). Every value uses panel rows up to d only, and the panel
places each value on the first 00:00 UTC it was known. Windows count calendar days.

| factor | definition |
|---|---|
| kr_rel_7d | mean over the last 7 days (3+) of the day's mean of upbit_rel and bithumb_rel: the coin's Korean premium over BTC's |
| wick_30d | share of the last 30 days (10+) with a traded print 2% or more beyond the mark price (wick_up or -wick_dn) |
| size | ln(mcap_est): Coin Metrics free-float cap, 2 days old |
| vol_mcap | ln(mean qvol over the last 30 days (7+) / mcap_est) |
| fee_yield | DefiLlama fees over the last 30 days (20+), annualized, / mcap_est |
| oi_mcap | ln(oi_usd / mcap_est) |
| n_venues_7d | mean over the last 7 days of the venues whose price passes the panel's identity check |
| fund_gap_all_7d | sum over the last 7 days (4+) of Binance funding minus the mean of the other venues' funding that day |
| age | ln(1 + days since the coin's first panel row); coins trading at the panel start count from 2021-01-02 |

usage: python scripts/pitfac_factors.py PANEL.parquet OUT.parquet
"""
import sys
import warnings

import numpy as np
import pandas as pd

H, DAY = 3_600_000, 86_400_000
TOP = 150
VENUES = ("gate", "mexc", "dydx", "hyperliquid", "kucoin", "kraken")
NEED = ["day", "perp", "rank_qvol30", "upbit_rel", "bithumb_rel", "wick_up", "wick_dn", "mcap_est", "qvol", "fees",
        "oi_usd", "n_venues", "fund", *[f"{v}_fund" for v in VENUES]]


def wide(df, col, days, perps):
    return df.pivot(index="day", columns="perp", values=col).reindex(index=days, columns=perps).to_numpy(np.float64)


def roll(x, n, min_obs, how="mean"):
    r = pd.DataFrame(x).rolling(n, min_periods=min_obs)
    return (r.mean() if how == "mean" else r.sum()).to_numpy()


def factors(df):
    df = df.assign(day=pd.to_datetime(df.day), perp=df.perp.astype(str))
    days = pd.date_range(df.day.min(), df.day.max(), freq="D")
    perps = sorted(df.perp.unique())
    w = {c: wide(df, c, days, perps) for c in NEED[2:]}
    present = ~np.isnan(wide(df.assign(one=1.0), "one", days, perps))
    cap = np.where(w["mcap_est"] > 0, w["mcap_est"], np.nan)
    with np.errstate(divide="ignore", invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)           # nanmean of a day with no venue
        kr = np.nanmean(np.stack([w["upbit_rel"], w["bithumb_rel"]]), axis=0)
        wick = np.where(np.isnan(w["wick_up"]), np.nan,
                        (np.fmax(w["wick_up"], -w["wick_dn"]) >= 0.02).astype(np.float64))
        other = np.nanmean(np.stack([w[f"{v}_fund"] for v in VENUES]), axis=0)
        gap = w["fund"] - other
        first = np.where(present.any(axis=0), present.argmax(axis=0), len(days))
        age = np.arange(len(days))[:, None] - first[None, :]
        out = {
            "kr_rel_7d": roll(kr, 7, 3),
            "wick_30d": roll(wick, 30, 10),
            "size": np.log(cap),
            "vol_mcap": np.log(roll(w["qvol"], 30, 7) / cap),
            "fee_yield": roll(w["fees"], 30, 20, "sum") * 365.0 / 30.0 / cap,
            "oi_mcap": np.log(np.where(w["oi_usd"] > 0, w["oi_usd"], np.nan) / cap),
            "n_venues_7d": roll(w["n_venues"], 7, 1),
            "fund_gap_all_7d": roll(gap, 7, 4, "sum"),
            "age": np.where(age >= 0, np.log1p(np.maximum(age, 0)), np.nan),
        }
    keep = present & (w["rank_qvol30"] <= TOP)
    i, j = np.nonzero(keep)
    t = (days[i].to_numpy().astype("datetime64[ms]").astype(np.int64) - H)
    res = pd.DataFrame({"t": t, "sym": np.array(perps)[j]})
    for k, v in out.items():
        x = v[i, j]
        res[k] = np.where(np.isfinite(x), x, np.nan)
    return res.sort_values(["t", "sym"], ignore_index=True)


def main():
    src, dst = sys.argv[1:3]
    res = factors(pd.read_parquet(src, columns=NEED))
    res.to_parquet(dst, index=False)
    print(f"{len(res)} rows, {res.t.nunique()} days, {res.sym.nunique()} coins; non-missing: "
          + ", ".join(f"{c} {res[c].notna().sum()}" for c in res.columns[2:]))


if __name__ == "__main__":
    main()
