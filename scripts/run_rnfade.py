"""rnfade_v1 (R249): fade the day's first close through a round-number level (two- or one-significant-figure grid),
held 4 h or 24 h, against the same book on a half-step-shifted grid, on the crypto validation window only, as set out
in experiments/rnfade_v1/PREREG.md.

usage: python scripts/run_rnfade.py
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
from run_ictlevels import held  # noqa: E402
from run_tsbattery import WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "rnfade_v1"
DAY = 86_400_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def first_cross_fade(c, t, sig, off):
    """Fade-signed triggers [T, S]: the first close per coin per UTC day through a level of the grid with step
    10^(floor(log10 c_{t-1}) - sig + 1), shifted by `off` steps."""
    pc = np.vstack([np.full((1, c.shape[1]), np.nan), c[:-1]])
    with np.errstate(invalid="ignore", divide="ignore"):
        g = 10.0 ** (np.floor(np.log10(pc)) - sig + 1)
        k0, k1 = np.floor(pc / g - off), np.floor(c / g - off)
    ok = np.isfinite(g) & np.isfinite(c) & (pc > 0)
    x = np.where(ok & (k1 > k0), -1, np.where(ok & (k1 < k0), 1, 0))
    day = np.asarray(t) // DAY
    out = np.zeros_like(x)
    for d in np.unique(day):
        r = np.flatnonzero(day == d)
        blk = x[r]
        hit = blk != 0
        first = hit.argmax(axis=0)
        has = hit.any(axis=0)
        cols = np.flatnonzero(has)
        out[r[first[cols]], cols] = blk[first[cols], cols]
    return out


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    t = np.asarray(u.p.t)
    c = np.asarray(u.p["close"], np.float64)
    e = np.asarray(u.elig)
    s = screen.Screen(u, windows=WINDOWS)
    a, b = s.rows["validation"]
    mk = market_daily(u, a, b)
    n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
    rows, stage, diff, trades = [], {}, {}, {}
    for grid, sig in (("RN2SF", 2), ("RN1SF", 1)):
        trig = {"round": first_cross_fade(c, t, sig, 0.0), "control": first_cross_fade(c, t, sig, 0.5)}
        for kind, x in trig.items():
            trades[f"{grid}/{kind}"] = int((np.abs(x[a:b]) * e[a:b]).sum())
        for hold in (4, 24):
            name = f"{grid}/{hold}"
            daily, res = {}, {}
            for kind, x in trig.items():
                P = np.where(e, held(x, hold), 0.0) / n_el
                for cm in (1.0, 2.0, 3.0):
                    o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                    nd = o["daily"]
                    Dd = len(nd)
                    day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
                    r = {"book": name, "grid": kind, "window": "validation", "cmult": cm,
                         "gross_bp_day": float(day_sum(o["gross"]).mean() * 1e4),
                         "cost_bp_day": float(day_sum(o["cost"]).mean() * 1e4),
                         "gross_exposure": float(o["gross_exposure"].mean()),
                         "net_exposure": float(o["net_exposure"].mean()),
                         **screen.window_stats(nd, s.days(a, b), mk[:Dd])}
                    if cm == 1.0:
                        r["trimmed_bp_day"] = trimmed(nd)
                        daily[kind] = nd
                    rows.append(r)
                    res[(kind, cm)] = r
            r1, r2 = res[("round", 1.0)], res[("round", 2.0)]
            passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and r2["mean_bp_day"] > 0 and r1["resid_bp_day"] > 0
            stage[name] = {"reached": "validation", "passed": bool(passed)}
            d = daily["round"] - daily["control"]
            diff[name] = {"net_diff_bp_day": float(d.mean() * 1e4), "t_nw10": float(stats.newey_west_t(d, 10)[2])}
            c1 = res[("control", 1.0)]
            log(name, f"round {r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw10']:+.2f} (2x {r2['mean_bp_day']:+.2f}),"
                f" gross {r1['gross_bp_day']:+.2f} cost {r1['cost_bp_day']:.2f}, alpha {r1['resid_bp_day']:+.2f};"
                f" control {c1['mean_bp_day']:+.2f} (gross {c1['gross_bp_day']:+.2f}); diff {diff[name]}",
                "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stages": stage, "round_minus_control": diff, "trades_validation": trades,
               "by_year_1x": {f"{x.book}/{x.grid}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "passers": [k for k, v in stage.items() if v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "passers", "round_minus_control", "trades_validation")}, indent=1))


if __name__ == "__main__":
    main()
