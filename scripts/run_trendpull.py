"""trendpull_v1 (R284): Visser's trend pullback on 10 world indices and every Binance perp, long after the 63-day rate
of change resets near zero inside a rising 200-day trend, as set out in experiments/trendpull_v1/PREREG.md (M277).

usage: python scripts/run_trendpull.py
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sst

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import data, prereg  # noqa: E402

LANE = ROOT / "experiments" / "trendpull_v1"
IDX = ["^GSPC", "^NDX", "^DJI", "^RUT", "^GDAXI", "^FTSE", "^N225", "^HSI", "^STOXX50E", "^AXJO"]
END = "2026-09-30"
KS = (0.25, 0.5)
HOLDS = {"IDX": (63, 21), "CRYPTO": (90, 30)}
COST = {"IDX": 1e-4, "CRYPTO": 7e-4}                      # one-way at 1x
SPLIT = {"IDX": "2014-01-01", "CRYPTO": "2024-01-01"}
TRIALS = 8
DAY_MS = 86_400_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
SHAS = {}


def idx_bars(sym):
    import run_chartxm as cx                              # R247's loader, unchanged
    d = cx.bars(sym)
    SHAS[f"yahoo/{sym}"] = cx.SHAS[sym]
    d = d[d.index <= END]
    return pd.DataFrame({"open": d.open.values, "close": d.close.values}, index=d.index)


def crypto_bars(path):
    SHAS[f"klines_1h/{path.stem}"] = prereg.sha256_file(path)
    k = pd.read_parquet(path, columns=["t", "open", "close", "count"])
    lo, hi = pd.Timestamp("2021-01-01", tz="UTC").value // 10**6, pd.Timestamp(END, tz="UTC").value // 10**6 + DAY_MS
    k = k[(k.t >= lo) & (k.t < hi)].sort_values("t")         # 2020 rows dropped before any use
    if k.empty:
        return None
    day = (k.t.values // DAY_MS).astype(np.int64)
    g = k.assign(day=day).groupby("day", sort=True)
    d = pd.DataFrame({"open": g.open.first(), "close": g.close.last(), "count": g["count"].sum()})
    d = d[d["count"] > 0]
    d.index = pd.to_datetime(d.index * DAY_MS, unit="ms")
    return d[["open", "close"]]


def funding_cum(sym):
    p = data.ROOT / "fundingRate" / f"{sym}.parquet"
    if not p.exists():
        return None
    SHAS[f"fundingRate/{sym}"] = prereg.sha256_file(p)
    f = pd.read_parquet(p, columns=["t", "rate"])
    f = f[f.t >= pd.Timestamp("2021-01-01", tz="UTC").value // 10**6].sort_values("t")
    return f.t.values.astype(np.int64), np.concatenate([[0.0], np.cumsum(f.rate.values.astype(float))])


def features(close):
    """SMA200, its value 20 rows back, ROC63, the 63-row peak of ROC63 before D and the 252-row q80 before D."""
    c = pd.Series(close)
    sma = c.rolling(200, min_periods=200).mean()
    roc = c / c.shift(63) - 1
    peak = roc.shift(1).rolling(63, min_periods=63).max()
    q80 = roc.shift(1).rolling(252, min_periods=252).quantile(0.8, interpolation="linear")
    return sma.values, sma.shift(20).values, roc.values, peak.values, q80.values


def signals(close, k):
    sma, sma20, roc, peak, q80 = features(close)
    with np.errstate(invalid="ignore"):
        sig = (close > sma) & (sma > sma20) & (peak > 0) & (peak >= q80) & (np.abs(roc) <= k * peak)
    eligible = ~np.isnan(sma20) & ~np.isnan(q80) & ~np.isnan(peak) & ~np.isnan(roc)
    trend = eligible & (close > sma) & (sma > sma20)
    return np.nan_to_num(sig, nan=0).astype(bool) & eligible, eligible, trend


def hold_returns(d, H, fund):
    """Return of entering at row i+1's open and exiting at row i+H's close, net of funding, for every row i (NaN when
    the hold runs past the data)."""
    n = len(d)
    o, c = d.open.values, d.close.values
    r = np.full(n, np.nan)
    i = np.arange(n - H)
    r[i] = c[i + H] / o[i + 1] - 1
    if fund is not None:
        ft, cum = fund
        t0 = (d.index.values.astype("datetime64[ms]").astype(np.int64))       # 00:00 UTC of each row's day
        a = np.searchsorted(ft, t0[i + 1], side="right")
        b = np.searchsorted(ft, t0[i + H] + DAY_MS, side="right")
        r[i] -= cum[b] - cum[a]
    return r


def trades(sig, H):
    """Rows acted on: a signal after the previous trade's exit row."""
    out, free = [], -1
    for i in np.flatnonzero(sig):
        if i > free:
            out.append(i)
            free = i + H
    return np.array(out, dtype=int)


