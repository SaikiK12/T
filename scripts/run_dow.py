"""dow_v1 (R254): day-of-week books on SPY, world indices, the US dollar, BTC and crypto. Discovery selects one weekday
and sign per market, which is then read on validation (and on the holdout for Yahoo passers), as set out in
experiments/dow_v1/PREREG.md.

usage: python scripts/run_dow.py
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
from lab import prereg, research, screen, slices, stats  # noqa: E402
from run_chartxm import GROUPS, bars  # noqa: E402
from run_fxindex import COST, WINDOWS as YWINDOWS, etf, etf_row, fx_returns  # noqa: E402
from run_tsbattery import WINDOWS as CWINDOWS, market_daily  # noqa: E402

LANE = ROOT / "experiments" / "dow_v1"
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def yahoo_series():
    """Daily returns of SPY, the equal-weight 10 indices and the USD basket, Mon-Fri rows only."""
    idx = pd.DataFrame({sym: bars(sym).close.pipe(lambda c: c / c.shift(1) - 1) for sym in GROUPS["IDX"]}).sort_index()
    out = {"SPY": etf("SPY").r.dropna(), "IDX": idx.mean(axis=1, skipna=True).dropna(),
           "USD": -fx_returns().mean(axis=1)}
    dropped = {k: int((v.index.weekday >= 5).sum()) for k, v in out.items()}
    return {k: v[v.index.weekday < 5] for k, v in out.items()}, dropped


def ybook(r, d, s, cm, a, b):
    m = (r.index >= a) & (r.index <= b)
    x = r[m]
    on = x.index.weekday == d
    net = np.where(on, s * x.values - 2 * COST * cm, 0.0)
    row = etf_row(net, x.values, on, x.index)
    return {"days": row["days"], "net_bp_day": row["mean_bp_day"], "net_t": float(stats.newey_west_t(net, 10)[2]),
            "alpha_bp_day":
            row["test_mean_bp_day"], "alpha_t": row["test_t"], "beta": row["beta"], "cost_bp_day":
            float(2 * COST * cm * on.mean() * 1e4), "mean_day_ret_bp": float(x.values[on].mean() * 1e4),
            "n_day": int(on.sum()), "by_year": {"alpha": row["by_year_bp_day"]}}


class Crypto:
    def __init__(self):
        self.u, _, _ = research.load_universe()
        u = self.u
        self.s = screen.Screen(u, windows=CWINDOWS)
        self.wd = pd.to_datetime(np.asarray(u.p.t) + 3_600_000, unit="ms", utc=True).weekday.values
        self.e = np.asarray(u.elig)
        self.n_el = np.maximum(self.e.sum(axis=1, keepdims=True), 1)
        self.btc = list(u.p.symbols).index("BTCUSDT")
        self.R = np.nan_to_num(np.asarray(u.ret, np.float64))

    def ref(self, kind, a, b):
        if kind == "CRYPTO":
            return market_daily(self.u, a, b)
        h = self.R[a:b, self.btc]
        D = len(h) // 24
        return h[:D * 24].reshape(D, 24).sum(axis=1)

    def book(self, kind, d, s, cm, w):
        a, b = self.s.rows[w]
        on = self.wd[a:b] == d
        if kind == "CRYPTO":
            P = np.where(self.e[a:b] & on[:, None], float(s), 0.0) / self.n_el[a:b]
        else:
            P = np.zeros((b - a, self.R.shape[1]))
            P[:, self.btc] = np.where(on, float(s), 0.0)
        r_ = slices.run(P, self.u.ret, self.u.elig, self.u.cmat, a, b, hedge=False, cmult=cm)
        nd = r_["daily"]
        Dd = len(nd)
        st = screen.window_stats(nd, self.s.days(a, b), self.ref(kind, a, b)[:Dd])
        day_ret = self.ref(kind, a, b)[:Dd]
        blk_on = on[:Dd * 24].reshape(Dd, 24).mean(axis=1) > 0.5
        return {"days": Dd, "net_bp_day": st["mean_bp_day"], "net_t": st["t_nw10"], "alpha_bp_day": st["resid_bp_day"],
                "alpha_t": st["resid_t_nw10"], "beta": st["beta_ref"],
                "cost_bp_day": float(r_["cost"][:Dd * 24].sum() / Dd * 1e4),
                "mean_day_ret_bp": float(day_ret[blk_on].mean() * 1e4), "n_day": int(blk_on.sum()),
                "by_year": {"net": st["by_year_bp_day"]}}


def decide(stage, r1, r2):
    if stage == "discovery":
        return r1["alpha_t"] >= 2 and r2["alpha_bp_day"] > 0 and r1["net_bp_day"] > 0
    if stage == "validation":
        return r1["alpha_bp_day"] > 0 and r1["alpha_t"] >= 1.5
    return r1["alpha_bp_day"] > 0 and r1["alpha_t"] >= 2


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    ys, dropped = yahoo_series()
    log("weekend rows dropped", dropped, "| series start", {k: str(v.index[0].date()) for k, v in ys.items()})
    cr = Crypto()
    markets = {}
    for k, r in ys.items():
        markets[k] = (5, [(w, a, b) for w, a, b in YWINDOWS],
                      lambda d, s, cm, w, r=r: ybook(r, d, s, cm, w[1], w[2]))
    for k in ("BTC", "CRYPTO"):
        markets[k] = (7, [(w, None, None) for w, _, _ in CWINDOWS],
                      lambda d, s, cm, w, k=k: cr.book(k, d, s, cm, w[0]))

    table, rows, stage = [], [], {}
    for name, (nd, windows, fn) in markets.items():
        disc, val = windows[0], windows[1]
        sel = []
        for win in (disc, val):
            for d in range(nd):
                r = fn(d, 1, 1.0, win)
                if win is disc:
                    sel.append(r)
                table.append({"market": name, "window": win[0], "weekday": DAYS[d],
                              **{k: v for k, v in r.items() if not k.startswith("by_year")}})
        best = int(np.argmax([abs(x["alpha_t"]) for x in sel]))
        sign = 1 if sel[best]["alpha_t"] > 0 else -1
        book = f"{name}/{DAYS[best]}/{'long' if sign > 0 else 'short'}"
        log(name, "selected", book, f"discovery alpha t {sel[best]['alpha_t']:+.2f}")
        passed = True
        for win in windows:
            if not passed:
                break
            res = {cm: fn(best, sign, cm, win) for cm in (1.0, 2.0, 3.0)}
            for cm, r in res.items():
                rows.append({"book": book, "window": win[0], "cmult": cm, **r})
            passed = bool(decide(win[0], res[1.0], res[2.0]))
            stage[name] = {"book": book, "reached": win[0], "passed": passed}
            r1 = res[1.0]
            log(book, win[0], f"net {r1['net_bp_day']:+.2f} bp/day, alpha {r1['alpha_bp_day']:+.2f} t {r1['alpha_t']:+.2f}"
                f" (2x alpha {res[2.0]['alpha_bp_day']:+.2f}), beta {r1['beta']:.2f}, cost {r1['cost_bp_day']:.2f},"
                f" day mean {r1['mean_day_ret_bp']:+.1f} bp over {r1['n_day']} days", "PASS" if passed else "stop")
    tb = pd.DataFrame(table)
    tb.to_csv(out / "weekday_table.csv", index=False)
    df = pd.DataFrame(rows)
    df.drop(columns=[c for c in df.columns if c.startswith("by_year")]).to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "weekend_rows_dropped": dropped,
               "by_year_1x": {f"{x['book']}/{x['window']}": x["by_year"] for x in rows if x["cmult"] == 1.0},
               "passers": [k for k, v in stage.items() if v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + tb.round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "passers")}, indent=1))


if __name__ == "__main__":
    main()
