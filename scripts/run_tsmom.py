"""tsmom_v1 (R237): cross-asset time-series momentum on equity ETFs, FX, metals and bond futures, as set out in
experiments/tsmom_v1/PREREG.md.

usage: python scripts/run_tsmom.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, markets, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "tsmom_v1"
CLASSES = {"equity": ["SPY", "QQQ", "IWM", "DIA"],
           "fx": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "EURJPY=X",
                  "GBPJPY=X", "EURGBP=X", "AUDJPY=X", "USDMXN=X", "USDZAR=X", "USDTRY=X"],
           "metals": ["GC=F", "SI=F", "HG=F"], "bonds": ["ZN=F", "ZB=F"]}
COST = {s: 1e-4 for c in CLASSES.values() for s in c}
COST.update({s: 2e-4 for s in ("EURJPY=X", "GBPJPY=X", "EURGBP=X", "AUDJPY=X")})
COST.update({s: 10e-4 for s in ("USDMXN=X", "USDZAR=X", "USDTRY=X")})
WINDOWS = (("discovery", "2001-01-01", "2012-12-31"), ("validation", "2013-01-01", "2019-12-31"),
           ("holdout", "2020-01-01", "2026-10-19"))
TARGET, CAP = 0.10, 3.0
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def load(sym):
    d = markets.fetch(sym)
    tz = d.attrs.get("tz") or "America/New_York"
    d.index = d.index.tz_convert(tz).normalize().tz_localize(None)
    d = d[~d.index.duplicated(keep="last")]
    return d["adjclose"].astype(float), prereg.sha256_file(markets.ROOT / f"{sym.replace('^', '_').replace('=', '_')}.parquet")


def signals(px, kind):
    """Per series on its own dates: the signal and the 63-day annualized volatility."""
    r = px.pct_change()
    vol = r.rolling(63).std() * np.sqrt(252)
    sg = lambda n: np.sign(px / px.shift(n) - 1)
    if kind == "TS12":
        s = sg(252)
    else:
        s = np.sign(sg(21) + sg(63) + sg(252)).where(sg(252).notna())
    return r, s, vol


def portfolio(px, kind, cm):
    """Daily net, gross, cost and per-class gross on the union calendar."""
    dates = sorted(set().union(*(p.index for p in px.values())))
    U = pd.DatetimeIndex(dates)
    R, S, V = {}, {}, {}
    for k, p in px.items():
        r, s, v = signals(p, kind)
        R[k] = r.reindex(U).fillna(0.0)
        S[k], V[k] = s.reindex(U).ffill(), v.reindex(U).ffill()
    R, S, V = pd.DataFrame(R), pd.DataFrame(S), pd.DataFrame(V)
    month_end = pd.Series(U, index=U).groupby(U.to_period("M")).transform("max").values == U.values
    ok = S.notna() & V.notna() & (V > 0)
    raw = (S * np.minimum(TARGET / V, CAP)).where(ok, 0.0)
    n = ok.sum(axis=1).replace(0, np.nan)
    w = raw.div(n, axis=0).fillna(0.0)
    W = w.where(pd.Series(month_end, index=U), np.nan).ffill().shift(1).fillna(0.0)   # held from the next date
    dW = W.diff().abs().fillna(W.abs())
    cost = (dW * pd.Series(COST)).sum(axis=1) * cm
    contrib = W * R
    gross = contrib.sum(axis=1)
    by_class = pd.DataFrame({c: contrib[[s for s in m if s in contrib]].sum(axis=1) for c, m in CLASSES.items()})
    turnover = dW.sum(axis=1)
    return gross - cost, gross, cost, by_class, turnover, R


def stats_row(net, spy, extra):
    s = events.summary(net.values)
    X = np.column_stack([np.ones(len(net)), spy.values])
    b = float(np.linalg.lstsq(X, net.values, rcond=None)[0][1])
    a = net.values - b * spy.values
    trim = np.sort(net.values)[10:-10]
    return {"days": len(net), "mean_bp_day": float(net.mean() * 1e4), "ann_return": float(net.mean() * 252),
            "ann_vol": float(net.std() * np.sqrt(252)), "t_nw10": float(stats.newey_west_t(net.values, 10)[2]),
            "sharpe_252": float(net.mean() / net.std() * np.sqrt(252)) if net.std() > 0 else np.nan,
            "max_dd": s.get("max_dd", np.nan), "beta_spy": b, "alpha_bp_day": float(a.mean() * 1e4),
            "alpha_t_nw10": float(stats.newey_west_t(a, 10)[2]), "trimmed_bp_day": float(trim.mean() * 1e4),
            **extra}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    px, shas = {}, {}
    for c in CLASSES.values():
        for s in c:
            px[s], shas[s] = load(s)
    log("series", len(px), "first dates", {s: str(p.index[0].date()) for s, p in px.items()})
    rows, stage, by_year, by_class = [], {}, {}, {}
    for kind in ("TS12", "BLEND"):
        res = {cm: portfolio(px, kind, cm) for cm in (1.0, 2.0, 3.0)}
        spy = res[1.0][5]["SPY"]
        passed = True
        for w, a, b in WINDOWS:
            if not passed:
                break
            r1 = None
            for cm, (net, gross, cost, cls, turn, _) in res.items():
                m = (net.index >= a) & (net.index <= b)
                row = {"strategy": kind, "window": w, "cmult": cm,
                       **stats_row(net[m], spy[m], {"gross_bp_day": float(gross[m].mean() * 1e4),
                                                    "cost_bp_day": float(cost[m].mean() * 1e4),
                                                    "turnover_per_year": float(turn[m].sum() / (m.sum() / 252))})}
                rows.append(row)
                if cm == 1.0:
                    r1 = row
                    by_year[f"{kind}/{w}"] = {int(y): float(v * 1e4) for y, v in net[m].groupby(net[m].index.year).mean().items()}
                    by_class[f"{kind}/{w}"] = {c: float(cls[c][m].mean() * 1e4) for c in cls}
                if cm == 2.0:
                    m2 = row["mean_bp_day"]
            if w == "discovery":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and m2 > 0
            elif w == "validation":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5
            else:
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2
            stage[kind] = {"reached": w, "passed": bool(passed)}
            log(kind, w, f"{r1['mean_bp_day']:+.2f} bp/day ({r1['ann_return'] * 100:+.1f}%/yr, vol "
                f"{r1['ann_vol'] * 100:.1f}%) t {r1['t_nw10']:+.2f}, 2x {m2:+.2f}", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.to_csv(out / "strategies.csv", index=False)
    verdict = {"stages": stage, "data_sha256": shas, "by_year_1x_bp_day": by_year, "by_class_1x_bp_day": by_class,
               "holdout_passers": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "holdout_passers", "by_class_1x_bp_day")}, indent=1))


if __name__ == "__main__":
    main()
