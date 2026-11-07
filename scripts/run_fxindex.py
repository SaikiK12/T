"""fxindex_v1 (R239): G10 forex momentum, dollar trend, VIX reversal, Halloween, pre-holiday and the variance risk
premium, as set out in experiments/fxindex_v1/PREREG.md.

usage: python scripts/run_fxindex.py
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

LANE = ROOT / "experiments" / "fxindex_v1"
WINDOWS = (("discovery", "2001-01-01", "2012-12-31"), ("validation", "2013-01-01", "2019-12-31"),
           ("holdout", "2020-01-01", "2026-10-19"))
G10 = {"EUR": ("EURUSD=X", 1), "GBP": ("GBPUSD=X", 1), "AUD": ("AUDUSD=X", 1), "NZD": ("NZDUSD=X", 1),
       "JPY": ("USDJPY=X", -1), "CAD": ("USDCAD=X", -1), "CHF": ("USDCHF=X", -1)}
COST = 1e-4                                                   # one-way at 1x, per unit of weight
UNSCHEDULED = (pd.Timestamp("2001-09-10"), pd.Timestamp("2012-10-26"))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
SHAS = {}


def load(sym):
    d = markets.fetch(sym)
    tz = d.attrs.get("tz") or "America/New_York"
    d.index = d.index.tz_convert(tz).normalize().tz_localize(None)
    d = d[~d.index.duplicated(keep="last")].astype(float)
    SHAS[sym] = prereg.sha256_file(markets.ROOT / f"{sym.replace('^', '_').replace('=', '_')}.parquet")
    return d


def etf(sym):
    d = load(sym)
    out = pd.DataFrame({"o": d.open * d.adjclose / d.close, "c": d.adjclose})
    out["r"] = out.c / out.c.shift(1) - 1
    out["oc"] = out.c / out.o - 1
    return out.iloc[1:]


def month_last(idx):
    """Last bar of each month; the data's final month is incomplete and has none."""
    month = idx.to_period("M")
    pos = pd.Series(np.arange(len(idx)), index=idx).groupby(month).transform(lambda x: np.arange(len(x)))
    n = pd.Series(1, index=idx).groupby(month).transform("size")
    return (pos == n - 1).values & (month != month[-1])


# ---------- forex ----------
def fx_returns():
    """Daily return of each G10 currency vs USD on the union calendar, from the date all seven exist."""
    R = {}
    for c, (sym, sgn) in G10.items():
        px = load(sym)["adjclose"]
        R[c] = px / px.shift(1) - 1 if sgn == 1 else px.shift(1) / px - 1
    start = max(r.index[0] for r in R.values())
    R = pd.DataFrame(R).sort_index()
    return R[R.index >= start].iloc[1:].fillna(0.0)


def fx_book(R, kind, cm):
    P = (1 + R).cumprod()
    if kind == "FXMOM":
        mom = P / P.shift(63) - 1
        rk = mom.rank(axis=1, method="first")
        w = (rk >= 6).astype(float) * 0.5 - (rk <= 2).astype(float) * 0.5
        w = w.where(mom.notna().all(axis=1), 0.0)
    else:
        B = (1 + R.mean(axis=1)).cumprod()
        sg = np.sign(B / B.shift(252) - 1).fillna(0.0)
        w = pd.DataFrame({c: sg / len(R.columns) for c in R.columns})
    W = w.where(pd.Series(month_last(R.index), index=R.index), np.nan).ffill().shift(1).fillna(0.0)
    dW = W.diff().abs().fillna(W.abs())
    cost = dW.sum(axis=1) * COST * cm
    gross = (W * R).sum(axis=1)
    active = W.abs().sum(axis=1) > 0
    first = active.values.argmax()
    sl = slice(first, None)
    return gross.iloc[sl] - cost.iloc[sl], gross.iloc[sl], cost.iloc[sl], dW.sum(axis=1).iloc[sl], W.iloc[sl]


