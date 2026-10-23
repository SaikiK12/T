"""seesaw_v1 (R219): do the five most liquid coins' last hours predict the altcoins (lead-lag and catch-up), as set
out in experiments/seesaw_v1/PREREG.md."""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import events, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "seesaw_v1"
START, VAL, HOLD_OUT, END = "2021-01-01", "2024-01-01", "2025-07-01", "2026-10-01"
W, MIN_PAIRS, MIN_ALTS = 720, 500, 15
VARIANTS = {"F1_H1": ("F1", 0, 1), "F1_H4": ("F1", 0, 4), "F2_L1_H4": ("F2", 1, 4), "F2_L4_H4": ("F2", 4, 4),
            "F2_L24_H24": ("F2", 24, 24)}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def roll(a, w):
    """Trailing sum over rows t-w+1..t (rows before the first full window use what exists)."""
    c = np.cumsum(a, axis=0)
    out = c.copy()
    out[w:] -= c[:-w]
    return out


def slope(x, y, w):
    """Rolling OLS slope of y[:, s] on x (1-D), pairs where both are finite, NaN under MIN_PAIRS pairs."""
    v = np.isfinite(x)[:, None] & np.isfinite(y)
    xs = np.where(v, x[:, None], 0.0)
    ys = np.where(v, y, 0.0)
    n = roll(v.astype(np.float64), w)
    sx, sy = roll(xs, w), roll(ys, w)
    sxx, sxy = roll(xs * xs, w), roll(xs * ys, w)
    del xs, ys
    with np.errstate(divide="ignore", invalid="ignore"):
        b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    b[n < MIN_PAIRS] = np.nan
    return b


def last_sum(a, L):
    """Sum over the last L rows, NaN unless all L are finite."""
    ok = roll(np.isfinite(a).astype(np.float64), L) == L
    return np.where(ok, roll(np.nan_to_num(a), L), np.nan)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t0, tv, th, t1 = (research.row_of(u.p, d) for d in (START, VAL, HOLD_OUT, END))
    assert t0 == 0
    T = t1 - t1 % 24
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in u.p.symbols])
    E = np.asarray(u.elig[:T]) & crypto[None, :]
    rank = np.asarray(u.rank[:T])
    close = np.asarray(u.p["close"][:T], np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.full_like(close, np.nan)
        lr[1:] = np.log(close[1:] / close[:-1])
    lead = E & (rank <= 5)
    alts = E & (rank >= 6)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        D = np.nanmean(np.where(lead, lr, np.nan), axis=1)
    D[lead.sum(1) == 0] = np.nan
    log("leaders per hour (mean):", round(float(lead.sum(1).mean()), 2), "alts:", round(float(alts.sum(1).mean()), 1))
    Dlag = np.concatenate([[np.nan], D[:-1]])
    g = slope(Dlag, lr, W)
    log("F1 slopes done")
    b = slope(D, lr, W)
    log("F2 betas done")
    scores = {}
    scores["F1"] = g * D[:, None]
    for L in (1, 4, 24):
        scores[("F2", L)] = b * last_sum(D, L)[:, None] - last_sum(lr, L)
    del g, b
    ret, cmat = u.ret[:T], u.cmat[:T]
    windows = {"discovery": (t0, tv), "validation": (tv, th), "holdout": (th, T)}
    rows, stage, spreads = [], {}, []

    def quint(sc):
        s = np.where(alts, sc, np.nan)
        ok = np.isfinite(s).sum(1) >= MIN_ALTS
        pct = pd.DataFrame(s).rank(axis=1, pct=True).values
        top = (pct > 0.8) & ok[:, None]
        bot = (pct <= 0.2) & ok[:, None]
        return top, bot

    def run(top, bot, H, K, a, bb, cm, delay=0):
        if delay:
            top, bot = (np.vstack([np.zeros((delay, top.shape[1]), bool), x[:-delay]]) & alts for x in (top, bot))
        w = max(a - H, 0)
        unit = 1.0 / (H * K)
        PL = slices.positions(top, H, w, bb, unit, 1)
        PS = slices.positions(bot, H, w, bb, unit, -1)
        o = slices.run(PL + PS, ret, E, cmat, w, bb, cmult=cm)
        D_ = (bb - a) // 24
        day = lambda x: x[a - w: a - w + D_ * 24].reshape(D_, 24).sum(1)
        r = np.nan_to_num(np.asarray(ret[w:bb], np.float64))
        legs = {"long_gross_bp_day": float(day((PL * r).sum(1)).mean() * 1e4),
                "short_gross_bp_day": float(day((PS * r).sum(1)).mean() * 1e4)}
        return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"]), legs

    for name, (fam, L, H) in VARIANTS.items():
        sc = scores["F1"] if fam == "F1" else scores[("F2", L)]
        top, bot = quint(sc)
        K = float((top[t0:tv].sum(1).mean() + bot[t0:tv].sum(1).mean()) / 2)
        r_next = np.nan_to_num(np.asarray(ret, np.float64))
        for w, (a, bb) in windows.items():
            if w == "holdout":                       # unread unless a variant reaches it through the stages
                continue
            nt, nb = top[a:bb].sum(1), bot[a:bb].sum(1)
            ok = (nt > 0) & (nb > 0)
            sp = ((r_next[a:bb] * top[a:bb]).sum(1)[ok] / nt[ok] - (r_next[a:bb] * bot[a:bb]).sum(1)[ok] / nb[ok])
            spreads.append({"variant": name, "window": w, "next_hour_spread_bp": float(sp.mean() * 1e4)})
        passed = True
        for w, (a, bb) in windows.items():
            if not passed:
                break
            res = {}
            for cm in (1.0, 2.0, 3.0):
                n, gr, co, legs = run(top, bot, H, K, a, bb, cm)
                s = events.summary(n)
                res[cm] = n
                rows.append({"variant": name, "K": K, "window": w, "cmult": cm, "delay_h": 0, "days": len(n),
                             "mean_bp_day": float(n.mean() * 1e4), "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                             "total": float(n.sum()), "max_dd": s.get("max_dd", np.nan),
                             "gross_bp_day": float(gr.mean() * 1e4), "cost_bp_day": float(co.mean() * 1e4), **legs})
            r1 = rows[-3]
            if w == "discovery":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2
            elif w == "validation":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5
                n, gr, co, legs = run(top, bot, H, K, a, bb, 1.0, delay=1)
                rows.append({"variant": name, "K": K, "window": w, "cmult": 1.0, "delay_h": 1, "days": len(n),
                             "mean_bp_day": float(n.mean() * 1e4), "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                             "total": float(n.sum()), "gross_bp_day": float(gr.mean() * 1e4),
                             "cost_bp_day": float(co.mean() * 1e4), **legs})
            else:
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2
            stage[name] = {"reached": w, "passed": bool(passed)}
            log(name, w, f"net {r1['mean_bp_day']:+.1f} bp/day t {r1['t_nw10']:+.2f} gross {r1['gross_bp_day']:+.1f} "
                         f"cost {r1['cost_bp_day']:.1f}", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.to_csv(out / "results.csv", index=False)
    pd.DataFrame(spreads).to_csv(out / "spreads.csv", index=False)
    verdict = {"stages": stage, "confirmed": [k for k, v in stage.items() if v["reached"] == "holdout" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    pd.set_option("display.width", 250)
    log("\n" + df.round(3).to_string(index=False))
    log("\n" + pd.DataFrame(spreads).round(3).to_string(index=False))
    log(json.dumps(verdict, indent=1))


if __name__ == "__main__":
    main()
