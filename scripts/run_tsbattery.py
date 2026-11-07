"""tsbattery_v1 (R242): week-open bias, pre-FOMC drift, ETH/BTC regime and vol-managed trend on the top-50 perps,
as set out in experiments/tsbattery_v1/PREREG.md. The holdout is not read.

usage: python scripts/run_tsbattery.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import features, prereg, research, screen, sessions, slices  # noqa: E402

LANE = ROOT / "experiments" / "tsbattery_v1"
HOUR = 3_600_000
WINDOWS = (("discovery", "2021-01-01", "2024-01-01"), ("validation", "2024-01-01", "2025-07-01"))
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def hold_daily(D, rows, T):
    """Positions D[k] decided at rows[k] (the bar ending 00:00 UTC), held until the next decision row."""
    P = np.zeros((T, D.shape[1]))
    for k, r in enumerate(rows):
        P[r:(rows[k + 1] if k + 1 < len(rows) else T)] = D[k]
    return P


def build(u):
    t = np.asarray(u.p.t)
    T, S = len(t), len(u.p.symbols)
    c = np.asarray(u.p["close"], np.float64)
    lc = np.where(c > 0, np.log(np.where(c > 0, c, 1)), np.nan)
    e = np.asarray(u.elig)
    end = pd.to_datetime(t + HOUR, unit="ms", utc=True)
    rows = np.flatnonzero(np.asarray(end.hour) == 0)
    wd = np.asarray(end.weekday)[rows]
    n = np.maximum(e[rows].sum(axis=1, keepdims=True), 1)
    books = {}

    # 1. WEEKOPEN
    D = np.zeros((len(rows), S))
    wopen = None
    for k, r in enumerate(rows):
        if wd[k] == 0:
            wopen = c[r]
            continue
        if wopen is None:
            continue
        with np.errstate(invalid="ignore", divide="ignore"):
            s = np.sign(c[r] / wopen - 1)
        D[k] = np.where(e[r] & np.isfinite(s), s, 0) / n[k]
    books["WEEKOPEN"] = hold_daily(D, rows, T)

    # 2. FOMC
    P = np.zeros((T, S))
    events = []
    for d in sessions.FOMC:
        prev = (pd.Timestamp(d) - pd.Timedelta(days=1)).date()
        start = pd.Timestamp(f"{prev} 14:00", tz="America/New_York")
        i = int((start.tz_convert("UTC").value // 10**6 - HOUR - t[0]) // HOUR)
        if 0 <= i and i + 24 <= T:
            P[i:i + 24] = e[i] / max(e[i].sum(), 1)
            events.append(int(t[i]))
    books["FOMC"] = P

    # 3. ETHBTC
    sym = list(u.p.symbols)
    ib, ie = sym.index("BTCUSDT"), sym.index("ETHUSDT")
    x = (lc[:, ie] - lc[:, ib])
    x60 = np.full(T, np.nan)
    x60[1440:] = x[1440:] - x[:-1440]
    D = np.zeros((len(rows), S))
    for k, r in enumerate(rows):
        if not np.isfinite(x60[r]):
            continue
        alt = e[r].copy()
        alt[ib] = False
        sg = 1.0 if x60[r] > 0 else -1.0
        D[k] = sg * 0.5 * alt / max(alt.sum(), 1)
        D[k, ib] = -sg * 0.5
    books["ETHBTC"] = hold_daily(D, rows, T)

    # 4. VOLTREND
    r1 = np.asarray(u.ret, np.float64)
    vol = features.roll(r1, 720, "std").astype(np.float64) * np.sqrt(8760)
    m30 = np.full_like(lc, np.nan)
    m30[720:] = lc[720:] - lc[:-720]
    D = np.zeros((len(rows), S))
    for k, r in enumerate(rows):
        ok = e[r] & np.isfinite(vol[r]) & (vol[r] > 0) & np.isfinite(m30[r])
        if ok.sum() == 0:
            continue
        D[k] = np.where(ok, np.sign(np.nan_to_num(m30[r])) * np.minimum(0.40 / np.where(ok, vol[r], 1), 2), 0) / ok.sum()
    books["VOLTREND"] = hold_daily(D, rows, T)
    return books, events


def market_daily(u, a, b):
    r = np.asarray(u.ret[a:b], np.float64)
    e = np.asarray(u.elig[a:b]) & np.isfinite(r)
    h = np.where(e, r, 0).sum(axis=1) / np.maximum(e.sum(axis=1), 1)
    D = len(h) // 24
    return h[:D * 24].reshape(D, 24).sum(axis=1)


def trimmed(n, k=10):
    s = np.sort(n)
    return float(s[k:-k].mean() * 1e4) if len(s) > 2 * k else np.nan


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    s = screen.Screen(u, windows=WINDOWS)
    books, events = build(u)
    rows, stage, extra = [], {}, {"fomc_events": {}, "market": {}}
    for w, (a, b) in s.rows.items():
        mk = market_daily(u, a, b)
        extra["market"][w] = screen.window_stats(mk, s.days(a, b))
        extra["fomc_events"][w] = int(sum(u.p.t[a] <= x < u.p.t[b - 1] for x in events))
    for name, P in books.items():
        passed = True
        for w, (a, b) in s.rows.items():
            if not passed:
                break
            mk = market_daily(u, a, b)
            res = {}
            for cm in (1.0, 2.0, 3.0):
                o = slices.run(P[a:b], u.ret, u.elig, u.cmat, a, b, hedge=False, cmult=cm)
                n = o["daily"]
                D = len(n)
                day = lambda x: x[:D * 24].reshape(D, 24).sum(axis=1)
                row = {"rule": name, "window": w, "cmult": cm, "gross_bp_day": float(day(o["gross"]).mean() * 1e4),
                       "cost_bp_day": float(day(o["cost"]).mean() * 1e4),
                       "gross_exposure": float(o["gross_exposure"].mean()), "net_exposure": float(o["net_exposure"].mean()),
                       **screen.window_stats(n, s.days(a, b), mk[:D])}
                if cm == 1.0:
                    row["trimmed_bp_day"] = trimmed(n)
                rows.append(row)
                res[cm] = row
            r1 = res[1.0]
            if w == "discovery":
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 2 and res[2.0]["mean_bp_day"] > 0 and r1["resid_bp_day"] > 0
            else:
                passed = r1["mean_bp_day"] > 0 and r1["t_nw10"] >= 1.5 and r1["resid_bp_day"] > 0
            stage[name] = {"reached": w, "passed": bool(passed)}
            log(name, w, f"{r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw10']:+.2f} (2x {res[2.0]['mean_bp_day']:+.2f}), "
                f"beta {r1['beta_ref']:+.2f} alpha {r1['resid_bp_day']:+.2f} t {r1['resid_t_nw10']:+.2f}",
                "PASS" if passed else "stop")
    df = pd.DataFrame(rows)
    df.drop(columns="by_year_bp_day").to_csv(out / "rules.csv", index=False)
    verdict = {"stages": stage, **extra,
               "by_year_1x": {f"{x.rule}/{x.window}": x.by_year_bp_day for x in df[df.cmult == 1.0].itertuples()},
               "validation_passers": [k for k, v in stage.items() if v["reached"] == "validation" and v["passed"]]}
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df.drop(columns="by_year_bp_day").round(3).to_string(index=False))
    log(json.dumps({k: verdict[k] for k in ("stages", "validation_passers", "fomc_events")}, indent=1))


if __name__ == "__main__":
    main()
