"""R307 rrskew_v1: does the Deribit 25-delta risk reversal time BTC and ETH perps week by week (M174), as set out in
experiments/rrskew_v1/PREREG.md.

The risk reversal is the implied vol of a 25-delta call minus that of a 25-delta put. Equity indices carry a
negative one (puts rich) most of the time; BTC's changes sign with the regime, and an unreviewed SMU dissertation
reports the 90-day one predicting BTC returns. The owner's reel DeKFE8OEq-i asked about it.

The lab has no stored skew series, so it is built from every Deribit option trade (scripts/fetch_deribit_trades.py,
hourly per-option rows with the amount-weighted IV and the last index price):
- for decision instant D (00:00 UTC), the option-hours in [D - 24 h, D);
- each row's Black-Scholes delta from its own IV, zero rates, the time to its 08:00 UTC expiry from the middle of its
  hour, and the forward F = index x exp(b x T), where b is the annualized log basis of the nearest Binance COIN-M
  quarterly with at least 14 days left, against the COIN-M perp, at the start of the row's hour;
- per tenor bucket (30 d: 14-60 days to expiry; 90 d: 60-150 days), the amount-weighted IV of calls with delta in
  [0.15, 0.35] and of puts with delta in [-0.35, -0.15], each needing 3 option-hours;
- RR = call IV - put IV, in vol points.

Signals per currency and tenor, on the daily RR series:
- sign: the RR itself (calls rich > 0);
- z: RR against its previous 90 daily values (at least 60), mean and standard deviation;
- chg7: RR minus RR 7 days earlier, z-scored the same way.
Each Monday 00:00 UTC a book holds the USDT perp long (signal > 0) or short for 7 days (follow), or the reverse (fade).
Costs per unit traded (manual web, 3 bp per side at 1x; 2x, 3x and the API's 8.5 bp reported), funding paid by longs.

usage: python scripts/run_rrskew.py [--plumbing] [--trees]
  --plumbing: RR and basis coverage counts only, no return read; --trees: the file-tree hash for the PREREG
"""
import argparse
import json
import re
import sys
import time
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402
from scripts.run_clockflow import T0, T1, check_inputs, load_funding  # noqa: E402
from scripts.run_msnr import tree_sha  # noqa: E402
from scripts.run_optflow import COINS, NH, PROVENANCE, hourly_prices, load_rows  # noqa: E402

LANE = ROOT / "experiments" / "rrskew_v1"
CM = data.ROOT / "coinm_1h"
HOUR, DAY = 3_600_000, 86_400_000
YEAR_MS = 365.25 * DAY
TENORS = {"30d": (14, 60), "90d": (60, 150)}       # days to expiry
WING = (0.15, 0.35)                                 # |delta| of the 25-delta wing
MIN_ROWS = 3
MIN_LEFT = 14                                       # days: the basis contract's shortest time to expiry
BASIS_FILL = 24                                     # hours a basis value is carried over a gap in the futures bars
Z_N, Z_NEED = 90, 60
SIGNALS = ("sign", "z", "chg7")
DIRS = ("follow", "fade")
BOOKS = [(c, ten, s, d) for c in COINS for ten in TENORS for s in SIGNALS for d in DIRS]
TRIALS = len(BOOKS)                                 # 24
WINDOWS = {"disc": ("2021-01-01", "2024-01-01"), "valid": ("2024-01-01", "2026-10-01")}
COST = 3e-4                                         # manual web, per side per unit traded, at 1x (R289)
API = 8.5e-4                                        # the API cost per side, reported, not decided on
CMULTS = {"1x": 1, "2x": 2, "3x": 3, "api": API / COST}
T_MIN = 2.0
NW_LAG = 4
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").value // 10**6)


# -------------------------------------------------------------------------------------------------------- basis
def quarterlies(cur, root=CM):
    """The COIN-M quarterly contracts of `cur` that expire after T0: [(path, expiry ms at 08:00 UTC)]."""
    out = []
    for p in sorted(root.glob(f"{cur}USD_[0-9]*.parquet")):
        exp = ms(pd.Timestamp("20" + p.stem.split("_")[1]).strftime("%Y-%m-%d")) + 8 * HOUR
        if exp > T0:
            out.append((p, exp))
    return out


def basis_files(root=CM):
    """Every COIN-M file the lane reads: both perps and the quarterlies above."""
    return [root / f"{c}USD_PERP.parquet" for c in COINS] + [p for c in COINS for p, _ in quarterlies(c, root)]


