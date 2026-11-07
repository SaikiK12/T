"""brute5k_v1 (R263): 5,472 chart strategies (76 base rules x 4 timeframes x 3 directions x 3 filters x 2 stops) on the
top-20 perps, a monthly walk-forward selection of what worked over the last L months, a random-selection null, White's
reality check on the best single strategy, and a Monte Carlo of leverage, as set out in experiments/brute5k_v1/PREREG.md.

usage: python scripts/run_brute5k.py            (computes the strategy nets into cache/, then the analysis)
       python scripts/run_brute5k.py --analyse  (analysis only, from cache/)
"""
import json
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lab import flowfeat, prereg, research, slices, stats  # noqa: E402

LANE = ROOT / "experiments" / "brute5k_v1"
TFS = (1, 4, 12, 24)
DIRS = ("both", "long", "short")
FILTERS = ("none", "trend", "calm")
STOPS = ("none", "atr2")
TOP, K_SEL, LOOKS, MAIN_L, N_RAND = 20, 20, (3, 6, 12), 6, 1000
SWITCH_COST = 6e-4
DECIDE = ("2021-07-01", "2025-07-01")
DISC = ("2021-07-01", "2024-01-01")
VALID = ("2024-01-01", "2025-07-01")
RC_B, RC_BLOCK, MC_PATHS, MC_DAYS, MC_BLOCK = 500, 10, 10000, 365, 20
LEVS = (1, 2, 3, 5, 10)
log = lambda *a: print(time.strftime("%H:%M:%S"), *a, flush=True)
warnings.simplefilter("ignore", RuntimeWarning)


# ---------------------------------------------------------------- rules (numba state machines, one column at a time)
@njit(cache=True)
def band_machine(z, k, fade):
    n, m = z.shape
    out = np.zeros((n, m), np.int8)
    for j in range(m):
        p = 0
        for i in range(n):
            x = z[i, j]
            if not np.isfinite(x):
                p = 0
            else:
                if fade:
                    if p == 1 and x >= 0:
                        p = 0
                    elif p == -1 and x <= 0:
                        p = 0
                    if p == 0:
                        if x < -k:
                            p = 1
                        elif x > k:
                            p = -1
                else:
                    if p == 1 and x <= 0:
                        p = 0
                    elif p == -1 and x >= 0:
                        p = 0
                    if p == 0:
                        if x > k:
                            p = 1
                        elif x < -k:
                            p = -1
            out[i, j] = p
    return out


@njit(cache=True)
def donchian_machine(c, hiN, loN, hiM, loM):
    n, m = c.shape
    out = np.zeros((n, m), np.int8)
    for j in range(m):
        p = 0
        for i in range(n):
            x = c[i, j]
            if not np.isfinite(x) or not np.isfinite(hiN[i, j]) or not np.isfinite(loN[i, j]):
                p = 0
            else:
                if p == 1 and np.isfinite(loM[i, j]) and x < loM[i, j]:
                    p = 0
                elif p == -1 and np.isfinite(hiM[i, j]) and x > hiM[i, j]:
                    p = 0
                if x > hiN[i, j]:
                    p = 1
                elif x < loN[i, j]:
                    p = -1
            out[i, j] = p
    return out


@njit(cache=True)
def supertrend_machine(h, l, c, atr, mult):
    n, m = c.shape
    out = np.zeros((n, m), np.int8)
    for j in range(m):
        fu, fl, tr, prev_c = np.nan, np.nan, 0, np.nan
        for i in range(n):
            x, a = c[i, j], atr[i, j]
            if not (np.isfinite(x) and np.isfinite(a) and np.isfinite(h[i, j]) and np.isfinite(l[i, j])):
                fu, fl, tr, prev_c = np.nan, np.nan, 0, np.nan
                out[i, j] = 0
                continue
            mid = (h[i, j] + l[i, j]) / 2
            bu, bl = mid + mult * a, mid - mult * a
            if not np.isfinite(fu):
                fu, fl = bu, bl
                tr = 1 if x >= mid else -1
            else:
                fu = bu if (bu < fu or prev_c > fu) else fu
                fl = bl if (bl > fl or prev_c < fl) else fl
                if tr == 1 and x < fl:
                    tr = -1
                elif tr == -1 and x > fu:
                    tr = 1
            prev_c = x
            out[i, j] = tr
    return out