# ---------- US index ----------
def vixrev(d, vix, cm):
    v = vix.reindex(d.index).ffill().shift(1).values
    trig = (d.r.values < -0.01) & (v > 25)
    n, iv = len(d), []
    for t in np.flatnonzero(trig):
        if t + 1 >= n:
            continue
        if iv and iv[-1][0] <= t <= iv[-1][1]:
            iv[-1][1] = max(iv[-1][1], t + 5)
        else:
            iv.append([t + 1, t + 5])
    net, inv = np.zeros(n), np.zeros(n, bool)
    for e, x in iv:
        x = min(x, n - 1)
        net[e] += d.oc.values[e]
        net[e + 1:x + 1] += d.r.values[e + 1:x + 1]
        inv[e:x + 1] = True
        net[e] -= COST * cm
        net[x] -= COST * cm
    return net, inv, trig


def halloween(d, cm):
    idx = d.index
    last = month_last(idx)
    m = idx.month.values
    pos = np.isin(m, (11, 12, 1, 2, 3)) | ((m == 4) & ~last) | ((m == 10) & last)
    held = np.r_[False, pos[:-1]]                             # long over day k if long at the close of k-1
    chg = np.abs(np.diff(np.r_[0, pos.astype(int)]))          # entries and exits at the close of each day
    net = np.where(held, d.r.values, 0.0) - COST * cm * chg
    return net, held


def prehol(d, cm):
    idx = d.index.values.astype("datetime64[D]")
    gap = np.r_[np.busday_count(idx[:-1] + 1, idx[1:]) > 0, False]
    gap &= ~d.index.isin(UNSCHEDULED)
    net = np.where(gap, d.r.values - 2 * COST * cm, 0.0)
    return net, gap


def vrp(spy, vix):
    v = vix.reindex(spy.index).ffill().values
    lr2 = np.log1p(spy.r.values) ** 2
    cs = np.r_[0, np.cumsum(lr2)]
    n = len(lr2)
    fwd = np.full(n, np.nan)
    fwd[:n - 21] = cs[22:n + 1] - cs[1:n - 20]               # sum of lr2[d+1 .. d+21]
    return pd.Series(v ** 2 - 1e4 * fwd * 252 / 21, index=spy.index).dropna()


# ---------- statistics ----------
def trimmed(x):
    s = np.sort(x)
    return float(s[10:-10].mean() * 1e4) if len(s) > 20 else np.nan


def etf_row(net, r, inv, days):
    X = np.column_stack([np.ones(len(r)), r])
    b = float(np.linalg.lstsq(X, net, rcond=None)[0][1])
    a = net - b * r
    s = events.summary(net)
    return {"days": len(net), "mean_bp_day": float(net.mean() * 1e4), "ann_return": float(net.mean() * 252),
            "ann_vol": float(net.std() * np.sqrt(252)), "sharpe": float(net.mean() / net.std() * np.sqrt(252)),
            "max_dd": s.get("max_dd", np.nan), "invested": float(inv.mean()), "beta": b,
            "test_mean_bp_day": float(a.mean() * 1e4), "test_t": float(stats.newey_west_t(a, 10)[2]),
            "trimmed_bp_day": trimmed(a),
            "by_year_bp_day": {int(y): float(a[days.year == y].mean() * 1e4) for y in np.unique(days.year)}}


def fx_row(net, gross, cost, turn, spy_r):
    n = net.values
    sr = spy_r.reindex(net.index).fillna(0.0).values
    b = float(np.linalg.lstsq(np.column_stack([np.ones(len(sr)), sr]), n, rcond=None)[0][1])
    s = events.summary(n)
    yrs = net.index.year
    return {"days": len(n), "mean_bp_day": float(n.mean() * 1e4), "ann_return": float(n.mean() * 260),
            "ann_vol": float(n.std() * np.sqrt(260)), "sharpe": float(n.mean() / n.std() * np.sqrt(260)),
            "max_dd": s.get("max_dd", np.nan), "beta": b, "gross_bp_day": float(gross.mean() * 1e4),
            "cost_bp_day": float(cost.mean() * 1e4), "turnover_per_year": float(turn.sum() / (len(n) / 260)),
            "test_mean_bp_day": float(n.mean() * 1e4), "test_t": float(stats.newey_west_t(n, 10)[2]),
            "trimmed_bp_day": trimmed(n),
            "by_year_bp_day": {int(y): float(n[yrs == y].mean() * 1e4) for y in np.unique(yrs)}}


