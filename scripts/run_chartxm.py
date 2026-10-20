"""chartxm_v1 (R247): R243's seven chart rules (run_chartist.states, unchanged) on daily bars of 11 forex pairs and 10
world equity indices, equal-weight books per group, as set out in experiments/chartxm_v1/PREREG.md. The holdout
(2020-01..2026-10-19) is read once, for validation passers only.

usage: python scripts/run_chartxm.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import events, markets, prereg, stats  # noqa: E402
from run_chartist import states  # noqa: E402
from run_fxindex import WINDOWS, decide  # noqa: E402

LANE = ROOT / "experiments" / "chartxm_v1"
GROUPS = {"FX": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "USDJPY=X", "USDCAD=X", "USDCHF=X", "EURGBP=X",
                 "EURJPY=X", "GBPJPY=X", "AUDJPY=X"],
          "IDX": ["^GSPC", "^NDX", "^DJI", "^RUT", "^GDAXI", "^FTSE", "^N225", "^HSI", "^STOXX50E", "^AXJO"]}
END = "2026-10-19"
COST = 1e-4                                                   # one-way at 1x, per unit of weight
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
SHAS = {}


def bars(sym):
    d = markets.fetch(sym)
    tz = d.attrs.get("tz") or "America/New_York"
    d.index = d.index.tz_convert(tz).normalize().tz_localize(None)
    d = d[~d.index.duplicated(keep="last")].astype(float)
    d = d[(d.index <= END) & (d[["open", "high", "low", "close"]] > 0).all(axis=1)]
    SHAS[sym] = prereg.sha256_file(markets.ROOT / f"{sym.replace('^', '_').replace('=', '_')}.parquet")
    return d


def asset_states(d):
    """{rule: Series of states} and the close-to-close return Series, on the asset's own calendar."""
    b = {k: d[c].values[:, None] for k, c in (("o", "open"), ("h", "high"), ("l", "low"), ("c", "close"))}
    prev = {k: np.vstack([[[np.nan]], b[k][:-1]]) for k in ("h", "l", "c")}
    st = {rule: pd.Series(x[:, 0], index=d.index) for rule, x in states(b, prev).items()}
    return st, d.close / d.close.shift(1) - 1


def book(S, R, cm):
    """S, R: [days, assets] states (NaN undefined) and returns on the union calendar. Returns net, gross, cost,
    turnover and held weights."""
    n = S.notna().sum(axis=1).clip(lower=1)
    W = S.fillna(0.0).div(n, axis=0)
    Wh = W.shift(1).fillna(0.0)
    turn = Wh.diff().abs().sum(axis=1)
    turn.iloc[0] = Wh.iloc[0].abs().sum()
    gross = (Wh * R).sum(axis=1)
    cost = turn * COST * cm
    return gross - cost, gross, cost, turn, Wh


def row(net, gross, cost, turn, Wh, bench):
    n, bm = net.values, bench.reindex(net.index).fillna(0.0).values
    X = np.column_stack([np.ones(len(bm)), bm])
    beta = float(np.linalg.lstsq(X, n, rcond=None)[0][1])
    a = n - beta * bm
    s = events.summary(n)
    yrs = net.index.year
    pos = Wh.values
    live = (pos != 0).any(axis=1)
    return {"days": len(n), "mean_bp_day": float(n.mean() * 1e4), "ann_return": float(n.mean() * 252),
            "sharpe": float(n.mean() / n.std() * np.sqrt(252)), "max_dd": s.get("max_dd", np.nan), "beta": beta,
            "gross_bp_day": float(gross.mean() * 1e4), "cost_bp_day": float(cost.mean() * 1e4),
            "turnover_per_year": float(turn.sum() / (len(n) / 252)),
            "long_share": float((pos > 0).sum() / max((pos != 0).sum(), 1)), "invested": float(live.mean()),
            "test_mean_bp_day": float(a.mean() * 1e4), "test_t": float(stats.newey_west_t(a, 10)[2]),
            "trimmed_bp_day": float(np.sort(a)[10:-10].mean() * 1e4) if len(a) > 20 else np.nan,
            "by_year_bp_day": {int(y): float(a[yrs == y].mean() * 1e4) for y in np.unique(yrs)}}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    rows, stage, extra = [], {}, {"first_bar": {}, "moves_above_8pct": {}}
    for g, syms in GROUPS.items():
        per, rets = {}, {}
        for sym in syms:
            d = bars(sym)
            per[sym], rets[sym] = asset_states(d)
            extra["first_bar"][sym] = str(d.index[0].date())
            extra["moves_above_8pct"][sym] = int((rets[sym].abs() > 0.08).sum())
        cal = pd.DatetimeIndex(sorted(set().union(*[r.index for r in rets.values()])))
        R = pd.DataFrame({s: rets[s].reindex(cal) for s in syms})
        started = R.notna().cummax()
        R = R.fillna(0.0)
        bench = R.where(started).mean(axis=1).fillna(0.0)
        log(g, "calendar", cal[0].date(), "to", cal[-1].date(), len(cal), "days")
        for rule in per[syms[0]]:
            S = pd.DataFrame({s: per[s][rule].reindex(cal, method="ffill") for s in syms})   # holidays carry state
            name = f"{rule}/{g}"
            books = {cm: book(S, R, cm) for cm in (1.0, 2.0, 3.0)}
            first = books[1.0][4].abs().sum(axis=1).values.argmax()
            passed = True
            for w, a, b in WINDOWS:
                if not passed:
                    break
                m = (cal >= a) & (cal <= b) & (np.arange(len(cal)) >= first)
                res = {cm: row(*(x[m] for x in bk), bench) for cm, bk in books.items()}
                for cm, r in res.items():
                    rows.append({"book": name, "window": w, "cmult": cm, **r})
                r1 = res[1.0]
                passed = bool(decide(w, r1, res[2.0]) and (w != "discovery" or r1["mean_bp_day"] > 0))
                stage[name] = {"reached": w, "passed": passed}
                log(name, w, f"net {r1['mean_bp_day']:+.2f} bp/day (gross {r1['gross_bp_day']:+.2f}, cost "
                    f"{r1['cost_bp_day']:.2f}), alpha {r1['test_mean_bp_day']:+.2f} t {r1['test_t']:+.2f}, beta "
                    f"{r1['beta']:+.2f} (2x alpha {res[2.0]['test_mean_bp_day']:+.2f})", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "data_sha256": SHAS, **extra,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] in ("validation", "holdout")
                                      and (v["reached"] == "holdout" or v["passed"])],
               "holdout_passers": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers", "holdout_passers")}, indent=1))


if __name__ == "__main__":
    main()
