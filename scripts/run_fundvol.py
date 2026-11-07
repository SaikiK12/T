"""R382 fundvol_v1 (M455): does trailing volatility sizing improve a funding-carry book's net return at executable cost?

Base book: R277's `gate+kucoin L14d th5% K20` (experiments/xfund_kd_v1/results/daily.csv, 1x/2x/3x net, gross, held).
Its engine is not re-run. Six fixed variants size or gate its saved daily net by a trailing volatility measured from
the book's own saved 1x net series or from BTCUSDT daily closes (data/klines_1h, rows from 2021-01-01 only). Variant
chosen on the first half of the evaluation sample by net 1x Sharpe; it must beat the unscaled base on the second half in
net 2x Sharpe and mean with a paired stationary-bootstrap p <= 0.05 for the Sharpe difference.

usage: python scripts/run_fundvol.py
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.inference import stationary_counts  # noqa: E402
from scripts.run_clockflow import check_inputs  # noqa: E402

LANE = ROOT / "experiments" / "fundvol_v1"
PREREG = LANE / "PREREG.md"
BASE_CSV = ROOT / "experiments" / "xfund_kd_v1" / "results" / "daily.csv"
BASE = "gate+kucoin L14d th5% K20"
BTC = ROOT / "data" / "klines_1h" / "BTCUSDT.parquet"
BTC_FROM_MS = 1609459200000  # 2021-01-01 00:00 UTC: no 2020 row is read
MULTS = (1, 2, 3)
COST = 0.0007  # per leg per side at 1x (R277's spec); the base's own multiples are 1x/2x/3x of it
SLOTS = 20  # K: a full book of `held` = 20 pairs trades held / SLOTS of capital per side
WARM = 100  # base dates before the evaluation sample (all variants need <= 92)
LAG = 2  # the volatility window ends two days before the traded date (date-label convention not re-derived)
MINHIST = 60  # observations of the volatility series needed before an expanding statistic is used
CAP = 2.0
GATE_Q = 0.8
BLOCK = 10
REPS = 5000
SEED = 382
DAYS = 365
VARIANTS = [  # (name, source, window, rule)
    ("own7_scale", "own", 7, "scale"),
    ("own30_scale", "own", 30, "scale"),
    ("btc7_scale", "btc", 7, "scale"),
    ("btc30_scale", "btc", 30, "scale"),
    ("btc7_gate", "btc", 7, "gate"),
    ("btc30_gate", "btc", 30, "gate"),
]


def load_base(path=BASE_CSV, book=BASE):
    d = pd.read_csv(path)
    d = d[d.strategy == book]
    out = {}
    for m in MULTS:
        x = d[d.cost_multiple == m].set_index("date").sort_index()
        out[f"net{m}"] = x["net"]
        if m == 1:
            out["held"] = x["held"]
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index)
    full = pd.date_range(df.index[0], df.index[-1], freq="D")
    if len(df) == 0 or not df.index.equals(full) or df.isna().any().any():
        raise ValueError("base series has gaps or missing multiples")
    return df


def load_btc_returns(path=BTC):
    k = pd.read_parquet(path, columns=["t", "close"], filters=[("t", ">=", BTC_FROM_MS)])
    k = k.sort_values("t").drop_duplicates("t")
    k["day"] = k.t // 86_400_000
    g = k.groupby("day").agg(close=("close", "last"), n=("t", "size"))
    g.loc[g.n != 24, "close"] = np.nan  # an incomplete day has no close
    g.index = pd.to_datetime(g.index * 86_400_000, unit="ms")
    c = g.close.reindex(pd.date_range(g.index[0], g.index[-1], freq="D"))
    return np.log(c / c.shift(1))


def trailing_vol(r, window, index):
    """Std (ddof 1) of the `window` daily returns ending LAG days before each date, on `index`."""
    v = r.rolling(window, min_periods=window).std(ddof=1).shift(LAG)
    return v.reindex(index)


def weights(v, rule):
    """Exposure on each date from the volatility series v (known at the start of the date). NaN -> 1 (neutral)."""
    if rule == "scale":
        med = v.expanding(min_periods=MINHIST).median()
        w = pd.Series(np.where(v > 0, med / v.where(v > 0), CAP), index=v.index).clip(0, CAP).where(med.notna())
    elif rule == "gate":
        q = v.expanding(min_periods=MINHIST).quantile(GATE_Q)
        w = (v <= q).astype(float).where(q.notna() & v.notna())
    else:
        raise ValueError(rule)
    return w.where(v.notna() & (w.notna()), 1.0).astype(float)


def sized(net, w, held, mult):
    """Weighted net minus the cost of changing the exposure: |dw| x (held / SLOTS) x COST x mult per date."""
    dw = w.diff().abs().fillna(0.0)
    return w * net - dw * (held / SLOTS) * COST * mult


def stats(x):
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return {"n": len(x), "mean_bp": float(x.mean() * 1e4), "pct_yr": float(x.mean() * DAYS * 100),
            "sharpe": float(x.mean() / sd * np.sqrt(DAYS)) if sd > 0 else float("nan")}


def sharpe_boot(x, y, counts):
    """Annualised Sharpe of x and y under bootstrap resamples given as draw counts [reps, n]."""
    n = x.shape[0]
    out = []
    for a in (x, y):
        m = counts @ a / n
        e2 = counts @ (a * a) / n
        out.append(m / np.sqrt(np.maximum(e2 - m * m, 1e-30) * n / (n - 1)) * np.sqrt(DAYS))
    return out


def boot_p(xv, xb, reps=REPS, block=BLOCK, seed=SEED):
    """One-sided paired stationary-bootstrap p for SR(xv) - SR(xb) <= 0 (centred on the observed difference)."""
    xv, xb = np.asarray(xv, np.float64), np.asarray(xb, np.float64)
    counts = stationary_counts(len(xv), reps, block, np.random.default_rng(seed)).astype(np.float64)
    sv, sb = sharpe_boot(xv, xb, counts)
    d_obs = stats(xv)["sharpe"] - stats(xb)["sharpe"]
    d_b = sv - sb
    return float(d_obs), float(np.mean(d_b - d_obs >= d_obs))


def run():
    prereg.verify(PREREG)
    shas = check_inputs(PREREG)
    base = load_base()
    idx = base.index
    ret = load_btc_returns()
    vol = {}
    for name, src, win, rule in VARIANTS:
        vol[name] = trailing_vol(base["net1"] if src == "own" else ret, win, idx)
    W = {name: weights(vol[name], rule) for name, _, _, rule in VARIANTS}
    n_nan = {name: int(vol[name].iloc[WARM:].isna().sum()) for name in vol}
    ev = idx[WARM:]
    half = len(ev) // 2
    halves = {"first": ev[:half], "second": ev[half:]}

    series = {"base": {m: base[f"net{m}"] for m in MULTS}}
    for name, *_ in VARIANTS:
        series[name] = {m: sized(base[f"net{m}"], W[name], base["held"], m) for m in MULTS}

    rows = []
    for name in series:
        for h, ix in halves.items():
            for m in MULTS:
                s = stats(series[name][m].loc[ix])
                w = W[name].loc[ix] if name != "base" else pd.Series(1.0, index=ix)
                rows.append({"variant": name, "half": h, "mult": m, **s, "mean_w": float(w.mean()),
                             "share_off": float((w == 0).mean()),
                             "turnover_w": float(w.diff().abs().mean()) if name != "base" else 0.0})
    tab = pd.DataFrame(rows)
    tab.to_csv(LANE / "results" / "variants.csv", index=False)

    first1 = tab[(tab.half == "first") & (tab.mult == 1) & (tab.variant != "base")].set_index("variant").sharpe
    pick = str(first1.idxmax())
    sec = halves["second"]
    xv, xb = series[pick][2].loc[sec].values, series["base"][2].loc[sec].values
    d_obs, p = boot_p(xv, xb)
    sv, sb = stats(xv), stats(xb)
    checks = {"sharpe_2x_beats_base": sv["sharpe"] > sb["sharpe"], "mean_2x_beats_base": sv["mean_bp"] > sb["mean_bp"],
              "p_le_0.05": p <= 0.05}
    verdict = "PARTIAL" if all(checks.values()) else "NULL"
    pd.DataFrame({"w": W[pick], "net1": series[pick][1], "net2": series[pick][2], "net3": series[pick][3],
                  "base_net2": base["net2"]}).loc[ev].to_csv(LANE / "results" / "pick_daily.csv")
    summary = {"verdict": verdict, "trials": len(VARIANTS), "pick": pick, "first_half_sharpe_1x": first1.to_dict(),
               "second_half_2x": {"pick": sv, "base": sb, "sharpe_diff": d_obs, "boot_p": p}, "checks": checks,
               "sample": {"first": [str(halves["first"][0].date()), str(halves["first"][-1].date())],
                          "second": [str(sec[0].date()), str(sec[-1].date())], "n_eval": len(ev)},
               "vol_nan_after_warmup": n_nan, "reps": REPS, "block": BLOCK, "seed": SEED, "inputs": shas}
    (LANE / "results" / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(tab.round(4).to_string())
    print(json.dumps({k: summary[k] for k in ("verdict", "pick", "first_half_sharpe_1x", "second_half_2x", "checks",
                                             "sample", "vol_nan_after_warmup")}, indent=1, default=str))
    return summary


if __name__ == "__main__":
    t0 = time.time()
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    run()
    print(f"done in {time.time() - t0:.1f}s")
