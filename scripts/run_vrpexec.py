"""R410 vrpexec_v1 (M477): R409's weekly short straddle with a maker sale, band hedges and maker-first hedges, as set
out in experiments/vrpexec_v1/PREREG.md. The rule is scripts/vrpexec_rule.py.

For each Friday D (2021-01-01..2026-09-18) and BTC/ETH: the point-in-time ATM strike for E = D + 7 d 08:00, its two
legs' raw trades from D 00:00 to 12:00 (`data/deribit_trades/<CUR>/atm_windows.parquet`), perp prices and 1-minute
extremes (`data/klines_1m`) and Binance funding. Twelve cells (2 sales x 6 hedges) at m = 0, 1, 2, 3. Only the
primary cell (maker sale, band 0.10, maker-first hedge) is decided on, with R409's six checks.

usage: python scripts/run_vrpexec.py [--plumbing]
  --plumbing: counts of weeks with a strike, both references and a complete price path; no P&L or fill is computed
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg  # noqa: E402
from scripts import vrpexec_rule as R  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs, load_funding  # noqa: E402
from scripts.run_optflow import COINS, hourly_prices  # noqa: E402
from scripts.run_vrpsell2 import decide, fridays, series_stats  # noqa: E402

LANE = ROOT / "experiments" / "vrpexec_v1"
PROV = ROOT / "docs" / "provenance" / "deribit_atm_windows.json"
MS = (0, 1, 2, 3)
log_ = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_trades(cur, hashes):
    path = data.ROOT / "deribit_trades" / cur / "atm_windows.parquet"
    rel = path.relative_to(ROOT).as_posix()
    if hashes.get(rel) != prereg.sha256_file(path):
        raise prereg.PreregError(f"{rel}: not in {PROV.name}, or changed since it")
    tr = pd.read_parquet(path)
    if (tr.friday_ms < T0).any() or (tr.timestamp < T0).any():
        raise prereg.PreregError(f"{rel}: holds rows before 2021 (reserved)")
    return tr


def minute_extremes(path):
    """Per-minute low/high of the bars opening at T0 + j min, j = 0..; NaN where missing or empty."""
    k = pd.read_parquet(path, columns=["t", "high", "low", "count"])
    k = k[(k.t >= T0) & (k.t < T1)].drop_duplicates("t")
    k = k[(k["count"] > 0) & (k.low > 0)]
    n = (T1 - T0) // R.MIN
    lo, hi = np.full(n, np.nan), np.full(n, np.nan)
    j = (k.t.values - T0) // R.MIN
    lo[j], hi[j] = k.low.values, k.high.values
    return lo, hi


def legs_for(tr_c, tr_p, D, PH, K, E, half):
    """{sale: {m: (call leg, put leg)}} plus the hedge-start IVs, or (None, reason)."""
    k9, k12 = (D + R.TAKER_H * R.HOUR - T0) // R.HOUR, (D + R.END_H * R.HOUR - T0) // R.HOUR
    if not (np.isfinite(PH[k9]) and np.isfinite(PH[k12])):
        return None, "no_price_at_sale"
    out = {"taker": {}, "maker": {}}
    for m in MS:
        tc = R.taker_leg(tr_c, D + R.TAKER_H * R.HOUR, PH[k9], K, E, "C", half, m)
        tp = R.taker_leg(tr_p, D + R.TAKER_H * R.HOUR, PH[k9], K, E, "P", half, m)
        mc = R.maker_leg(tr_c, D, PH, T0, K, E, "C", half, m)
        mp = R.maker_leg(tr_p, D, PH, T0, K, E, "P", half, m)
        if None in (tc, tp, mc, mp):
            return None, "no_reference"
        out["taker"][m], out["maker"][m] = (tc, tp), (mc, mp)
    iv12 = [R.mark_iv(t, D + R.END_H * R.HOUR, K, E, cp) for t, cp in ((tr_c, "C"), (tr_p, "P"))]
    if None in iv12:
        return None, "no_reference"
    sig = {"taker": float(np.mean([x["iv_ref"] for x in out["taker"][1]])), "maker": float(np.mean(iv12))}
    return (out, sig), None


def build(cur, hashes, plumbing=False):
    tr = load_trades(cur, hashes)
    PH = hourly_prices(data.ROOT / "klines_1m" / f"{COINS[cur]}.parquet")
    F_t, F_r = load_funding(data.ROOT / "fundingRate" / f"{COINS[cur]}.parquet")
    if not plumbing:
        lo1, hi1 = minute_extremes(data.ROOT / "klines_1m" / f"{COINS[cur]}.parquet")
        LO, HI = R.hourly_extremes(lo1, hi1, T0, (T1 - T0) // R.HOUR)
    weeks, skips = [], {}
    by_f = dict(tuple(tr.groupby("friday_ms")))
    for D in fridays():
        g = by_f.get(D)
        if g is None:
            skips["no_strike"] = skips.get("no_strike", 0) + 1
            continue
        K, E = float(g.strike.iloc[0]), int(g.expiry_ms.iloc[0])
        tr_c, tr_p = g[g.cp == "C"].sort_values("timestamp"), g[g.cp == "P"].sort_values("timestamp")
        kE = (E - T0) // R.HOUR
        if plumbing:                                # references and prices only: no fill, no P&L
            refs = [R.mark_iv(t, D + h * R.HOUR, K, E, cp) for t, cp in ((tr_c, "C"), (tr_p, "P"))
                    for h in (R.POST_H, R.TAKER_H, R.END_H)]
            why = "no_reference" if None in refs else None
            got = True
        else:
            got, why = legs_for(tr_c, tr_p, D, PH, K, E, R.HALF_SPREAD[cur])
        if why is None and not np.all(np.isfinite(PH[(D + R.POST_H * R.HOUR - T0) // R.HOUR: kE + 1])):
            why = "no_price_path"
        if why is not None:
            skips[why] = skips.get(why, 0) + 1
            continue
        if plumbing:
            weeks.append({"D": D})
            continue
        legs, sig = got
        S0 = float(PH[(D + R.POST_H * R.HOUR - T0) // R.HOUR])
        row = {"D": D, "K": K, "S0": S0, "ST": float(PH[kE]), "sig_taker": sig["taker"], "sig_maker": sig["maker"],
               "fill_C": legs["maker"][1][0]["filled"], "fill_P": legs["maker"][1][1]["filled"],
               "fill_min_C": (legs["maker"][1][0]["t"] - D - R.POST_H * R.HOUR) / R.MIN,
               "fill_min_P": (legs["maker"][1][1]["t"] - D - R.POST_H * R.HOUR) / R.MIN,
               "iv_post": float(np.mean([x["iv_post"] for x in legs["maker"][1]])), "cells": {}}
        for sale in R.SALES:
            te = D + (R.TAKER_H if sale == "taker" else R.END_H) * R.HOUR
            k0 = (te - T0) // R.HOUR
            path = PH[k0: kE + 1]
            for hname in R.HEDGES:
                for m in MS:
                    row["cells"][(sale, hname, m)] = R.week(legs[sale][m], path, LO[k0:kE], HI[k0:kE], K, sig[sale],
                                                            hname, m, F_t, F_r, te, E, S0)
        weeks.append(row)
    return weeks, skips


def summarize(weeks):
    dates = [w["D"] + R.POST_H * R.HOUR for w in weeks]
    cells = {}
    for sale in R.SALES:
        for hname in R.HEDGES:
            c = {f"{m}x": series_stats([w["cells"][(sale, hname, m)]["r"] for w in weeks], dates) for m in MS}
            one = [w["cells"][(sale, hname, 1)] for w in weeks]
            c["cost_split_1x_bp"] = {k: float(np.mean([x[k] for x in one]) * 1e4) for k in
                                     ("premium", "payoff", "hedge_pnl", "opt_fee", "hedge_fee", "funding", "delivery")}
            c["turnover_median_coins"] = float(np.median([x["turnover"] for x in one]))
            posts = sum(x["posts"] for x in one)
            c["hedge_maker_fill_rate"] = (sum(x["fills"] for x in one) / posts) if posts else None
            cells[f"{sale}/{hname}"] = c
    fills = [w["fill_C"] for w in weeks] + [w["fill_P"] for w in weeks]
    tmin = [w[f"fill_min_{cp}"] for w in weeks for cp in "CP" if w[f"fill_{cp}"]]
    return cells, {"leg_fill_rate": float(np.mean(fills)), "both_filled": float(np.mean([w["fill_C"] and w["fill_P"]
                                                                                         for w in weeks])),
                   "median_minutes_to_fill": float(np.median(tmin)) if tmin else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    a = ap.parse_args()
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROV.read_text())["file_hashes"]}
    if a.plumbing:
        rep = {}
        for cur in COINS:
            w, sk = build(cur, hashes, plumbing=True)
            rep[cur] = {"fridays": len(fridays()), "weeks": len(w), "skips": sk}
        print(json.dumps(rep, indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    log_(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    res, rows = {"registry": "R410", "prereg_sha": sha, "primary": "/".join(R.PRIMARY), "coins": {}}, []
    for cur in COINS:
        weeks, skips = build(cur, hashes)
        cells, fills = summarize(weeks)
        p = cells["/".join(R.PRIMARY)]
        res["coins"][cur] = {"decision": decide(p["1x"], p["2x"]), "weeks": len(weeks), "skips": skips,
                             "maker_sale": fills, "cells": cells}
        for w in weeks:
            rows.append({"coin": cur, "friday": pd.Timestamp(w["D"], unit="ms").date().isoformat(), "K": w["K"],
                         "S0": w["S0"], "ST": w["ST"], "iv_post": w["iv_post"], "sig_maker": w["sig_maker"],
                         "fill_C": w["fill_C"], "fill_P": w["fill_P"],
                         **{f"{s}/{h}/{m}x": w["cells"][(s, h, m)]["r"] for s in R.SALES for h in R.HEDGES
                            for m in MS}})
        log_(f"{cur}: {len(weeks)} weeks, {res['coins'][cur]['decision']}, primary 1x {p['1x']['mean_bp']:+.1f} bp/wk "
             f"t {p['1x']['t_nw']:.2f}; maker legs filled {fills['leg_fill_rate']:.0%}")
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(res, indent=1))
    pd.DataFrame(rows).to_csv(LANE / "results" / "weeks.csv", index=False)
    print(json.dumps({c: v["decision"] for c, v in res["coins"].items()}))


if __name__ == "__main__":
    main()
