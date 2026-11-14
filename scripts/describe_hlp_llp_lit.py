"""Describe the large moves in HLP, LLP and LIT series the lab has already read (R446, R447), plus Lighter's
exchange-level daily metrics (buybacks, fees, liquidations). Descriptive only: no statistic relates one series to
another series's later values (FEAT-003 freezes that test first). Every series stops at --until (default 2026-11-10,
the last gate-0 day of R446 and R447), so no gate-1 return is read.

Inputs:
  --data DIR      a checkout of claude/okx-xperp-data (vaults/llp, vaults/hlp, lit/), as run_dexvault.py takes
  --hlp-hist CSV  optional: HLP's allTime history from claude/hl-vaults-data (hist/dfc2/0xdfc24b...csv)
  --metrics DIR   optional: Lighter exchangeMetrics bodies saved as em_<kind>_all.json (period=all)

usage: python scripts/describe_hlp_llp_lit.py --data DIR [--hlp-hist CSV] [--metrics DIR] [--until YYYY-MM-DD]
Prints one JSON report. Paper only: it reads files and writes nothing.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("run_dexvault", ROOT / "scripts" / "run_dexvault.py")
dv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dv)
rx = dv.rx

TOP = 10


def pct(x):
    return None if x is None or not np.isfinite(x) else round(float(x) * 100, 2)


def drawdowns(level, n=3):
    """Largest peak-to-trough falls of a level series (index: day label): [peak day, trough day, fall, recovered day]."""
    out, peak_i, i = [], 0, 0
    v, d = level.to_numpy(float), list(level.index)
    episodes = []
    while i < len(v):
        if v[i] >= v[peak_i]:
            peak_i = i
            i += 1
            continue
        j, trough_i = i, i
        while j < len(v) and v[j] < v[peak_i]:
            if v[j] < v[trough_i]:
                trough_i = j
            j += 1
        episodes.append((v[trough_i] / v[peak_i] - 1, d[peak_i], d[trough_i], d[j] if j < len(v) else None))
        peak_i, i = j if j < len(v) else peak_i, j
    for fall, p, t, r in sorted(episodes)[:n]:
        out.append({"peak": p, "trough": t, "fall_pct": pct(fall), "recovered": r})
    return out


def extremes(ret, n=TOP):
    s = ret.sort_values()
    return {"largest_losses": [[d, pct(r)] for d, r in s.head(n).items()],
            "largest_gains": [[d, pct(r)] for d, r in s.tail(n)[::-1].items()]}


def monthly(ret):
    """Compounded return by calendar month from daily returns indexed by day label."""
    m = (1 + ret).groupby([d[:7] for d in ret.index]).prod() - 1
    return {k: pct(v) for k, v in m.items()}


def llp(data, until):
    p = dv.llp_prices(data)
    s = pd.Series(p.to_numpy(), index=[rx.day_label(t) for t in p.index])
    s = s[s.index <= until]
    per = dv.llp_periods(p, s.index[0], until)
    ret = pd.Series([r for _, _, r in per], index=[d for d, _, _ in per])
    gaps = [[d, round(g, 2)] for d, g, _ in per if g > 1.5]
    meta = json.loads((Path(data) / "vaults" / "llp" / "meta.json").read_text())
    return {"read_before_in": "R446 (dexvault_v1 gate 0) and R447 (llpstake_v1 gate 0)",
            "first_day": s.index[0], "last_day": s.index[-1], "days": len(ret), "multi_day_periods": gaps,
            "share_price_first": float(s.iloc[0]), "share_price_last": float(s.iloc[-1]),
            "total_return_pct": pct(s.iloc[-1] / s.iloc[0] - 1),
            "daily_sd_pct": pct(ret.std(ddof=1)), "days_up": int((ret > 0).sum()), "days_down": int((ret < 0).sum()),
            "days_below_minus_1pct": int((ret < -0.01).sum()), "days_above_plus_1pct": int((ret > 0.01).sum()),
            **extremes(ret), "monthly_pct": monthly(ret), "drawdowns": drawdowns(s, 5),
            "meta_single_point": {"fetched": rx.day_label(meta["fetched_ms"]), "total_shares": meta["total_shares"],
                                  "operator_fee": meta["operator_fee"],
                                  "usdc_at_last_price": round(meta["total_shares"] * float(s.iloc[-1]))}}


def hlp_alltime(df, until, source):
    w = df.sort_values("ts")
    w = w[[rx.day_label(t) <= until for t in w.ts]]
    t, av, pnl = w.ts.to_numpy(np.int64), w.account_value.to_numpy(float), w.pnl.to_numpy(float)
    rows = []
    for i in range(1, len(t)):
        if av[i - 1] > 0:
            rows.append((rx.day_label(t[i]), (t[i] - t[i - 1]) / dv.DAY, (pnl[i] - pnl[i - 1]) / av[i - 1],
                         pnl[i] - pnl[i - 1]))
    ret = pd.Series([r[2] for r in rows], index=[r[0] for r in rows])
    usd = pd.Series([r[3] for r in rows], index=[r[0] for r in rows])
    idx = (1 + ret).cumprod()
    peak_av = int(np.argmax(av))
    by_year = (1 + ret).groupby([d[:4] for d in ret.index]).prod() - 1
    return {"source": source, "read_before_in": "M285 (vaultDetails history) and R446 (dexvault_v1 gate 0, from 2025-01-01)",
            "points": len(t), "first_day": rx.day_label(t[0]), "last_day": rx.day_label(t[-1]),
            "median_step_days": float(np.median([r[1] for r in rows])),
            "account_value_last": round(av[-1]), "account_value_peak": round(av[peak_av]),
            "account_value_peak_day": rx.day_label(t[peak_av]), "pnl_cum_last": round(pnl[-1]),
            **extremes(ret), "largest_usd_losses": [[d, round(v)] for d, v in usd.sort_values().head(5).items()],
            "largest_usd_gains": [[d, round(v)] for d, v in usd.sort_values().tail(5)[::-1].items()],
            "by_year_pct": {k: pct(v) for k, v in by_year.items()}, "drawdowns": drawdowns(idx, 3)}


def lit(data, until):
    c = rx.read_dir(Path(data) / "lit" / "perp_candles_1d").drop_duplicates("ts").sort_values("ts")
    c["day"] = [rx.day_label(t) for t in c.ts]
    c = c[c.day <= until].set_index("day")
    close = c.close.astype(float)
    ret = close.pct_change().dropna()
    f = rx.read_dir(Path(data) / "lit" / "perp_funding").drop_duplicates("ts").sort_values("ts")
    f["day"] = [rx.day_label(t) for t in f.ts]
    f = f[f.day <= until]
    # record_lit_hedge.py stores `rate` signed: + when longs pay, - when shorts pay (hourly fraction)
    signed = f.rate.astype(float).to_numpy()
    fm = pd.Series(signed, index=[d[:7] for d in f.day]).groupby(level=0).sum()
    hi, lo = c.high.astype(float), c.low.astype(float)
    spot = rx.read_dir(Path(data) / "lit" / "spot_candles_1d").drop_duplicates("ts").sort_values("ts")
    spot["day"] = [rx.day_label(t) for t in spot.ts]
    spot = spot[spot.day <= until]
    return {"read_before_in": "R447 (llpstake_v1 gate 0: LIT perp, LIT/USDC spot and hourly funding)",
            "first_day": close.index[0], "last_day": close.index[-1], "close_first": float(close.iloc[0]),
            "close_last": float(close.iloc[-1]), "high_max": float(hi.max()), "high_max_day": hi.idxmax(),
            "low_min": float(lo.min()), "low_min_day": lo.idxmin(), "close_max": float(close.max()),
            "close_max_day": close.idxmax(), "close_min": float(close.min()), "close_min_day": close.idxmin(),
            "rise_from_close_min_pct": pct(close.iloc[-1] / close.min() - 1),
            "daily_sd_pct": pct(ret.std(ddof=1)), "days_abs_move_over_10pct": int((ret.abs() > 0.10).sum()),
            **extremes(ret), "monthly_pct": monthly(ret), "drawdowns": drawdowns(close, 3),
            "funding_long_pays_pct_by_month": {k: pct(v) for k, v in fm.items()},
            "funding_hours": len(f), "funding_long_pays_ann_pct": pct(signed.mean() * 24 * 365),
            "perp_quote_volume_median_usd": round(float(c.quote_volume.astype(float).median())),
            "spot_quote_volume_median_usd": round(float(spot.quote_volume.astype(float).median()))}


def metric(path):
    d = json.loads(Path(path).read_text())["metrics"]
    s = pd.Series([float(x["data"]) for x in d], index=[rx.day_label(int(x["timestamp"]) * 1000) for x in d])
    return s[~s.index.duplicated(keep="last")].sort_index()


def lighter_metrics(folder, until, circulating=None):
    m = {k: metric(Path(folder) / f"em_{k}_all.json") for k in
         ("buyback", "buyback_usdc", "taker_fee", "maker_fee", "liquidation_fee", "liquidation_volume", "volume",
          "open_interest", "inflow", "outflow") if (Path(folder) / f"em_{k}_all.json").exists()}
    m = {k: v[v.index <= until] for k, v in m.items()}
    out = {"read_before_in": "none (first read here)", "until": until}
    if "buyback" in m:
        bb, bu = m["buyback"], m["buyback_usdc"]
        mon = pd.DataFrame({"lit": bb.groupby([d[:7] for d in bb.index]).sum(),
                            "usdc": bu.groupby([d[:7] for d in bu.index]).sum()})
        fees = None
        if "taker_fee" in m and "maker_fee" in m:
            fe = m["taker_fee"].add(m["maker_fee"], fill_value=0)
            fees = fe.groupby([d[:7] for d in fe.index]).sum()
        out["buyback"] = {
            "first_day": bb.index[0], "last_day": bb.index[-1], "days": len(bb), "lit_total": round(bb.sum()),
            "usdc_total": round(bu.sum()), "avg_price": round(bu.sum() / bb.sum(), 4),
            "lit_per_day_median": round(float(bb.median())), "usdc_per_day_median": round(float(bu.median())),
            "largest_days_usdc": [[d, round(v)] for d, v in bu.sort_values().tail(8)[::-1].items()],
            "share_of_circulating_pct": pct(bb.sum() / circulating) if circulating else None,
            "monthly": {k: {"lit": round(r.lit), "usdc": round(r.usdc),
                            "fees_usdc": None if fees is None or k not in fees.index else round(float(fees[k])),
                            "buyback_over_fees_pct": None if fees is None or k not in fees.index or not fees[k]
                            else pct(r.usdc / fees[k])}
                        for k, r in mon.iterrows()}}
    for k in ("taker_fee", "maker_fee", "liquidation_fee", "liquidation_volume", "volume", "open_interest"):
        if k in m:
            s = m[k]
            out[k] = {"first_day": s.index[0], "last_day": s.index[-1],
                      "monthly_sum" if k != "open_interest" else "month_end":
                      {kk: round(float(vv)) for kk, vv in (s.groupby([d[:7] for d in s.index]).sum() if k != "open_interest"
                                                           else s.groupby([d[:7] for d in s.index]).last()).items()},
                      "largest_days": [[d, round(v)] for d, v in s.sort_values().tail(5)[::-1].items()]}
    if "inflow" in m and "outflow" in m:
        net = m["inflow"].sub(m["outflow"], fill_value=0)
        out["net_inflow"] = {"largest_outflow_days": [[d, round(v)] for d, v in net.sort_values().head(5).items()],
                             "largest_inflow_days": [[d, round(v)] for d, v in net.sort_values().tail(5)[::-1].items()]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--hlp-hist")
    ap.add_argument("--metrics")
    ap.add_argument("--until", default="2026-11-10")
    ap.add_argument("--circulating", type=float, help="LIT circulating supply for the buyback share (single point)")
    a = ap.parse_args()
    if a.until > "2026-11-10":
        raise SystemExit("HLP and LLP returns after 2026-11-10 are gate-1 windows of R446/R447; not read here")
    rep = {"until": a.until, "data_head": rx.data_head(a.data), "llp": llp(a.data, a.until)}
    snaps = dv.hlp_snaps(a.data)
    if snaps:
        w = snaps[0][1]
        rep["hlp_snapshot_alltime"] = hlp_alltime(w[w.window == "allTime"], a.until,
                                                  f"vaults/hlp/snap/{snaps[0][0]}.csv allTime")
    if a.hlp_hist:
        rep["hlp_hist_alltime"] = hlp_alltime(pd.read_csv(a.hlp_hist), a.until, a.hlp_hist)
    rep["lit"] = lit(a.data, a.until)
    if a.metrics:
        rep["lighter_metrics"] = lighter_metrics(a.metrics, a.until, a.circulating)
    print(json.dumps(rep, indent=1, default=float))


if __name__ == "__main__":
    main()