def bar_closes(path, n=NH + 1):
    """C[k] = the close of the hourly bar that ends at the instant T0 + k h. Rows outside [T0, T1) are dropped on
    read."""
    k = pd.read_parquet(path, columns=["t", "close"])
    k = k[(k.t >= T0) & (k.t < T1) & (k.close > 0)].drop_duplicates("t")
    C = np.full(n, np.nan)
    i = (k.t.to_numpy(np.int64) - T0) // HOUR + 1
    C[i[i < n]] = k.close.to_numpy(float)[i < n]
    return C


def hourly_basis(cur, root=CM, n=NH + 1):
    """b[k]: the annualized log basis ln(F / S) / tau at the instant T0 + k h, from the quarterly with the shortest
    time to expiry tau of at least MIN_LEFT days, against the COIN-M perp; carried forward over gaps of up to
    BASIS_FILL hours."""
    S = bar_closes(root / f"{cur}USD_PERP.parquet", n)
    inst = T0 + np.arange(n, dtype=np.int64) * HOUR
    best_tau = np.full(n, np.inf)
    b = np.full(n, np.nan)
    for p, exp in quarterlies(cur, root):
        F = bar_closes(p, n)
        tau = (exp - inst) / YEAR_MS
        ok = np.isfinite(F) & np.isfinite(S) & (tau * 365.25 >= MIN_LEFT) & (tau < best_tau)
        with np.errstate(invalid="ignore", divide="ignore"):
            b[ok] = np.log(F[ok] / S[ok]) / tau[ok]
        best_tau[ok] = tau[ok]
    return pd.Series(b).ffill(limit=BASIS_FILL).to_numpy(float)


# --------------------------------------------------------------------------------------------------------- skew
def ncdf(x):
    return 0.5 * (1.0 + np.vectorize(erf)(np.asarray(x, float) / sqrt(2.0)))