def cluster_t(x, groups):
    x = np.asarray(x, float)
    g = pd.Series(x - x.mean()).groupby(np.asarray(groups)).sum().values
    G, n = len(g), len(x)
    if G < 2:
        return float("nan"), G
    var = (g ** 2).sum() * G / (G - 1) / n ** 2                # CR1: cluster sums, small-sample factor G/(G-1)
    return float(x.mean() / np.sqrt(var)), G


def run_cell(assets, univ, k, H):
    rows, base_trend = [], []
    for name, (d, fund) in assets.items():
        if len(d) < 252 + 64 + H:
            continue
        r = hold_returns(d, H, fund if univ == "CRYPTO" else None)
        sig, elig, trend = signals(d.close.values, k)
        ok = elig & ~np.isnan(r)
        if not ok.any():
            continue
        m = r[ok].mean()
        base_trend += list(r[ok & trend] - m)
        for i in trades(sig & ok, H):
            rows.append({"universe": univ, "k": k, "H": H, "asset": name, "entry": d.index[i + 1].date(),
                         "exit": d.index[i + H].date(), "ret": r[i], "excess": r[i] - m})
    t = pd.DataFrame(rows)
    c = 2 * COST[univ]
    out = {"universe": univ, "k": k, "H": H, "trades": len(t)}
    if t.empty:
        return out | {"p": 1.0, "pass": False}, t
    q = pd.PeriodIndex(pd.to_datetime(t.entry), freq="Q").astype(str)
    tt, G = cluster_t(t.excess.values, q)
    p = float(sst.t.sf(tt, G - 1)) if G > 1 else 1.0
    early = t[pd.to_datetime(t.entry) < SPLIT[univ]]
    late = t[pd.to_datetime(t.entry) >= SPLIT[univ]]
    tops = np.sort(t.excess.values)[::-1][:5].sum()
    out |= {"assets": t.asset.nunique(), "quarters": G,
            "net1_pct": (t.ret.mean() - c) * 100, "net2_pct": (t.ret.mean() - 2 * c) * 100,
            "net3_pct": (t.ret.mean() - 3 * c) * 100, "excess_pct": t.excess.mean() * 100, "t": tt, "p": p,
            "hit": float((t.ret - c > 0).mean()), "median_pct": (t.ret.median() - c) * 100,
            "worst_pct": (t.ret.min() - c) * 100,
            "early_n": len(early), "early_excess_pct": early.excess.mean() * 100 if len(early) else float("nan"),
            "late_n": len(late), "late_excess_pct": late.excess.mean() * 100 if len(late) else float("nan"),
            "top5_share": float(tops / t.excess.sum()) if t.excess.sum() > 0 else float("nan"),
            "trend_state_excess_pct": float(np.mean(base_trend)) * 100 if base_trend else float("nan"),
            "per_year": {str(y): int(n) for y, n in pd.to_datetime(t.entry).dt.year.value_counts().sort_index().items()}}
    out["pass"] = bool(p <= 0.05 / TRIALS and out["net2_pct"] > 0 and out["early_excess_pct"] > 0
                       and out["late_excess_pct"] > 0)
    return out, t


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}")
    uni = {"IDX": {s: (idx_bars(s), None) for s in IDX}, "CRYPTO": {}}
    files = sorted((data.ROOT / "klines_1h").glob("*.parquet"))
    for i, p in enumerate(files, 1):
        d = crypto_bars(p)
        if d is not None and len(d) >= 252 + 64 + 30:
            uni["CRYPTO"][p.stem] = (d, funding_cum(p.stem))
        if i % 200 == 0:
            log(f"{i}/{len(files)} perps read")
    log(f"{len(uni['CRYPTO'])} perps with enough history")
    cells, alltr = [], []
    for univ in ("IDX", "CRYPTO"):
        for k in KS:
            for H in HOLDS[univ]:
                row, t = run_cell(uni[univ], univ, k, H)
                cells.append(row)
                alltr.append(t)
                log(f"{univ:6s} k {k} H {H:2d}: {row['trades']:4d} trades, net1 {row.get('net1_pct', float('nan')):6.2f}%"
                    f" excess {row.get('excess_pct', float('nan')):6.2f}% t {row.get('t', float('nan')):5.2f} "
                    f"p {row['p']:.4f}{'  PASS' if row['pass'] else ''}")
    verdict = "PARTIAL" if any(c["pass"] for c in cells) else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{k: v for k, v in c.items() if k != "per_year"} for c in cells]).to_csv(
        out / "cells.csv", index=False, float_format="%.6g")
    pd.concat(alltr).to_csv(out / "trades.csv", index=False, float_format="%.6g")
    pd.Series(SHAS, name="sha256").rename_axis("file").to_csv(out / "inputs.csv")
    combined = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(SHAS.items())).encode()).hexdigest()
    summary = {"rid": "R284", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha,
               "per_year": {f"{c['universe']} k{c['k']} H{c['H']}": c.get("per_year", {}) for c in cells},
               "inputs": len(SHAS), "inputs_combined_sha256": combined}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}")
    return summary


if __name__ == "__main__":
    main()
