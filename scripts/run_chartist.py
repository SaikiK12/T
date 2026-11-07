"""chartist_v1 (R243): seven classic chart rules on 4 h and 1 d bars of the top-50 perps, directional books, as set
out in experiments/chartist_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_chartist.py
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
from run_tsbattery import WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "chartist_v1"
HOUR = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def resample(o, h, l, c, t, k):
    """UTC-aligned k-hour bars; a bar with any missing hour is NaN. Returns bars and each bar's last hourly row."""
    hour = (np.asarray(t) // HOUR) % 24
    s = int(np.flatnonzero(hour % k == 0)[0])
    n = (len(t) - s) // k
    def grp(x):
        return np.asarray(x[s:s + n * k], np.float64).reshape(n, k, -1)
    O, H, L, C = grp(o), grp(h), grp(l), grp(c)
    bad = np.isnan(O).any(1) | np.isnan(H).any(1) | np.isnan(L).any(1) | np.isnan(C).any(1)
    bars = {"o": O[:, 0], "h": H.max(1), "l": L.min(1), "c": C[:, -1]}
    for x in bars.values():
        x[bad] = np.nan
    return bars, s + np.arange(n) * k + k - 1


def F(x):
    return pd.DataFrame(x)


def wilder(x, n):
    return F(x).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().values


def rsi(c, n=14):
    d = np.diff(c, axis=0, prepend=np.nan)
    up, dn = wilder(np.where(d > 0, d, 0.0) + 0 * d, n), wilder(np.where(d < 0, -d, 0.0) + 0 * d, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100 - 100 / (1 + up / dn)


def atr(h, l, c, n):
    pc = np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]])
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    tr[np.isnan(h - l)] = np.nan
    return wilder(tr, n)


def supertrend(h, l, c, n=10, m=3.0):
    a = atr(h, l, c, n)
    mid = (h + l) / 2
    bu, bl = mid + m * a, mid - m * a
    T, S = c.shape
    fu, fl, up = np.full((T, S), np.nan), np.full((T, S), np.nan), np.full((T, S), np.nan)
    for t in range(T):
        ok = np.isfinite(bu[t]) & np.isfinite(c[t])
        if t == 0:
            fu[t], fl[t], up[t] = np.where(ok, bu[t], np.nan), np.where(ok, bl[t], np.nan), np.where(ok, 1.0, np.nan)
            continue
        pfu, pfl, pc, pup = fu[t - 1], fl[t - 1], c[t - 1], up[t - 1]
        start = ok & ~np.isfinite(pup)                         # first bar after a gap: restart
        fu[t] = np.where(start, bu[t], np.where((bu[t] < pfu) | (pc > pfu), bu[t], pfu))
        fl[t] = np.where(start, bl[t], np.where((bl[t] > pfl) | (pc < pfl), bl[t], pfl))
        u = np.where(pup == 1, np.where(c[t] < fl[t], -1.0, 1.0), np.where(c[t] > fu[t], 1.0, -1.0))
        up[t] = np.where(start, 1.0, u)
        fu[t][~ok], fl[t][~ok], up[t][~ok] = np.nan, np.nan, np.nan
    return up


def roll(x, n, how):
    return getattr(F(x).rolling(n, min_periods=n), how)().values


def states(b, day):
    """Rule -> [bars, S] state in {-1, 0, +1} (NaN where undefined). `day` holds the previous-day pivots."""
    o, h, l, c = b["o"], b["h"], b["l"], b["c"]
    out = {}
    st = supertrend(h, l, c)
    r = rsi(c)
    out["SUPERTREND_RSI"] = np.where(np.isnan(st) | np.isnan(r), np.nan,
                                     np.where((st == 1) & (r > 50), 1, np.where((st == -1) & (r < 50), -1, 0)))
    ema = lambda x, n: F(x).ewm(span=n, adjust=False, min_periods=n).mean().values
    macd = ema(c, 12) - ema(c, 26)
    sig = F(macd).ewm(span=9, adjust=False, min_periods=9).mean().values
    out["MACD"] = np.sign(macd - sig)
    ll, hh = roll(l, 14, "min"), roll(h, 14, "max")
    with np.errstate(invalid="ignore", divide="ignore"):
        k = 100 * (c - ll) / (hh - ll)
    dd = roll(k, 3, "mean")
    out["STOCH"] = np.where(np.isnan(dd), np.nan, np.where(dd < 20, 1, np.where(dd > 80, -1, 0)))
    tp = (h + l + c) / 3
    sma = roll(tp, 20, "mean")
    win = np.lib.stride_tricks.sliding_window_view(tp, 20, axis=0)          # [T-19, S, 20]
    mad = np.full_like(tp, np.nan)
    mad[19:] = np.abs(win - sma[19:, :, None]).mean(axis=2)
    with np.errstate(invalid="ignore", divide="ignore"):
        cci = (tp - sma) / (0.015 * mad)
    out["CCI"] = np.where(np.isnan(cci), np.nan, np.where(cci < -100, 1, np.where(cci > 100, -1, 0)))
    m20, s20 = roll(c, 20, "mean"), F(c).rolling(20, min_periods=20).std(ddof=0).values
    out["BOLL"] = np.where(np.isnan(s20), np.nan, np.where(c < m20 - 2 * s20, 1, np.where(c > m20 + 2 * s20, -1, 0)))
    mid = lambda n: (roll(h, n, "max") + roll(l, n, "min")) / 2
    ten, kij = mid(9), mid(26)
    sa, sb = (ten + kij) / 2, mid(52)
    lag = lambda x, n: np.vstack([np.full((n, x.shape[1]), np.nan), x[:-n]])
    ca, cb = lag(sa, 26), lag(sb, 26)
    top, bot = np.fmax(ca, cb), np.fmin(ca, cb)
    top[np.isnan(ca) | np.isnan(cb)] = np.nan
    out["ICHIMOKU"] = np.where(np.isnan(top) | np.isnan(ten) | np.isnan(kij), np.nan,
                               np.where((c > top) & (ten > kij), 1, np.where((c < bot) & (ten < kij), -1, 0)))
    P = (day["h"] + day["l"] + day["c"]) / 3
    R1, S1 = 2 * P - day["l"], 2 * P - day["h"]
    out["PIVOT_BREAK"] = np.where(np.isnan(P) | np.isnan(c), np.nan, np.where(c > R1, 1, np.where(c < S1, -1, 0)))
    return out