@njit(cache=True)
def fib_machine(c, atr, k, entry, target):
    n, m = c.shape
    out = np.zeros((n, m), np.int8)
    for j in range(m):
        d, ext, piv = 0, np.nan, np.nan
        ul, uh, dh, dl = np.nan, np.nan, np.nan, np.nan
        uarm, darm = False, False
        p, stop, tgt = 0, 0.0, 0.0
        for i in range(n):
            x, a = c[i, j], atr[i, j]
            if not (np.isfinite(x) and np.isfinite(a)):
                d, p, uarm, darm = 0, 0, False, False
                out[i, j] = 0
                continue
            if p == 1 and (x <= stop or x >= tgt):
                p = 0
            elif p == -1 and (x >= stop or x <= tgt):
                p = 0
            if d == 0:
                d, ext, piv = 1, x, x
            elif d == 1:
                if x > ext:
                    ext = x
                elif x < ext - k * a:
                    ul, uh, uarm = piv, ext, True
                    d, piv, ext = -1, ext, x
            else:
                if x < ext:
                    ext = x
                elif x > ext + k * a:
                    dh, dl, darm = piv, ext, True
                    d, piv, ext = 1, ext, x
            if p == 0 and uarm and d == -1:
                rng = uh - ul
                le, ls = uh - entry * rng, uh - 0.786 * rng
                if x <= ls:
                    uarm = False
                elif x <= le:
                    p, stop, tgt, uarm = 1, ls, uh + (target - 1.0) * rng, False
            if p == 0 and darm and d == 1:
                rng = dh - dl
                le, ls = dl + entry * rng, dl + 0.786 * rng
                if x >= ls:
                    darm = False
                elif x >= le:
                    p, stop, tgt, darm = -1, ls, dl - (target - 1.0) * rng, False
            out[i, j] = p
    return out


@njit(cache=True)
def stop_overlay(pos, c, atr, mult):
    n, m = pos.shape
    out = np.zeros((n, m), np.int8)
    for j in range(m):
        prev, stopped, peak = 0, False, np.nan
        for i in range(n):
            x = pos[i, j]
            if x != prev:
                stopped, peak, prev = False, c[i, j], x
            if x == 0 or stopped or not np.isfinite(c[i, j]):
                out[i, j] = 0
                continue
            a = atr[i, j]
            if x > 0:
                peak = max(peak, c[i, j]) if np.isfinite(peak) else c[i, j]
                if np.isfinite(a) and c[i, j] < peak - mult * a:
                    stopped = True
                    out[i, j] = 0
                    continue
            else:
                peak = min(peak, c[i, j]) if np.isfinite(peak) else c[i, j]
                if np.isfinite(a) and c[i, j] > peak + mult * a:
                    stopped = True
                    out[i, j] = 0
                    continue
            out[i, j] = x
    return out


def base_rules():
    R = [("ema", (f, s)) for f in (5, 10, 20) for s in (50, 100, 200)]
    R += [("donchian", (n,)) for n in (20, 55, 100)]
    R += [("rsi", (p, lo)) for p in (2, 7, 14) for lo in (10, 20, 30)]
    R += [("boll", (n, k, md)) for n in (20, 50) for k in (1.5, 2.0, 2.5) for md in ("fade", "follow")]
    R += [("supertrend", (a, mu)) for a in (10, 14) for mu in (2.0, 3.0, 4.0)]
    R += [("fib", (k, e, t)) for k in (2.0, 3.0, 5.0) for e in (0.382, 0.5, 0.618) for t in (1.0, 1.272)]
    R += [("tsmom", (n,)) for n in (12, 24, 72, 168)]
    R += [("macd", spec) for spec in ((6, 13, 5), (12, 26, 9), (24, 52, 18))]
    R += [("vwap", (n, k, md)) for n in (24, 72, 168) for k in (1.0, 2.0) for md in ("fade", "follow")]
    assert len(R) == 76
    return R


def sgn(x):
    return np.nan_to_num(np.sign(x)).astype(np.int8)


def wilder(x, n):
    return x.ewm(alpha=1.0 / n, adjust=False).mean()


