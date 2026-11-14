"""fundrev_v1 (R491, M172): does a coin's within-cycle premium index forecast the next settled funding rate
better than a no-change forecast, on Binance USDT perpetuals? Frozen in experiments/fundrev_v1/PREREG.md.

Primary estimand: at offset k hours before settlement, the paired absolute-error difference
d = |r_prev - r_next| - |partial_premium - r_next|, aggregated to calendar days and tested with Newey-West.
The point-in-time rule uses only premium bars that have CLOSED at or before T - k hours, so nothing after the
decision bar enters a forecast. No positions are held, so there is no trading cost; the secondary diagnostic maps
any forecast edge to a cross-sectional return IC.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "fundrev_v1"
H = 3_600_000
OFFSETS = (0, 1, 2, 3, 4, 6, 8, 12, 16, 24)
PRIMARY_K = 1
NW = 7
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def symbol_events(sym, pi, fr, kl):
    """Per settlement: settlement hour, interval hours, settled rate, prev rate, partial premium means, next-cycle ret."""
    ph = (pi["t"].values // H).astype(np.int64)
    pc = pi["close"].values.astype(np.float64)
    pmap = dict(zip(ph.tolist(), pc.tolist()))
    kh = (kl["t"].values // H).astype(np.int64)
    kc = kl["close"].values.astype(np.float64)
    kmap = dict(zip(kh.tolist(), kc.tolist()))
    ft = fr["t"].values.astype(np.int64)
    frate = fr["rate"].values.astype(np.float64)
    fint = fr["interval_h"].values.astype(np.int64)
    sh = ft // H
    rows = []
    for j in range(1, len(ft)):
        T = int(sh[j]); I = int(fint[j])
        if I <= 0 or I > 48:
            continue
        prev = float(frate[j - 1])
        cyc = list(range(T - I, T))                 # bar hours open in the cycle
        if not all(h in pmap for h in cyc):
            continue
        preds = {}
        ok = True
        for k in OFFSETS:
            known = [h for h in cyc if h <= T - 1 - k]
            if len(known) < 1 or k >= I:
                preds[k] = np.nan
                continue
            preds[k] = float(np.mean([pmap[h] for h in known]))
        # next-cycle return over (T, T+I] in the kline closes, and this cycle's return for reference
        c0, c1 = kmap.get(T), kmap.get(T + I)
        nxt = np.log(c1 / c0) if (c0 and c1 and c0 > 0 and c1 > 0) else np.nan
        rows.append((T, I, prev, float(frate[j]), preds, nxt))
    return rows


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    syms = sorted(p.stem for p in (data.ROOT / "fundingRate").glob("*.parquet"))
    syms = [s for s in syms if (data.ROOT / "premiumIndexKlines_1h" / f"{s}.parquet").exists()
            and (data.ROOT / "klines_1h" / f"{s}.parquet").exists()]
    log(f"{len(syms)} symbols with funding+premium+klines")

    # Collect per-offset paired errors and per-settlement revision/next-return for the IC diagnostic.
    err = {k: [] for k in OFFSETS}          # (day, d, err_partial, err_nochange)
    ic = []                                  # (day, revision, next_ret, sym)
    n_events = 0
    for s in syms:
        pi = pd.read_parquet(data.ROOT / "premiumIndexKlines_1h" / f"{s}.parquet")
        fr = pd.read_parquet(data.ROOT / "fundingRate" / f"{s}.parquet")
        kl = pd.read_parquet(data.ROOT / "klines_1h" / f"{s}.parquet")
        ev = symbol_events(s, pi, fr, kl)
        n_events += len(ev)
        for (T, I, prev, actual, preds, nxt) in ev:
            day = (T * H) // (24 * H)  # settlement day (UTC day index)
            en = abs(prev - actual)
            for k in OFFSETS:
                p = preds[k]
                if np.isfinite(p):
                    ep = abs(p - actual)
                    err[k].append((day, en - ep, ep, en))
            p1 = preds[PRIMARY_K]
            if np.isfinite(p1) and np.isfinite(nxt):
                ic.append((day, p1 - prev, nxt, s))
    log(f"events {n_events:,}")

    curve = {}
    for k in OFFSETS:
        a = np.array([(d, ep, en) for (_, d, ep, en) in err[k]], float)
        if len(a) == 0:
            continue
        # daily-aggregated paired difference -> NW t
        days = np.array([r[0] for r in err[k]])
        d = a[:, 0]
        df = pd.DataFrame({"day": days, "d": d}).groupby("day")["d"].mean()
        n, mu, t = stats.newey_west_t(df.values, NW)
        curve[k] = {"n": int(len(a)), "mae_partial_bp": float(a[:, 1].mean() * 1e4),
                    "mae_nochange_bp": float(a[:, 2].mean() * 1e4),
                    "mae_reduction_bp": float(mu * 1e4), "days": int(n), "nw_t": float(t)}
        log(f"k={k:2d}h  MAE partial {curve[k]['mae_partial_bp']:8.3f}  no-change {curve[k]['mae_nochange_bp']:8.3f} "
            f"reduction {curve[k]['mae_reduction_bp']:+7.3f} bp  NW t {t:+.1f}  n {len(a):,}")

    # Secondary diagnostic: cross-sectional rank IC of revision (k=1) vs next-cycle return, per settlement day.
    ics = []
    by_day = {}
    for (day, rev, nxt, s) in ic:
        by_day.setdefault(day, []).append((rev, nxt))
    for day, lst in by_day.items():
        if len(lst) < 10:
            continue
        r = pd.Series([x[0] for x in lst]).rank()
        y = pd.Series([x[1] for x in lst]).rank()
        ics.append(float(np.corrcoef(r, y)[0, 1]))
    ic_series = np.array(ics)
    n_ic, mu_ic, t_ic = stats.newey_west_t(ic_series, NW)
    ic_out = {"mean_rank_ic": float(np.nanmean(ic_series)), "nw_t": float(t_ic), "days": int(n_ic),
              "n_pairs": len(ic)}
    log(f"revision -> next-cycle return rank IC {ic_out['mean_rank_ic']:+.4f} t {ic_out['nw_t']:+.2f} "
        f"({ic_out['days']} days, {ic_out['n_pairs']:,} pairs)")

    p = curve[PRIMARY_K]
    adds = p["mae_reduction_bp"] > 0 and p["nw_t"] >= 3.0
    verdict = {"R491": "fundrev_v1", "primary_k_hours": PRIMARY_K, "adds_information": bool(adds),
               "curve": {str(k): v for k, v in curve.items()}, "rank_ic": ic_out,
               "events": n_events, "symbols": len(syms)}
    (out / "report.json").write_text(json.dumps({"curve": {str(k): v for k, v in curve.items()},
                                                 "rank_ic": ic_out, "verdict": verdict}, indent=1, sort_keys=True))
    log("WROTE", out / "report.json")
    print(json.dumps(verdict, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