def decide(w, r1, r2):
    if w == "discovery":
        return r1["test_t"] >= 2 and r2["test_mean_bp_day"] > 0
    if w == "validation":
        return r1["test_mean_bp_day"] > 0 and r1["test_t"] >= 1.5
    return r1["test_mean_bp_day"] > 0 and r1["test_t"] >= 2


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    spy, qqq = etf("SPY"), etf("QQQ")
    vix = load("^VIX")["adjclose"]
    R = fx_returns()
    big = {c: int((R[c].abs() > 0.08).sum()) for c in R}
    log("fx from", R.index[0].date(), "moves above 8%:", big)

    rows, stage, extra = [], {}, {"fx_moves_above_8pct": big, "vixrev_triggers": {}}

    def staged(name, window_row):
        passed = True
        for w, a, b in WINDOWS:
            if not passed:
                break
            res = {cm: window_row(cm, a, b) for cm in (1.0, 2.0, 3.0)}
            if res[1.0] is None:
                log(name, w, "no days")
                break
            for cm, row in res.items():
                rows.append({"strategy": name, "window": w, "cmult": cm, **row})
            passed = bool(decide(w, res[1.0], res[2.0]))
            stage[name] = {"reached": w, "passed": passed}
            r1 = res[1.0]
            log(name, w, f"net {r1['mean_bp_day']:+.2f} bp/day, test {r1['test_mean_bp_day']:+.2f} "
                f"t {r1['test_t']:+.2f} (2x {res[2.0]['test_mean_bp_day']:+.2f})", "PASS" if passed else "stop")

    for kind in ("FXMOM", "DOLLAR"):
        books = {cm: fx_book(R, kind, cm) for cm in (1.0, 2.0, 3.0)}

        def fxw(cm, a, b, books=books):
            net, gross, cost, turn, _ = books[cm]
            m = (net.index >= a) & (net.index <= b)
            return fx_row(net[m], gross[m], cost[m], turn[m], spy.r) if m.sum() > 30 else None
        log(kind, "first position", books[1.0][0].index[0].date())
        staged(kind, fxw)

    for sym, d in (("SPY", spy), ("QQQ", qqq)):
        nets = {cm: vixrev(d, vix, cm) for cm in (1.0, 2.0, 3.0)}

        def vw(cm, a, b, d=d, nets=nets, sym=sym):
            net, inv, trig = nets[cm]
            m = (d.index >= a) & (d.index <= b)
            extra["vixrev_triggers"][f"{sym}/{a[:4]}"] = int(trig[m].sum())
            return etf_row(net[m], d.r.values[m], inv[m], d.index[m])
        staged(f"VIXREV-{sym}", vw)

    for name, fn in (("HALLOWEEN-SPY", halloween), ("PREHOL-SPY", prehol)):
        nets = {cm: fn(spy, cm) for cm in (1.0, 2.0, 3.0)}

        def cw(cm, a, b, nets=nets):
            net, inv = nets[cm]
            m = (spy.index >= a) & (spy.index <= b)
            return etf_row(net[m], spy.r.values[m], inv[m], spy.index[m])
        staged(name, cw)

    vr = vrp(spy, vix)

    def vrw(cm, a, b):
        x = vr[(vr.index >= a) & (vr.index <= b)]
        yrs = x.index.year
        return {"days": len(x), "mean_bp_day": np.nan, "test_mean_bp_day": float(x.mean()),
                "test_t": float(stats.newey_west_t(x.values, 21)[2]), "share_positive": float((x > 0).mean()),
                "median": float(x.median()), "min": float(x.min()),
                "by_year_bp_day": {int(y): float(x[yrs == y].mean()) for y in np.unique(yrs)}}
    staged("VRP", vrw)

    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "strategies.csv", index=False)
    verdict = {"stages": stage, "data_sha256": SHAS, **extra,
               "by_year_1x": {f"{x.strategy}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "holdout_passers": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "holdout_passers", "vixrev_triggers")}, indent=1))


if __name__ == "__main__":
    main()