def prev_day_levels(dbars, drows, rows):
    """For each bar decided at hourly row `rows[j]`, the high/low/close of the last complete UTC day before it."""
    # the day before the bar's own day: a bar ending exactly at a day's last row belongs to that day (side="left")
    idx = np.searchsorted(drows, rows, side="left") - 1
    out = {}
    for f in ("h", "l", "c"):
        x = np.full((len(rows), dbars[f].shape[1]), np.nan)
        ok = idx >= 0
        x[ok] = dbars[f][idx[ok]]
        out[f] = x
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    kl = flowfeat.load("klines", t, u.p.symbols, ("open", "high", "low"))
    c = np.asarray(u.p["close"], np.float64)
    e = np.asarray(u.elig)
    s = screen.Screen(u, windows=WINDOWS)
    dbars, drows = resample(kl["open"], kl["high"], kl["low"], c, t, 24)
    rows_out, stage, shares = [], {}, {}
    for tf, k in (("4h", 4), ("1d", 24)):
        bars, rows = resample(kl["open"], kl["high"], kl["low"], c, t, k)
        day = prev_day_levels(dbars, drows, rows)
        log(tf, "bars", len(rows))
        for rule, x in states(bars, day).items():
            name = f"{rule}/{tf}"
            x = np.nan_to_num(x)
            er = e[rows]
            n = np.maximum(er.sum(axis=1, keepdims=True), 1)
            D = np.where(er, x, 0.0) / n
            a0, b0 = s.rows["discovery"][0], s.rows["validation"][1]
            sel = (rows >= a0) & (rows < b0)
            shares[name] = {"long": float((x[sel] > 0)[er[sel]].mean()), "short": float((x[sel] < 0)[er[sel]].mean())}
            P = np.zeros((T, S))
            for j, r in enumerate(rows):
                P[r:(rows[j + 1] if j + 1 < len(rows) else T)] = D[j]
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
                    row = {"rule": name, "window": w, "cmult": cm,
                           "gross_bp_day": float(day_sum(o["gross"]).mean() * 1e4),
                           "cost_bp_day": float(day_sum(o["cost"]).mean() * 1e4),
                           "gross_exposure": float(o["gross_exposure"].mean()),
                           "net_exposure": float(o["net_exposure"].mean()),
                           **screen.window_stats(nd, s.days(a, b), mk[:Dd])}
                    if cm == 1.0:
                        row["trimmed_bp_day"] = trimmed(nd)
                    rows_out.append(row)
                    res[cm] = row
                r1 = res[1.0]
                if w == "discovery":
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0 and r1["resid_bp_day"] > 0
                else:
                    passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5 and r1["resid_bp_day"] > 0
                stage[name] = {"reached": w, "passed": bool(passed)}
                log(name, w, f"{r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.2f}),"
                    f" gross {r1['gross_bp_day']:+.2f} cost {r1['cost_bp_day']:.2f}, beta {r1['beta_ref']:+.2f}"
                    f" alpha {r1['resid_bp_day']:+.2f} t {r1['resid_t_nw10']:+.2f}", "PASS" if passed else "stop")
            del P
    df = pd.DataFrame(rows_out)
    df.drop(columns="by_year_bp_day").to_csv(out / "rules.csv", index=False)
    verdict = {"stages": stage, "state_shares_2021_2025H1": shares,
               "by_year_1x": {f"{x.rule}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "discovery_passers": [k for k, v in stage.items() if v["reached"] == "validation" or v["passed"]],
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("discovery_passers", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
