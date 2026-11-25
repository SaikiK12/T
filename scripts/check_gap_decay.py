"""Why did the design gap's return fall through 2026? Decompose R508's seen window by leg (descriptive).

Reads R508's pinned files (data/kraken_hist/open/funding, data/hyperliquid/funding) for the 111 coins of
experiments/xfund_eea_v1/symbols.csv over 2025-11-17 .. 2026-11-15 (all seen by R508). By month, equal weight across
coins, annualized from hourly rates: Hyperliquid's funding, its share of hours above the 0.01%/8 h floor, Kraken's
funding, and the gap. Also BTC's monthly return (Hyperliquid daily closes) for the regime.

    python scripts/check_gap_decay.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
START, END = pd.Timestamp("2025-11-17", tz="UTC"), pd.Timestamp("2026-11-16", tz="UTC")
FLOOR_H = 0.0001 / 8          # Hyperliquid's interest floor per hour
HY = 24 * 365


def hourly(path: Path) -> pd.Series:
    d = pd.read_parquet(path, columns=["t", "rate"])
    t = pd.to_datetime(d.t.astype("int64") // 3_600_000 * 3_600_000, unit="ms", utc=True)
    s = pd.Series(d.rate.to_numpy(float), index=t)
    s = s[~s.index.duplicated()].sort_index()
    return s[(s.index >= START) & (s.index < END)]


def main() -> int:
    rows = list(csv.DictReader(open(ROOT / "experiments/xfund_eea_v1/symbols.csv")))
    per = []
    for r in rows:
        pk = ROOT / "data/kraken_hist/open/funding" / f"{r['kraken']}.parquet"
        ph = ROOT / "data/hyperliquid/funding" / f"{r['hyperliquid']}.parquet"
        if not (pk.exists() and ph.exists()):
            continue
        k, h = hourly(pk), hourly(ph)
        j = pd.concat({"k": k, "h": h}, axis=1, sort=True).dropna()
        if j.empty:
            continue
        j["coin"] = r["key"]
        per.append(j)
    d = pd.concat(per)
    d["month"] = d.index.strftime("%Y-%m")
    d["above"] = d.h > FLOOR_H * 1.0001
    d["k_above_floor"] = d.k > FLOOR_H
    by = d.groupby(["month", "coin"]).agg(h=("h", "mean"), k=("k", "mean"), above=("above", "mean"),
                                          kab=("k_above_floor", "mean"))
    m = by.groupby("month").agg(coins=("h", "size"), h=("h", "mean"), k=("k", "mean"), above=("above", "mean"),
                                kab=("kab", "mean"), k_med=("k", "median"))
    m[["h", "k", "k_med"]] *= HY * 100
    m["gap"] = m.h - m.k
    btc = pd.read_parquet(ROOT / "data/hyperliquid/candles_1d/BTC.parquet")
    tcol = "t" if "t" in btc else btc.columns[0]
    btc.index = pd.to_datetime(btc[tcol].astype("int64"), unit="ms", utc=True)
    c = btc["close"].astype(float).resample("MS").last()
    ret = (c.pct_change() * 100).rename("btc_ret")
    ret.index = ret.index.strftime("%Y-%m")
    m = m.join(ret)
    print("| month | coins | HL funding %/yr | HL hours above floor | Kraken funding %/yr (mean) | Kraken (median) | "
          "Kraken hours above HL floor | gap %/yr | BTC return % |")
    print("|---|---|---|---|---|---|---|---|---|")
    for mo, x in m.iterrows():
        print(f"| {mo} | {int(x.coins)} | {x.h:+.1f} | {x.above:.0%} | {x.k:+.1f} | {x.k_med:+.1f} | {x.kab:.0%} | "
              f"{x.gap:+.1f} | {x.btc_ret:+.1f} |")
    # The opportunity a sign-agnostic book (R275's rule) harvests: cross-venue dispersion, by month
    dm = d.groupby(["month", "coin"]).agg(h=("h", "mean"), k=("k", "mean"))
    dm["g"] = (dm.h - dm.k) * HY * 100
    rows_ = []
    for mo, x in dm.groupby(level=0):
        a = x.g.abs().sort_values(ascending=False)
        rows_.append((mo, a.mean(), a.head(20).mean(), (x.g > 0).mean(), x.g[x.g.abs() >= 5].gt(0).mean()))
    print("\n| month | mean abs gap %/yr | top-20 abs gap %/yr | share of coins with HL > Kraken | "
          "share HL > Kraken among abs gap >= 5 |")
    print("|---|---|---|---|---|")
    for mo, a, t20, sh, sh5 in rows_:
        print(f"| {mo} | {a:.1f} | {t20:.1f} | {sh:.0%} | {sh5:.0%} |")
    # Coins with Hyperliquid portfolio-margin collateral against the rest (cause 2)
    pm = {"BTC", "HYPE"}
    d["grp"] = np.where(d.coin.isin(pm), "pm", "rest")
    d["half"] = np.where(d.index < pd.Timestamp("2026-04-15", tz="UTC"), "before 04-15", "after 04-15")
    g = d.groupby(["grp", "half"]).agg(h=("h", "mean"), above=("above", "mean"), k=("k", "mean"))
    g[["h", "k"]] *= HY * 100
    print("\nportfolio-margin coins (BTC, HYPE) against the rest, before and after portfolio margin opened:")
    print(g.round(2).to_string())
    # Correlation of the monthly gap with the market's move
    cc = m[["gap", "btc_ret", "k", "h"]].dropna()
    print(f"\ncorrelation across months: gap vs BTC return {cc.gap.corr(cc.btc_ret):+.2f}; "
          f"Kraken funding vs BTC return {cc.k.corr(cc.btc_ret):+.2f}; HL funding vs BTC return "
          f"{cc.h.corr(cc.btc_ret):+.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
