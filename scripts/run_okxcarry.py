"""R430 okxcarry_v1 (M484, gate 0): a static cash-and-carry on OKX Europe X-Perps, as set out in
experiments/okxcarry_v1/PREREG.md.

Per coin (BTC, ETH): short the coin's X-Perp and hold the same notional of spot (OKX's index stands in for the spot
price) from T0 = 2026-08-06 16:00 UTC to T1 = 2026-11-09 16:00 UTC, the whole funding history OKX EEA's public API
still served on 2026-11-09. Constant notional; the short receives each realized funding print in (T0, T1].
Basis P&L = index(T1)/index(T0) - mark(T1)/mark(T0), from the closes of OKX 1D bars. Costs: one round trip of both
legs, 0.30% of notional at 1x (0.05% X-Perp taker + 0.10% spot taker, opened and closed), 2x and 3x. Capital =
notional x (1 + 1/L): spot fully paid plus X-Perp margin of 1/L; L = 2 is the primary. Compared with the mean 3-month
T-bill (DTB3, 2-day lag) over the same days.

Inputs, read locally: data/okx_xperp/snap_20261109/{funding,mark_1d,index_1d}.parquet (written by
scripts/fetch_okx_xperp.py, gitignored, hashes frozen in the PREREG) and experiments/okxcarry_v1/inputs/
tbill_dtb3_20261103.csv. Paper only: no account, no order, no network.

usage: python scripts/run_okxcarry.py [--plumbing]
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
from lab import prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "okxcarry_v1"
SNAP = ROOT / "data" / "okx_xperp" / "snap_20261109"
TBILL = LANE / "inputs" / "tbill_dtb3_20261103.csv"
COINS = ("BTC", "ETH")
T0 = pd.Timestamp("2026-08-06 16:00", tz="UTC")     # entry: close of the 1D bar that opens 2026-08-05 16:00 UTC
T1 = pd.Timestamp("2026-11-09 16:00", tz="UTC")     # exit: close of the 1D bar that opens 2026-11-08 16:00 UTC
DAY = pd.Timedelta(days=1)
DAY_MS = 86_400_000
RT_COST = 0.0030               # 1x round trip on notional: 2 x (0.05% X-Perp taker + 0.10% spot taker)
MULTS = (1, 2, 3)
LEVERAGES = (1.0, 2.0, 3.0)
L_PRIMARY = 2.0
EXCESS_BAR = 0.02              # annual excess over the T-bill at 1x costs and L = 2
NEG_SHARE_MAX = 0.20
RISE_MAX = 0.40                # largest rise of the daily mark high above the entry mark
BLOCKS = 3
TBILL_LAG_MS = 2 * DAY_MS
BASELINE = 1e-4                # the X-Perp formula's interest component per 8 h
NW_LAG = 10
XS_MIN_PRINTS = 90             # cross-section summary: X-Perps with at least 30 days of prints in the window
log = lambda *a: print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def ms(t):
    return int(pd.Timestamp(t).value // 10**6)


def load(snap=SNAP):
    return (pd.read_parquet(snap / "funding.parquet"), pd.read_parquet(snap / "mark_1d.parquet"),
            pd.read_parquet(snap / "index_1d.parquet"))


def inst_of(f, coin):
    ids = sorted(x for x in f.instId.unique() if str(x).startswith(coin + "-USD_UM_XPERP-"))
    if len(ids) != 1:
        raise ValueError(f"{coin}: {len(ids)} X-Perps in the funding file; the rule needs exactly one")
    return ids[0]


def prints(f, inst, t0=T0, t1=T1):
    """Funding prints of one instrument in (t0, t1], oldest first. The realized rate, or the funding rate where the
    realized rate is missing (counted in `fallback`)."""
    x = f[f.instId == inst].copy()
    x["t"] = pd.to_datetime(x.fundingTime.astype("int64"), unit="ms", utc=True)
    x = x[(x.t > t0) & (x.t <= t1)].drop_duplicates("t").sort_values("t")
    realized = pd.to_numeric(x.realizedRate, errors="coerce")
    rate = realized.where(realized.notna(), pd.to_numeric(x.fundingRate, errors="coerce"))
    return pd.DataFrame({"t": x.t.to_numpy(), "rate": rate.to_numpy(float), "fallback": realized.isna().to_numpy()})


def close_at(c, inst, t):
    """Close of the OKX 1D bar that closes at t (its open time is t minus one day)."""
    v = c[(c.instId == inst) & (c.ts == ms(t - DAY))].c
    if len(v) != 1:
        raise ValueError(f"{inst}: {len(v)} daily bars close at {t}")
    return float(v.iloc[0])


def bars(c, inst, t0=T0, t1=T1):
    """Daily bars lying inside [t0, t1]: opened at or after t0 and closed at or before t1."""
    return c[(c.instId == inst) & (c.ts >= ms(t0)) & (c.ts <= ms(t1 - DAY))].sort_values("ts")


def tbill_series(path=TBILL):
    t = pd.read_csv(path)
    return list(zip(t.t_ms.astype("int64"), t.pct.astype(float)))


def tbill_mean(series, t0=T0, t1=T1, lag_ms=TBILL_LAG_MS):
    """Mean over the window's days of the latest DTB3 value dated at least `lag_ms` earlier, as an annual fraction."""
    vals = []
    for d in pd.date_range(t0, t1 - DAY, freq="D"):
        known = [v for t, v in series if t <= ms(d) - lag_ms]
        if not known:
            raise ValueError(f"no T-bill value known at {d}")
        vals.append(known[-1] / 100.0)
    return float(np.mean(vals))


