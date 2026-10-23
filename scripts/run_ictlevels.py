"""ictlevels_v1 (R246): round-number levels, SMT divergence against BTC and the 8 AM New York range on hourly bars of
the top-50 perps, directional books, as set out in experiments/ictlevels_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_ictlevels.py
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

LANE = ROOT / "experiments" / "ictlevels_v1"
HOLD = 24
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def held(trig, hold=HOLD):
    """trig [T, S] in {-1, 0, +1}: each nonzero trigger sets the state for `hold` rows (its own row included); a newer
    trigger replaces it."""
    x = pd.DataFrame(np.where(trig != 0, trig, np.nan))
    return np.nan_to_num(x.ffill(limit=hold - 1).values)


def round_numbers(h, l, c):
    """RN_CROSS and RN_REJECT triggers on the two-significant-figure grid of the prior close."""
    pc = np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        g = 10.0 ** (np.floor(np.log10(pc)) - 1)
        k0, k1 = np.floor(pc / g), np.floor(c / g)
    ok = np.isfinite(g) & np.isfinite(c) & np.isfinite(h) & np.isfinite(l) & (pc > 0)
    cross = np.where(ok & (k1 > k0), 1, np.where(ok & (k1 < k0), -1, 0))
    up, dn = (k0 + 1) * g, k0 * g
    rej_hi = ok & (h >= up) & (c < up)
    rej_lo = ok & (l <= dn) & (c > dn) & (pc > dn)
    reject = np.where(rej_hi & ~rej_lo, -1, np.where(rej_lo & ~rej_hi, 1, 0))
    reject[cross != 0] = 0
    return cross, reject


def smt(h, l, ib, n):
    """Fade-signed SMT triggers: -1 where a coin makes a new n-hour high that BTC (column ib) does not, +1 for lows."""
    H = pd.DataFrame(h).rolling(n, min_periods=n).max().shift(1).values
    L = pd.DataFrame(l).rolling(n, min_periods=n).min().shift(1).values
    with np.errstate(invalid="ignore"):
        nh, nl = h > H, l < L
    bear = nh & ~nh[:, [ib]]
    bull = nl & ~nl[:, [ib]]
    x = np.where(bear & ~bull, -1, np.where(bull & ~bear, 1, 0))
    x[:, ib] = 0
    return x


def am8(h, l, c, t):
    """Fade-signed 8 AM New York range book, already held until the 16:00 New York close (state per row)."""
    ny = pd.to_datetime(t, unit="ms", utc=True).tz_convert("America/New_York")
    hr, wd, day = np.asarray(ny.hour), np.asarray(ny.weekday), np.asarray(ny.normalize().asi8)
    T, S = c.shape
    st = np.zeros((T, S))
    for r in np.flatnonzero((hr == 8) & (wd < 5)):
        hi, lo = h[r], l[r]
        rows = r + 1 + np.arange(7)                        # bars opening 09:00..15:00 on the same day
        rows = rows[rows < T]
        rows = rows[day[rows] == day[r]]
        if len(rows) < 2 or hr[rows[-1]] != 15:
            continue
        open_ = np.isfinite(hi) & np.isfinite(lo)
        done = ~open_
        for j, q in enumerate(rows[:-1]):                  # triggers at bars opening 09:00..14:00
            with np.errstate(invalid="ignore"):
                up, dn = (c[q] > hi) & ~done, (c[q] < lo) & ~done
            s = np.where(up, -1.0, np.where(dn, 1.0, 0.0))
            hit = s != 0
            if hit.any():
                st[q:rows[-1], hit] = s[hit]                # held through row rows[-1]-1, which earns the 15:00 bar
            done |= hit
    return st


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    kl = flowfeat.load("klines", t, u.p.symbols, ("high", "low"))
    h, l = np.asarray(kl["high"], np.float64), np.asarray(kl["low"], np.float64)
    c = np.asarray(u.p["close"], np.float64)
    e = np.asarray(u.elig)
    ib = list(u.p.symbols).index("BTCUSDT")
    s = screen.Screen(u, windows=WINDOWS)

    cross, reject = round_numbers(h, l, c)
    trig = {"RN_CROSS": cross, "RN_REJECT": reject}
    for n in (24, 168):
        x = smt(h, l, ib, n)
        trig[f"SMT_FADE/{n}"], trig[f"SMT_FOLLOW/{n}"] = x, -x
    states = {k: held(v) for k, v in trig.items()}
    a8 = am8(h, l, c, t)
    states["AM8_FADE"], states["AM8_FOLLOW"] = a8, -a8
    a0, b0 = s.rows["discovery"]
    counts = {k: int((np.abs(v[a0:b0]) * e[a0:b0]).sum()) for k, v in trig.items()}
    entries = np.abs(np.diff(a8[a0:b0], axis=0, prepend=0)) * (a8[a0:b0] != 0) * e[a0:b0]
    counts["AM8_FADE"] = counts["AM8_FOLLOW"] = int((entries > 0).sum())
    log("discovery triggers on eligible coins", counts)

    n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
    rows_out, stage = [], {}
    for name, x in states.items():
        P = np.where(e, x, 0.0) / n_el
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
                row = {"book": name, "window": w, "cmult": cm,
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
    df = pd.DataFrame(rows_out)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "discovery_triggers": counts,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "discovery_passers": [k for k, v in stage.items() if v["reached"] == "validation" or v["passed"]],
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("discovery_passers", "validation_passers")}, indent=1))


if __name__ == "__main__":
    main()
