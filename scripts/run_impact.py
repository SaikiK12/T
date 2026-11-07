"""impact_v1 (R262): square-root market impact on flow books A, B and X2 at capital $1k-$10M, on top of the tier
costs, as set out in experiments/impact_v1/PREREG.md. A measurement (trials 0). Books are rebuilt with R233's build()
and checked against R217 first. The holdout is not read.

usage: python scripts/run_impact.py
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import flowfeat, prereg, research, slices, stats  # noqa: E402
from run_regime import BOOKS, HOLD_OUT, R217, VAL, build  # noqa: E402

LANE = ROOT / "experiments" / "impact_v1"
CAPS = (1e3, 1e4, 1e5, 1e6, 1e7)
YS = (1.0, 0.5)
LOOK, MIN_DAYS, DECIDE_C, DECIDE_SHARE = 30, 20, 1e4, 0.10
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def daily_sum(x, D):
    """[D*24, S] hourly values -> [D, S] day sums, NaN where the coin has no finite hour that day."""
    x = x.reshape(D, 24, -1)
    return np.where(np.isfinite(x).any(axis=1), np.nan_to_num(x).sum(axis=1), np.nan)


def coin_stats(u, D):
    """(sigma, V, missing) per day and coin from days d-30..d-1, with the PREREG's conservative fill."""
    T = D * 24
    r = daily_sum(np.asarray(u.ret[:T], np.float64), D)
    qv = flowfeat.load("klines", u.p.t, u.p.symbols, ("quote_volume",))["quote_volume"]
    v = daily_sum(np.asarray(qv[:T], np.float64), D)
    sig = pd.DataFrame(r).shift(1).rolling(LOOK, min_periods=MIN_DAYS).std().values
    V = pd.DataFrame(v).shift(1).rolling(LOOK, min_periods=MIN_DAYS).mean().values
    ok = np.isfinite(sig) & np.isfinite(V) & (V > 0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        s90 = np.nanpercentile(np.where(ok, sig, np.nan), 90, axis=1)
        v10 = np.nanpercentile(np.where(ok, V, np.nan), 10, axis=1)
    s90 = pd.Series(s90).bfill().values
    v10 = pd.Series(v10).bfill().values
    return np.where(ok, sig, s90[:, None]), np.where(ok, V, v10[:, None]), ~ok


def impact_base(P, sig, V, miss, elig, D):
    """Per day: K (impact at C, Y is Y*sqrt(C)*K), traded notional / capital, and the missing-stat share of
    main-leg notional; plus each day's main-leg trades as |dP| / V (Q / V at capital C is that times C)."""
    S = P.shape[1]
    prev = np.zeros(S)
    h_prev = 0.0
    K, turn, miss_n, qv = np.zeros(D), np.zeros(D), np.zeros(D), []
    for d in range(D):
        rows = P[d * 24:(d + 1) * 24]
        dP = np.abs(np.diff(np.vstack([prev, rows]), axis=0))
        H = -rows.sum(axis=1)
        dH = np.abs(np.diff(np.concatenate([[h_prev], H])))
        prev, h_prev = rows[-1], H[-1]
        g = sig[d] / np.sqrt(V[d])
        e = elig[d * 24:(d + 1) * 24]
        n = np.maximum(e.sum(axis=1), 1)
        K[d] = (dP ** 1.5 * g).sum() + ((dH / n) ** 1.5 * (e * g).sum(axis=1)).sum()
        turn[d] = dP.sum() + dH.sum()
        miss_n[d] = (dP * miss[d]).sum()
        nz = dP > 0
        qv.append((dP / V[d])[nz])
    return K, turn, miss_n, qv


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    u, _, _ = research.load_universe()
    P, idx, elig, ret, cmat, D = build(u)
    dv, dh = research.row_of(u.p, VAL) // 24, research.row_of(u.p, HOLD_OUT) // 24
    ref = np.load(R217)
    tier = {}
    for b in BOOKS:
        tier[b] = {cm: slices.run(P[b][:dh * 24], ret, elig, cmat, 0, dh * 24, cmult=cm) for cm in (1.0, 2.0, 3.0)}
    for b, key in (("A", "A_C0"), ("B", "B_C0"), ("X2", "X2")):
        gap = float(np.max(np.abs(tier[b][1.0]["daily"] - ref[key][:dh])))
        log(f"parity {b} vs R217 {key}: max |diff| {gap:.2e}")
        assert gap < 1e-12, f"book {b} does not reproduce R217"

    sig, V, miss = coin_stats(u, dh)
    el = np.asarray(elig[:dh * 24])
    W = {"discovery": slice(0, dv), "validation": slice(dv, dh)}
    rows, caps, verdict = [], [], {"books": {}}
    for b in BOOKS:
        K, turn, miss_n, qv_all = impact_base(np.asarray(P[b][:dh * 24]), sig, V, miss, el, dh)
        info = {}
        for w, s in W.items():
            info[w] = {"turnover_per_day": float(turn[s].mean()),
                       "missing_stat_share_of_main_notional": float(miss_n[s].sum() / max(turn[s].sum(), 1e-300)),
                       "impact_bp_day_at_10k_Y1": float(np.sqrt(DECIDE_C) * K[s].mean() * 1e4)}
            for cm in (1.0, 2.0, 3.0):
                o = tier[b][cm]
                day = lambda x: x[:dh * 24].reshape(dh, 24).sum(axis=1)[s]
                net0, tc = o["daily"][s], day(o["cost"] + o["hedge_cost"])
                for Y in YS:
                    for C in CAPS:
                        imp = Y * np.sqrt(C) * K[s]
                        n = net0 - imp
                        rows.append({"book": b, "window": w, "cmult": cm, "Y": Y, "capital": C,
                                     "net_bp_day": float(n.mean() * 1e4), "t_nw10": float(stats.newey_west_t(n, 10)[2]),
                                     "net_no_impact_bp_day": float(net0.mean() * 1e4),
                                     "impact_bp_day": float(imp.mean() * 1e4), "tier_cost_bp_day": float(tc.mean() * 1e4),
                                     "impact_over_tier": float(imp.mean() / tc.mean()) if tc.mean() > 0 else np.nan})
                    if cm == 1.0:
                        m0, k = net0.mean(), Y * K[s].mean()
                        caps.append({"book": b, "window": w, "Y": Y,
                                     "C50_usd": float((0.5 * m0 / k) ** 2) if m0 > 0 else 0.0,
                                     "C0_usd": float((m0 / k) ** 2) if m0 > 0 else 0.0})
        for w, s in W.items():     # median main-leg trade's Q / V at C = $10k
            q = np.concatenate(qv_all[s])
            info[w]["median_trade_q_over_v_at_10k"] = float(np.median(q) * DECIDE_C) if q.size else np.nan
        net_val = tier[b][1.0]["daily"][W["validation"]].mean()
        share = info["validation"]["impact_bp_day_at_10k_Y1"] / (net_val * 1e4) if net_val > 0 else np.inf
        info["validation_impact_share_of_net_at_10k_Y1"] = float(share)
        verdict["books"][b] = info
        log(b, json.dumps(info))
    passed = all(v["validation_impact_share_of_net_at_10k_Y1"] < DECIDE_SHARE for v in verdict["books"].values())
    verdict["verdict"] = "DATA_PASS" if passed else "NULL"
    verdict["capacity"] = caps
    df = pd.DataFrame(rows)
    df.to_csv(out / "impact.csv", index=False)
    pd.DataFrame(caps).to_csv(out / "capacity.csv", index=False)
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1, default=float))
    pd.set_option("display.width", 250)
    log("\n" + df[(df.cmult == 1.0) & (df.Y == 1.0)].round(4).to_string(index=False))
    log("\n" + pd.DataFrame(caps).round(0).to_string(index=False))
    log("verdict", verdict["verdict"])


if __name__ == "__main__":
    main()