class Bars:
    """OHLCV bars of one timeframe for the member coins, with cached indicators."""

    def __init__(self, o, h, l, c, v, k, daily_ema200):
        nb = c.shape[0] // k
        blk = lambda x: x[:nb * k].reshape(nb, k, -1)
        self.k, self.nb = k, nb
        self.c = blk(c)[:, -1]
        self.o = blk(o)[:, 0]
        self.h = np.fmax(np.nanmax(blk(h), axis=1), self.c)
        self.l = np.fmin(np.nanmin(blk(l), axis=1), self.c)
        self.v = np.nansum(blk(v), axis=1)
        self.C = pd.DataFrame(self.c)
        prev = self.C.shift(1).values
        tr = np.fmax(self.h - self.l, np.fmax(np.abs(self.h - prev), np.abs(self.l - prev)))
        tr[~np.isfinite(self.c)] = np.nan
        self.TR = pd.DataFrame(tr)
        self.cache = {}
        dd = (np.arange(nb) + 1) * k // 24 - 1           # last completed day at each bar's close
        e = np.full((nb, c.shape[1]), np.nan)
        ok = dd >= 0
        e[ok] = daily_ema200[dd[ok]]
        self.trend_long = self.c > e
        self.trend_short = self.c < e
        atrp = self.atr(14) / self.c
        w = 180 * 24 // k
        med = pd.DataFrame(atrp).rolling(w, min_periods=w // 2).median().shift(1).values
        self.calm = atrp < med

    def atr(self, n):
        key = ("atr", n)
        if key not in self.cache:
            self.cache[key] = wilder(self.TR, n).values
        return self.cache[key]

    def ema(self, n):
        key = ("ema", n)
        if key not in self.cache:
            self.cache[key] = self.C.ewm(span=n, adjust=False, min_periods=n).mean().values
        return self.cache[key]

    def rule(self, fam, prm):
        c = self.c
        if fam == "ema":
            return sgn(self.ema(prm[0]) - self.ema(prm[1]))
        if fam == "tsmom":
            return sgn(c / self.C.shift(prm[0]).values - 1)
        if fam == "macd":
            f, s, g = prm
            macd = self.C.ewm(span=f, adjust=False, min_periods=s).mean() - self.C.ewm(span=s, adjust=False, min_periods=s).mean()
            sig = macd.ewm(span=g, adjust=False, min_periods=g).mean()
            return sgn((macd - sig).values)
        if fam == "donchian":
            n = prm[0]
            H, L = pd.DataFrame(self.h), pd.DataFrame(self.l)
            hiN, loN = H.rolling(n).max().shift(1).values, L.rolling(n).min().shift(1).values
            hiM, loM = H.rolling(n // 2).max().shift(1).values, L.rolling(n // 2).min().shift(1).values
            return donchian_machine(c, hiN, loN, hiM, loM)
        if fam == "rsi":
            p, lo = prm
            dlt = self.C.diff()
            up, dn = wilder(dlt.clip(lower=0), p), wilder((-dlt).clip(lower=0), p)
            rsi = 100 - 100 / (1 + up / dn)
            return band_machine(rsi.values - 50, 50.0 - lo, True)
        if fam == "boll":
            n, k, md = prm
            z = ((self.C - self.C.rolling(n).mean()) / self.C.rolling(n).std()).values
            return band_machine(z, k, md == "fade")
        if fam == "vwap":
            n, k, md = prm
            V = pd.DataFrame(self.v)
            vw = (self.C * V).rolling(n).sum() / V.rolling(n).sum()
            dev = self.C / vw - 1
            z = (dev / dev.rolling(n).std()).values
            return band_machine(z, k, md == "fade")
        if fam == "supertrend":
            a, mu = prm
            return supertrend_machine(self.h, self.l, c, self.atr(a), mu)
        if fam == "fib":
            k, e, t = prm
            return fib_machine(c, self.atr(14), k, e, t)
        raise ValueError(fam)

    def variants(self, base):
        """Yield ((direction, filter, stop), positions) for the 18 variants of one base rule, in PREREG order."""
        for dr in DIRS:
            p = base if dr == "both" else (np.maximum(base, 0) if dr == "long" else np.minimum(base, 0))
            for fl in FILTERS:
                if fl == "none":
                    q = p
                elif fl == "trend":
                    q = np.where(((p > 0) & self.trend_long) | ((p < 0) & self.trend_short), p, 0).astype(np.int8)
                else:
                    q = np.where(self.calm, p, 0).astype(np.int8)
                for st in STOPS:
                    yield (dr, fl, st), (q if st == "none" else stop_overlay(q, c=self.c, atr=self.atr(14), mult=2.0))


# ---------------------------------------------------------------- compute
def compute():
    u, _, _ = research.load_universe()
    T = len(u.p.t)
    D = T // 24
    syms = list(u.p.symbols)
    tf = set(json.loads((ROOT / "experiments" / "venue_gap_v1" / "results" / "tradfi_symbols.json").read_text()))
    crypto = np.array([s not in tf for s in syms])
    rank, elig = np.asarray(u.rank), np.asarray(u.elig)
    day0 = (rank[::24] <= TOP) & elig[::24] & crypto[None, :]
    member = np.repeat(day0, 24, axis=0)[:T] & elig
    cols = np.flatnonzero(member.any(axis=0))
    log(f"{len(cols)} coins are ever members; members per row mean {member.sum(1).mean():.2f}")
    mem = member[:, cols]
    ret = np.asarray(u.ret, np.float64)[:, cols]
    cmat = np.asarray(u.cmat, np.float64)[:, cols]
    log("member cells with a missing next return (legacy zero):", int((mem & ~np.isfinite(ret)).sum()))
    kl = flowfeat.load("klines", u.p.t, u.p.symbols, ("open", "high", "low", "quote_volume"))
    o, h, l, v = (np.asarray(kl[x], np.float64)[:, cols] for x in ("open", "high", "low", "quote_volume"))
    c = np.asarray(u.p["close"], np.float64)[:, cols]
    dc = c[23::24][:D]
    ema200 = pd.DataFrame(dc).ewm(span=200, adjust=False, min_periods=200).mean().values
    w = mem / TOP
    r0 = np.nan_to_num(ret)
    wr = w * r0
    cm0 = cmat.copy()
    rows_month_end = None
    names, G, Cst, E = [], [], [], []
    days = np.asarray(u.p.t[0:D * 24:24])
    mon = pd.to_datetime(days, unit="ms", utc=True).to_period("M")
    first = np.r_[True, mon[1:] != mon[:-1]]
    rows_month_end = np.flatnonzero(first)[1:] * 24 - 1          # last row of each month except the final one
    check = {0, 2000, 4000}
    parity = {}
    cache = LANE / "cache"
    cache.mkdir(exist_ok=True)
    key = prereg.verify(LANE / "PREREG.md")[:16]
    for k in TFS:
        part = cache / f"part_{key}_{k}h.npz"        # resume: a container restart kills long runs; results are unchanged
        if part.exists():
            z = np.load(part, allow_pickle=False)
            meta = json.loads(str(z["meta"]))
            assert meta["first_id"] == len(names), f"checkpoint {part.name} out of order"
            names += meta["names"]
            parity.update({int(a): b for a, b in meta["parity"].items()})
            G += list(z["gross"])
            Cst += list(z["cost"])
            E += list(z["expo"])
            log(f"timeframe {k} h: {len(meta['names'])} strategies loaded from {part.name}")
            continue
        first_id, par0 = len(names), dict(parity)
        B = Bars(o, h, l, c, v, k, ema200)
        jidx = (np.arange(T) + 1) // k - 1
        valid = jidx >= 0
        jidx = np.maximum(jidx, 0)
        log(f"timeframe {k} h: {B.nb} bars")
        for fam, prm in base_rules():
            base = B.rule(fam, prm)
            for (dr, fl, st), pos in B.variants(base):
                ph = pos[jidx].astype(np.float64)
                ph[~valid] = 0
                P = ph * w
                gross = (ph * wr).sum(axis=1)
                dP = np.diff(P, axis=0, prepend=0)
                adp = np.abs(dP)
                bad = (adp > 0) & ~np.isfinite(cm0)
                if bad.any():
                    raise ValueError(f"traded cell without a tier cost: {fam}{prm} {k}h")
                cost = (adp * cm0).sum(axis=1)
                i = len(names)
                if i in check:
                    full = np.zeros((T, len(syms)))
                    full[:, cols] = P
                    ref = slices.run(full, u.ret, u.elig, u.cmat, 0, T, hedge=False, cmult=1.0)
                    mine = (gross - cost)[:D * 24].reshape(D, 24).sum(1)
                    parity[i] = float(np.max(np.abs(ref["daily"] - mine)))
                    log(f"parity strategy {i}: max |diff| {parity[i]:.2e}")
                    assert parity[i] < 1e-9
                names.append({"id": i, "tf_h": k, "family": fam, "params": str(prm), "direction": dr, "filter": fl,
                              "stop": st})
                G.append(gross[:D * 24].reshape(D, 24).sum(1).astype(np.float32))
                Cst.append(cost[:D * 24].reshape(D, 24).sum(1).astype(np.float32))
                E.append(np.abs(P[rows_month_end]).sum(axis=1).astype(np.float32))
            if len(names) % 360 == 0:
                log(f"{len(names)} strategies done")
        meta = {"first_id": first_id, "names": names[first_id:],
                "parity": {str(a): b for a, b in parity.items() if a not in par0}}
        tmp = cache / f"part_{key}_{k}h.tmp.npz"
        np.savez(tmp, gross=np.array(G[first_id:]), cost=np.array(Cst[first_id:]), expo=np.array(E[first_id:]),
                 meta=np.array(json.dumps(meta)))
        tmp.replace(part)
    np.savez(cache / "nets.npz", gross=np.array(G), cost=np.array(Cst), expo=np.array(E), days=days)
    pd.DataFrame(names).to_csv(LANE / "results" / "strategies.csv", index=False)
    (LANE / "results" / "parity.json").write_text(json.dumps(parity, indent=1))
    log(f"saved {len(names)} strategies")


# ---------------------------------------------------------------- analysis
def nw_t_rows(X, lag=10):
    """Newey-West t of the mean for each row of X [N, n]."""
    n = X.shape[1]
    m = X.mean(axis=1, keepdims=True)
    e = X - m
    s = (e * e).sum(axis=1) / n
    for L in range(1, lag + 1):
        s += 2 * (1 - L / (lag + 1)) * (e[:, L:] * e[:, :-L]).sum(axis=1) / n
    return m[:, 0] / np.sqrt(s / n)


def stationary_idx(rng, n, length, block, paths):
    """Index arrays [paths, length] of a stationary bootstrap with mean block length `block`."""
    idx = np.empty((paths, length), np.int64)
    idx[:, 0] = rng.integers(0, n, paths)
    new = rng.random((paths, length)) < 1.0 / block
    starts = rng.integers(0, n, (paths, length))
    for t in range(1, length):
        idx[:, t] = np.where(new[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def walk_forward(net_sel, net_eval, expo, mon_id, months, L, cm, pick=None, rng=None):
    """Daily stream of the monthly walk-forward over months[L:], selecting on net_sel and earning net_eval.
    pick=None ranks by trailing Sharpe; pick='random' draws K uniformly. Returns (day mask, daily stream, picks)."""
    N = net_sel.shape[0]
    out = np.zeros(net_eval.shape[1])
    on = np.zeros(net_eval.shape[1], bool)
    prev, picks = set(), {}
    for mi in range(L, len(months)):
        dm = mon_id == mi
        if pick == "random":
            sel = set(rng.choice(N, K_SEL, replace=False).tolist())
        else:
            tr = (mon_id >= mi - L) & (mon_id < mi)
            x = net_sel[:, tr]
            mu, sd = x.mean(axis=1), x.std(axis=1)
            sh = np.where((sd > 0) & (mu > 0), mu / np.where(sd > 0, sd, 1), -np.inf)
            order = np.argsort(-sh, kind="stable")[:K_SEL]
            sel = set(int(i) for i in order if np.isfinite(sh[i]))
        out[dm] = net_eval[sorted(sel)][:, dm].sum(axis=0) / K_SEL if sel else 0.0
        changed = sel ^ prev
        if changed and mi > 0:
            first_day = np.flatnonzero(dm)[0]
            out[first_day] -= sum(float(expo[i, mi - 1]) for i in changed) / K_SEL * SWITCH_COST * cm
        on |= dm
        prev = sel
        picks[str(months[mi])] = sorted(sel)
    return on, out, picks


def mc_leverage(r, rng):
    idx = stationary_idx(rng, len(r), MC_DAYS, MC_BLOCK, MC_PATHS)
    R = r[idx]
    res, grid = {}, np.arange(0.5, 20.01, 0.5)
    medlog = []
    for Lv in sorted(set(LEVS) | set(grid.tolist())):
        x = 1 + Lv * R
        ruin = (x <= 0).any(axis=1)
        x = np.where(x <= 0, np.nan, x)
        W = np.nancumprod(x, axis=1)
        W[ruin] = 0.0
        term = np.where(ruin, 0.0, W[:, -1])
        peak = np.maximum.accumulate(np.where(ruin[:, None], 1.0, W), axis=1)
        dd = np.where(ruin, 1.0, (1 - W / peak).max(axis=1))
        if Lv in grid:
            medlog.append(np.median(np.log(np.maximum(term, 1e-9))))
        if Lv in LEVS:
            res[str(Lv)] = {"median_wealth": float(np.median(term)), "p05_wealth": float(np.percentile(term, 5)),
                            "p_dd50": float((dd >= 0.5).mean()), "p_ruin": float(ruin.mean()),
                            "p_loss_year": float((term < 1).mean())}
    res["growth_optimal_leverage"] = float(grid[int(np.argmax(medlog))])
    return res


def analyse():
    z = np.load(LANE / "cache" / "nets.npz")
    gross, cost, expo, days = z["gross"].astype(np.float64), z["cost"].astype(np.float64), z["expo"], z["days"]
    names = pd.read_csv(LANE / "results" / "strategies.csv")
    N, D = gross.shape
    net = {cm: gross - cm * cost for cm in (1.0, 2.0, 3.0)}
    dt = pd.to_datetime(days, unit="ms", utc=True)
    per = dt.to_period("M")
    months = per.unique()
    mon_id = np.searchsorted(months.to_timestamp().values, per.to_timestamp().values)
    win = lambda a, b: (dt >= pd.Timestamp(a, tz="UTC")) & (dt < pd.Timestamp(b, tz="UTC"))
    dec = win(*DECIDE)
    out = {"n_strategies": int(N)}
    rng = np.random.default_rng(263)

    # walk-forward streams
    wf = {}
    for L in LOOKS:
        streams = {}
        for cm in (1.0, 2.0, 3.0):
            on, s, picks = walk_forward(net[1.0], net[cm], expo, mon_id, months, L, cm)
            streams[cm] = s
        wf[L] = (on, streams, picks)
    rows = []
    for L, (on, streams, _) in wf.items():
        for wname, msk in (("decided 2021-07..2025-06", dec & on), ("2022-01..2025-06 (common)", win("2022-01-01", DECIDE[1])),
                           ("exploratory 2025-07..2026-09", win(DECIDE[1], "2026-10-01") & on)):
            for cm in (1.0, 2.0, 3.0):
                x = streams[cm][msk]
                yr = dt[msk].year
                rows.append({"L_months": L, "window": wname, "cmult": cm, "days": int(msk.sum()),
                             "mean_bp_day": float(x.mean() * 1e4), "t_nw10": float(stats.newey_west_t(x, 10)[2]),
                             "sharpe": float(x.mean() / x.std() * np.sqrt(365)) if x.std() > 0 else np.nan,
                             "by_year_bp_day": {int(y): float(x[yr == y].mean() * 1e4) for y in np.unique(yr)}})
    wfdf = pd.DataFrame(rows)
    log("\n" + wfdf.drop(columns="by_year_bp_day").round(3).to_string(index=False))

    # random-selection null for the decided stream
    on6, s6, picks6 = wf[MAIN_L]
    m_dec = dec & on6
    null = []
    for b in range(N_RAND):
        _, sr, _ = walk_forward(net[1.0], net[1.0], expo, mon_id, months, MAIN_L, 1.0, pick="random", rng=rng)
        null.append(sr[m_dec].mean())
    null = np.array(null)
    x1, x2 = s6[1.0][m_dec], s6[2.0][m_dec]
    t1 = float(stats.newey_west_t(x1, 10)[2])
    p95 = float(np.percentile(null, 95))
    primary = {"mean_1x_bp": float(x1.mean() * 1e4), "t_1x": t1, "mean_2x_bp": float(x2.mean() * 1e4),
               "null_mean_bp": float(null.mean() * 1e4), "null_p95_bp": p95 * 1e4,
               "null_share_above": float((null >= x1.mean()).mean()),
               "all_strategies_ew_bp": float(net[1.0][:, m_dec].mean() * 1e4)}
    primary["passed"] = bool(t1 >= 2 and x2.mean() > 0 and x1.mean() > p95)
    out["primary"] = primary
    log("primary", json.dumps(primary))

    # best single strategy + reality check
    disc, val = win(*DISC), win(*VALID)
    X = net[1.0][:, disc]
    tn = nw_t_rows(X)
    best = int(np.nanargmax(tn))
    n = X.shape[1]
    sd = X.std(axis=1)
    stat = np.sqrt(n) * X.mean(axis=1) / np.where(sd > 0, sd, np.inf)
    Xd = X - X.mean(axis=1, keepdims=True)
    bidx = stationary_idx(rng, n, n, RC_BLOCK, RC_B)
    mx = np.empty(RC_B)
    for b in range(RC_B):
        Y = Xd[:, bidx[b]]
        mx[b] = np.max(np.sqrt(n) * Y.mean(axis=1) / np.where(sd > 0, sd, np.inf))
    rc_p = float((mx >= stat.max()).mean())
    v1, v2 = net[1.0][best, val], net[2.0][best, val]
    tv = float(stats.newey_west_t(v1, 10)[2])
    secondary = {"strategy": names.iloc[best].to_dict(), "disc_t_1x": float(tn[best]),
                 "disc_mean_1x_bp": float(X[best].mean() * 1e4), "rc_stat": float(stat.max()), "rc_p": rc_p,
                 "rc_null_p95": float(np.percentile(mx, 95)), "val_mean_1x_bp": float(v1.mean() * 1e4),
                 "val_t_1x": tv, "val_mean_2x_bp": float(v2.mean() * 1e4),
                 "val_mean_3x_bp": float(net[3.0][best, val].mean() * 1e4)}
    secondary["passed"] = bool(rc_p < 0.05 and tv >= 1.5 and v2.mean() > 0)
    out["secondary"] = secondary
    log("secondary", json.dumps(secondary, default=str))

    # landscape: distribution of single-strategy results
    tv_all = nw_t_rows(net[1.0][:, val])
    names["disc_mean_1x_bp"] = net[1.0][:, disc].mean(axis=1) * 1e4
    names["disc_t_1x"] = tn
    names["val_mean_1x_bp"] = net[1.0][:, val].mean(axis=1) * 1e4
    names["val_t_1x"] = tv_all
    names["disc_gross_bp"] = gross[:, disc].mean(axis=1) * 1e4
    names["disc_cost_bp"] = cost[:, disc].mean(axis=1) * 1e4
    names.to_csv(LANE / "results" / "strategies_scored.csv", index=False)
    out["landscape"] = {
        "share_disc_net_positive": float((names.disc_mean_1x_bp > 0).mean()),
        "share_disc_gross_positive": float((names.disc_gross_bp > 0).mean()),
        "share_disc_t_ge_2": float((tn >= 2).mean()), "share_val_t_ge_2": float((tv_all >= 2).mean()),
        "corr_disc_val_t": float(np.corrcoef(tn, tv_all)[0, 1]),
        "top100_disc_val_mean_t": float(tv_all[np.argsort(-tn)[:100]].mean())}
    by = names.groupby(["family", "tf_h"])[["disc_mean_1x_bp", "val_mean_1x_bp", "disc_gross_bp", "disc_cost_bp"]].mean()
    by.round(3).to_csv(LANE / "results" / "family_tf.csv")
    log("landscape", json.dumps(out["landscape"]))
    log("\n" + by.round(2).to_string())

    # persistence IC
    sel_net = net[1.0]
    ics = []
    for mi in range(MAIN_L, len(months)):
        tr = (mon_id >= mi - MAIN_L) & (mon_id < mi)
        x = sel_net[:, tr]
        sh = x.mean(axis=1) / np.where(x.std(axis=1) > 0, x.std(axis=1), np.nan)
        nxt = sel_net[:, mon_id == mi].mean(axis=1)
        ok = np.isfinite(sh)
        ics.append({"month": str(months[mi]), "ic": float(pd.Series(sh[ok]).rank().corr(pd.Series(nxt[ok]).rank()))})
    icdf = pd.DataFrame(ics)
    icdf.to_csv(LANE / "results" / "persistence_ic.csv", index=False)
    d_ic = icdf[(icdf.month >= "2021-07") & (icdf.month < "2025-07")].ic.values
    out["persistence"] = {"mean_ic_decided": float(d_ic.mean()), "t_nw3": float(stats.newey_west_t(d_ic, 3)[2]),
                          "share_positive": float((d_ic > 0).mean()),
                          "mean_ic_exploratory": float(icdf[icdf.month >= "2025-07"].ic.mean())}
    log("persistence", json.dumps(out["persistence"]))

    # families: half-year means, pick shares, regime correlations
    half = (dt.year.astype(str) + "H" + np.where(dt.month <= 6, "1", "2")).values
    fam = names.family.values
    fh = {f: {h: float(net[1.0][fam == f][:, half == h].mean() * 1e4) for h in np.unique(half)} for f in np.unique(fam)}
    out["family_halfyear_bp_day"] = fh
    shares = {}
    for mstr, sel in picks6.items():
        y = mstr[:4]
        for i in sel:
            shares.setdefault(y, {}).setdefault(fam[i], 0)
            shares[y][fam[i]] += 1
    out["pick_share_by_year"] = {y: {f: v / sum(d.values()) for f, v in d.items()} for y, d in shares.items()}
    u, _, _ = research.load_universe()
    bi = list(u.p.symbols).index("BTCUSDT")
    bret = np.nan_to_num(np.asarray(u.ret[:D * 24, bi], np.float64)).reshape(D, 24).sum(1)
    mret = pd.Series(bret).groupby(mon_id).sum().values
    mvol = pd.Series(bret).groupby(mon_id).std().values * np.sqrt(30)
    reg = {}
    for f in np.unique(fam):
        fm = pd.Series(net[1.0][fam == f].mean(axis=0)).groupby(mon_id).sum().values
        reg[f] = {"corr_btc_month_ret": float(np.corrcoef(fm, mret)[0, 1]),
                  "corr_btc_abs_ret": float(np.corrcoef(fm, np.abs(mret))[0, 1]),
                  "corr_btc_vol": float(np.corrcoef(fm, mvol)[0, 1])}
    out["family_regime_corr"] = reg
    log("regime", json.dumps(reg))
    last = sorted(picks6)[-1]
    out["current_selection"] = {"month": last, "strategies": names.iloc[picks6[last]][
        ["id", "tf_h", "family", "params", "direction", "filter", "stop"]].to_dict("records")}

    # Monte Carlo leverage
    out["mc_leverage_walkforward"] = mc_leverage(x1, rng)
    out["mc_leverage_best_single_disc"] = mc_leverage(X[best], rng)
    log("mc walk-forward", json.dumps(out["mc_leverage_walkforward"]))
    log("mc best single", json.dumps(out["mc_leverage_best_single_disc"]))

    wfdf.drop(columns="by_year_bp_day").to_csv(LANE / "results" / "walkforward.csv", index=False)
    out["walkforward_by_year_1x"] = {f"L{r.L_months}/{r.window}": r.by_year_bp_day
                                     for r in wfdf[wfdf.cmult == 1.0].itertuples()}
    out["picks_L6"] = picks6
    out["verdict"] = "PASS" if primary["passed"] or secondary["passed"] else "NULL"
    (LANE / "results" / "verdict.json").write_text(json.dumps(out, indent=1, default=str))
    log("verdict", out["verdict"])


def main():
    log("prereg sha", prereg.verify(LANE / "PREREG.md")[:12])
    (LANE / "results").mkdir(parents=True, exist_ok=True)
    if "--analyse" not in sys.argv:
        compute()
    analyse()


if __name__ == "__main__":
    main()
