"""oiwick_v1 (R252): fade liquidation cascades proxied by a >= 3% hourly open-interest drop plus a >= 3 ATR wick, on the
top-50 perps, as set out in experiments/oiwick_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_oiwick.py
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
from run_ictlevels import held  # noqa: E402
from run_tsbattery import WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "oiwick_v1"
OI_DROP, WICK_ATR, ATR_N = np.log(0.97), 3.0, 24
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def wilder_atr_prev(h, l, c, n=ATR_N):
    """Wilder ATR over n hourly bars ending at t-1 (the trigger bar excluded)."""
    pc = np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]])
    tr = np.fmax(h - l, np.fmax(np.abs(h - pc), np.abs(l - pc)))
    tr[~np.isfinite(h - l)] = np.nan
    a = pd.DataFrame(tr).ewm(alpha=1 / n, adjust=False, min_periods=n, ignore_na=True).mean().values
    return np.vstack([np.full((1, c.shape[1]), np.nan), a[:-1]])


def triggers(o, h, l, c, oi):
    """+1 after a long cascade (OI drop + lower wick), -1 after a short squeeze (OI drop + upper wick)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        doi = np.log(oi) - np.log(np.vstack([np.full((1, oi.shape[1]), np.nan), oi[:-1]]))
    atr = wilder_atr_prev(h, l, c)
    lower = np.fmin(o, c) - l
    upper = h - np.fmax(o, c)
    with np.errstate(invalid="ignore"):
        drop = doi <= OI_DROP
        lw = drop & (lower >= WICK_ATR * atr)
        uw = drop & (upper >= WICK_ATR * atr)
    return np.where(lw & ~uw, 1, np.where(uw & ~lw, -1, 0))


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    kl = flowfeat.load("klines", t, u.p.symbols, ("open", "high", "low"))
    m = flowfeat.load("metrics", t, u.p.symbols, ("oi",))
    o, h, l = (np.asarray(kl[k], np.float64) for k in ("open", "high", "low"))
    c = np.asarray(u.p["close"], np.float64)
    oi = np.asarray(m["oi"], np.float64)
    e = np.asarray(u.elig)
    s = screen.Screen(u, windows=WINDOWS)
    trig = triggers(o, h, l, c, oi) * e
    a0, b0 = s.rows["discovery"]
    lc = np.log(np.where(c > 0, c, np.nan))
    fwd = {}
    for side, v in (("long_cascade_fade", 1), ("squeeze_fade", -1)):
        hit = trig[a0:b0] == v
        fwd[side] = {"n": int(hit.sum())}
        for k in (1, 4, 24):
            f = lc[a0 + k:b0 + k] - lc[a0:b0]
            x = f[hit]
            x = x[np.isfinite(x)]
            fwd[side][f"raw_fwd_{k}h_bp"] = float(x.mean() * 1e4) if len(x) else None
    log("discovery triggers and raw forward returns", fwd)
    n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
    rows, stage = [], {}
    for side, keep in (("ALL", (1, -1)), ("SQZ", (-1,))):
        x0 = np.where(np.isin(trig, keep), trig, 0)
        for hold in (4, 24):
            name = f"{side}/{hold}"
            P = np.where(e, held(x0, hold), 0.0) / n_el
            passed = True
            for w, (a, b) in s.rows.items():
                if not passed:
                    break
                mk = market_daily(u, a, b)
                res = {}
                for cm in (1.0, 2.0, 3.0):
                    r_ = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                    nd = r_["daily"]
                    Dd = len(nd)
                    day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
                    r = {"book": name, "window": w, "cmult": cm,
                         "gross_bp_day": float(day_sum(r_["gross"]).mean() * 1e4),
                         "cost_bp_day": float(day_sum(r_["cost"]).mean() * 1e4),
                         "gross_exposure": float(r_["gross_exposure"].mean()),
                         "net_exposure": float(r_["net_exposure"].mean()),
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
                log(name, w, f"{r1['mean_bp_day']:+.3f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.3f}),"
                    f" gross {r1['gross_bp_day']:+.3f} cost {r1['cost_bp_day']:.3f}, exposure {r1['gross_exposure']:.4f},"
                    f" alpha {r1['resid_bp_day']:+.3f} t {r1['resid_t_nw10']:+.2f}", "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "discovery_triggers_and_raw_forward": fwd,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "passers": [k for k, v in stage.items() if v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(4).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "passers")}, indent=1))


if __name__ == "__main__":
    main()