def deltas(rows, basis=None):
    """Black-Scholes delta of each option-hour from its own IV (percent) and zero rates, on the forward
    F = index x exp(b x T) with `basis` b per row (0 when None); the time to expiry T runs from the middle of the
    row's hour. Returns (delta, days to expiry); delta is NaN where the inputs are not usable."""
    T = (rows.expiry_ms.to_numpy(float) - (rows.t.to_numpy(float) + HOUR / 2)) / YEAR_MS
    sig = rows.iv.to_numpy(float) / 100.0
    b = np.zeros(len(rows)) if basis is None else np.asarray(basis, float)
    F = rows.index_price.to_numpy(float) * np.exp(b * np.maximum(T, 0.0))
    K = rows.strike.to_numpy(float)
    ok = (T > 0) & (sig > 0) & (F > 0) & (K > 0) & np.isfinite(F)
    d1 = np.full(len(rows), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        d1[ok] = (np.log(F[ok] / K[ok]) + 0.5 * sig[ok] ** 2 * T[ok]) / (sig[ok] * np.sqrt(T[ok]))
    call = rows.cp.to_numpy() == "C"
    nd = ncdf(np.nan_to_num(d1))
    return np.where(np.isfinite(d1), np.where(call, nd, nd - 1.0), np.nan), T * 365.25


def daily_rr(rows, days_ms, b_hourly=None):
    """{tenor: array of RR (vol points) at each decision instant in days_ms}, from the option-hours of the 24 h before.
    `b_hourly[k]` is the basis at the instant T0 + k h (None: zero basis); a row at hour t uses the value at t, and a
    row without one is dropped."""
    rows = rows[(rows.iv > 0) & (rows.iv < 500) & ((rows.buy + rows.sell) > 0)].copy()
    if b_hourly is not None:
        k = ((rows.t.to_numpy(np.int64) - T0) // HOUR).clip(0, len(b_hourly) - 1)
        rows["b"] = b_hourly[k]
        rows = rows[np.isfinite(rows.b)]
    rows["delta"], rows["tdays"] = deltas(rows, None if b_hourly is None else rows.b.to_numpy())
    rows["w"] = rows.buy + rows.sell
    rows["day"] = (rows.t // DAY + 1) * DAY            # the decision instant the row feeds: the next 00:00 UTC
    out = {}
    for ten, (lo, hi) in TENORS.items():
        r = rows[(rows.tdays >= lo) & (rows.tdays < hi)]
        call = r[(r.cp == "C") & (r.delta >= WING[0]) & (r.delta <= WING[1])]
        put = r[(r.cp == "P") & (r.delta >= -WING[1]) & (r.delta <= -WING[0])]
        iv = {}
        for name, g in (("c", call), ("p", put)):
            n = g.groupby("day").size()
            avg = (g.iv * g.w).groupby(g.day).sum() / g.w.groupby(g.day).sum()
            iv[name] = avg[n >= MIN_ROWS]
        out[ten] = (iv["c"] - iv["p"]).reindex(days_ms).to_numpy(float)
    return out


def rolling_z(x, n=Z_N, need=Z_NEED):
    """x[k] against the previous n values (not including k), at least `need` of them finite."""
    s = pd.Series(x)
    prev = s.shift(1).rolling(n, min_periods=need)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (s - prev.mean()) / prev.std()
    return z.to_numpy(float)


def signals(rr):
    """{signal: daily array} from one tenor's daily RR."""
    chg = np.full(len(rr), np.nan)
    chg[7:] = rr[7:] - rr[:-7]
    return {"sign": rr, "z": rolling_z(rr), "chg7": rolling_z(chg)}


# -------------------------------------------------------------------------------------------------------- books
def mondays(days_ms):
    """Indices of the Monday decision instants among days_ms (consecutive 00:00 UTC instants)."""
    return np.flatnonzero(pd.to_datetime(days_ms, unit="ms").dayofweek == 0)


def week_returns(P, f_t, f_rate, days_ms, idx):
    """Per Monday index: the perp's simple return over the next 7 days and the funding a long pays in (D, D + 7 d]."""
    r = np.full(len(idx), np.nan)
    fund = np.zeros(len(idx))
    for j, k in enumerate(idx):
        if k + 7 < len(P) and np.isfinite(P[k]) and np.isfinite(P[k + 7]) and P[k] > 0:
            r[j] = P[k + 7] / P[k] - 1.0
        a, b = days_ms[k], days_ms[k] + 7 * DAY
        m = (f_t > a) & (f_t <= b)
        fund[j] = float(f_rate[m].sum())
    return r, fund


def book(sig_w, r, fund, direction, cmult):
    """Weekly net series of a +-1 book: side = sign(signal) (follow) or its negative (fade), held 7 days; flat (NaN)
    when the signal or the return is missing. Cost per unit traded: a change of side is charged to the week it opens
    (an entry 1 unit, a flip 2), and a move to flat, or the end of the series, to the last week held (1 unit)."""
    side = np.sign(np.nan_to_num(sig_w)) * (1.0 if direction == "follow" else -1.0)
    side[~np.isfinite(sig_w) | ~np.isfinite(r)] = 0.0
    prev = np.concatenate([[0.0], side[:-1]])
    nxt = np.concatenate([side[1:], [0.0]])
    c = cmult * COST
    cost = c * np.abs(side - prev) + c * np.abs(side) * (nxt == 0)
    return np.where(side != 0, side * np.nan_to_num(r) - side * fund - cost, np.nan)


def series_stats(x):
    """Newey-West t on the weekly series (flat weeks are gaps), mean bp per week, weeks, without the 10 best."""
    ok = np.isfinite(x)
    if ok.sum() < 20:
        return {"weeks": int(ok.sum())}
    n, m, t = stats.newey_west_t(x, NW_LAG)
    s = np.sort(x[ok])
    return {"weeks": int(n), "mean_bp": float(m * 1e4), "t": float(t) if np.isfinite(t) else None,
            "hit": float((x[ok] > 0).mean()), "wo_best10_bp": float(s[:-10].mean() * 1e4)}


def decide(rep):
    cand = [(k, v["disc"]["1x"]) for k, v in rep.items()
            if v["disc"]["1x"].get("t") is not None and v["disc"]["1x"]["mean_bp"] > 0]
    if not cand:
        return None, False, {}
    pick = max(cand, key=lambda z: z[1]["t"])[0]
    v = rep[pick]["valid"]
    checks = {"t_1x": (v["1x"].get("t") or -np.inf) >= T_MIN, "mean_2x": v["2x"].get("mean_bp", -1) > 0,
              "wo_best": (v["1x"].get("wo_best10_bp") or -1) > 0}
    return pick, all(checks.values()), checks


def label(b):
    return " ".join(b)


# ---------------------------------------------------------------------------------------------------------- inputs
def check_trees(prereg_path):
    """The COIN-M tree in the PREREG's trees block must still hash to its frozen sha256."""
    block = re.search(r"```trees\n(.*?)```", Path(prereg_path).read_text(), re.S).group(1)
    want = dict(line.split()[::-1] for line in block.strip().splitlines())
    got = {"coinm_1h": tree_sha(basis_files())}
    if set(want) != set(got) or want["coinm_1h"] != got["coinm_1h"]:
        raise prereg.PreregError(f"trees: {got} != frozen {want}")
    return got


def build_rr(hashes):
    days_ms = np.arange(T0, T1 + 1, DAY, dtype=np.int64)    # decision instants 2021-01-01 .. 2026-10-01
    rr, cover = {}, {}
    for cur in COINS:
        b = hourly_basis(cur)
        rows = load_rows(cur, hashes=hashes)
        k = ((rows.t.to_numpy(np.int64) - T0) // HOUR).clip(0, len(b) - 1)
        cover[cur] = {"option_hours": int(len(rows)), "with_basis": int(np.isfinite(b[k]).sum()),
                      "basis_hours": int(np.isfinite(b).sum()), "hours": int(len(b))}
        for ten, v in daily_rr(rows, days_ms, b).items():
            rr[(cur, ten)] = v
    return days_ms, rr, cover


def plumbing(hashes):
    """Counts only: option-hours with a basis, and decision days with an RR per window. No return is read."""
    days_ms, rr, cover = build_rr(hashes)
    out = {"basis": cover}
    for (cur, ten), v in rr.items():
        out[f"{cur} {ten}"] = {w: {"days": int(((days_ms >= ms(a)) & (days_ms < ms(b))).sum()),
                                   "with_rr": int(np.isfinite(v[(days_ms >= ms(a)) & (days_ms < ms(b))]).sum())}
                               for w, (a, b) in WINDOWS.items()}
    return out


# --------------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--trees", action="store_true")
    a = ap.parse_args()
    if a.trees:
        print(f"{tree_sha(basis_files())}  coinm_1h  ({len(basis_files())} files)")
        return
    hashes = {h["path"]: h["sha256"] for h in json.loads(PROVENANCE.read_text())["file_hashes"]}
    if a.plumbing:
        print(json.dumps(plumbing(hashes), indent=1))
        return
    sha = prereg.verify(LANE / "PREREG.md")
    shas = check_inputs(LANE / "PREREG.md")
    trees = check_trees(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs and {len(trees)} file tree match")
    days_ms, rr, cover = build_rr(hashes)
    log(f"basis cover {cover}")
    idx = mondays(days_ms)
    rets, rep, weekly = {}, {}, {}
    for cur, sym in COINS.items():
        P = hourly_prices(data.ROOT / "klines_1m" / f"{sym}.parquet")[::24][: len(days_ms)]
        ft, fr = load_funding(data.ROOT / "fundingRate" / f"{sym}.parquet")
        keep = (ft >= T0) & (ft < T1)
        rets[cur] = week_returns(P, ft[keep], fr[keep], days_ms, idx)
    t_w = days_ms[idx]
    for b in BOOKS:
        cur, ten, s, d = b
        sig = signals(rr[(cur, ten)])[s][idx]
        r, fund = rets[cur]
        rep[label(b)] = {}
        for w, (lo, hi) in WINDOWS.items():
            m = (t_w >= ms(lo)) & (t_w + 7 * DAY <= ms(hi))
            rep[label(b)][w] = {k: series_stats(book(sig[m], r[m], fund[m], d, c)) for k, c in CMULTS.items()}
        weekly[label(b)] = book(sig, r, fund, d, 1)
        v, dd = rep[label(b)]["valid"]["1x"], rep[label(b)]["disc"]["1x"]
        log(f"{label(b)}: disc {dd.get('mean_bp', float('nan')):+.1f} t {dd.get('t')}; valid "
            f"{v.get('mean_bp', float('nan')):+.1f} t {v.get('t')}")
    pick, ok, checks = decide(rep)
    log(f"pick {pick}, passes {ok} {checks}")
    hold = {cur: {w: series_stats(np.where((t_w >= ms(lo)) & (t_w + 7 * DAY <= ms(hi)), rets[cur][0] - rets[cur][1],
                                           np.nan)) for w, (lo, hi) in WINDOWS.items()} for cur in COINS}
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"t": t_w, **{f"rr_{c}_{t}": rr[(c, t)][idx] for c, t in rr},
                  **{f"ret_{c}": rets[c][0] for c in COINS}, **{f"fund_{c}": rets[c][1] for c in COINS},
                  **{f"net1_{k}": v for k, v in weekly.items()}}).to_csv(res / "weeks.csv", index=False,
                                                                         float_format="%.6g")
    summary = {"rid": "R307", "verdict": "PARTIAL" if ok else "NULL", "trials": TRIALS, "prereg_sha256": sha,
               "inputs": shas, "trees": trees, "basis_cover": cover, "pick": pick, "pick_passes": bool(ok),
               "checks": checks, "books": rep, "buy_and_hold": hold}
    (res / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


if __name__ == "__main__":
    main()
