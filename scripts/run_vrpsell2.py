"""R409 vrpsell_v2 (M477; R408 with its stats call fixed): sell the crypto variance risk premium on Deribit, as set out in
experiments/vrpsell_v2/PREREG.md.

Each Friday a book sells one at-the-money straddle on 1 coin of BTC (or ETH) on the next weekly expiry (Friday + 7 d,
08:00 UTC), delta-hedges it every hour with the USDT perp and holds it to expiry.

- **Entry:** the first of the hours starting 08:00, 09:00, 10:00 or 11:00 UTC that has trades in both the call and the
  put of one strike for that expiry. The strike is the one nearest the perp price at the start of that hour. The book
  sells at the end of that hour, at the amount-weighted IV of the two legs (`data/deribit_trades/<CUR>/flow`, a
  mid-like price) less the measured half-spread, in vol points.
- **Model:** Black-Scholes, zero rates, forward = the perp price.
- **Hedge:** hourly, at the mid IV, long 2N(d1) - 1 coins on the perp. Every change pays the taker fee; funding is
  paid on the hedge.
- **Settlement:** at the perp price at 08:00 UTC on expiry day, a proxy for Deribit's 30-minute index average.
- **Costs at m x (m = 1, 2, 3):** the half-spread, the option fee, the delivery fee and the hedge taker fee are all
  scaled; funding is not.
- **Unit:** P&L per coin of straddle, in fractions of the entry price (one week of notional).

usage: python scripts/run_vrpsell2.py [--plumbing]
  --plumbing: entry counts and IV coverage only, no P&L is computed
"""
import argparse
import json
import sys
import time
from math import erf, log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs, load_funding  # noqa: E402
from scripts.run_optflow import COINS, PROVENANCE, hourly_prices, load_rows  # noqa: E402

LANE = ROOT / "experiments" / "vrpsell_v2"
HOUR, DAY = 3_600_000, 86_400_000
YEAR_H = 365.0 * 24.0
BUCKETS = (8, 9, 10, 11)                         # entry-hour starts, UTC, on Fridays
HALF_SPREAD = {"BTC": 0.9, "ETH": 1.1}          # vol points, measured 2026-11-05 (costs_measured_20261105.json)
OPT_FEE = 3e-4                                   # per leg, of the underlying, capped at 12.5% of the leg price
DEL_FEE = 1.5e-4                                 # delivery, of the underlying, capped at 12.5% of the payoff
HEDGE_FEE = 5e-4                                 # perp taker, per unit of notional traded
CAP = 0.125
CMULTS = (1, 2, 3)
IV_RANGE = (10.0, 300.0)                         # percent
HALVES = (("2021-01-01", "2024-01-01"), ("2024-01-01", "2026-10-01"))
T_MIN = 2.24                                     # one-sided 1.25% (Bonferroni over 2 trials)
NW_LAG = 2
TRIM = 0.05
WO_BEST = 10
log_ = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ncdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def bs(S, K, tau_y, sig):
    """(call, put, d1) under Black-Scholes with zero rates and forward S."""
    if tau_y <= 0 or sig <= 0:
        return max(S - K, 0.0), max(K - S, 0.0), (np.inf if S > K else -np.inf)
    v = sig * sqrt(tau_y)
    d1 = (log(S / K) + 0.5 * v * v) / v
    d2 = d1 - v
    c = S * ncdf(d1) - K * ncdf(d2)
    return c, c - (S - K), d1


