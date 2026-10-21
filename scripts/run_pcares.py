"""pcares_v1 (R287): Avellaneda-Lee PCA residual reversion on the top-50 Binance perps at hourly scale, as set out in
experiments/pcares_v1/PREREG.md (M298). 24 variants (K factors x OU window L x entry e x hedge), a White reality check
on 2021-03..2023 and the selected variant read on 2024-01..2026-09.

usage: python scripts/run_pcares.py
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import data, prereg, stats  # noqa: E402

LANE = ROOT / "experiments" / "pcares_v1"
H_MS = 3_600_000
T0 = int(pd.Timestamp("2021-01-01", tz="UTC").value // 10**6)       # 2020 is reserved: dropped on load
T1 = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)       # exclusive
FIRST_DAY = "2021-03-03"
DISC = ("2021-03-03", "2023-12-31")
VALID = ("2024-01-01", "2026-09-30")
HALVES = (("2024-01-01", "2025-06-30"), ("2025-07-01", "2026-09-30"))
N, W, VOLW = 50, 1440, 720
KS, LS, ES, HEDGES = (1, 3, 5), (72, 168), (1.25, 2.0), ("factor", "dollar")
EXIT = 0.5
COST = 7e-4                                                         # per side at 1x
TRIALS = 24
RC_B, RC_BLOCK, SEED = 2000, 10, 287
TRADFI = ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json"
EXTRA = {"USDCUSDT", "PAXGUSDT", "XAUTUSDT", "BLUEBIRDUSDT", "FOOTBALLUSDT"}
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
SHAS = {}


# ---------------------------------------------------------------------------------------------------------- model
def fit_day(R, QV, d0, allowed, kmax=max(KS)):
    """Universe and PCA of the day whose first hour is d0, from the W hours before it. Returns (U, V, sd): symbol
    columns of the top-N by quote volume, the kmax leading eigenvectors (kmax x n) and the return sd (ddof 1)."""
    Rw = R[d0 - W:d0]
    elig = allowed & ~np.isnan(Rw).any(axis=0)
    cand = np.flatnonzero(elig)
    sd_all = Rw[:, cand].std(axis=0, ddof=1)
    cand = cand[sd_all > 0]
    vol = np.nansum(QV[d0 - VOLW:d0][:, cand], axis=0)
    U = cand[np.lexsort((cand, -vol))][:N]                         # columns are in alphabetical order
    X = Rw[:, U]
    sd = X.std(axis=0, ddof=1)
    Y = (X - X.mean(axis=0)) / sd
    _, vecs = np.linalg.eigh(Y.T @ Y / (W - 1))
    return U, vecs[:, ::-1][:, :kmax].T, sd


def betas(R, d0, U, V, sd, K):
    """Eigenportfolio weights Q (K x n) and OLS betas (K x n) of each coin on [1, F_1..F_K] over the window."""
    X = R[d0 - W:d0][:, U]
    Q = V[:K] / sd
    F = X @ Q.T
    B = np.linalg.lstsq(np.column_stack([np.ones(W), F]), X, rcond=None)[0]
    return Q, B[1:]


def day_scores(R, d0, U, Q, beta, L, hours=24):
    """s-scores and the fast-enough flag at the closes of hours d0..d0+hours-1 (fewer at the end of the data)."""
    lo, hi = d0 - (L - 1), min(d0 + hours, len(R))
    Rb = R[lo:hi][:, U]
    eps = Rb - (np.nan_to_num(Rb) @ Q.T) @ beta                   # a missing return counts as 0 in F, NaN in eps
    miss = np.isnan(eps)
    Xc = np.cumsum(np.where(miss, 0.0, eps), axis=0)               # s is invariant to the running sum's offset
    nh = hi - d0
    win = sliding_window_view(Xc, L, axis=0)[:nh]                  # (nh, n, L): window j ends at hour d0 + j
    gap = sliding_window_view(miss, L, axis=0)[:nh].any(axis=2)
    x, y = win[..., :-1], win[..., 1:]
    mx, my = x.mean(axis=-1), y.mean(axis=-1)
    dx, dy = x - mx[..., None], y - my[..., None]
    vx, cxy, vy = (dx * dx).mean(axis=-1), (dx * dy).mean(axis=-1), (dy * dy).mean(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = cxy / vx
        a = my - b * mx
        v = vy - b * cxy                                           # mean squared AR(1) residual
        ok = (vx > 0) & (b > 0) & (b < 1) & (v > 0) & ~gap
        s = (y[..., -1] - a / (1 - b)) / np.sqrt(v / (1 - b * b))
    s = np.where(ok, s, np.nan)
    return s, ok & (b < np.exp(-2.0 / L))


# ------------------------------------------------------------------------------------------------------- the book
def simulate(R, FUND, days, U_of, model, S, FAST, h0, e, hedge, n_days):
    """Hourly book from the decision at h0 to the last bar. U_of[d]: day d's universe columns; model[d] = (Q, beta);
    S, FAST: (hours, n) local scores. Returns daily gross, cost at 1x, funding, turnover, exposure, plus counts and
    the per-column gross."""
    n_h, n_s = R.shape
    out = {k: np.zeros(n_days) for k in ("gross", "cost", "funding", "turnover", "exposure")}
    p_full = np.zeros(n_s, np.int8)
    w_prev = np.zeros(n_s)
    col_gross = np.zeros(n_s)
    opened = pos_hours = 0
    for h in range(h0, n_h - 1):
        d = h // 24
        U = U_of[d]
        s, f = S[h, :len(U)], FAST[h, :len(U)]
        po = p_full[U]
        p = np.where(np.isnan(s), 0, po).astype(np.int8)
        p[(p == 1) & (s >= -EXIT)] = 0
        p[(p == -1) & (s <= EXIT)] = 0
        m0 = (p == 0) & f
        p[m0 & (s <= -e)] = 1
        p[m0 & (s >= e)] = -1
        opened += int(((p != 0) & (p != po)).sum())
        pos_hours += int((p != 0).sum())
        p_full[:] = 0
        p_full[U] = p
        w = np.zeros(n_s)
        if hedge == "dollar":
            nl, ns = int((p == 1).sum()), int((p == -1).sum())
            if nl and ns:
                w[U] = np.where(p == 1, 0.5 / nl, np.where(p == -1, -0.5 / ns, 0.0))
        else:
            n = int(np.abs(p).sum())
            if n:
                Q, beta = model[d]
                u = p / n
                w[U] = u - (beta @ u) @ Q
        r = np.nan_to_num(R[h + 1])
        g = w * r
        dd = (h + 1) // 24 - days[0]
        turn = float(np.abs(w - w_prev).sum())
        out["gross"][dd] += g.sum()
        out["cost"][dd] += COST * turn
        out["funding"][dd] += float(w @ FUND[h + 1])
        out["turnover"][dd] += turn
        out["exposure"][dd] += float(np.abs(w).sum()) / 24
        col_gross += g
        w_prev = w
    out["opened"], out["pos_hours"], out["col_gross"] = opened, pos_hours, col_gross
    return out


def build(R, QV, days, allowed):
    """Fit every day's model and score its hours for every (K, L)."""
    n_h = len(R)
    U_of, model = {}, {K: {} for K in KS}
    S = {(K, L): np.full((n_h, N), np.nan) for K in KS for L in LS}
    FAST = {(K, L): np.zeros((n_h, N), bool) for K in KS for L in LS}
    small = []
    for d in days:
        d0 = d * 24
        U, V, sd = fit_day(R, QV, d0, allowed)
        U_of[d] = U
        if len(U) < N:
            small.append((int(d), len(U)))
        for K in KS:
            Q, beta = betas(R, d0, U, V, sd, K)
            model[K][d] = (Q, beta)
            for L in LS:
                s, f = day_scores(R, d0, U, Q, beta, L)
                S[K, L][d0:d0 + len(s), :len(U)] = s
                FAST[K, L][d0:d0 + len(s), :len(U)] = f
        if d % 200 == 0:
            log(f"model day {d}/{n_h // 24}")
    return U_of, model, S, FAST, small


