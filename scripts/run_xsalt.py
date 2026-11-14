"""xsalt_v1 (R222): slow altcoin cross-sections (low beta, residual momentum, MAX, premium net of funding), as set out
in experiments/xsalt_v1/PREREG.md."""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, panel, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "xsalt_v1"
START, VAL, HOLD_OUT, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
MIN_N = 15
# variant -> (score key, side of the top quintile: +1 long top / -1 short top, hold hours, NW lag)
VARIANTS = {"BETA": ("beta", -1, 168, 10), "RESMOM": ("resmom", 1, 720, 30), "MOM": ("mom", 1, 720, 30),
            "MAX_POS": ("max", 1, 168, 10), "MAX_NEG": ("max", -1, 168, 10), "PREM": ("prem", 1, 168, 10)}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def roll(a, w):
    """Trailing sum over rows t-w+1..t."""
    c = np.cumsum(a, axis=0)
    out = c.copy()
    out[w:] -= c[:-w]
    return out


def lag(a, k):
    return np.vstack([np.full((k,) + a.shape[1:], np.nan), a[:-k]]) if k else a


def ols_parts(x, y, w, min_n):
    """Rolling OLS of y[:, s] on x[:, s] (or 1-D x) over w rows: n, alpha, beta, residual variance; NaN under min_n."""
    if x.ndim == 1:
        x = np.broadcast_to(x[:, None], y.shape)
    v = np.isfinite(x) & np.isfinite(y)
    xs, ys = np.where(v, x, 0.0), np.where(v, y, 0.0)
    n = roll(v.astype(np.float64), w)
    sx, sy, sxx, sxy, syy = (roll(a, w) for a in (xs, ys, xs * xs, xs * ys, ys * ys))
    with np.errstate(divide="ignore", invalid="ignore"):
        b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        a = (sy - b * sx) / n
        var = (syy - 2 * a * sy - 2 * b * sxy + a * a * n + 2 * a * b * sx + b * b * sxx) / n
    bad = n < min_n
    for z in (a, b, var):
        z[bad] = np.nan
    return n, a, b, var, (sx, sy, v)