def fridays(t0=T0, t1=T1):
    """Friday 00:00 UTC instants D with D + 7 d + 8 h <= t1 (the expiry must be inside the data)."""
    d = pd.Timestamp(t0, unit="ms")
    d = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    out = []
    while int(d.value // 10**6) + 7 * DAY + 8 * HOUR <= t1:
        out.append(int(d.value // 10**6))
        d += pd.Timedelta(days=7)
    return out


def pick_entry(rows, D, PH, t0=T0):
    """The entry for Friday D: (bucket start, strike, call IV, put IV), or (None, reason)."""
    E = D + 7 * DAY + 8 * HOUR
    week = rows[rows.expiry_ms == E]
    if week.empty:
        return None, "no_expiry"
    for h in BUCKETS:
        b = D + h * HOUR
        r = week[week.t == b]
        both = r.pivot_table(index="strike", columns="cp", values="iv", aggfunc="first")
        if not {"C", "P"} <= set(both.columns):
            continue
        both = both.dropna()
        both = both[(both.C.between(*IV_RANGE)) & (both.P.between(*IV_RANGE))]
        k = (b - t0) // HOUR
        if both.empty or not 0 <= k < len(PH) or not np.isfinite(PH[k]):
            continue
        K = float(min(both.index, key=lambda s: (abs(s - PH[k]), s)))
        return (b, K, float(both.loc[K, "C"]), float(both.loc[K, "P"])), None
    return None, "no_two_legged_strike"


def straddle(S, K, iv_mid, half, m, F_t, F_r, te, E, t0=T0):
    """Net P&L of one short hedged straddle on 1 coin over [te, E] (dict, USD and fraction of the entry price).
    S: hourly prices PH (PH[k] at t0 + k h). half: half-spread in vol points. m: cost multiplier."""
    k0, kE = (te - t0) // HOUR, (E - t0) // HOUR
    path = S[k0: kE + 1]
    if len(path) != kE - k0 + 1 or not np.all(np.isfinite(path)):
        return None
    S0, ST = float(path[0]), float(path[-1])
    n = kE - k0
    sig_mid = iv_mid / 100.0
    sig_s = max(sig_mid - m * half / 100.0, 1e-4)
    c, p, _ = bs(S0, K, n / YEAR_H, sig_s)
    premium = c + p
    opt_fee = m * (min(OPT_FEE * S0, CAP * c) + min(OPT_FEE * S0, CAP * p))
    H = np.empty(n)
    for i in range(n):
        _, _, d1 = bs(float(path[i]), K, (n - i) / YEAR_H, sig_mid)
        H[i] = 2.0 * ncdf(d1) - 1.0 if np.isfinite(d1) else (1.0 if d1 > 0 else -1.0)
    hedge_pnl = float(np.sum(H * np.diff(path)))
    traded = abs(H[0]) * path[0] + np.sum(np.abs(np.diff(H)) * path[1:n]) + abs(H[-1]) * ST
    hedge_fee = m * HEDGE_FEE * float(traded)
    sel = (F_t > te) & (F_t <= E)
    fund = 0.0
    for ft, fr in zip(F_t[sel], F_r[sel]):
        i = min(int((ft - te) // HOUR) - (1 if (ft - te) % HOUR == 0 else 0), n - 1)
        fund += H[i] * float(path[i + 1]) * fr          # a long hedge pays a positive rate
    payoff = abs(ST - K)
    delivery = m * min(DEL_FEE * ST, CAP * payoff) if payoff > 0 else 0.0
    net = premium - payoff + hedge_pnl - opt_fee - hedge_fee - fund - delivery
    rv = float(np.sqrt(np.sum(np.diff(np.log(path)) ** 2) * YEAR_H / n))
    return {"S0": S0, "ST": ST, "K": K, "iv_mid": iv_mid, "premium": premium, "payoff": payoff,
            "hedge_pnl": hedge_pnl, "opt_fee": opt_fee, "hedge_fee": hedge_fee, "funding": fund, "delivery": delivery,
            "net": net, "r": net / S0, "unhedged_r": (premium - payoff - opt_fee - delivery) / S0, "rv": rv * 100.0}


def series_stats(x, dates):
    x = np.asarray(x, float)
    d = pd.to_datetime(dates, unit="ms")
    o = np.sort(x)
    k = int(np.floor(TRIM * len(x)))
    cum = np.cumsum(x)
    halves = [float(x[(d >= a) & (d < b)].mean()) if ((d >= a) & (d < b)).any() else None for a, b in HALVES]
    return {"weeks": int(len(x)), "mean_bp": float(x.mean() * 1e4), "t_nw": float(stats.newey_west_t(x, NW_LAG)[2]),
            "ann_pct": float(x.mean() * 52 * 100), "hit": float((x > 0).mean()),
            "worst_bp": float(x.min() * 1e4), "best_bp": float(x.max() * 1e4),
            "max_dd_pct": float(np.max(np.maximum.accumulate(np.r_[0.0, cum]) - np.r_[0.0, cum]) * 100),
            "halves_bp": [None if h is None else h * 1e4 for h in halves],
            "trimmed_bp": float(o[k: len(o) - k].mean() * 1e4) if len(o) > 2 * k else None,
            "wo_best_bp": float(o[: max(len(o) - WO_BEST, 0)].mean() * 1e4) if len(o) > WO_BEST else None}


def decide(s1, s2):
    ok = (s1["mean_bp"] > 0 and s1["t_nw"] >= T_MIN and s2["mean_bp"] > 0
          and all(h is not None and h > 0 for h in s1["halves_bp"])
          and (s1["trimmed_bp"] or -1) > 0 and (s1["wo_best_bp"] or -1) > 0)
    return "PASS" if ok else "NULL"


def build(cur, hashes, compute=True):
    rows = load_rows(cur, hashes=hashes)
    PH = hourly_prices(data.ROOT / "klines_1m" / f"{COINS[cur]}.parquet")
    F_t, F_r = load_funding(data.ROOT / "fundingRate" / f"{COINS[cur]}.parquet")
    out, skips, used = [], {}, {h: 0 for h in BUCKETS}
    for D in fridays():
        e, why = pick_entry(rows, D, PH)
        if e is None:
            skips[why] = skips.get(why, 0) + 1
            continue
        b, K, ivc, ivp = e
        used[(b - D) // HOUR] += 1
        if not compute:
            out.append({"D": D, "K": K})
            continue
        te, E = b + HOUR, D + 7 * DAY + 8 * HOUR
        res = {m: straddle(PH, K, (ivc + ivp) / 2.0, HALF_SPREAD[cur], m, F_t, F_r, te, E) for m in (0,) + CMULTS}
        if res[1] is None:
            skips["no_price_path"] = skips.get("no_price_path", 0) + 1
            continue
        out.append({"D": D, "te": te, "E": E, "K": K, "ivc": ivc, "ivp": ivp, **{f"m{m}": v for m, v in res.items()}})
    return out, skips, used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    if a.plumbing:
        rep = {}
        for cur in COINS:
            out, skips, used = build(cur, hashes, compute=False)
            rep[cur] = {"fridays": len(fridays()), "entries": len(out), "skips": skips, "bucket_used": used}
        print(json.dumps(rep, indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log_(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    res, weeks = {"registry": "R409", "prereg_sha": sha, "coins": {}}, []
    for cur in COINS:
        out, skips, used = build(cur, hashes)
        dates = [w["te"] for w in out]
        st = {f"{m}x": series_stats([w[f"m{m}"]["r"] for w in out], dates) for m in CMULTS}
        gross = series_stats([w["m0"]["r"] for w in out], dates)
        unh = series_stats([w["m1"]["unhedged_r"] for w in out], dates)
        vrp = float(np.mean([w["m1"]["iv_mid"] - w["m1"]["rv"] for w in out]))
        res["coins"][cur] = {"decision": decide(st["1x"], st["2x"]), "stats": st, "gross_m0": gross,
                             "unhedged_1x": unh, "mean_iv_minus_rv_volpts": vrp, "skips": skips,
                             "bucket_used": used}
        for w in out:
            weeks.append({"coin": cur, "entry_utc": pd.Timestamp(w["te"], unit="ms").isoformat(), "K": w["K"],
                          "iv_mid": w["m1"]["iv_mid"], "rv": w["m1"]["rv"], "S0": w["m1"]["S0"], "ST": w["m1"]["ST"],
                          **{f"r_{m}x": w[f"m{m}"]["r"] for m in (0,) + CMULTS},
                          "unhedged_1x": w["m1"]["unhedged_r"], "funding": w["m1"]["funding"] / w["m1"]["S0"]})
        log_(f"{cur}: {len(out)} weeks, {res['coins'][cur]['decision']}, 1x {st['1x']['mean_bp']:+.1f} bp/wk "
             f"t {st['1x']['t_nw']:.2f}")
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1))
    pd.DataFrame(weeks).to_csv(LANE / "results" / "weeks.csv", index=False)
    print(json.dumps({c: v["decision"] for c, v in res["coins"].items()}))


if __name__ == "__main__":
    main()
