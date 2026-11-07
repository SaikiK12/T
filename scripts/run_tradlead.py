"""tradlead_v1 (R261): does the last hour of TradFi perps (commodities CMD, US equities EQ) lead crypto? A market-timing
book (TS) and a beta cross-section (XS), holds 1/4/24 h, sign chosen in discovery 2026-01..05, validation 2026-06..09
for discovery passers only, as set out in experiments/tradlead_v1/PREREG.md. All of it lies in the spent holdout.

usage: python scripts/run_tradlead.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg, research, screen, slices  # noqa: E402

LANE = ROOT / "experiments" / "tradlead_v1"
LEADERS = {"CMD": ("XAUUSDT", "XAGUSDT", "CLUSDT", "BZUSDT"),
           "EQ": ("QQQUSDT", "NVDAUSDT", "TSLAUSDT", "INTCUSDT", "MUUSDT", "MRVLUSDT", "SNDKUSDT", "NBISUSDT")}
HOLDS = (1, 4, 24)
Z_MIN, LOOK, MIN_OBS, MIN_COINS, WARM = 1.0, 720, 240, 10, 24
WINDOWS = (("discovery", "2026-01-01", "2026-06-01"), ("validation", "2026-06-01", "2026-09-30"))
START = "2025-11-01"   # first row loaded; leaders start 2025-12-11 at the earliest
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def rsum(x, n):
    """Sum over the last n rows (including the current one); x has no NaN."""
    c = np.cumsum(x, axis=0)
    out = c.copy()
    out[n:] -= c[:-n]
    return out


def lagged(x):
    """Row t holds x[t - 1]: the value for the bar that ends at row t's close."""
    y = np.full_like(x, np.nan)
    y[1:] = x[:-1]
    return y


def leader(R, cols):
    """(Lk, z): the leader's return over the bar ending at row t, and Lk over its trailing standard deviation."""
    with np.errstate(all="ignore"):
        L = np.nanmean(R[:, cols], axis=1)
    Lk = lagged(L)
    sd = pd.Series(Lk).rolling(LOOK, min_periods=MIN_OBS).std().values
    return Lk, Lk / sd


def betas(R, Lk):
    """beta[t, s]: OLS slope of coin s's return over the bar ending at row k on Lk[k], k in t-719..t."""
    Rk = lagged(R)
    m = np.isfinite(Rk) & np.isfinite(Lk)[:, None]
    x = np.where(m, Lk[:, None], 0.0)
    y = np.where(m, Rk, 0.0)
    n = rsum(m.astype(np.float64), LOOK)
    sx, sy, sxy, sxx = rsum(x, LOOK), rsum(y, LOOK), rsum(x * y, LOOK), rsum(x * x, LOOK)
    nn = np.maximum(n, 1)
    var, cov = sxx - sx * sx / nn, sxy - sx * sy / nn
    return np.where((n >= MIN_OBS) & (var > 0), cov / np.where(var > 0, var, 1.0), np.nan)


