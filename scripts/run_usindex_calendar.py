"""usindex_calendar_v1 (R235): turn-of-month and overnight drift on SPY and QQQ, as alpha against buy-and-hold of the
same ETF, as set out in experiments/usindex_calendar_v1/PREREG.md.

usage: python scripts/run_usindex_calendar.py
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

LANE = ROOT / "experiments" / "usindex_calendar_v1"
WINDOWS = (("discovery", "2000-01-03", "2012-12-31"), ("validation", "2013-01-01", "2019-12-31"),
           ("holdout", "2020-01-01", "2026-10-19"))
COST = 1e-4                                                   # one-way at 1x
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def load(sym):
    p = markets.ROOT / f"{sym}.parquet"
    d = markets.fetch(sym)
    d.index = d.index.tz_convert("America/New_York").normalize().tz_localize(None)
    f = d.adjclose / d.close
    out = pd.DataFrame({"o": d.open * f, "c": d.adjclose})
    out["r"] = out.c / out.c.shift(1) - 1
    out["on"] = out.o / out.c.shift(1) - 1
    out["id"] = out.c / out.o - 1
    return out.iloc[1:], prereg.sha256_file(p)


def tom_days(idx):
    """Boolean per bar: last trading day of a month or one of the first three of the next; and the exit days."""
    month = idx.to_period("M")
    pos = pd.Series(np.arange(len(idx)), index=idx).groupby(month).transform(lambda x: np.arange(len(x)))
    n = pd.Series(1, index=idx).groupby(month).transform("size")
    last = (pos == n - 1).values & (month != month[-1])       # the data's final month is incomplete
    first3 = (pos <= 2).values
    inv = last | first3
    inv[:np.argmax(last)] = False                              # start with the first full turn
    exit_ = (pos == 2).values & inv
    return inv, exit_


def strategy(d, rule, cm):
    """Daily net return and invested flag of a rule over all bars."""
    if rule == "TOM":
        inv, exit_ = tom_days(d.index)
        entry = inv & ~np.roll(inv, 1)
        net = np.where(inv, d.r.values, 0.0) - COST * cm * (entry.astype(float) + exit_.astype(float))
        return net, inv
    net = d.on.values - 2 * COST * cm
    return net, np.ones(len(d), bool)


def stats_row(net, r, inv, days):
    X = np.column_stack([np.ones(len(r)), r])
    b = float(np.linalg.lstsq(X, net, rcond=None)[0][1])
    a = net - b * r
    s, sb = events.summary(net), events.summary(r)
    trim = np.sort(a)[10:-10]
    year = days.year
    return {"days": len(net), "mean_bp_day": float(net.mean() * 1e4), "sharpe": s.get("sharpe", np.nan),
            "max_dd": s.get("max_dd", np.nan), "invested": float(inv.mean()), "beta": b,
            "alpha_bp_day": float(a.mean() * 1e4), "alpha_t_nw10": float(stats.newey_west_t(a, 10)[2]),
            "alpha_trimmed_bp_day": float(trim.mean() * 1e4),
            "bh_mean_bp_day": float(r.mean() * 1e4), "bh_sharpe": sb.get("sharpe", np.nan),
            "bh_max_dd": sb.get("max_dd", np.nan),
            "alpha_by_year_bp_day": {int(y): float(a[year == y].mean() * 1e4) for y in np.unique(year)}}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    data, shas = {}, {}
    for s in ("SPY", "QQQ"):
        data[s], shas[s] = load(s)
    log("data sha256", json.dumps(shas))
    rows, stage = [], {}
    for rule in ("TOM", "ON"):
        for s, d in data.items():
            name = f"{rule}-{s}"
            nets = {cm: strategy(d, rule, cm) for cm in (1.0, 2.0, 3.0)}
            passed = True
            for w, a, b in WINDOWS:
                if not passed:
                    break
                m = (d.index >= a) & (d.index <= b)
                res = {}
                for cm, (net, inv) in nets.items():
                    row = {"strategy": name, "window": w, "cmult": cm,
                           **stats_row(net[m], d.r.values[m], inv[m], d.index[m])}
                    if rule == "ON":
                        row["intraday_bp_day"] = float(d["id"].values[m].mean() * 1e4)
                    rows.append(row)
                    res[cm] = row
                r1 = res[1.0]
                if w == "discovery":
                    passed = r1["alpha_t_nw10"] >= 2 and res[2.0]["alpha_bp_day"] > 0
                elif w == "validation":
                    passed = r1["alpha_bp_day"] > 0 and r1["alpha_t_nw10"] >= 1.5
                else:
                    passed = r1["alpha_bp_day"] > 0 and r1["alpha_t_nw10"] >= 2
                stage[name] = {"reached": w, "passed": bool(passed)}
                log(name, w, f"net {r1['mean_bp_day']:+.2f} bp/day, alpha {r1['alpha_bp_day']:+.2f} "
                    f"t {r1['alpha_t_nw10']:+.2f} (2x {res[2.0]['alpha_bp_day']:+.2f})", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="alpha_by_year_bp_day").to_csv(out / "strategies.csv", index=False)
    verdict = {"stages": stage, "data_sha256": shas,
               "alpha_by_year_1x": {f"{x.strategy}/{x.window}": x.alpha_by_year_bp_day
                                    for x in df[df.cmult == 1.0].itertuples()},
               "holdout_passers": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="alpha_by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "holdout_passers")}, indent=1))


if __name__ == "__main__":
    main()
