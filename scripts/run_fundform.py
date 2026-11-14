"""fundform_v1 (R492, M172): the funding-formula forecast. Frozen in experiments/fundform_v1/PREREG.md.

R491 tested the *naive* within-cycle premium mean and found it far worse than no-change. The mechanism diagnostic
showed the naive mean is the wrong object: Binance's settled rate is F = P + clip(I - P, -0.05%, +0.05%) with
I = 0.01%, so the settled rate is clamped to [+/-0.05%] around I. This lane tests the formula on the point-in-time
partial premium average, at each offset k hours before settlement, against the no-change forecast.
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

LANE = ROOT / "experiments" / "fundform_v1"
H = 3_600_000
OFFSETS = (0, 1, 2, 3, 4, 6, 8, 12, 16, 24)
PRIMARY_K = 1
NW = 7
INTEREST = 0.0001
CLIP = 0.0005
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def formula(avg, interest=INTEREST, clip=CLIP):
    return avg + np.clip(interest - avg, -clip, clip)


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    syms = sorted(p.stem for p in (data.ROOT / "fundingRate").glob("*.parquet"))
    syms = [s for s in syms if (data.ROOT / "premiumIndexKlines_1h" / f"{s}.parquet").exists()]
    log(f"{len(syms)} symbols with funding+premium")

    err = {k: [] for k in OFFSETS}
    full_resid = []
    n_events = 0
    for s in syms:
        pi = pd.read_parquet(data.ROOT / "premiumIndexKlines_1h" / f"{s}.parquet")
        fr = pd.read_parquet(data.ROOT / "fundingRate" / f"{s}.parquet")
        pmap = dict(zip((pi["t"].values // H).astype(np.int64).tolist(), pi["close"].values.astype(float).tolist()))
        ft = fr["t"].values.astype(np.int64)
        frate = fr["rate"].values.astype(float)
        fint = fr["interval_h"].values.astype(np.int64)
        for j in range(1, len(ft)):
            T = int(ft[j] // H); I = int(fint[j])
            if I <= 0 or I > 48:
                continue
            cyc = list(range(T - I, T))
            if not all(h in pmap for h in cyc):
                continue
            n_events += 1
            prev = float(frate[j - 1]); actual = float(frate[j])
            en = abs(prev - actual)
            # exactness diagnostic: formula on the FULL cycle average (only knowable at settlement)
            full_resid.append(formula(np.mean([pmap[h] for h in cyc])) - actual)
            for k in OFFSETS:
                known = [h for h in cyc if h <= T - 1 - k]
                if len(known) < 1 or k >= I:
                    continue
                p = formula(np.mean([pmap[h] for h in known]))
                err[k].append(((T * H) // (24 * H), en - abs(p - actual), abs(p - actual), en))
    log(f"events {n_events:,}")

    curve = {}
    for k in OFFSETS:
        a = np.array([(day, dd, ep, en) for (day, dd, ep, en) in err[k]], float)
        if len(a) == 0:
            continue
        df = pd.DataFrame({"day": a[:, 0], "d": a[:, 1]}).groupby("day")["d"].mean()
        n, mu, t = stats.newey_west_t(df.values, NW)
        curve[k] = {"n": int(len(a)), "mae_formula_bp": float(a[:, 2].mean() * 1e4),
                    "mae_nochange_bp": float(a[:, 3].mean() * 1e4), "reduction_bp": float(mu * 1e4),
                    "days": int(n), "nw_t": float(t)}
        log(f"k={k:2d}h  MAE formula {curve[k]['mae_formula_bp']:8.3f}  no-change {curve[k]['mae_nochange_bp']:8.3f} "
            f"reduction {curve[k]['reduction_bp']:+7.3f} bp  NW t {t:+.2f}  n {len(a):,}")

    # Null: block bootstrap on the daily primary series (mean removed).
    a1 = np.array([(day, dd, ep, en) for (day, dd, ep, en) in err[PRIMARY_K]], float)
    day = pd.DataFrame({"day": a1[:, 0], "d": a1[:, 1]}).groupby("day")["d"].mean().values
    x = day - np.nanmean(day)
    rng = np.random.default_rng(20261114)
    B = 7; nb = max(1, len(x) // B)
    null = np.array([stats.newey_west_t(np.concatenate([x[s * B:(s + 1) * B] for s in rng.integers(0, nb, nb)]), NW)[2]
                     for _ in range(2000)])
    p95 = float(np.nanpercentile(null, 95)); p5 = float(np.nanpercentile(null, 5))

    fr_res = np.array(full_resid)
    diag = {"full_cycle_formula_mae_bp": float(np.abs(fr_res).mean() * 1e4),
            "full_cycle_formula_bias_bp": float(fr_res.mean() * 1e4),
            "share_at_clamp": float(np.mean(np.isclose(np.abs(fr_res), 0.0004, atol=1e-9)))}
    log(f"full-cycle formula MAE {diag['full_cycle_formula_mae_bp']:.3f} bp bias {diag['full_cycle_formula_bias_bp']:+.3f}")

    p = curve[PRIMARY_K]
    adds = p["reduction_bp"] > 0 and p["nw_t"] >= 3.0 and p["nw_t"] > p95
    verdict = {"R492": "fundform_v1", "primary_k_hours": PRIMARY_K, "adds_information": bool(adds),
               "primary": p, "null_p95_t": p95, "null_p5_t": p5, "diagnostic": diag,
               "events": n_events, "symbols": len(syms)}
    (out / "report.json").write_text(json.dumps({"curve": {str(k): v for k, v in curve.items()},
                                                 "null": {"p95_t": p95, "p5_t": p5},
                                                 "diagnostic": diag, "verdict": verdict}, indent=1, sort_keys=True))
    log("WROTE", out / "report.json")
    print(json.dumps(verdict, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