def xs_open(beta, Lk, e, trig):
    """[T, S] slice weights of the follow XS book: +1/q on the top quintile of beta x Lk, -1/q on the bottom one."""
    out = np.zeros(beta.shape)
    for t in np.flatnonzero(trig):
        ok = e[t] & np.isfinite(beta[t])
        n = int(ok.sum())
        if n < MIN_COINS:
            continue
        idx = np.flatnonzero(ok)
        order = idx[np.argsort(beta[t, idx] * Lk[t], kind="stable")]
        q = n // 5
        out[t, order[-q:]] += 1.0 / q
        out[t, order[:q]] -= 1.0 / q
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s0 = research.row_of(u.p, START)
    t = np.asarray(u.p.t[s0:])
    syms = list(u.p.symbols)
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in syms])
    R = np.asarray(u.ret[s0:], np.float64)
    elig = np.asarray(u.elig[s0:]) & crypto[None, :]
    ret, cmat = u.ret[s0:], u.cmat[s0:]
    W = {w: (research.row_of(u.p, a) - s0, research.row_of(u.p, b) - s0) for w, a, b in WINDOWS}
    W = {w: (a, b - (b - a) % 24) for w, (a, b) in W.items()}
    wmkt = elig / np.maximum(elig.sum(axis=1, keepdims=True), 1)
    mkt = np.where(elig & np.isfinite(R), R, 0).sum(axis=1) / np.maximum((elig & np.isfinite(R)).sum(axis=1), 1)
    hour = pd.to_datetime(t, unit="ms", utc=True).hour.values
    cash = (hour >= 13) & (hour < 20)

    def daily(x, a, b):
        D = (b - a) // 24
        return x[a:a + D * 24].reshape(D, 24).sum(axis=1)

    def run(P, a, b, cm):
        w = a - WARM
        o = slices.run(P[w:b], ret, elig, cmat, w, b, hedge=False, cmult=cm, missing="raise")
        D = (b - a) // 24
        day = lambda x: x[a - w: a - w + D * 24].reshape(D, 24).sum(axis=1)
        return day(o["net"]), day(o["gross"]), day(o["cost"]), float(o["gross_exposure"][a - w:].mean())

    sig, desc = {}, {}
    for name, members in LEADERS.items():
        cols = [syms.index(s) for s in members]
        Lk, z = leader(R, cols)
        trig = np.isfinite(z) & (np.abs(z) >= Z_MIN)
        sig[name] = (Lk, z, trig)
        d = {w: {"trigger_hours": int(trig[a:b].sum()), "signal_hours": int(np.isfinite(z[a:b]).sum())}
             for w, (a, b) in W.items()}
        a, b = W["discovery"]
        for lab_, msk in (("all", np.ones(len(t), bool)), ("13-20utc", cash), ("other", ~cash)):
            k = np.zeros(len(t), bool)
            k[a:b] = True
            k &= msk & np.isfinite(Lk)
            d["discovery"][f"corr_lead_{lab_}"] = float(np.corrcoef(Lk[k], mkt[k])[0, 1])
            mk0 = lagged(mkt)
            k2 = k & np.isfinite(mk0)
            d["discovery"][f"corr_same_bar_{lab_}"] = float(np.corrcoef(Lk[k2], mk0[k2])[0, 1])
        desc[name] = d
        log(name, json.dumps(d))

    rows, verdict = [], {"describe": desc, "books": {}}
    for name, (Lk, z, trig) in sig.items():
        B = betas(R, Lk)
        xs = xs_open(B, Lk, elig, trig)
        ts = np.where(trig, np.sign(z), 0.0)
        for kind in ("TS", "XS"):
            for H in HOLDS:
                if kind == "TS":
                    P1 = slices.positions(ts[:, None], H, 0, len(t), 1.0 / H, 1) * wmkt
                else:
                    P1 = slices.positions(xs, H, 0, len(t), 1.0 / H, 1)
                key = f"{name}/{kind}/{H}"
                a, b = W["discovery"]
                mk = daily(mkt, a, b)
                means = {dd: run(dd * P1, a, b, 1.0)[0].mean() for dd in (1, -1)}
                dsel = 1 if means[1] >= means[-1] else -1
                P = dsel * P1
                res = {}
                for w in ("discovery", "validation"):
                    if w == "validation" and not res["discovery"]["passed"]:
                        break
                    a, b = W[w]
                    mk = daily(mkt, a, b)
                    per = {}
                    for cm in (1.0, 2.0, 3.0):
                        n, g, c, gx = run(P, a, b, cm)
                        st = screen.window_stats(n, t[a:a + (b - a) // 24 * 24:24], mk)
                        mon = pd.to_datetime(t[a:a + len(n) * 24:24], unit="ms", utc=True).strftime("%Y-%m")
                        per[cm] = n
                        rows.append({"book": key, "sign": "follow" if dsel == 1 else "fade", "window": w, "cmult": cm,
                                     "gross_bp_day": float(g.mean() * 1e4), "cost_bp_day": float(c.mean() * 1e4),
                                     "gross_exposure": gx, **st,
                                     "by_month_bp_day": {m_: float(n[mon == m_].mean() * 1e4) for m_ in np.unique(mon)}})
                    r1 = rows[-3]
                    if w == "discovery":
                        ok = r1["t_nw10"] >= 2 and per[2.0].mean() > 0
                    else:
                        ok = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5 and per[2.0].mean() > 0
                    res[w] = {"passed": bool(ok), "mean_1x_bp": r1["mean_bp_day"], "t_1x": r1["t_nw10"],
                              "mean_2x_bp": float(per[2.0].mean() * 1e4), "mean_3x_bp": float(per[3.0].mean() * 1e4)}
                verdict["books"][key] = {"sign": "follow" if dsel == 1 else "fade",
                                         "discovery_1x_mean_follow_bp": float(means[1] * 1e4),
                                         "discovery_1x_mean_fade_bp": float(means[-1] * 1e4), **res}
                log(key, json.dumps(verdict["books"][key]))
    df = pd.DataFrame(rows)
    df.drop(columns=["by_year_bp_day", "by_month_bp_day"]).to_csv(out / "books.csv", index=False)
    verdict["by_month_1x"] = {f"{x.book}/{x.window}": x.by_month_bp_day for x in df[df.cmult == 1.0].itertuples()}
    verdict["discovery_passers"] = [k for k, v in verdict["books"].items() if v["discovery"]["passed"]]
    verdict["validation_passers"] = [k for k, v in verdict["books"].items()
                                     if v.get("validation", {}).get("passed")]
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns=["by_year_bp_day", "by_month_bp_day"]).round(4).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("discovery_passers", "validation_passers")}))


if __name__ == "__main__":
    main()
