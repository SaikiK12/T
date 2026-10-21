"""vixpanic_v1 (R283): long SPY, QQQ and the BTCUSDT perp after VIX-panic onsets (VIX above VIX3M, VVIX in its top
5%, or both), tested against random dates, as set out in experiments/vixpanic_v1/PREREG.md (method M278).

usage: python scripts/run_vixpanic.py
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
from lab import data, prereg  # noqa: E402

LANE = ROOT / "experiments" / "vixpanic_v1"
CBOE = ROOT / "data" / "cboe"
TRIGGERS = ("BACKW", "VVIX95", "BOTH")
HORIZONS = {5: 7, 10: 14, 20: 28}                       # trading days -> calendar days for BTC
ASSETS = ("SPY", "QQQ", "BTC")
COST = {"SPY": 1e-4, "QQQ": 1e-4, "BTC": 7e-4}          # one-way at 1x
GAP, PCT_WIN, PCT = 20, 252, 95
FIRST, LAST, BTC_FIRST = "2009-10-19", "2026-09-01", "2021-01-04"
DRAWS, SEED = 20_000, 283
TRIALS = len(TRIGGERS) * len(HORIZONS) * len(ASSETS)
H_MS = 3_600_000
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def cboe(name):
    d = pd.read_parquet(CBOE / f"{name}.parquet")
    return pd.Series(d.close.values, index=pd.to_datetime(d.day), name=name)


def triggers(vix, v3m, vvix):
    """Daily trigger flags on the days all three closes exist (index: Cboe days)."""
    q = vvix.rolling(PCT_WIN, min_periods=PCT_WIN).quantile(PCT / 100, interpolation="linear")
    df = pd.concat([vix, v3m, vvix, q.rename("q")], axis=1).dropna(subset=["VIX", "VIX3M", "VVIX"])
    backw = df.VIX > df.VIX3M
    hot = (df.VVIX >= df.q) & df.q.notna()
    return pd.DataFrame({"BACKW": backw, "VVIX95": hot, "BOTH": backw & hot})


def onsets(flag, gap=GAP):
    """Days where the flag holds and held on none of the `gap` previous rows."""
    f = flag.astype(bool).values
    prev = pd.Series(f).shift(1).rolling(gap, min_periods=1).max().fillna(0).astype(bool).values
    return flag.index[f & ~prev]


def equity_returns(px, days, h):
    """h-day return from the adjusted open of the first trading day after each D to the adjusted close of day h.
    px: frame with columns o, c on trading dates. Days without a full hold are dropped."""
    idx = px.index
    pos = idx.searchsorted(days, side="right")              # first trading day after D
    ok = pos + h - 1 < len(idx)
    pos, d = pos[ok], days[ok]
    r = px.c.values[pos + h - 1] / px.o.values[pos] - 1
    return pd.Series(r, index=d)


def btc_returns(k, fund, days, cal):
    """Open of the 22:00 UTC bar on D to the open of the bar `cal` days later, minus funding settled in between."""
    opens = pd.Series(k.open.values, index=k.t.values.astype(np.int64))
    ft, fr = fund.t.values.astype(np.int64), fund.rate.values.astype(float)
    cum = np.concatenate([[0.0], np.cumsum(fr)])
    out = {}
    for d in days:
        t0 = int(pd.Timestamp(d).tz_localize("UTC").value // 10**6) + 22 * H_MS
        t1 = t0 + cal * 24 * H_MS
        if t0 not in opens.index or t1 not in opens.index:
            continue
        paid = cum[np.searchsorted(ft, t1, side="right")] - cum[np.searchsorted(ft, t0, side="right")]
        out[d] = opens[t1] / opens[t0] - 1 - paid
    return pd.Series(out, dtype=float)


def null_p(obs, pool, n, rng):
    if n < 5:
        return 1.0
    means = np.array([pool[rng.choice(len(pool), n, replace=False)].mean() for _ in range(DRAWS)])
    return float((1 + (means >= obs).sum()) / (1 + DRAWS))


def cell_row(trig, h, asset, r_on, r_all, rng):
    n = len(r_on)
    c = 2 * COST[asset]
    row = {"trigger": trig, "h": h, "asset": asset, "n": n, "eligible": len(r_all),
           "eligible_mean_bp": r_all.mean() * 1e4}
    if n == 0:
        return row | {"p": 1.0, "pass": False}
    srt = np.sort(r_on.values)
    early, late = r_on[r_on.index < "2018-01-01"], r_on[r_on.index >= "2018-01-01"]
    row |= {"gross_bp": r_on.mean() * 1e4,
            "net1_bp": (r_on.mean() - c) * 1e4, "net2_bp": (r_on.mean() - 2 * c) * 1e4,
            "net3_bp": (r_on.mean() - 3 * c) * 1e4,
            "excess_bp": (r_on.mean() - r_all.mean()) * 1e4, "median_bp": float(np.median(srt)) * 1e4,
            "hit": float((r_on > 0).mean()), "worst_bp": srt[0] * 1e4,
            "mean_wo_best_bp": (srt[:-1].mean() * 1e4) if n > 1 else float("nan"),
            "early_n": len(early), "early_bp": early.mean() * 1e4 if len(early) else float("nan"),
            "late_n": len(late), "late_bp": late.mean() * 1e4 if len(late) else float("nan")}
    row["p"] = null_p(r_on.mean(), r_all.values, n, rng)
    row["pass"] = bool(row["p"] <= 0.05 / TRIALS and row["net2_bp"] > 0 and row["mean_wo_best_bp"] > 0)
    return row


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}")
    import run_fxindex as fx                                # Yahoo loaders of R239, unchanged
    shas = {f"cboe/{n}": prereg.sha256_file(CBOE / f"{n}.parquet") for n in ("VIX", "VIX3M", "VVIX")}
    vix, v3m, vvix = cboe("VIX"), cboe("VIX3M"), cboe("VVIX")
    flags = triggers(vix, v3m, vvix)
    px = {s: fx.etf(s) for s in ("SPY", "QQQ")}
    shas |= {f"yahoo/{k}": v for k, v in fx.SHAS.items()}
    k = pd.read_parquet(data.ROOT / "klines_1h" / "BTCUSDT.parquet", columns=["t", "open"])
    fund = pd.read_parquet(data.ROOT / "fundingRate" / "BTCUSDT.parquet", columns=["t", "rate"])
    lo = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)
    k, fund = k[k.t >= lo].reset_index(drop=True), fund[fund.t >= lo].sort_values("t").reset_index(drop=True)
    shas |= {"klines_1h/BTCUSDT": prereg.sha256_file(data.ROOT / "klines_1h" / "BTCUSDT.parquet"),
             "fundingRate/BTCUSDT": prereg.sha256_file(data.ROOT / "fundingRate" / "BTCUSDT.parquet")}

    rng = np.random.default_rng(SEED)
    cells, legs, onset_days = [], [], {}
    for trig in TRIGGERS:
        on = onsets(flags[trig])
        onset_days[trig] = [str(d.date()) for d in on]
        for asset in ASSETS:
            first = BTC_FIRST if asset == "BTC" else FIRST
            win = flags.index[(flags.index >= first) & (flags.index <= LAST)]
            on_w = on[(on >= first) & (on <= LAST)]
            for h, cal in HORIZONS.items():
                if asset == "BTC":
                    r_all = btc_returns(k, fund, win, cal)
                else:
                    r_all = equity_returns(px[asset], win, h)
                r_on = r_all.reindex(on_w).dropna()
                row = cell_row(trig, h, asset, r_on, r_all, rng)
                cells.append(row)
                legs += [{"trigger": trig, "asset": asset, "h": h, "day": str(d.date()), "gross": v,
                          "net1": v - 2 * COST[asset]} for d, v in r_on.items()]
                log(f"{trig:6s} {asset} h{h:2d}: n {row['n']:2d} net1 {row.get('net1_bp', float('nan')):7.1f} bp "
                    f"excess {row.get('excess_bp', float('nan')):7.1f} p {row['p']:.4f}{'  PASS' if row['pass'] else ''}")
    cells = pd.DataFrame(cells)
    after = {t: [d for d in onset_days[t] if d > LAST] for t in TRIGGERS}
    after_days = {t: [str(d.date()) for d in flags.index[(flags.index > LAST) & flags[t].values]] for t in TRIGGERS}
    verdict = "PARTIAL" if cells["pass"].any() else "NULL"
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    cells.to_csv(out / "cells.csv", index=False, float_format="%.6g")
    pd.DataFrame(legs).to_csv(out / "onsets.csv", index=False, float_format="%.6g")
    summary = {"rid": "R283", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha,
               "passes": cells[cells["pass"]][["trigger", "h", "asset"]].to_dict("records"),
               "family_p05": int((cells.p <= 0.05).sum()), "family_expected": 0.05 * TRIALS,
               "onsets_in_window": {t: [d for d in onset_days[t] if FIRST <= d <= LAST] for t in TRIGGERS},
               "onsets_after_window": after, "trigger_days_after_window": after_days, "inputs_sha256": shas}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    log(f"verdict {verdict}; {summary['family_p05']} of {TRIALS} cells at p <= 0.05 (expected {0.05 * TRIALS:.2f})")
    return summary


if __name__ == "__main__":
    main()