def stationary_idx(rng, n, block, B):
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    jump = rng.random((B, n)) < 1.0 / block
    fresh = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jump[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def reality_check(X, rng):
    """White's reality check, studentized, as in R263: X is (variants, days)."""
    n = X.shape[1]
    sd = X.std(axis=1)
    sd = np.where(sd > 0, sd, np.inf)
    stat = np.sqrt(n) * X.mean(axis=1) / sd
    Xd = X - X.mean(axis=1, keepdims=True)
    mx = np.array([np.max(np.sqrt(n) * Xd[:, b].mean(axis=1) / sd) for b in stationary_idx(rng, n, RC_BLOCK, RC_B)])
    return stat, float((mx >= stat.max()).mean()), float(np.percentile(mx, 95))


# ----------------------------------------------------------------------------------------------------------- data
def load():
    excluded = set(json.loads(TRADFI.read_text())) | EXTRA
    SHAS["tradfi_symbols.json"] = prereg.sha256_file(TRADFI)
    files = [p for p in sorted((data.ROOT / "klines_1h").glob("*USDT.parquet")) if p.stem not in excluded]
    n_h = (T1 - T0) // H_MS
    syms = [p.stem for p in files]
    R = np.full((n_h, len(files)), np.nan)
    QV = np.zeros((n_h, len(files)), np.float32)
    FUND = np.zeros((n_h, len(files)), np.float32)
    for j, p in enumerate(files):
        SHAS[f"klines_1h/{p.stem}"] = prereg.sha256_file(p)
        k = pd.read_parquet(p, columns=["t", "close", "count", "quote_volume"])
        k = k[(k.t >= T0) & (k.t < T1)].drop_duplicates("t").sort_values("t")
        idx = ((k.t.values - T0) // H_MS).astype(np.int64)
        c = np.full(n_h, np.nan)
        good = (k["count"].values > 0) & (k.close.values > 0)
        c[idx[good]] = k.close.values[good]
        R[1:, j] = c[1:] / c[:-1] - 1
        QV[idx, j] = np.nan_to_num(k.quote_volume.values)
        fp = data.ROOT / "fundingRate" / f"{p.stem}.parquet"
        if fp.exists():
            SHAS[f"fundingRate/{p.stem}"] = prereg.sha256_file(fp)
            f = pd.read_parquet(fp, columns=["t", "rate"])
            bar = np.rint(f.t.values / H_MS).astype(np.int64) - 1 - T0 // H_MS   # the bar that ends at F
            keep = (bar >= 0) & (bar < n_h)
            np.add.at(FUND[:, j], bar[keep], f.rate.values[keep].astype(np.float32))
        if (j + 1) % 200 == 0:
            log(f"{j + 1}/{len(files)} perps read")
    return syms, R, QV, FUND, excluded


def window(days_dt, a, b):
    return (days_dt >= pd.Timestamp(a)) & (days_dt <= pd.Timestamp(b))


def summarize(o, m, name, n_days_dt):
    rows = []
    net = {c: o["gross"] - o["funding"] - c * o["cost"] for c in (1, 2, 3)}
    for wname, (a, b) in (("discovery", DISC), ("validation", VALID), ("valid_h1", HALVES[0]), ("valid_h2", HALVES[1])):
        sel = window(n_days_dt, a, b)
        x1 = net[1][sel]
        _, mu, t = stats.newey_west_t(x1, 10)
        turn = o["turnover"][sel].mean()
        rows.append({"variant": name, **m, "window": wname, "days": int(sel.sum()),
                     "gross_bp": o["gross"][sel].mean() * 1e4, "cost1_bp": o["cost"][sel].mean() * 1e4,
                     "funding_bp": o["funding"][sel].mean() * 1e4,
                     "net1_bp": mu * 1e4, "net2_bp": net[2][sel].mean() * 1e4, "net3_bp": net[3][sel].mean() * 1e4,
                     "nw_t1": t, "sharpe1": x1.mean() / x1.std() * np.sqrt(365) if x1.std() > 0 else np.nan,
                     "turnover": turn, "exposure": o["exposure"][sel].mean(),
                     "breakeven_bp_side": o["gross"][sel].mean() / turn * 1e4 if turn > 0 else np.nan,
                     "pos_days": float((x1 > 0).mean())})
    return rows, net


def main():
    sha = prereg.verify(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}")
    syms, R, QV, FUND, excluded = load()
    n_h, n_s = R.shape
    log(f"{n_s} perps after excluding {len(excluded)} names; {n_h} hours")
    allowed = np.ones(n_s, bool)
    d_first = (int(pd.Timestamp(FIRST_DAY, tz="UTC").value // 10**6) - T0) // (24 * H_MS)
    days = np.arange(d_first, n_h // 24)
    U_of, model, S, FAST, small = build(R, QV, days, allowed)
    if small:
        log(f"{len(small)} days with fewer than {N} symbols, smallest {min(n for _, n in small)}")
    days_dt = pd.to_datetime((T0 // H_MS // 24 + days) * 86_400_000, unit="ms")
    rows, nets, extra = [], [], {}
    for K in KS:
        for L in LS:
            for e in ES:
                for hedge in HEDGES:
                    name = f"K{K}_L{L}_e{e}_{hedge}"
                    o = simulate(R, FUND, days, U_of, model[K], S[K, L], FAST[K, L], d_first * 24, e, hedge,
                                 len(days))
                    r, net = summarize(o, {"K": K, "L": L, "e": e, "hedge": hedge}, name, days_dt)
                    for x in r:
                        x["opened"] = o["opened"]
                        x["hold_hours"] = o["pos_hours"] / o["opened"] if o["opened"] else np.nan
                    rows += r
                    nets.append(net)
                    extra[name] = o
                    log(f"{name:22s} disc net1 {r[0]['net1_bp']:7.2f} bp/d t {r[0]['nw_t1']:5.2f} gross "
                        f"{r[0]['gross_bp']:6.2f} turn {r[0]['turnover']:6.2f}  valid net1 {r[1]['net1_bp']:7.2f}")
    names = list(extra)
    disc = window(days_dt, *DISC)
    val = window(days_dt, *VALID)
    X = np.array([n[1][disc] for n in nets])
    stat, rc_p, p95 = reality_check(X, np.random.default_rng(SEED))
    j = int(np.argmax(stat))
    v1, v2 = nets[j][1][val], nets[j][2][val]
    tv = float(stats.newey_west_t(v1, 10)[2])
    halves = [float(nets[j][1][window(days_dt, *hh)].mean()) for hh in HALVES]
    passed = bool(rc_p < 0.05 and tv >= 2.0 and v2.mean() > 0 and min(halves) > 0)
    verdict = "PARTIAL" if passed else "NULL"
    best = extra[names[j]]
    netj = pd.Series(nets[j][1], index=days_dt)
    by_year = (netj.groupby(netj.index.year).mean() * 1e4).round(3).to_dict()
    top5d = float(np.sort(nets[j][1])[::-1][:5].sum() / nets[j][1].sum()) if nets[j][1].sum() > 0 else float("nan")
    cg = best["col_gross"]
    top5c = {syms[i]: float(cg[i] * 1e4) for i in np.argsort(-cg)[:5]}
    log(f"reality check: best {names[j]} stat {stat[j]:.2f} p {rc_p:.4f} (null p95 {p95:.2f}); "
        f"validation t {tv:.2f}, 2x {v2.mean() * 1e4:.2f} bp/d, halves {[round(h * 1e4, 2) for h in halves]} -> {verdict}")
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "variants.csv", index=False, float_format="%.6g")
    daily = []
    for name in names:
        o = extra[name]
        daily.append(pd.DataFrame({"day": days_dt.date, "variant": name, "gross": o["gross"], "cost1": o["cost"],
                                   "funding": o["funding"], "net1": o["gross"] - o["funding"] - o["cost"]}))
    pd.concat(daily).to_csv(out / "daily.csv.gz", index=False, float_format="%.8g")
    pd.Series(SHAS, name="sha256").rename_axis("file").to_csv(out / "inputs.csv")
    combined = hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(SHAS.items())).encode()).hexdigest()
    summary = {"rid": "R287", "verdict": verdict, "trials": TRIALS, "prereg_sha256": sha,
               "rc_p": rc_p, "rc_null_p95": p95, "best": names[j], "best_disc_stat": float(stat[j]),
               "best_disc_net1_bp": float(X[j].mean() * 1e4), "valid_t1": tv,
               "valid_net1_bp": float(v1.mean() * 1e4), "valid_net2_bp": float(v2.mean() * 1e4),
               "valid_net3_bp": float(nets[j][3][val].mean() * 1e4),
               "valid_halves_net1_bp": [h * 1e4 for h in halves], "best_net1_bp_by_year": by_year,
               "best_top5_days_share": top5d, "best_top5_coins_gross_bp": top5c,
               "days_small_universe": len(small), "symbols": n_s, "excluded_names": len(excluded),
               "inputs": len(SHAS), "inputs_combined_sha256": combined}
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log(f"verdict {verdict}")
    return summary


if __name__ == "__main__":
    main()