def carry(funding, basis, days, tb, m=1, lev=L_PRIMARY, cost=RT_COST):
    """Net on notional after m x the round trip, annualized on capital = notional x (1 + 1/lev), and its excess over
    the T-bill."""
    net = funding + basis - m * cost
    ann = net / (1.0 + 1.0 / lev) * 365.0 / days
    return {"net_on_notional": float(net), "annual_on_capital": float(ann), "excess_over_tbill": float(ann - tb)}


def thirds(rates, k=BLOCKS):
    return [float(np.mean(b)) for b in np.array_split(np.asarray(rates, float), k)]


def daily_path(p, mk, ix, inst, idx, m0, i0, t0=T0, t1=T1, lev=L_PRIMARY, cost=RT_COST):
    """The carry account at each daily close inside the window, as a fraction of capital: realized funding so far plus
    the basis P&L, less the entry half of the round trip (and the exit half at t1). With its drawdown from the running
    peak, the opening capital included."""
    j = bars(mk, inst, t0, t1)[["ts", "c"]].merge(bars(ix, idx, t0, t1)[["ts", "c"]], on="ts", suffixes=("_m", "_i"))
    rows = []
    for ts, cm, ci in j.itertuples(index=False):
        tc = pd.Timestamp(int(ts), unit="ms", tz="UTC") + DAY
        fund = float(p.rate[p.t <= tc].sum())
        basis = ci / i0 - cm / m0
        net = fund + basis - cost / 2 - (cost / 2 if tc >= t1 else 0.0)
        rows.append({"close": tc, "funding": fund, "basis": basis, "equity": net / (1.0 + 1.0 / lev)})
    d = pd.DataFrame(rows, columns=["close", "funding", "basis", "equity"])
    path = np.r_[1.0, 1.0 + d.equity.to_numpy(float)]
    d["drawdown"] = (path / np.maximum.accumulate(path) - 1.0)[1:]
    return d


def static_quantity_funding(p, mk, inst, m0):
    """Reported variant: a fixed coin quantity instead of a fixed notional, so each print is scaled by the latest daily
    mark close known at the print over the entry mark."""
    b = mk[mk.instId == inst][["ts", "c"]].copy()
    b["known"] = pd.to_datetime(b.ts + DAY_MS, unit="ms", utc=True)
    x = pd.merge_asof(p.sort_values("t"), b.sort_values("known"), left_on="t", right_on="known")
    return float((x.rate * x.c / m0).sum())


def daily_nw_t(p, lag=NW_LAG):
    s = p.groupby(p.t.dt.floor("D")).rate.sum()
    return float(stats.newey_west_t(s.to_numpy(float), lag)[2])


def coin_result(f, mk, ix, coin, tb, t0=T0, t1=T1):
    inst, idx = inst_of(f, coin), f"{coin}-USD"
    p = prints(f, inst, t0, t1)
    days = (t1 - t0) / DAY
    m0, m1 = close_at(mk, inst, t0), close_at(mk, inst, t1)
    i0, i1 = close_at(ix, idx, t0), close_at(ix, idx, t1)
    funding, basis = float(p.rate.sum()), i1 / i0 - m1 / m0
    grid = [{"coin": coin, "cost_mult": m, "leverage": lev, **carry(funding, basis, days, tb, m, lev)}
            for m in MULTS for lev in LEVERAGES]
    path = daily_path(p, mk, ix, inst, idx, m0, i0, t0, t1)
    res = {"inst": inst, "index": idx, "prints": int(len(p)), "fallback_prints": int(p.fallback.sum()),
           "first_print": p.t.min(), "last_print": p.t.max(), "days": float(days),
           "mark_entry": m0, "mark_exit": m1, "index_entry": i0, "index_exit": i1,
           "funding_sum": funding, "funding_annual_on_notional": funding * 365.0 / days, "basis_pnl": float(basis),
           "tbill_mean": tb, "thirds_mean_rate": thirds(p.rate),
           "negative_share": float((p.rate < 0).mean()), "baseline_share": float(np.isclose(p.rate, BASELINE,
                                                                                          rtol=0, atol=1e-10).mean()),
           "max_rise": float(bars(mk, inst, t0, t1).h.max() / m0 - 1.0),
           "max_drawdown_L2_1x": float(path.drawdown.min()) if len(path) else 0.0,
           "static_quantity_funding_sum": static_quantity_funding(p, mk, inst, m0),
           "daily_funding_nw_t": daily_nw_t(p)}
    primary = next(g for g in grid if g["cost_mult"] == 1 and g["leverage"] == L_PRIMARY)
    second = next(g for g in grid if g["cost_mult"] == 2 and g["leverage"] == L_PRIMARY)
    res["checks"] = {"excess_1x_L2_ge_2pct": primary["excess_over_tbill"] >= EXCESS_BAR,
                     "excess_2x_L2_gt_0": second["excess_over_tbill"] > 0,
                     "each_third_mean_rate_gt_0": all(v > 0 for v in res["thirds_mean_rate"]),
                     "negative_share_le_20pct": res["negative_share"] <= NEG_SHARE_MAX,
                     "max_rise_lt_40pct": res["max_rise"] < RISE_MAX}
    res["verdict"] = "FORWARD_WORTHY" if all(res["checks"].values()) else "NULL"
    return res, grid, path


