"""Cross-venue factors for qx factors (R276 xvfac_v1): what another venue says about a Binance perp at 00:00 UTC.

One row per decision day and coin: t = the open of the hourly bar ending at 00:00 UTC (entry at its close), sym = the
Binance perp. A coin is eligible on day d when its Binance bar ending at day d traded and it ranks in the top `TOP` by
Binance quote volume over the last 30 days. Every value uses only bars and settlements at or before day d:

| factor | definition |
|---|---|
| fund_gap_3d / fund_gap_7d | Binance funding settled over the last 3 / 7 days minus Gate's (Binance longs paying more than Gate's) |
| hl_fund_gap_3d | Binance minus Hyperliquid, last 3 days |
| price_gap_dev | ln(Binance close / Gate close) at day d minus its median over the last 30 days (needs 20) |
| vshare_chg | ln(Gate volume 7 d / 30 d) minus ln(Binance volume 7 d / 30 d): attention moving to Gate |
| bn_fund_3d | Binance funding over the last 3 days alone (the known level, as the reference) |

A funding window counts only if the venue's history covers it and it settled at least once in it. Rows before
2021-01-01 are never read (the reserved 2020 sample).

usage: python scripts/xvenue_factors.py SYMBOLS.csv OUT.parquet
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data  # noqa: E402

T0 = 1_609_459_200_000                 # 2021-01-01
END = 1_790_812_800_000                # 2026-10-01 00:00 UTC, the last instant of the archive
H, DAY = 3_600_000, 86_400_000
ND = (END - T0) // DAY + 1
TOP = 150
D = data.ROOT


def daily_bars(path, vol, bar_h=1):
    """(close at each day instant if the bar ending there traded, volume per day (T_{d-1}, T_d])."""
    df = pd.read_parquet(path, columns=["t", "close", vol])
    df = df[(df.t >= T0) & np.isfinite(df.close) & (df.close > 0)]
    end = df.t.values + bar_h * H
    d = (end - T0 + DAY - 1) // DAY
    ok = (d >= 0) & (d < ND)
    close = np.full(ND, np.nan)
    volume = np.zeros(ND)
    traded = (df[vol].values > 0) & ok
    at = traded & (end == T0 + d * DAY)
    close[d[at]] = df.close.values[at]
    np.add.at(volume, d[ok], np.nan_to_num(df[vol].values[ok]))
    return close, volume


def daily_funding(path):
    """(funding per day, settlements per day, first day with a settlement)."""
    f = np.zeros(ND)
    n = np.zeros(ND)
    if not path.exists():
        return f, n, ND
    df = pd.read_parquet(path, columns=["t", "rate"])
    df = df[(df.t >= T0) & np.isfinite(df.rate)]
    th = df.t.values - df.t.values % H
    d = (th - T0 + DAY - 1) // DAY
    ok = (d >= 1) & (d < ND)
    np.add.at(f, d[ok], df.rate.values[ok])
    np.add.at(n, d[ok], 1)
    first = int(d[ok].min()) if ok.any() else ND
    return f, n, first


def window(f, n, first, L):
    """Funding over (day d - L, day d] for every d, NaN where the history does not cover it."""
    cf, cn = np.concatenate([[0], np.cumsum(f)]), np.concatenate([[0], np.cumsum(n)])
    out = np.full(ND, np.nan)
    d = np.arange(L, ND)
    s = cf[d + 1] - cf[d + 1 - L]
    c = cn[d + 1] - cn[d + 1 - L]
    good = (first <= d - L + 1) & (c > 0)
    out[d[good]] = s[good]
    return out


def roll_sum(x, w):
    c = np.concatenate([[0], np.cumsum(x)])
    out = np.full(len(x), np.nan)
    out[w - 1:] = c[w:] - c[:-w]
    return out


def coin(row):
    b, g, h = row["binance"], row["gate"], row["hyperliquid"]
    bc, bv = daily_bars(D / "klines_1h" / f"{b}.parquet", "quote_volume")
    bf = daily_funding(D / "fundingRate" / f"{b}.parquet")
    out = {"bn_close": bc, "bn_qv30": roll_sum(bv, 30), "bn_fund_3d": window(*bf, 3)}
    _, bvol = daily_bars(D / "klines_1h" / f"{b}.parquet", "volume")
    if g:
        gc, gv = daily_bars(D / "gate_hist" / "open" / "candlesticks_1h" / f"{g}.parquet", "vol_contracts")
        gf = daily_funding(D / "gate_hist" / "open" / "funding_applies" / f"{g}.parquet")
        out["fund_gap_3d"] = out["bn_fund_3d"] - window(*gf, 3)
        out["fund_gap_7d"] = window(*bf, 7) - window(*gf, 7)
        gap = np.log(bc / gc)
        med = pd.Series(gap).rolling(30, min_periods=20).median().values
        out["price_gap_dev"] = gap - med
        with np.errstate(divide="ignore", invalid="ignore"):
            out["vshare_chg"] = (np.log(roll_sum(gv, 7) / 7 / (roll_sum(gv, 30) / 30))
                                 - np.log(roll_sum(bvol, 7) / 7 / (roll_sum(bvol, 30) / 30)))
    if h:
        hf = daily_funding(D / "hyperliquid" / "funding" / f"{h}.parquet")
        out["hl_fund_gap_3d"] = out["bn_fund_3d"] - window(*hf, 3)
    return out


FACTORS = ("fund_gap_3d", "fund_gap_7d", "hl_fund_gap_3d", "price_gap_dev", "vshare_chg", "bn_fund_3d")


def build(symbols):
    rows = pd.read_csv(symbols, dtype=str).fillna("")
    rows = rows[rows.binance != ""]
    per = {r["binance"]: coin(r) for _, r in rows.iterrows()}
    syms = sorted(per)
    qv = np.vstack([per[s]["bn_qv30"] for s in syms])
    traded = np.vstack([np.isfinite(per[s]["bn_close"]) for s in syms])
    out = []
    for d in range(31, ND):
        q = np.where(traded[:, d] & np.isfinite(qv[:, d]), qv[:, d], -np.inf)
        order = np.argsort(-q, kind="stable")[:TOP]
        for i in order:
            if not np.isfinite(q[i]):
                continue
            rec = {"t": T0 + d * DAY - H, "sym": syms[i]}
            for f in FACTORS:
                v = per[syms[i]].get(f)
                rec[f] = float(v[d]) if v is not None and np.isfinite(v[d]) else np.nan
            out.append(rec)
    df = pd.DataFrame(out, columns=["t", "sym", *FACTORS])
    return df.sort_values(["t", "sym"], kind="stable").reset_index(drop=True)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    df = build(sys.argv[1])
    df.to_parquet(sys.argv[2], index=False)
    print(f"{len(df)} rows, {df.t.nunique()} days, {df.sym.nunique()} coins; non-missing per factor: "
          + ", ".join(f"{f} {df[f].notna().sum()}" for f in FACTORS))


if __name__ == "__main__":
    main()
