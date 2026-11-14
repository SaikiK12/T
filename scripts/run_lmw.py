"""lmw_v1 (R251): Lo-Mamaysky-Wang kernel chart patterns (head-and-shoulders, broadening, triangle and rectangle tops
and bottoms) on daily bars of the top-50 perps, 11 forex pairs and 10 world indices, as set out in
experiments/lmw_v1/PREREG.md. The crypto holdout is not read; the forex/index holdout only for validation passers.

usage: python scripts/run_lmw.py
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
from lab import flowfeat, prereg, research, screen, slices  # noqa: E402
from run_chartist import resample  # noqa: E402
from run_chartxm import GROUPS, SHAS, bars, book, row  # noqa: E402
from run_fxindex import WINDOWS as XM_WINDOWS, decide  # noqa: E402
from run_tsbattery import WINDOWS as CRYPTO_WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "lmw_v1"
W, LAG, BW, HOLD = 38, 3, 2.0, 5
TOPS, BOTS = ("HS", "BTOP", "TTOP", "RTOP"), ("IHS", "BBOT", "TBOT", "RBOT")
_i = np.arange(W)
KMAT = np.exp(-0.5 * ((_i[:, None] - _i[None, :]) / BW) ** 2)
KMAT /= KMAT.sum(axis=1, keepdims=True)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def extrema(w):
    """[(index, +1 max / -1 min, price)] of the smoothed window, alternating."""
    m = KMAT @ w
    out = []
    for k in range(1, W - 1):
        if m[k] > m[k - 1] and m[k] >= m[k + 1]:
            kind, p = 1, w[k - 1:k + 2].max()
        elif m[k] < m[k - 1] and m[k] <= m[k + 1]:
            kind, p = -1, w[k - 1:k + 2].min()
        else:
            continue
        if out and out[-1][1] == kind:
            if (kind == 1 and p > out[-1][2]) or (kind == -1 and p < out[-1][2]):
                out[-1] = (k, kind, p)
            continue
        out.append((k, kind, p))
    return out


def near(a, b, x):
    return abs(a - b) <= x * (a + b) / 2


def within(vals, x):
    mu = sum(vals) / len(vals)
    return all(abs(v - mu) <= x * mu for v in vals)


def pattern(w):
    if not np.isfinite(w).all() or (w <= 0).any():
        return None
    ex = extrema(w)
    if len(ex) < 5:
        return None
    e = ex[-5:]
    if not (W - 1 - LAG - 4 <= e[-1][0] <= W - 1 - LAG):
        return None
    E1, E2, E3, E4, E5 = (x[2] for x in e)
    top = e[0][1] == 1
    if top:
        if E3 > E1 and E3 > E5 and near(E1, E5, 0.015) and near(E2, E4, 0.015):
            return "HS"
        if E1 < E3 < E5 and E2 > E4:
            return "BTOP"
        if E1 > E3 > E5 and E2 < E4:
            return "TTOP"
        if within((E1, E3, E5), 0.0075) and within((E2, E4), 0.0075) and min(E1, E3, E5) > max(E2, E4):
            return "RTOP"
    else:
        if E3 < E1 and E3 < E5 and near(E1, E5, 0.015) and near(E2, E4, 0.015):
            return "IHS"
        if E1 > E3 > E5 and E2 < E4:
            return "BBOT"
        if E1 < E3 < E5 and E2 > E4:
            return "TBOT"
        if within((E1, E3, E5), 0.0075) and within((E2, E4), 0.0075) and max(E1, E3, E5) < min(E2, E4):
            return "RBOT"
    return None


def detect(c, mask=None):
    """c [n, m] daily closes. Returns an object array [n, m] of pattern names (None where none), at the bar where the
    window ends; mask limits detection to True cells."""
    n, m = c.shape
    out = np.full((n, m), None, object)
    for j in range(m):
        for t in range(W - 1, n):
            if mask is not None and not mask[t, j]:
                continue
            out[t, j] = pattern(c[t - W + 1:t + 1, j])
    return out


def states(pat, which):
    """Held states [n, m]: -1 after a TOP, +1 after a BOT among `which`, for HOLD bars; newer replaces."""
    trig = np.zeros(pat.shape)
    for p in which:
        trig[pat == p] = -1.0 if p in TOPS else 1.0
    x = pd.DataFrame(np.where(trig != 0, trig, np.nan))
    return np.nan_to_num(x.ffill(limit=HOLD - 1).values), trig


def fwd_table(pat, c, sel):
    """Mean raw 5-bar forward close-to-close return after each pattern, rows `sel` (bool [n])."""
    f = np.full(c.shape, np.nan)
    f[:-HOLD] = c[HOLD:] / c[:-HOLD] - 1
    out = {}
    for p in TOPS + BOTS:
        hit = (pat == p) & sel[:, None]
        v = f[hit]
        v = v[np.isfinite(v)]
        out[p] = {"n": int(hit.sum()), "fwd5_bp": float(v.mean() * 1e4) if len(v) else None}
    return out


def crypto(rows, stage, extra):
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    kl = flowfeat.load("klines", t, u.p.symbols, ("open", "high", "low"))
    c = np.asarray(u.p["close"], np.float64)
    e = np.asarray(u.elig)
    s = screen.Screen(u, windows=CRYPTO_WINDOWS)
    bb, rr = resample(kl["open"], kl["high"], kl["low"], c, t, 24)
    er = e[rr]
    v_end = s.rows["validation"][1]
    pat = detect(bb["c"], er & (rr < v_end)[:, None])
    a0, b0 = s.rows["discovery"]
    extra["fwd5_after_pattern"]["CRYPTO-1d"] = fwd_table(pat, bb["c"], (rr >= a0) & (rr < b0))
    n = np.maximum(er.sum(axis=1, keepdims=True), 1)
    for book_name, which in (("ALL8", TOPS + BOTS), ("REV2", ("HS", "IHS"))):
        st, _ = states(pat, which)
        D = np.where(er, st, 0.0) / n
        P = np.zeros((T, S))
        for j, r in enumerate(rr):
            P[r:(rr[j + 1] if j + 1 < len(rr) else T)] = D[j]
        name = f"{book_name}/CRYPTO-1d"
        passed = True
        for w, (a, b) in s.rows.items():
            if not passed:
                break
            mk = market_daily(u, a, b)
            res = {}
            for cm in (1.0, 2.0, 3.0):
                o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                nd = o["daily"]
                Dd = len(nd)
                day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
                r = {"book": name, "window": w, "cmult": cm,
                     "gross_bp_day": float(day_sum(o["gross"]).mean() * 1e4),
                     "cost_bp_day": float(day_sum(o["cost"]).mean() * 1e4),
                     "gross_exposure": float(o["gross_exposure"].mean()),
                     "net_exposure": float(o["net_exposure"].mean()),
                     **screen.window_stats(nd, s.days(a, b), mk[:Dd])}
                if cm == 1.0:
                    r["trimmed_bp_day"] = trimmed(nd)
                rows.append(r)
                res[cm] = r
            r1 = res[1.0]
            if w == "discovery":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0 and r1["resid_bp_day"] > 0
            else:
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5 and r1["resid_bp_day"] > 0
            stage[name] = {"reached": w, "passed": bool(passed)}
            log(name, w, f"{r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.2f}),"
                f" gross {r1['gross_bp_day']:+.2f} cost {r1['cost_bp_day']:.2f}, exposure {r1['gross_exposure']:.2f},"
                f" alpha {r1['resid_bp_day']:+.2f} t {r1['resid_t_nw10']:+.2f}", "PASS" if passed else "stop")


def cross_market(rows, stage, extra):
    for g, syms in GROUPS.items():
        pats, rets, closes = {}, {}, {}
        for sym in syms:
            d = bars(sym)
            cc = d.close.values[:, None]
            pats[sym] = detect(cc)[:, 0]
            closes[sym] = pd.Series(d.close.values, index=d.index)
            rets[sym] = closes[sym] / closes[sym].shift(1) - 1
        cal = pd.DatetimeIndex(sorted(set().union(*[r.index for r in rets.values()])))
        R = pd.DataFrame({s: rets[s].reindex(cal) for s in syms})
        started = R.notna().cummax()
        R = R.fillna(0.0)
        bench = R.where(started).mean(axis=1).fillna(0.0)
        fw = {}
        for sym in syms:
            idx = closes[sym].index
            sel = (idx >= XM_WINDOWS[0][1]) & (idx <= XM_WINDOWS[0][2])
            fw[sym] = fwd_table(pats[sym][:, None], closes[sym].values[:, None], np.asarray(sel))
        extra["fwd5_after_pattern"][g] = {p: {"n": sum(fw[s][p]["n"] for s in syms),
                                              "fwd5_bp": (float(np.nansum([fw[s][p]["fwd5_bp"] * fw[s][p]["n"]
                                                                           for s in syms if fw[s][p]["n"]])
                                                                / max(sum(fw[s][p]["n"] for s in syms), 1))
                                                          if sum(fw[s][p]["n"] for s in syms) else None)}
                                          for p in TOPS + BOTS}
        for book_name, which in (("ALL8", TOPS + BOTS), ("REV2", ("HS", "IHS"))):
            per = {}
            for sym in syms:
                st, _ = states(pats[sym][:, None], which)
                x = pd.Series(st[:, 0], index=closes[sym].index)
                x.iloc[:W - 1] = np.nan                        # detector undefined before 38 bars
                per[sym] = x
            S = pd.DataFrame({s: per[s].reindex(cal, method="ffill") for s in syms})
            books = {cm: book(S, R, cm) for cm in (1.0, 2.0, 3.0)}
            name = f"{book_name}/{g}"
            passed = True
            for w, a, b in XM_WINDOWS:
                if not passed:
                    break
                m = (cal >= a) & (cal <= b)
                res = {cm: row(*(y[m] for y in bk), bench) for cm, bk in books.items()}
                for cm, r in res.items():
                    rows.append({"book": name, "window": w, "cmult": cm, **r})
                r1 = res[1.0]
                passed = bool(decide(w, r1, res[2.0]) and (w != "discovery" or r1["mean_bp_day"] > 0))
                stage[name] = {"reached": w, "passed": passed}
                log(name, w, f"net {r1['mean_bp_day']:+.2f} (gross {r1['gross_bp_day']:+.2f}, cost {r1['cost_bp_day']:.2f}),"
                    f" alpha {r1['test_mean_bp_day']:+.2f} t {r1['test_t']:+.2f}, beta {r1['beta']:+.2f},"
                    f" invested {r1['invested']:.2f}", "PASS" if passed else "stop")


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    rows, stage, extra = [], {}, {"fwd5_after_pattern": {}}
    cross_market(rows, stage, extra)
    crypto(rows, stage, extra)
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    by_year = {}
    for x in df[df.cmult == 1.0].itertuples():
        by_year[f"{x.book}/{x.window}"] = x.by_year_bp_day
    verdict = {"stages": stage, "data_sha256": SHAS, **extra, "by_year_1x": by_year,
               "passers": [k for k, v in stage.items() if v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "passers", "fwd5_after_pattern")}, indent=1))


if __name__ == "__main__":
    main()