def xsection(f, t0=T0, t1=T1, min_prints=XS_MIN_PRINTS):
    """Descriptive only, never traded or decided: each crypto X-Perp's realized funding over its prints in (t0, t1]."""
    rows = []
    for inst in sorted(f.instId.unique()):
        p = prints(f, inst, t0, t1)
        if len(p):
            rows.append({"inst": inst, "prints": int(len(p)), "first_print": p.t.min(),
                         "mean_annual_on_notional": float(p.rate.mean() * 3 * 365),
                         "negative_share": float((p.rate < 0).mean())})
    d = pd.DataFrame(rows).sort_values("mean_annual_on_notional", ascending=False)
    full = d[d.prints >= min_prints]
    q = full.mean_annual_on_notional.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(6).to_dict() if len(full) else {}
    return d, {"instruments": int(len(d)), f"with_at_least_{min_prints}_prints": int(len(full)),
               "quantiles_annual_on_notional": {str(k): v for k, v in q.items()},
               "share_with_mean_below_baseline_annual": float((full.mean_annual_on_notional < BASELINE * 3 * 365 - 1e-9)
                                                              .mean()) if len(full) else None}


def plumbing(f, mk, ix, series):
    for coin in COINS:
        inst = inst_of(f, coin)
        p = prints(f, inst)
        log(f"{coin} {inst}: {len(p)} prints in (T0, T1], first {p.t.min()}, last {p.t.max()}, "
            f"{int(p.fallback.sum())} without realizedRate; {len(bars(mk, inst))} mark bars and "
            f"{len(bars(ix, coin + '-USD'))} index bars inside the window")
        for t in (T0, T1):
            close_at(mk, inst, t), close_at(ix, coin + "-USD", t)
    log(f"T-bill: {len(series)} rows, last dated {pd.Timestamp(series[-1][0], unit='ms').date()}; "
        f"X-Perps in the funding file: {f.instId.nunique()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only")
    a = ap.parse_args()
    if not a.plumbing:
        sha = prereg.verify(LANE / "PREREG.md")
        from scripts.run_clockflow import check_inputs
        log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match")
    f, mk, ix = load()
    series = tbill_series()
    if a.plumbing:
        plumbing(f, mk, ix, series)
        return
    tb = tbill_mean(series)
    out, grids = {"prereg_sha256": sha, "window": [str(T0), str(T1)], "coins": {}}, []
    res_dir = LANE / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    for coin in COINS:
        res, grid, path = coin_result(f, mk, ix, coin, tb)
        out["coins"][coin] = res
        grids += grid
        path.to_csv(res_dir / f"daily_{coin}.csv", index=False, float_format="%.8g")
        prim = next(g for g in grid if g["cost_mult"] == 1 and g["leverage"] == L_PRIMARY)
        log(f"{coin}: {res['verdict']}; funding {res['funding_annual_on_notional']:+.4f}/yr on notional, basis "
            f"{res['basis_pnl']:+.4f}, 1x L2 {prim['annual_on_capital']:+.4f}/yr vs T-bill {tb:.4f}")
    pd.DataFrame(grids).to_csv(res_dir / "coins.csv", index=False, float_format="%.8g")
    xs, out["xsection"] = xsection(f)
    xs.to_csv(res_dir / "xsection.csv", index=False, float_format="%.8g")
    out["lane_verdict"] = ("FORWARD_WORTHY" if any(c["verdict"] == "FORWARD_WORTHY" for c in out["coins"].values())
                           else "NULL")
    (res_dir / "summary.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    log(f"lane verdict {out['lane_verdict']}")


if __name__ == "__main__":
    main()
