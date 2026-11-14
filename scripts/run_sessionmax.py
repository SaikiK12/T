"""sessionmax_v1 (R490, M539): session-decomposed MAX on 24/7 crypto perps, as frozen in
experiments/sessionmax_v1/PREREG.md. One run; no search.

Books (each a daily top/bottom-quintile, dollar-neutral, 7-day-hold slice book):
  S-INTRA : score = max of the last 7 intraday session returns (14:00-20:59 UTC)
  S-OVER  : score = max of the last 7 overnight session returns (21:00-13:59 UTC)
  CONTROL : score = max of the last 7 plain 24 h returns (the M144 book R222 found NULL)

Decision rows are 14:00 UTC, where both the day's intraday and overnight sessions are complete and equally fresh.
Everything is computed from data up to the decision row; no look-ahead.
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
from lab import config, panel, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "sessionmax_v1"
H = 168          # hold hours (7 d)
NW = 10          # Newey-West lag for the daily net
MIN_N = 15       # scored coins per day
SEED = 20261114
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)


def session_sums(lr, b, length, min_finite):
    """Sum of lr over rows b+1..b+length (per symbol); NaN unless at least min_finite hours are finite."""
    seg = lr[b + 1: b + 1 + length]
    if seg.shape[0] < length:
        return None
    fin = np.isfinite(seg)
    if (fin.sum(0) < min_finite).any():
        s = np.nansum(seg, axis=0)
        return np.where(fin.sum(0) >= min_finite, s, np.nan)
    return seg.sum(0)


def build_scores(lr, K):
    """Per decision index k (0..K-1): the three MAX scores. Decision row dec[k] = 24k + 37 (the 13:00 UTC bar,
    closing 14:00 UTC). At that row the fully completed sessions are day k's: the 24 h day (rows 24k..24k+23), the
    intraday window (rows 24k+14..24k+20) and the overnight window (rows 24k+21..24k+37, ending exactly at dec[k]).
    All three are therefore equally fresh and lag-free; nothing uses a row after dec[k].
    """
    n = lr.shape[1]
    A24 = np.full((K, n), np.nan)
    AIN = np.full((K, n), np.nan)
    AON = np.full((K, n), np.nan)
    for k in range(K):
        b = 24 * k - 1
        A24[k] = session_sums(lr, b, 24, 20)                 # day k, 00:00-23:59
        AIN[k] = session_sums(lr, b + 14, 7, 6)              # day k, 14:00-20:59
        AON[k] = session_sums(lr, b + 21, 17, 15)            # day k, 21:00 .. day k+1 13:59
    def rmax(a):
        out = np.full_like(a, np.nan)
        for k in range(7, K):
            w = a[k - 7:k]
            fin = np.isfinite(w).sum(0)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                m = np.nanmax(w, axis=0)
            out[k] = np.where(fin >= 5, m, np.nan)
        return out
    return rmax(A24), rmax(AIN), rmax(AON)


def quint(score, E, dec, T):
    s = np.where(E[dec], score, np.nan)
    ok = np.isfinite(s).sum(1) >= MIN_N
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        pct = pd.DataFrame(s).rank(axis=1, pct=True).values
    top = np.zeros((T, score.shape[1]), bool)
    bot = np.zeros((T, score.shape[1]), bool)
    top[dec] = (pct > 0.8) & ok[:, None]
    bot[dec] = (pct <= 0.2) & ok[:, None]
    return top, bot


def book(top, bot, K, a, bb, ret, E, cmat, cm):
    w = max(a - H, 0)
    unit = 1.0 / ((H / 24) * K)
    PL = slices.positions(top, H, w, bb, unit, 1)
    PS = slices.positions(bot, H, w, bb, unit, -1)
    o = slices.run(PL + PS, ret, E, cmat, w, bb, cmult=cm)
    D = (bb - a) // 24
    day = lambda x: x[a - w: a - w + D * 24].reshape(D, 24).sum(1)
    return day(o["net"]), day(o["gross"] + o["hedge"]), day(o["cost"] + o["hedge_cost"])


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    out = LANE / "results"
    out.mkdir(parents=True, exist_ok=True)
    p = panel.load_panel()
    u = research.make_universe(p, elig_top=50, col_top=50)
    syms = list(u.p.symbols)
    T = u.p.T
    T -= T % 24
    E = np.asarray(u.elig[:T], bool)
    ret = np.asarray(u.ret[:T], np.float64)
    cmat = np.asarray(u.cmat[:T], np.float64)
    close = np.asarray(u.p["close"][:T], np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr = np.full_like(close, np.nan)
        lr[1:] = np.log(close[1:] / close[:-1])
    K = (T - 37) // 24
    dec = 37 + 24 * np.arange(K)                   # 14:00 UTC decision rows (bar closing 14:00)
    dec = dec[dec < T]
    K = len(dec)
    m24, min_, mov = build_scores(lr, K)
    log(f"panel T={T} S={len(syms)} decision rows={K} {pd.Timestamp(dec[0]*panel.HOUR + panel.ms('2021-01-01'), unit='ms')}")

    t0, tv, th = (research.row_of(u.p, d) for d in ("2021-01-01", "2024-01-01", "2025-07-01"))
    th = min(th, T); tv = min(tv, T)
    btc = syms.index("BTCUSDT")

    # BTC daily log return over the day ending at row i: log(close[i]/close[i-24]) (0 before i=24).
    with np.errstate(invalid="ignore"):
        bclose = close[:, btc]
        bd_full = np.full(T, np.nan)
        bd_full[24:] = np.log(bclose[24:] / bclose[:-24])

    def window_bd(n_days, a, w):
        """BTC daily return for each book day j: the log return over the same rows the book's day j covers."""
        idx = (a - w) + 24 + 24 * np.arange(n_days)
        idx = idx[idx < T]
        return bd_full[idx]

    scores = {"S-INTRA": min_, "S-OVER": mov, "CONTROL": m24}
    rows, nets, spreads = [], {}, {}
    results = {}
    stage = {}
    for name, sc in scores.items():
        top, bot = quint(sc, E, dec, T)
        for w, (a, bb) in (("discovery", (t0, tv)), ("validation", (tv, th))):
            drow_win = dec[(dec >= a) & (dec < bb)]
            Kpos = float((top[drow_win].sum(1).mean() + bot[drow_win].sum(1).mean()) / 2) if len(drow_win) else np.nan
            if not np.isfinite(Kpos) or Kpos <= 0:
                Kpos = 1.0
            for cm in (1.0, 2.0, 3.0):
                n, gr, co = book(top, bot, Kpos, a, bb, ret, E, cmat, cm)
                rows.append({"book": name, "window": w, "cmult": cm, "days": len(n),
                             "mean_bp_day": float(np.nanmean(n) * 1e4),
                             "t_nw": float(stats.newey_west_t(n, NW)[2]),
                             "gross_bp_day": float(np.nanmean(gr) * 1e4),
                             "cost_bp_day": float(np.nanmean(co) * 1e4),
                             "total": float(np.nansum(n))})
                if cm == 1.0:
                    nets[(name, w)] = n
                    m = len(n)
                    bd = window_bd(m, a, max(a - H, 0))
                    k = min(len(n), len(bd))
                    x, y = n[:k], bd[:k]
                    ok = np.isfinite(x) & np.isfinite(y)
                    if ok.sum() > 2 and np.var(y[ok]) > 0:
                        beta = float(np.cov(x[ok], y[ok])[0, 1] / np.var(y[ok], ddof=1))
                        at = float(stats.newey_west_t(x[ok] - beta * y[ok], NW)[2])
                    else:
                        beta, at = np.nan, np.nan
                    results[(name, w)] = {"mean_bp_day": float(np.nanmean(n) * 1e4),
                                          "alpha_t": at, "beta_btc": beta, "days": int(np.isfinite(n).sum())}
            r1 = [r for r in rows if r["book"] == name and r["window"] == w and r["cmult"] == 1.0][0]
            gate = 1.5 if w == "validation" else 2.0
            passed = r1["mean_bp_day"] > 0 and results[(name, w)]["alpha_t"] >= gate
            stage[name] = stage.get(name, {})
            stage[name][w] = {"net_bp_day": r1["mean_bp_day"], "alpha_t": results[(name, w)]["alpha_t"],
                              "passed": bool(passed)}
            log(f"{name:8s} {w:10s} net {r1['mean_bp_day']:+.2f} bp/day t {r1['t_nw']:+.2f} "
                f"alpha_t {results[(name,w)]['alpha_t']:+.2f} gross {r1['gross_bp_day']:+.2f} cost {r1['cost_bp_day']:.2f}",
                "PASS" if passed else "stop")

    # M539-specific claim: each session book must beat its own 24 h control on discovery.
    comp = {}
    for name in ("S-INTRA", "S-OVER"):
        d = nets[(name, "discovery")] - nets[("CONTROL", "discovery")]
        m = min(len(nets[(name, "discovery")]), len(nets[("CONTROL", "discovery")]))
        d = d[:m]
        n, mu, t = stats.newey_west_t(d, NW)
        comp[name] = {"vs_control_mean_bp_day": float(np.nanmean(d) * 1e4), "t_nw": float(t), "days": int(n)}
        log(f"{name} - CONTROL discovery: {comp[name]['vs_control_mean_bp_day']:+.2f} bp/day t {comp[name]['t_nw']:+.2f}")

    # Block bootstrap null on the best discovery book's own 1x daily net (mean removed).
    rng = np.random.default_rng(SEED)
    best = max(("S-INTRA", "S-OVER", "CONTROL"),
               key=lambda nm: results[(nm, "discovery")]["alpha_t"] if np.isfinite(results[(nm, "discovery")]["alpha_t"]) else -9)
    x = np.nan_to_num(nets[(best, "discovery")])
    x = x[np.isfinite(nets[(best, "discovery")])]
    B, L, REPS = 10, NW, 2000
    xc = x - x.mean()
    nb = len(xc) // B
    null_t = np.empty(REPS)
    for i in range(REPS):
        st = rng.integers(0, nb, nb)
        samp = np.concatenate([xc[s * B:(s + 1) * B] for s in st])
        null_t[i] = stats.newey_west_t(samp, L)[2]
    thr = float(np.nanpercentile(null_t, 95))
    obs_t = float(results[(best, "discovery")]["alpha_t"])
    boot = {"best_book": best, "obs_alpha_t": obs_t, "null_95pct": thr, "reps": REPS, "block": B, "seed": SEED,
            "signal": bool(obs_t > thr)}

    # Session-label permutation: swap intraday/overnight per day and re-run both session books.
    perm_spread = {"S-INTRA": [], "S-OVER": []}
    for rep in range(200):
        sw = rng.random(K) < 0.5
        a1, a2 = min_.copy(), mov.copy()
        a1[sw], a2[sw] = mov[sw], min_[sw]
        for nm, sc in (("S-INTRA", a1), ("S-OVER", a2)):
            top, bot = quint(sc, E, dec, T)
            drow_win = dec[(dec >= t0) & (dec < tv)]
            Kp = float((top[drow_win].sum(1).mean() + bot[drow_win].sum(1).mean()) / 2) or 1.0
            n, _, _ = book(top, bot, Kp, t0, tv, ret, E, cmat, 1.0)
            ctrl = nets[("CONTROL", "discovery")]
            m = min(len(n), len(ctrl))
            perm_spread[nm].append(float(np.nanmean(n[:m] - ctrl[:m]) * 1e4))
    perm = {nm: {"real_bp_day": comp[nm]["vs_control_mean_bp_day"],
                 "perm_mean_bp_day": float(np.mean(v)), "perm_sd_bp_day": float(np.std(v)),
                 "p_ge_real": float((np.array(v) >= comp[nm]["vs_control_mean_bp_day"]).mean())}
            for nm, v in perm_spread.items()}

    # Diagnostics promised in the PREREG: 10% trimmed mean and leave-two-coins-out (discovery, 1x).
    diag = {}
    for name in ("S-INTRA", "S-OVER", "CONTROL"):
        n = nets[(name, "discovery")]
        x = n[np.isfinite(n)]
        lo, hi = np.percentile(x, [10, 90])
        trimmed = float(x[(x >= lo) & (x <= hi)].mean() * 1e4)
        top, bot = quint(scores[name], E, dec, T)
        drow_win = dec[(dec >= t0) & (dec < tv)]
        Kp = float((top[drow_win].sum(1).mean() + bot[drow_win].sum(1).mean()) / 2) or 1.0
        base = float(np.nanmean(n) * 1e4)
        worst = []
        n_sym = len(syms)
        for i in range(n_sym):
            for j in range(i + 1, n_sym):
                keep = np.ones(n_sym, bool)
                keep[[i, j]] = False
                t2 = top[:, keep].copy()
                b2 = bot[:, keep].copy()
                nn, _, _ = book(t2, b2, Kp, t0, tv, ret[:, keep], E[:, keep], cmat[:, keep], 1.0)
                worst.append(float(np.nanmean(nn) * 1e4))
        worst = np.array(worst)
        diag[name] = {"trimmed_1x_bp_day": trimmed, "base_1x_bp_day": base,
                      "l2co_min_bp_day": float(worst.min()), "l2co_mean_bp_day": float(worst.mean()),
                      "l2co_frac_positive": float((worst > 0).mean()), "l2co_pairs": int(worst.size)}
        log(f"diag {name}: trimmed {trimmed:+.2f} | L2CO min {worst.min():+.2f} mean {worst.mean():+.2f} "
            f"frac>0 {(worst > 0).mean():.2f}")

    verdict = {"R490": "sessionmax_v1", "best_book": best, "bootstrap": boot, "vs_control": comp, "permutation": perm,
               "stage": stage, "diagnostics": diag}
    (out / "report.json").write_text(json.dumps({"rows": rows, "results": {f"{k[0]}|{k[1]}": v for k, v in results.items()},
                                                 "verdict": verdict}, indent=1, sort_keys=True))
    log("WROTE", out / "report.json")
    print(json.dumps(verdict, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