def xs_resid(y, x, ok):
    """Per row, residual of y on x (with intercept) across the columns where ok and both finite."""
    out = np.full(y.shape, np.nan)
    for i in range(y.shape[0]):
        m = ok[i] & np.isfinite(y[i]) & np.isfinite(x[i])
        if m.sum() < MIN_N:
            continue
        X = np.column_stack([np.ones(m.sum()), x[i, m]])
        coef, *_ = np.linalg.lstsq(X, y[i, m], rcond=None)
        out[i, m] = y[i, m] - X @ coef
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    assert t0 == 0 and u.p.t[0] % (24 * panel.HOUR) == 0
    T = t1 - t1 % 24
    syms = list(u.p.symbols)
    p = panel.load_panel(symbols=syms)
    assert np.array_equal(p.t[:T], u.p.t[:T])
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in syms])
    E = np.asarray(u.elig[:T]) & crypto[None, :]
    close = np.asarray(u.p["close"][:T], np.float64)
    btc = syms.index("BTCUSDT")
    # daily rows: the bar closing at 00:00 UTC (row hour 23)
    drow = np.arange(23, T, 24)
    dc = close[drow]
    with np.errstate(divide="ignore", invalid="ignore"):
        dlr = np.full_like(dc, np.nan)
        dlr[1:] = np.log(dc[1:] / dc[:-1])
        hlr = np.full_like(close, np.nan)
        hlr[1:] = np.log(close[1:] / close[:-1])
    dE = E[drow]
    sc = {}
    # BETA: 90-day slope on BTC
    _, _, b90, _, _ = ols_parts(dlr[:, btc], dlr, 90, 60)
    sc["beta"] = b90
    # RESMOM: market ex-i, 180-day regression, residual sum over d-179..d-30 / residual sd
    em = np.where(dE, dlr, np.nan)
    tot, cnt = np.nansum(em, axis=1)[:, None], np.isfinite(em).sum(1)[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        mex = (tot - np.nan_to_num(em)) / (cnt - np.isfinite(em))
    n, a, b, var, (_, _, v) = ols_parts(mex, dlr, 180, 120)
    xs, ys = np.where(v, mex, 0.0), np.where(v, dlr, 0.0)
    sub_n = lag(roll(v.astype(np.float64), 150), 30)
    sub_y, sub_x = lag(roll(ys, 150), 30), lag(roll(xs, 150), 30)
    with np.errstate(invalid="ignore", divide="ignore"):
        sc["resmom"] = (sub_y - a * sub_n - b * sub_x) / np.sqrt(var)
    vm = np.isfinite(dlr).astype(np.float64)
    mom_n = lag(roll(vm, 150), 30)
    sc["mom"] = np.where(mom_n >= 120, lag(roll(np.nan_to_num(dlr), 150), 30), np.nan)
    log("daily scores: beta, resmom, mom")
    # MAX: 168 h max hourly log return, residualized on ln 720 h mean quote volume
    hl = pd.DataFrame(hlr)
    mx = hl.rolling(168, min_periods=120).max().values[drow]
    qv = pd.DataFrame(np.nan_to_num(np.asarray(p["quote_volume"][:T], np.float64))).rolling(720, min_periods=360) \
        .mean().values[drow]
    with np.errstate(divide="ignore", invalid="ignore"):
        lqv = np.where(qv > 0, np.log(qv), np.nan)
    sc["max"] = xs_resid(mx, lqv, dE)
    # PREM: 168 h mean premium residualized on 168 h mean funding
    prem = pd.DataFrame(np.asarray(p["premium"][:T], np.float64)).rolling(168, min_periods=120).mean().values[drow]
    fund = pd.DataFrame(np.asarray(p["funding"][:T], np.float64)).rolling(168, min_periods=120).mean().values[drow]
    sc["prem"] = xs_resid(prem, fund, dE)
    log("daily scores: max, prem")
    ret, cmat = u.ret[:T], u.cmat[:T]
    r_btc = np.nan_to_num(np.asarray(ret[:, btc], np.float64))
    windows = {"discovery": (t0, tv), "validation": (tv, th), "holdout": (th, T)}

    def quint(score):
        s = np.where(dE, score, np.nan)
        ok = np.isfinite(s).sum(1) >= MIN_N
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            pct = pd.DataFrame(s).rank(axis=1, pct=True).values
        top, bot = np.zeros((T, len(syms)), bool), np.zeros((T, len(syms)), bool)
        top[drow] = (pct > 0.8) & ok[:, None]
        bot[drow] = (pct <= 0.2) & ok[:, None]
        return top, bot

    def run(top, bot, side, H, K, a, bb, cm):
        w = max(a - H, 0)
        unit = 1.0 / ((H / 24) * K)
        PL = slices.positions(top if side > 0 else bot, H, w, bb, unit, 1)
        PS = slices.positions(bot if side > 0 else top, H, w, bb, unit, -1)
        o = slices.run(PL + PS, ret, E, cmat, w, bb, cmult=cm)
        D_ = (bb - a) // 24
        day = lambda x: x[a - w: a - w + D_ * 24].reshape(D_, 24).sum(1)
        r = np.nan_to_num(np.asarray(ret[w:bb], np.float64))
        legs = {"long_gross_bp_day": float(day((PL * r).sum(1)).mean() * 1e4),
                "short_gross_bp_day": float(day((PS * r).sum(1)).mean() * 1e4)}
        bd = r_btc[a: a + D_ * 24].reshape(D_, 24).sum(1)
        return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"]), bd, legs

    def alpha_t(n, bd, L):
        bb_ = np.cov(n, bd)[0, 1] / np.var(bd, ddof=1)
        return float(bb_), float(stats.newey_west_t(n - bb_ * bd, L)[2])

    rows, stage, spreads, nets = [], {}, [], {}
    r24 = roll(np.nan_to_num(np.asarray(ret, np.float64)), 24)   # sum of ret over rows t-23..t
    for name, (key, side, H, L) in VARIANTS.items():
        top, bot = quint(sc[key])
        K = float((top[t0:tv].sum(1)[drow[drow < tv]].mean() + bot[t0:tv].sum(1)[drow[drow < tv]].mean()) / 2)
        for w, (a, bb) in windows.items():
            if w == "holdout":                                # unread unless a variant reaches it through the stages
                continue
            dd = drow[(drow >= a) & (drow < bb - 24)]
            fwd = r24[dd + 23]                                 # rows dd..dd+23: what a slice opened at dd earns
            nt, nb = top[dd].sum(1), bot[dd].sum(1)
            ok = (nt > 0) & (nb > 0)
            sp = (fwd * top[dd]).sum(1)[ok] / nt[ok] - (fwd * bot[dd]).sum(1)[ok] / nb[ok]
            spreads.append({"variant": name, "window": w, "days": int(ok.sum()),
                            "next_24h_spread_top_minus_bottom_bp": float(sp.mean() * 1e4)})
        passed = True
        for w, (a, bb) in windows.items():
            if not passed:
                break
            for cm in (1.0, 2.0, 3.0):
                n, gr, co, bd, legs = run(top, bot, side, H, K, a, bb, cm)
                beta, at = alpha_t(n, bd, L)
                s = events.summary(n)
                if cm == 1.0:
                    nets[(name, w)] = n
                rows.append({"variant": name, "K": K, "window": w, "cmult": cm, "days": len(n),
                             "mean_bp_day": float(n.mean() * 1e4), "t_nw": float(stats.newey_west_t(n, L)[2]),
                             "beta_btc": beta, "alpha_t": at, "total": float(n.sum()), "max_dd": s.get("max_dd", np.nan),
                             "sharpe": s.get("sharpe", np.nan), "gross_bp_day": float(gr.mean() * 1e4),
                             "cost_bp_day": float(co.mean() * 1e4), **legs})
            r1 = rows[-3]
            gate = 1.5 if w == "validation" else 2.0
            passed = r1["mean_bp_day"] > 0 and r1["alpha_t"] >= gate
            stage[name] = {"reached": w, "passed": bool(passed)}
            log(name, w, f"net {r1['mean_bp_day']:+.1f} bp/day alpha t {r1['alpha_t']:+.2f} beta {r1['beta_btc']:+.2f} "
                         f"gross {r1['gross_bp_day']:+.1f} cost {r1['cost_bp_day']:.1f}", "PASS" if passed else "stop")
    # BETA persistence: rank correlation of beta 90 days apart, discovery and validation days
    pers = {}
    for w, (a, bb) in (("discovery", (t0, tv)), ("validation", (tv, th))):
        idx = np.flatnonzero((drow >= a) & (drow < bb))
        cs = []
        for i in idx:
            if i - 90 < 0:
                continue
            x, y = np.where(dE[i], sc["beta"][i - 90], np.nan), np.where(dE[i], sc["beta"][i], np.nan)
            m = np.isfinite(x) & np.isfinite(y)
            if m.sum() >= MIN_N:
                cs.append(pd.Series(x[m]).corr(pd.Series(y[m]), method="spearman"))
        pers[w] = float(np.mean(cs)) if cs else None
    diff = {}
    for w in ("discovery", "validation"):
        if ("RESMOM", w) in nets and ("MOM", w) in nets:
            d = nets[("RESMOM", w)] - nets[("MOM", w)]
            diff[w] = {"mean_bp_day": float(d.mean() * 1e4), "t_nw30": float(stats.newey_west_t(d, 30)[2])}
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)
    pd.DataFrame(spreads).to_csv(out / "spreads.csv", index=False)
    verdict = {"stages": stage, "confirmed": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]],
               "beta_persistence_spearman_90d": pers, "resmom_minus_mom": diff}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log("\n" + pd.DataFrame(spreads).round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
