"""Descriptive (2026-11-24): intraday vs daily adverse moves of an equal-weight basket of the forward lanes' coins, from
Binance hourly closes (lower bound) and each coin's hourly low on the worst days (upper bound). No strategy statistic.

usage: python scripts/check_intraday_wicks.py
"""
import numpy as np
import pandas as pd
from pathlib import Path
lanes = {"R509 Kraken+HL coins": pd.read_csv("experiments/xfund_kaster_v1/symbols.csv").key.tolist(),
         "R520 Deribit+HL coins": pd.read_csv("experiments/xfund_dhl_fwd/symbols.csv").key.tolist()}
def bsym(k):
    for c in (f"{k}USDT", f"{k.replace('1000', '')}USDT", f"1000{k}USDT"):
        if Path(f"data/klines_1h/{c}.parquet").exists(): return c
out = {}
for name, keys in lanes.items():
    syms = sorted({s for s in (bsym(k) for k in keys) if s})
    px = {}
    for s in syms:
        d = pd.read_parquet(f"data/klines_1h/{s}.parquet", columns=["t", "close"])
        px[s] = pd.Series(d.close.values, index=pd.to_datetime(d.t, unit="ms") + pd.Timedelta(hours=1))   # stamp = bar close
    P = pd.DataFrame(px).sort_index()
    P = P[P.index >= "2021-01-01"]
    r = np.log(P).diff()
    # equal-weight basket of coins trading that hour (log-return average), cumulated
    b = r.mean(axis=1, skipna=True).fillna(0).cumsum()
    day = b.index.floor("D")
    close_prev = b.groupby(day).last().shift(1)                # basket at the previous 00:00 UTC close
    base = close_prev.reindex(day).values
    path = b.values - base                                     # log move from the previous daily close, hour by hour
    df = pd.DataFrame({"day": day, "path": path}).dropna()
    g = df.groupby("day").path
    daily = pd.DataFrame({"close_move": g.last(), "worst_down": g.min(), "worst_up": g.max()})
    daily = np.expm1(daily) * 100
    print(f"== {name}: {len(syms)} Binance coins, {len(daily)} days")
    print("   worst close-to-close: down %.1f%%, up %.1f%%" % (daily.close_move.min(), daily.close_move.max()))
    print("   worst intraday (from the previous close): down %.1f%%, up %.1f%%" % (daily.worst_down.min(), daily.worst_up.max()))
    gap = (daily.close_move - daily.worst_down)
    print("   largest intraday dip beyond the day's close (recovered before 00:00): %.1f pts" % gap.max())
    print("   days with an intraday drop worse than -15%%: %d; worse than -20%%: %d; up moves above +15%%: %d" % ((daily.worst_down < -15).sum(), (daily.worst_down < -20).sum(), (daily.worst_up > 15).sum()))
    print("   ten worst intraday drops:", daily.worst_down.nsmallest(10).round(1).to_dict())
# upper bound on the worst days: each coin's hourly low (not simultaneous, so it overstates the basket)
keys = lanes["R509 Kraken+HL coins"]
syms = sorted({s for s in (bsym(k) for k in keys) if s})
for day in ("2021-05-19", "2025-10-10", "2022-05-11"):
    lows = []
    for s in syms:
        d = pd.read_parquet(f"data/klines_1h/{s}.parquet", columns=["t", "close", "low"])
        d["ts"] = pd.to_datetime(d.t, unit="ms") + pd.Timedelta(hours=1)
        prev = d[d.ts <= pd.Timestamp(day)]
        cur = d[(d.ts > pd.Timestamp(day)) & (d.ts <= pd.Timestamp(day) + pd.Timedelta(days=1))]
        if len(prev) and len(cur):
            lows.append(cur.low.min() / prev.close.iloc[-1] - 1)
    lows = np.array(lows)
    print(day, "coins", len(lows), "mean of each coin's intraday low: %.1f%%" % (lows.mean() * 100), "median %.1f%%" % (np.median(lows) * 100), "worst coin %.1f%%" % (lows.min() * 100))
