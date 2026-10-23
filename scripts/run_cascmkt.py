"""cascmkt_v1 (R253): buy the equal-weight market for 24 h after an hour in which at least 3 top-50 perps show R252's
long-cascade trigger, as set out in experiments/cascmkt_v1/PREREG.md. The decided read is validation 2024-01..2025-06;
2021-23 is reported as post hoc. The holdout is not read.

usage: python scripts/run_cascmkt.py
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
from run_oiwick import triggers  # noqa: E402
from run_tsbattery import WINDOWS, market_daily, trimmed  # noqa: E402

LANE = ROOT / "experiments" / "cascmkt_v1"
K, HOLD = 3, 24
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


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
    count = ((triggers(o, h, l, c, oi) == 1) & e).sum(axis=1)
    n_el = np.maximum(e.sum(axis=1, keepdims=True), 1)
    R = np.asarray(u.ret, np.float64)
    ok = e & np.isfinite(R)
    mkt_h = np.where(ok, R, 0).sum(axis=1) / np.maximum(ok.sum(axis=1), 1)    # EW market return earned over row t
    cm_ = np.r_[0, np.cumsum(mkt_h)]
    year = pd.to_datetime(t, unit="ms", utc=True).year.values

    desc = {}
    for w, (a, b) in s.rows.items():
        label = w if w == "validation" else "discovery_posthoc"
        d = {}
        for k in (1, 2, 3, 5):
            hit = np.nonzero(count[a:b] >= k)[0] + a
            d[f"K{k}"] = {"cascade_hours": int(len(hit)),
                          "by_year": {int(y): int((year[hit] == y).sum()) for y in np.unique(year[a:b])}}
            for f in (1, 4, 24):
                fwd = cm_[np.minimum(hit + f, len(mkt_h))] - cm_[hit]
                allf = cm_[np.arange(a, b) + f] - cm_[np.arange(a, b)]
                d[f"K{k}"][f"mkt_fwd_{f}h_bp"] = float(fwd.mean() * 1e4) if len(hit) else None
                d[f"K{k}"][f"uncond_fwd_{f}h_bp"] = float(allf.mean() * 1e4)
        desc[label] = d
        log(label, json.dumps(d["K3"]))

    trig = (count >= K).astype(float)[:, None]
    on = held(trig, HOLD)[:, 0] != 0
    P = np.where(e & on[:, None], 1.0, 0.0) / n_el
    rows, stage = [], {}
    for w in ("discovery", "validation"):
        a, b = s.rows[w]
        label = w if w == "validation" else "discovery_posthoc"
        mk = market_daily(u, a, b)
        res = {}
        for cmult in (1.0, 2.0, 3.0):
            r_ = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cmult)
            nd = r_["daily"]
            Dd = len(nd)
            day_sum = lambda z: z[:Dd * 24].reshape(Dd, 24).sum(axis=1)
            r = {"book": f"CASC{K}/{HOLD}", "window": label, "cmult": cmult,
                 "gross_bp_day": float(day_sum(r_["gross"]).mean() * 1e4),
                 "cost_bp_day": float(day_sum(r_["cost"]).mean() * 1e4),
                 "gross_exposure": float(r_["gross_exposure"].mean()),
                 "invested_hours": float(on[a:b].mean()),
                 **screen.window_stats(nd, s.days(a, b), mk[:Dd])}
            if cmult == 1.0:
                r["trimmed_bp_day"] = trimmed(nd)
            rows.append(r)
            res[cmult] = r
        r1 = res[1.0]
        passed = (r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0
                  and r1["resid_bp_day"] > 0)
        if w == "validation":
            stage = {"window": "validation", "passed": bool(passed)}
        log(label, f"{r1['mean_bp_day']:+.3f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.3f}),"
            f" gross {r1['gross_bp_day']:+.3f} cost {r1['cost_bp_day']:.3f}, invested {r1['invested_hours']:.3f},"
            f" alpha {r1['resid_bp_day']:+.3f} t {r1['resid_t_nw10']:+.2f} beta {r1['beta_ref']:.2f}",
            ("PASS" if passed else "fail") if w == "validation" else "(post hoc, not decided)")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "books.csv", index=False)
    verdict = {"stage": stage, "describe": desc,
               "by_year_1x": {f"{x.book}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()}}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(4).to_string(index=False))
    log(json.dumps(stage))


if __name__ == "__main__":
    main()
