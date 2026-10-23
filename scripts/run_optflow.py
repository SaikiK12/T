"""optflow_v1 (R295): does signed Deribit option flow lead BTC and ETH perp returns over the next 1, 4 or 24 hours?
As set out in experiments/optflow_v1/PREREG.md. Five signals from the taker side of every Deribit option trade (M311
block prints, M313 net drift) at three horizons: 15 trials.

Signals per currency and flow row hour t (trades in [t, t + 1 h), known at t + 1 h), in USD:
- block_delta: the sum over options of (block taker buys - block taker sells) x Black-76 delta x index price (M311);
- screen_delta: the same for the trades on the order book (all trades minus blocks);
- drift: QuantData's net drift (M313), signed premium with bullish = call taker buys + put taker sells, where an
  option-hour's signed premium is premium x (buys - sells) / (buys + sells);
- drift_otm: drift over out-of-the-money options only (call strike above the index, put strike below);
- drift_screen: drift with the block amounts taken out of the signed share.
At each UTC hour T, the signal over a window of W = h hours is the sum of the rows in [T - W h, T). It is z-scored
against its own previous 720 hourly values (at least 500) and winsorized at +-5, giving x_T. The test reads x_T
against the perp's log return from T to T + h; positive flow is predicted to lead a rise.

usage: python scripts/run_optflow.py [--plumbing]
       (--plumbing prints row and hour counts only, no statistic: the pre-freeze check)
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
from lab import data, exposure, prereg, stats  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs, load_prices  # noqa: E402

LANE = ROOT / "experiments" / "optflow_v1"
OUT = data.ROOT / "optflow_v1"                     # the hourly frame (large, gitignored)
FLOW = data.ROOT / "deribit_trades"
PROVENANCE = ROOT / "docs" / "provenance" / "deribit_trades.json"
COINS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
MIN, HOUR = 60_000, 3_600_000
NH = (T1 - T0) // HOUR                             # decision instants T0 + k h, k = 0..NH
DISC = ("2021-04-01", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HORIZONS = (1, 4, 24)
SIGNALS = ("block_delta", "screen_delta", "drift", "drift_otm", "drift_screen")
METHOD = {"block_delta": "M311", "screen_delta": "M311", "drift": "M313", "drift_otm": "M313", "drift_screen": "M313"}
TRIALS = len(SIGNALS) * len(HORIZONS)              # 15
T_MIN = 2.94                                       # Bonferroni over 15 trials, two-sided 5%
Z_HOURS, Z_NEED, WINSOR = 720, 500, 5.0
ENTRY = 1.0                                        # the reported rule trades when |x| >= 1
COST = 8.5e-4                                      # API, per side, at 1x (R289's API figure); 2x and 3x reported
IV_RANGE = (10.0, 300.0)                           # Deribit IV is in percent: the median must sit in this range
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------------------------------------------------- flow
def load_rows(cur, root=FLOW, hashes=None, t0=T0, t1=T1):
    """The hourly flow rows of one currency with t0 <= t < t1 (scripts/fetch_deribit_trades.py). Only the monthly files
    that overlap [t0, t1) are read, and with `hashes` (path relative to `root` -> sha256) each must still hash to its
    recorded value."""
    lo = pd.Timestamp(t0, unit="ms").strftime("%Y-%m")
    hi = pd.Timestamp(t1 - 1, unit="ms").strftime("%Y-%m")
    parts = []
    for p in sorted((root / cur / "flow").glob("*.parquet")):
        if not lo <= p.stem <= hi:
            continue
        if hashes is not None:
            rel = p.relative_to(root).as_posix()
            if hashes.get(rel) != prereg.sha256_file(p):
                raise prereg.PreregError(f"{rel}: not in the provenance record, or changed since it")
        f = pd.read_parquet(p, columns=["t", "expiry_ms", "strike", "cp", "buy", "sell", "block_buy", "block_sell",
                                        "iv", "premium", "index_price"])
        parts.append(f[(f.t >= t0) & (f.t < t1)])
    return pd.concat(parts, ignore_index=True)


def hourly_signals(f):
    """Per flow row hour t: the five signals (USD), the traded amount (coins) and the amount without a delta (no IV,
    no index or at expiry)."""
    F = f.index_price.to_numpy(float)
    K = f.strike.to_numpy(float)
    call = f.cp.to_numpy() == "C"
    T = (f.expiry_ms.to_numpy(float) - (f.t.to_numpy(float) + HOUR / 2)) / exposure.YEAR_MS    # from the hour's middle
    delta = exposure.greeks(F, K, T, f.iv.to_numpy(float) / 100, call).delta.to_numpy()
    ok = np.isfinite(delta)
    buy, sell = f.buy.to_numpy(float), f.sell.to_numpy(float)
    bnet = f.block_buy.to_numpy(float) - f.block_sell.to_numpy(float)
    net = buy - sell
    tot = buy + sell
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(tot > 0, net / tot, 0.0)
        share_s = np.where(tot > 0, (net - bnet) / tot, 0.0)
    usd = np.nan_to_num(f.premium.to_numpy(float) * F)
    side = np.where(call, 1.0, -1.0)
    otm = np.where(call, K > F, K < F)
    drift = side * usd * share
    out = pd.DataFrame({
        "t": f.t.to_numpy(np.int64),
        "block_delta": np.where(ok, bnet * delta * F, 0.0),
        "screen_delta": np.where(ok, (net - bnet) * delta * F, 0.0),
        "drift": drift,
        "drift_otm": np.where(otm, drift, 0.0),
        "drift_screen": side * usd * share_s,
        "amount": tot,
        "amount_no_delta": np.where(ok, 0.0, tot),
        "block_amount": f.block_buy.to_numpy(float) + f.block_sell.to_numpy(float),
    })
    return out.groupby("t", sort=True).sum()


def hour_array(h, col, t0=T0, nh=NH):
    """s[j] = the value of the flow row hour t0 + j h (0 for an hour without trades), j = 0..nh - 1."""
    s = np.zeros(nh)
    j = (h.index.to_numpy(np.int64) - t0) // HOUR
    keep = (j >= 0) & (j < nh)
    s[j[keep]] = h[col].to_numpy(float)[keep]
    return s


def window_sum(s, w):
    """S[k] = sum of s[k - w .. k - 1]: the flow known at the decision instant T0 + k h over the last w hours,
    k = 0..len(s); NaN for k < w."""
    c = np.concatenate([[0.0], np.cumsum(s)])
    S = np.full(len(c), np.nan)
    S[w:] = c[w:] - c[:-w]
    return S


def zscore(S, n=Z_HOURS, need=Z_NEED, cap=WINSOR):
    """(S[k] - mean) / sd over S[k - n .. k - 1] (at least `need` defined), winsorized at +-cap."""
    p = pd.Series(S).shift(1).rolling(n, min_periods=need)
    m, sd = p.mean().to_numpy(), p.std(ddof=1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        x = np.where(sd > 0, (S - m) / sd, np.nan)
    return np.clip(x, -cap, cap)


# ----------------------------------------------------------------------------------------------------------- perp
def hourly_prices(path, t0=T0, t1=T1):
    """PH[k] = the perp price at the instant t0 + k h (the close of the 1-minute bar that ends there), k = 0..NH."""
    P = load_prices(path, t0, t1)
    return P[:: 60][: (t1 - t0) // HOUR + 1]


def fwd_return(PH, h):
    """r[k] = log(PH[k + h] / PH[k]); NaN where either is missing or k + h is past the end."""
    r = np.full(len(PH), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        r[: len(PH) - h] = np.log(PH[h:] / PH[: len(PH) - h])
    return r


# ---------------------------------------------------------------------------------------------------------- tests
def window_mask(win, h, t0=T0, n=NH + 1):
    """Decision instants T0 + k h inside the window whose return ends by the window's last day's end."""
    a = int(pd.Timestamp(win[0], tz="UTC").value // 10**6)
    b = int(pd.Timestamp(win[1], tz="UTC").value // 10**6) + 86_400_000
    T = t0 + np.arange(n, dtype=np.int64) * HOUR
    return (T >= a) & (T + h * HOUR <= b)


def cross(xs, rs):
    """u[k] = the sum over coins of x[k] r[k], over the coins where both are defined; NaN where none is."""
    prods = np.array([x * r for x, r in zip(xs, rs)])
    ok = np.isfinite(prods)
    return np.where(ok.any(0), np.where(ok, prods, 0.0).sum(0), np.nan)


def nw(u, mask, h):
    n, mu, t = stats.newey_west_t(np.where(mask, u, np.nan)[mask.argmax(): len(mask) - mask[::-1].argmax()],
                                  max(5, h))
    return {"n": int(n), "mean": float(mu) if np.isfinite(mu) else None, "t": float(t) if np.isfinite(t) else None}


def rule(x, r, h, mask, entry=ENTRY):
    """The reported trading rule on one coin: at an instant with no open position and |x| >= entry, take the sign of x
    for h hours. Returns the side x log return of each trade (gross)."""
    out, k, n = [], 0, len(x)
    while k < n:
        if mask[k] and np.isfinite(x[k]) and np.isfinite(r[k]) and abs(x[k]) >= entry:
            out.append(np.sign(x[k]) * r[k])
            k += h
        else:
            k += 1
    return np.array(out)


def rule_stats(g, cost=COST):
    if not len(g):
        return {"trades": 0}
    nets = {m: g - 2 * m * cost for m in (1, 2, 3)}
    sd = nets[1].std(ddof=1) if len(g) > 1 else np.nan
    return {"trades": int(len(g)), "gross_bp": float(g.mean() * 1e4),
            **{f"net{m}_bp": float(v.mean() * 1e4) for m, v in nets.items()},
            "t_net1": float(nets[1].mean() / sd * np.sqrt(len(g))) if sd > 0 else None,
            "hit": float((g > 0).mean())}


def analyze(x, r):
    """x[(cur, signal, h)] and r[(cur, h)] arrays over the decision instants; the 15 trials and their reports."""
    rows, passes, against = [], [], []
    for sig in SIGNALS:
        for h in HORIZONS:
            res = {"signal": sig, "method": METHOD[sig], "h": h}
            for name, win in (("disc", DISC), ("valid", VALID)):
                m = window_mask(win, h)
                u = cross([x[(c, sig, h)] for c in COINS], [r[(c, h)] for c in COINS])
                res[name] = nw(u, m, h)
                res[f"{name}_by_coin"] = {c: nw(x[(c, sig, h)] * r[(c, h)], m, h)["t"] for c in COINS}
                g = np.concatenate([rule(x[(c, sig, h)], r[(c, h)], h, m) for c in COINS])
                res[f"{name}_rule"] = rule_stats(g)
            res["valid_by_year"] = {}
            for y in (2024, 2025, 2026):
                m = window_mask((f"{y}-01-01", f"{y}-12-31" if y < 2026 else VALID[1]), h)
                u = cross([x[(c, sig, h)] for c in COINS], [r[(c, h)] for c in COINS])
                res["valid_by_year"][str(y)] = nw(u, m, h)["t"]
            td, tv = res["disc"]["t"], res["valid"]["t"]
            res["pass"] = bool(tv is not None and td is not None and tv >= T_MIN and td > 0)
            res["significant_against"] = bool(tv is not None and td is not None and tv <= -T_MIN and td < 0)
            vr = res["valid_rule"]
            res["lane_earned"] = bool(res["pass"] and vr.get("trades", 0) and vr["net1_bp"] > 0 and vr["net2_bp"] > 0)
            if res["pass"]:
                passes.append(f"{sig} h{h}")
            if res["significant_against"]:
                against.append(f"{sig} h{h}")
            rows.append(res)
    return {"tests": rows, "passes": passes, "significant_against": against,
            "verdict": "PARTIAL" if passes else "NULL"}


# ----------------------------------------------------------------------------------------------------------- main
def build(hashes):
    """(x, r, descriptives) from the frozen inputs."""
    x, r, desc = {}, {}, {}
    for cur, sym in COINS.items():
        rows = load_rows(cur, hashes=hashes)
        iv_med = float(np.nanmedian(rows.iv.to_numpy(float)))
        if not IV_RANGE[0] <= iv_med <= IV_RANGE[1]:
            raise SystemExit(f"{cur}: median traded IV {iv_med} is not in percent")
        hs = hourly_signals(rows)
        desc[cur] = {"flow_rows": int(len(rows)), "hours_with_trades": int(len(hs)),
                     "hours_with_blocks": int((hs.block_amount > 0).sum()),
                     "amount_without_delta_share": float(hs.amount_no_delta.sum() / hs.amount.sum()),
                     "block_amount_share": float(hs.block_amount.sum() / hs.amount.sum())}
        PH = hourly_prices(data.ROOT / "klines_1m" / f"{sym}.parquet")
        desc[cur]["price_instants_missing"] = int((~np.isfinite(PH)).sum())
        for h in HORIZONS:
            r[(cur, h)] = fwd_return(PH, h)
            for sig in SIGNALS:
                x[(cur, sig, h)] = zscore(window_sum(hour_array(hs, sig), h))
        log(cur, desc[cur])
    return x, r, desc


def frame(x, r):
    cols = {"T": T0 + np.arange(NH + 1, dtype=np.int64) * HOUR}
    for (c, h), v in r.items():
        cols[f"{c}_r{h}"] = v
    for (c, s, h), v in x.items():
        cols[f"{c}_{s}_{h}"] = v
    return pd.DataFrame(cols)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true", help="counts only, no statistic (before the freeze)")
    a = ap.parse_args()
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    if a.plumbing:
        x, r, desc = build(hashes)
        for h in HORIZONS:
            for name, win in (("disc", DISC), ("valid", VALID)):
                m = window_mask(win, h)
                n = {c: int((m & np.isfinite(x[(c, "drift", h)]) & np.isfinite(r[(c, h)])).sum()) for c in COINS}
                log(f"h{h} {name}: instants with x and r defined {n}")
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    x, r, desc = build(hashes)
    res = analyze(x, r)
    OUT.mkdir(parents=True, exist_ok=True)
    frame(x, r).to_parquet(OUT / "hourly.parquet", index=False)
    summary = {"lane": "optflow_v1", "rid": "R295", "prereg_sha": sha, "inputs": shas, "trials": TRIALS, "bar": T_MIN,
               "cost_per_side_1x": COST, "descriptives": desc, **res,
               "run": pd.Timestamp.now(tz="UTC").isoformat()}
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    (LANE / "results" / "summary.json").write_text(json.dumps(summary, indent=1))
    for t in res["tests"]:
        log(f"{t['signal']:>13} h{t['h']:<2} disc t {t['disc']['t']}  valid t {t['valid']['t']}  pass {t['pass']}")
    log("verdict", res["verdict"], "passes", res["passes"], "against", res["significant_against"])


if __name__ == "__main__":
    main()
