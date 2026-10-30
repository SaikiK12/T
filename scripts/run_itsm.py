"""itsm_v1 (R203): intraday time-series momentum, as set out in experiments/itsm_v1/PREREG.md.

usage: python scripts/run_itsm.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import panel, prereg, research, stats  # noqa: E402

LANE = ROOT / "experiments" / "itsm_v1"
OUT = LANE / "results"
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
PERIODS = {"discovery": ("2021-01-01", "2024-01-01"), "validation": ("2024-01-01", "2025-07-01"),
           "holdout": ("2025-07-01", "2026-10-01")}


def day_trades(ret, cost, start_hour):
    """Per day d (rows 24d .. 24d+23 of the coin's clock starting at start_hour[d]): signal = sign of the first bar's
    return, trade = the last bar's return. ret[t] is bar t+1's return, so the first bar of a day starting at row s is
    ret[s - 1] and the last bar is ret[s + 22] (position set at the close of bar s + 22)."""
    D = len(start_hour)
    gross = np.full(D, np.nan)
    cst = np.full(D, np.nan)
    for d in range(1, D - 1):
        s = 24 * d + int(start_hour[d])
        if s + 23 > len(ret) - 1:
            break
        first, last = ret[s - 1], ret[s + 22]
        if not (np.isfinite(first) and np.isfinite(last)) or first == 0:
            continue
        gross[d] = np.sign(first) * last
        cst[d] = 2 * cost[s + 22]
    return gross, cst


def volume_clock(qv):
    """Hour of day with the lowest mean quote volume over the previous 30 days, per day (0 before enough data)."""
    D = len(qv) // 24
    h = np.nan_to_num(qv[: D * 24]).reshape(D, 24)
    m = pd.DataFrame(h).rolling(30, min_periods=10).mean().shift(1).values
    return np.where(np.isfinite(m).all(axis=1), np.nanargmin(np.nan_to_num(m, nan=np.inf), axis=1), 0)


def summarize(x, days):
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    if ok.sum() < 30:
        return {"n": int(ok.sum())}
    v = x[ok]
    return {"n": int(ok.sum()), "mean_bp": float(v.mean() * 1e4), "t_nw": float(stats.newey_west_t(v, 5)[2]),
            "hit": float((v > 0).mean())}


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    OUT.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    T = len(u.p.t) - len(u.p.t) % 24
    D = T // 24
    days = pd.to_datetime(u.p.t[:T:24], unit="ms", utc=True)
    syms = u.p.symbols
    need = sorted({syms.index("BTCUSDT"), syms.index("ETHUSDT")} |
                  {j for d in range(D) for j in np.flatnonzero(u.rank[24 * d] <= 10)})
    qp = panel.load_panel([syms[j] for j in need])
    assert np.array_equal(qp.t[:T], u.p.t[:T])
    series = {}
    for clock in ("utc", "volume"):
        per_coin = {}
        for k, j in enumerate(need):
            start = np.zeros(D, int) if clock == "utc" else volume_clock(qp["quote_volume"][:T, k])
            per_coin[syms[j]] = day_trades(u.ret[:T, j], u.cmat[:T, j], start)
        series[(clock, "BTC")] = per_coin["BTCUSDT"]
        series[(clock, "ETH")] = per_coin["ETHUSDT"]
        g = np.full((D, len(need)), np.nan)
        c = np.full((D, len(need)), np.nan)
        for k, j in enumerate(need):
            top = u.rank[np.arange(D) * 24, j] <= 10
            g[:, k] = np.where(top, per_coin[syms[j]][0], np.nan)
            c[:, k] = np.where(top, per_coin[syms[j]][1], np.nan)
        with np.errstate(invalid="ignore"):
            series[(clock, "top10")] = (np.nanmean(g, axis=1), np.nanmean(c, axis=1))
    rows = []
    gate = None
    for (clock, uni), (gross, cst) in series.items():
        for period, (a, b) in PERIODS.items():
            if period == "holdout":
                continue
            m = (days >= a) & (days < b)
            r = {"clock": clock, "universe": uni, "period": period}
            for name, x in (("gross", gross), ("net1", gross - cst), ("net2", gross - 2 * cst),
                            ("net3", gross - 3 * cst)):
                s = summarize(x[m], days[m])
                r.update({f"{name}_{k}": v for k, v in s.items()})
            rows.append(r)
    df = pd.DataFrame(rows)
    prim = df[(df.clock == "utc") & (df.universe == "BTC")].set_index("period")
    gate = bool(all(prim.loc[p, "gross_mean_bp"] > 0 and prim.loc[p, "gross_t_nw"] >= 2
                    for p in ("discovery", "validation")))
    verdict = {"gate1": gate}
    if gate:
        a, b = PERIODS["holdout"]
        m = (days >= a) & (days < b)
        for (clock, uni), (gross, cst) in series.items():
            r = {"clock": clock, "universe": uni, "period": "holdout"}
            for name, x in (("gross", gross), ("net1", gross - cst), ("net2", gross - 2 * cst),
                            ("net3", gross - 3 * cst)):
                r.update({f"{name}_{k}": v for k, v in summarize(x[m], days[m]).items()})
            df = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
        h = df[(df.clock == "utc") & (df.universe == "BTC") & (df.period == "holdout")].iloc[0]
        verdict["confirmed"] = bool(h.net1_mean_bp > 0 and h.net1_t_nw >= 2)
    else:
        verdict["confirmed"] = False
    df.to_csv(OUT / "results.csv", index=False)
    (OUT / "verdict.json").write_text(json.dumps(verdict, indent=1))
    log("\n" + df.round(3).to_string(index=False))
    log(verdict)


if __name__ == "__main__":
    main()
