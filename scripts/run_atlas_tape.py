"""R386 atlas_tape_v1: one large gate-0 screen of short-horizon conditional forward returns on the recorded tape-scale data.

Block A: Binance USD-M 1-minute bars (12 coins, 2021-01..2026-09), signals at bar i, entry at the open of i+1, exit at the
close of i+h (h = 1..60 minutes). Block B: the 1-second tape (Binance/Lighter/MEXC books and Binance trades, 7 recorded
days), signals at second t, entry at t+d on Lighter's mid, exit d+H seconds later. Every cell is priced at the coin's
measured Lighter $1k walk (R348 summary) and counted as a trial. Time split: discovery first, validation after, whole days.
A circular-shift placebo (the signal moved against the returns) is rerun over the full grid for the max-statistic test.

This is a screen. It never claims an edge; the candidate list goes to a later read on unseen days.
"""
import argparse
import json
import multiprocessing as mp
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lab import nulls, prereg  # noqa: E402
import run_minflow as r349  # noqa: E402  R349's frozen runner: bar loader, input check, calendar constants

LANE = ROOT / "experiments" / "atlas_tape_v1"
RES = LANE / "results"
REG_ID = "R386"

COINS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "BNB", "SUI", "ADA", "LINK", "AVAX", "LTC", "TRX")
MAJ3 = ("BTC", "ETH", "SOL")
COST_SRC = ROOT / "experiments" / "tapelag_lighter_v2" / "results" / "summary.json"
QS = (0.90, 0.95, 0.98, 0.99, 0.995)
SEED = 386
NPLACEBO = 300
MIN_TRADES = 100            # per period, for a cell to be testable (it is still a trial)
MIN_CLUSTERS = 10           # days (A) or half hours (B) with a trade, per period: fewer leaves the t undefined
T_PASS = 2.0
P_PASS = 0.05
MEXC_WEB_BP, MEXC_API_BP = 3.0, 8.5      # a side, reported only

A_HOLDS = (1, 3, 5, 10, 15, 30, 60)      # minutes
A_BASES = ([f"ret_{k}" for k in (1, 3, 5, 15, 30, 60)] + [f"flow_{k}" for k in (1, 3, 5, 15, 30)]
           + [f"imb_{k}" for k in (3, 5, 15, 30)] + [f"div_{k}" for k in (5, 15, 30)]
           + [f"rel_{k}" for k in (1, 3, 5, 15)])
A_GATES = ("none", "hi_act", "lo_act", "asia", "eu", "us", "settle", "nyopen")
A_DISC_END = "2024-01-01"                # discovery < this day <= validation

B_DAYS = ("2026-10-21", "2026-10-22", "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30")
B_N_DISC_DAYS = 5                        # 10-21 .. 10-28 discovery, 10-29 and 10-30 validation
B_DELAYS = (1, 3)
B_HOLD_S = (5, 15, 30, 60, 180, 300)
B_HOLDS = tuple((d, h) for d in B_DELAYS for h in B_HOLD_S)
B_BASES = ([f"bret_{k}" for k in (1, 3, 10, 30, 60)] + [f"bofi_{k}" for k in (1, 3, 10, 30)]
           + [f"bimb_{k}" for k in (1, 5, 30)] + [f"btf_{k}" for k in (3, 10, 30)]
           + [f"lret_{k}" for k in (3, 10, 30)] + [f"lofi_{k}" for k in (3, 10, 30)]
           + [f"mofi_{k}" for k in (3, 10)] + ["dev_bl", "dev_ml", "dev_bm"])
B_GATES = ("none", "hi_act", "lo_act")
GAP_S = 7200
DAY_S = 86400


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------ rolling helpers
def lag(a, k):
    out = np.full(len(a), np.nan)
    out[k:] = a[:-k]
    return out


def rollsum(a, k):
    """Sum over the k values ending at i; NaN unless all k are finite."""
    ok = np.isfinite(a)
    c = np.concatenate(([0.0], np.cumsum(np.where(ok, a, 0.0))))
    v = np.concatenate(([0], np.cumsum(ok)))
    out = np.full(len(a), np.nan)
    out[k - 1:] = np.where(v[k:] - v[:-k] == k, c[k:] - c[:-k], np.nan)
    return out


def rollmean_tol(a, k, minfrac):
    """Mean of the finite values among the k ending at i; NaN below minfrac * k finite values."""
    ok = np.isfinite(a)
    c = np.concatenate(([0.0], np.cumsum(np.where(ok, a, 0.0))))
    v = np.concatenate(([0], np.cumsum(ok)))
    nv = (v[k:] - v[:-k]).astype(float)
    out = np.full(len(a), np.nan)
    out[k - 1:] = np.where(nv >= minfrac * k, (c[k:] - c[:-k]) / np.maximum(nv, 1.0), np.nan)
    return out


# ------------------------------------------------------------------------------------------------ numba kernels
@njit(cache=False)
def block_thresholds(x, block, window, minfin, qs, nb):
    """thr[b, q]: the q-quantile of |x| over the `window` values just before block b (none from block b itself)."""
    Q = len(qs)
    out = np.full((nb, Q), np.nan)
    buf = np.empty(window)
    for b in range(nb):
        end = b * block
        s = end - window
        if s < 0 or end > len(x):
            continue
        m = 0
        for t in range(s, end):
            v = x[t]
            if v == v:
                buf[m] = abs(v)
                m += 1
        if m < minfin:
            continue
        arr = np.sort(buf[:m])
        for qi in range(Q):
            out[b, qi] = arr[int(np.ceil(qs[qi] * (m - 1)))]
    return out


@njit(cache=False)
def kernel(x, thr, tb, gate, pe, px, cl, eoff, xoff, i0, i1, shift, cl0, G, N):
    """Add, per (quantile q, horizon k, cluster), the sum of side * gross return and the trade count.

    Return time i in [i0, i1) reads the signal at j = i - shift (circular inside the period). An event is |x[j]| >= thr
    of j's threshold block with the gate open and x != 0. It trades side sign(x[j]) at pe[i+eoff[k]] and exits at
    px[i+xoff[k]] (which must lie inside the period). One position per (q, k): the next signal must come at i + xoff[k]
    or later. A trade skipped for a missing price blocks nothing."""
    L = i1 - i0
    Q = thr.shape[1]
    K = eoff.shape[0]
    nxt = np.full((Q, K), i0, np.int64)
    for i in range(i0, i1):
        j = i - shift
        if j < i0:
            j += L
        xv = x[j]
        if xv != xv or xv == 0.0:
            continue
        if gate[j] == 0:
            continue
        a = abs(xv)
        b = tb[j]
        if not (a >= thr[b, 0]):
            continue
        sg = 1.0 if xv > 0 else -1.0
        c = cl[i] - cl0
        for q in range(Q):
            if not (a >= thr[b, q]):
                break
            for k in range(K):
                if i >= nxt[q, k]:
                    ix = i + xoff[k]
                    if ix >= i1:
                        continue
                    p0 = pe[i + eoff[k]]
                    p1 = px[ix]
                    if p0 == p0 and p1 == p1 and p0 > 0.0:
                        G[q, k, c] += sg * (p1 / p0 - 1.0)
                        N[q, k, c] += 1.0
                        nxt[q, k] = ix


# ------------------------------------------------------------------------------------------------ statistics
def sets_of(coins):
    """Coin sets: each coin, all of them, and the majors present. Returns names and the 0/1 membership matrix."""
    names = list(coins) + ["all12", "maj3"]
    W = np.zeros((len(names), len(coins)))
    for i in range(len(coins)):
        W[i, i] = 1.0
    W[len(coins), :] = 1.0
    for i, c in enumerate(coins):
        if c in MAJ3:
            W[len(coins) + 1, i] = 1.0
    return names, W


def agg(G, N, cost_rt, W):
    """Per set: summed gross, trades and round-trip cost per cluster. cost_rt is per coin in return units."""
    sh = G.shape
    flat = lambda a: a.reshape(sh[0], -1)  # noqa: E731
    out = (W @ flat(G), W @ flat(N), (W * cost_rt[None, :]) @ flat(N))
    return tuple(o.reshape((W.shape[0],) + sh[1:]) for o in out)


def cluster_t(G, N, C, sigma, m):
    """Mean per trade and cluster-robust t of sigma*G - m*C. Clusters are on the last axis (days or half hours)."""
    with np.errstate(all="ignore"):
        R = sigma * G - m * C
        Nt = N.sum(-1)
        mean = R.sum(-1) / Nt
        res = R - mean[..., None] * N
        nc = (N > 0).sum(-1)
        var = (res ** 2).sum(-1) * nc / np.maximum(nc - 1, 1) / Nt ** 2
        t = mean / np.sqrt(var)
    return mean, t


def real_stats(Gd, Nd, Cd, Gv, Nv, Cv):
    """Everything the table needs, arrays (sigma, set, gate, q, k) with sigma 0 = follow, 1 = fade."""
    out = {}
    sg = (1.0, -1.0)
    for si, s in enumerate(sg):
        for m in (0, 1, 2, 3):
            mv, tv = cluster_t(Gv, Nv, Cv, s, m)
            out.setdefault(f"val_m{m}", []).append(mv)
            out.setdefault(f"val_t{m}", []).append(tv)
        for m in (0, 1):
            md, td = cluster_t(Gd, Nd, Cd, s, m)
            out.setdefault(f"disc_m{m}", []).append(md)
            out.setdefault(f"disc_t{m}", []).append(td)
    out = {k: np.stack(v) for k, v in out.items()}
    out["n_val"] = Nv.sum(-1)
    out["n_disc"] = Nd.sum(-1)
    out["ncl_val"] = (Nv > 0).sum(-1)
    out["ncl_disc"] = (Nd > 0).sum(-1)
    with np.errstate(all="ignore"):
        out["cost_rt"] = Cv.sum(-1) / Nv.sum(-1)
    return out


# ------------------------------------------------------------------------------------------------ blocks
def run_period(blk, xs, thr, period, shift):
    i0, i1, cl0, ncl = blk.per[period]
    nc, ng, Q, K = len(blk.coins), len(blk.gate_names), len(QS), len(blk.eoff)
    G = np.zeros((nc, ng, Q, K, ncl))
    N = np.zeros_like(G)
    for ci, c in enumerate(blk.coins):
        if xs[c] is None:
            continue
        for gi in range(ng):
            kernel(xs[c], thr[c], blk.tb, blk.gates[c][gi], blk.pe[c], blk.px[c], blk.cl, blk.eoff, blk.xoff,
                   i0, i1, shift, cl0, G[ci, gi], N[ci, gi])
    return G, N


def labels(blk, base, shape):
    """Index grids for a (sigma, set, gate, q, k) array."""
    s, e, g, q, k = np.indices(shape)
    return dict(
        block=blk.name, base=base, side=np.array(["follow", "fade"])[s.ravel()],
        coin_set=np.array(blk.set_names)[e.ravel()], gate=np.array(blk.gate_names)[g.ravel()],
        q=np.array(QS)[q.ravel()], hold=np.array(blk.hold_names)[k.ravel()])


def run_base(args):
    """One base feature on all coins: the real discovery and validation stats and the placebo replicas."""
    name, bi, nplacebo = args
    blk = BLOCKS[name]
    base = blk.bases[bi]
    t0 = time.time()
    xs = blk.features(base, blk)
    thr = {}
    for c in blk.coins:
        thr[c] = (block_thresholds(xs[c], blk.thr_block, blk.thr_window, blk.thr_minfin, np.array(QS), blk.n_tb)
                  if xs[c] is not None else None)
    Gd, Nd = run_period(blk, xs, thr, "disc", 0)
    Gv, Nv = run_period(blk, xs, thr, "val", 0)
    Gd, Nd, Cd = agg(Gd, Nd, blk.cost_rt, blk.W)
    Gv, Nv, Cv = agg(Gv, Nv, blk.cost_rt, blk.W)
    st = real_stats(Gd, Nd, Cd, Gv, Nv, Cv)
    elig = ((st["n_val"] >= MIN_TRADES) & (st["n_disc"] >= MIN_TRADES)
            & (st["ncl_val"] >= MIN_CLUSTERS) & (st["ncl_disc"] >= MIN_CLUSTERS))      # (set, gate, q, k)
    disc_ok = elig[None] & (st["disc_m1"] > 0)                                       # (sigma, ...)
    shape = disc_ok.shape
    tab = labels(blk, base, shape)
    cols = dict(tab)
    cols.update(n_disc=np.broadcast_to(st["n_disc"], shape).ravel(), n_val=np.broadcast_to(st["n_val"], shape).ravel(),
                cost_rt_bp=np.broadcast_to(st["cost_rt"], shape).ravel() * 1e4,
                gross_disc_bp=st["disc_m0"].ravel() * 1e4, gross_val_bp=st["val_m0"].ravel() * 1e4,
                net1x_disc_bp=st["disc_m1"].ravel() * 1e4,
                net1x_val_bp=st["val_m1"].ravel() * 1e4, net2x_val_bp=st["val_m2"].ravel() * 1e4,
                net3x_val_bp=st["val_m3"].ravel() * 1e4,
                t_disc_1x=st["disc_t1"].ravel(), t_val_1x=st["val_t1"].ravel(), t_val_2x=st["val_t2"].ravel(),
                t_val_3x=st["val_t3"].ravel(),
                net_mexcweb_bp=st["val_m0"].ravel() * 1e4 - 2 * MEXC_WEB_BP,
                net_mexcapi_bp=st["val_m0"].ravel() * 1e4 - 2 * MEXC_API_BP,
                eligible=np.broadcast_to(elig, shape).ravel(), disc_ok=disc_ok.ravel())
    df = pd.DataFrame(cols)
    # placebo: the validation signal moved against the returns by a whole-unit circular shift
    Mf = np.full(nplacebo, -np.inf)
    Ms = np.full(nplacebo, -np.inf)
    cnt = np.zeros(nplacebo, np.int64)
    cnt2 = np.zeros(nplacebo, np.int64)
    for b in range(nplacebo):
        Gp, Np = run_period(blk, xs, thr, "val", int(blk.shifts[b]))
        Gp, Np, Cp = agg(Gp, Np, blk.cost_rt, blk.W)
        _, t0p = cluster_t(Gp, Np, Cp, 1.0, 0)
        tp = np.stack([t0p, -t0p])                                       # centred: break-even null, either side
        gsum = Gp.sum(-1)
        csum = Cp.sum(-1)
        beats = np.stack([gsum > csum, -gsum > csum])                     # the 2x analogue of net(2x) > 0
        el = np.broadcast_to(elig[None], tp.shape)
        v = np.where(el & np.isfinite(tp), tp, -np.inf)
        Mf[b] = v.max()
        Ms[b] = np.where(disc_ok, v, -np.inf).max()
        cnt[b] = int((disc_ok & (tp >= T_PASS) & beats).sum())
        cnt2[b] = int((el & (tp >= T_PASS)).sum())
    return name, base, df, Mf, Ms, cnt, cnt2, time.time() - t0


BLOCKS = {}


# ------------------------------------------------------------------------------------------------ Block A (minutes)
def a_ret(bars, k):
    lc = np.log(bars["close"])
    return lc - lag(lc, k)


def a_features(base, blk):
    kind, k = base.split("_")
    k = int(k)
    out = {}
    if kind == "rel":
        r = {c: a_ret(blk.bars[c], k) for c in blk.coins}
        for c in blk.coins:
            out[c] = r["ETH" if c == "BTC" else "BTC"] - r[c]
        return out
    for c in blk.coins:
        b = blk.bars[c]
        vol = b["volume"]
        d = 2.0 * b["tbv"] - vol
        if kind == "ret":
            out[c] = a_ret(b, k)
        elif kind == "flow":
            out[c] = rollsum(d, k)
        elif kind == "imb":
            sv = rollsum(vol, k)
            with np.errstate(all="ignore"):
                out[c] = np.where(sv > 0, rollsum(d, k) / sv, np.nan)
        elif kind == "div":
            sv = lag(rollmean_tol(vol, 1440, 0.5), k)
            r1 = np.abs(a_ret(b, 1))
            sr = lag(rollmean_tol(r1, 1440, 0.5), k)
            with np.errstate(all="ignore"):
                out[c] = rollsum(d, k) / (sv * np.sqrt(k)) - a_ret(b, k) / (sr * np.sqrt(k))
        else:
            raise ValueError(base)
    return out


def a_gates(bars, n):
    """Gate masks (uint8) per coin and the shared clock gates, by the minute of the UTC day of the signal bar."""
    m = np.arange(n) % 1440
    clock = {
        "asia": m < 480, "eu": (m >= 480) & (m < 840), "us": (m >= 840) & (m < 1260),
        "settle": ((m >= 464) & (m < 484)) | ((m >= 944) & (m < 964)) | (m >= 1424) | (m < 4),
        "nyopen": (m >= 794) & (m < 884)}
    clock = {k: v.astype(np.uint8) for k, v in clock.items()}
    out = {}
    for c, b in bars.items():
        vol = b["volume"]
        with np.errstate(all="ignore"):
            ar = (rollsum(vol, 5) / 5.0) / lag(rollmean_tol(vol, 1440, 0.5), 5)
            hi = (ar >= 1.5).astype(np.uint8)
            lo = (ar <= 1.0 / 1.5).astype(np.uint8)
        out[c] = [np.ones(n, np.uint8), hi, lo] + [clock[g] for g in A_GATES[3:]]
    return out


def walk_costs():
    w = json.loads(COST_SRC.read_text())["walk_cost_bp"]
    return {c: float(w[c]) for c in COINS}


def build_block_a(bars, walk, coins=COINS, t0=None, t1=None, split_ms=None, nplacebo=NPLACEBO):
    t0 = r349.T0 if t0 is None else t0
    t1 = r349.T1 if t1 is None else t1
    n = (t1 - t0) // r349.MIN
    nd = n // 1440
    split = (r349.ms(A_DISC_END) - t0) // r349.MIN if split_ms is None else (split_ms - t0) // r349.MIN
    day = (np.arange(n) // 1440).astype(np.int32)
    sd = split // 1440
    names, W = sets_of(coins)
    rng = np.random.default_rng(SEED)
    lo, hi = 14, nd - sd - 14
    shifts = rng.integers(lo, hi, nplacebo) * 1440 if hi > lo else np.zeros(nplacebo, np.int64)
    return SimpleNamespace(
        name="A", coins=list(coins), bars=bars, bases=list(A_BASES), gate_names=list(A_GATES), features=a_features,
        gates=a_gates(bars, n), eoff=np.ones(len(A_HOLDS), np.int64), xoff=np.array(A_HOLDS, np.int64),
        hold_names=[f"{h}m" for h in A_HOLDS], pe={c: bars[c]["open"] for c in coins},
        px={c: bars[c]["close"] for c in coins}, tb=day, cl=day, n_tb=nd, thr_block=1440, thr_window=7 * 1440,
        thr_minfin=5000, per={"disc": (0, split, 0, sd), "val": (split, n, sd, nd - sd)},
        cost_rt=np.array([2.0 * walk[c] * 1e-4 for c in coins]), set_names=names, W=W, shifts=shifts)


def load_block_a():
    bars = {}
    for c in COINS:
        folder = "klines_1m" if c in MAJ3 else "klines_1m_tape"
        bars[c] = r349.load_bars(ROOT / "data" / folder / f"{c}USDT.parquet")
    return bars


# ------------------------------------------------------------------------------------------------ Block B (seconds)
def day_offsets(days):
    """Slot offset of each recorded day; a gap of 2 h before a day that does not follow the previous calendar day."""
    off, cur, prev = [], 0, None
    for d in days:
        dd = pd.Timestamp(d)
        if prev is not None and (dd - prev).days != 1:
            cur += GAP_S
        off.append(cur)
        cur += DAY_S
        prev = dd
    return off, cur


def load_tape(root=ROOT, days=B_DAYS, coins=COINS):
    """Per coin 1-second arrays on the concatenated slot grid. Binance is dense; Lighter and MEXC rows exist only
    when something changed, so their mid is carried forward (at most 120 s, never across a recorder outage) and
    their flow is 0 in a second with no row. NaN wherever the recorder was down."""
    off, ns = day_offsets(days)
    up = np.zeros(ns, bool)
    cols = ["s", "sym", "bid", "bid_sz", "ask", "ask_sz", "ofi", "n"]
    tp = {c: {k: np.full(ns, np.nan) for k in ("bmid", "bofi", "bimb", "bn", "tf", "lmid", "lofi", "mmid", "mofi")}
          for c in coins}
    present = {c: np.zeros(ns, bool) for c in coins}
    lraw = {c: {"mid": np.full(ns, np.nan), "ofi": np.full(ns, np.nan)} for c in coins}
    mraw = {c: {"mid": np.full(ns, np.nan), "ofi": np.full(ns, np.nan)} for c in coins}
    for di, day in enumerate(days):
        d0 = int(pd.Timestamp(day, tz="UTC").timestamp()) * 1000
        for venue in ("binance", "lighter", "mexc"):
            bk = pd.read_parquet(root / "data" / "tape" / venue / "book" / f"{day}.parquet", columns=cols)
            sec = ((bk["s"].to_numpy() - d0) // 1000).astype(np.int64)
            ok = (sec >= 0) & (sec < DAY_S)
            bk, sec = bk[ok], sec[ok] + off[di]
            sym = bk["sym"].astype(str).to_numpy()
            for c in coins:
                m = sym == c
                if not m.any():
                    continue
                ix = sec[m]
                mid = (bk["bid"].to_numpy()[m] + bk["ask"].to_numpy()[m]) / 2.0
                ofi = bk["ofi"].to_numpy()[m]
                if venue == "binance":
                    present[c][ix] = True
                    up[ix] = True
                    tp[c]["bmid"][ix] = mid
                    tp[c]["bofi"][ix] = ofi
                    bs, as_ = bk["bid_sz"].to_numpy()[m], bk["ask_sz"].to_numpy()[m]
                    tp[c]["bimb"][ix] = (bs - as_) / (bs + as_)
                    tp[c]["bn"][ix] = bk["n"].to_numpy()[m]
                elif venue == "lighter":
                    lraw[c]["mid"][ix] = mid
                    lraw[c]["ofi"][ix] = ofi
                else:
                    mraw[c]["mid"][ix] = mid
                    mraw[c]["ofi"][ix] = ofi
        tr = pd.read_parquet(root / "data" / "tape" / "binance" / "trades" / f"{day}.parquet",
                             columns=["s", "sym", "buy_qty", "sell_qty"])
        sec = ((tr["s"].to_numpy() - d0) // 1000).astype(np.int64)
        ok = (sec >= 0) & (sec < DAY_S)
        tr, sec = tr[ok], sec[ok] + off[di]
        sym = tr["sym"].astype(str).to_numpy()
        for c in coins:
            m = sym == c
            if m.any():
                tp[c]["tf"][sec[m]] = tr["buy_qty"].to_numpy()[m] - tr["sell_qty"].to_numpy()[m]
    rid = np.cumsum(~up)          # a new group at every second the recorder was down: no carry across an outage
    for c in coins:
        t = tp[c]
        t["bmid"][~present[c]] = np.nan
        t["tf"] = np.where(present[c] & np.isnan(t["tf"]), 0.0, t["tf"])
        t["tf"][~present[c]] = np.nan
        for key, raw in (("l", lraw[c]), ("m", mraw[c])):
            mid = pd.Series(raw["mid"]).groupby(rid).ffill(limit=120).to_numpy().copy()
            mid[~up] = np.nan
            t[key + "mid"] = mid
            f = raw["ofi"].copy()
            f[np.isnan(f) & up] = 0.0
            f[~up] = np.nan
            t[key + "ofi"] = f
    return tp, ns, off


def b_features(base, blk):
    kind, k = base.split("_")
    out = {}
    for c in blk.coins:
        t = blk.tp[c]
        with np.errstate(all="ignore"):
            if kind == "dev":
                a, b = {"bl": ("bmid", "lmid"), "ml": ("mmid", "lmid"), "bm": ("bmid", "mmid")}[k]
                out[c] = np.log(t[a] / t[b])
                continue
            k = int(k)
            if kind == "bret":
                lm = np.log(t["bmid"])
                out[c] = lm - lag(lm, k)
            elif kind == "lret":
                lm = np.log(t["lmid"])
                out[c] = lm - lag(lm, k)
            elif kind == "bofi":
                out[c] = rollsum(t["bofi"], k)
            elif kind == "bimb":
                out[c] = rollsum(t["bimb"], k) / k
            elif kind == "btf":
                out[c] = rollsum(t["tf"], k)
            elif kind == "lofi":
                out[c] = rollsum(t["lofi"], k)
            elif kind == "mofi":
                out[c] = rollsum(t["mofi"], k)
            else:
                raise ValueError(base)
    return out


def build_block_b(tp, ns, off, walk, coins=COINS, nplacebo=NPLACEBO, n_disc_days=B_N_DISC_DAYS):
    ix = np.arange(ns)
    gates = {}
    for c in coins:
        with np.errstate(all="ignore"):
            ar = rollmean_tol(tp[c]["bn"], 60, 0.8) / lag(rollmean_tol(tp[c]["bn"], 1800, 0.5), 60)
        gates[c] = [np.ones(ns, np.uint8), (ar >= 1.5).astype(np.uint8), (ar <= 1.0 / 1.5).astype(np.uint8)]
    split = off[n_disc_days]
    ncl_all = ns // 1800
    names, W = sets_of(coins)
    rng = np.random.default_rng(SEED + 1)
    lenv = ns - split
    shifts = rng.integers(3600, max(lenv - 3600, 3601), nplacebo)
    return SimpleNamespace(
        name="B", coins=list(coins), tp=tp, bases=list(B_BASES), gate_names=list(B_GATES), features=b_features,
        gates=gates, eoff=np.array([d for d, _ in B_HOLDS], np.int64), xoff=np.array([d + h for d, h in B_HOLDS], np.int64),
        hold_names=[f"d{d}s+{h}s" for d, h in B_HOLDS], pe={c: tp[c]["lmid"] for c in coins},
        px={c: tp[c]["lmid"] for c in coins}, tb=(ix // 600).astype(np.int32), cl=(ix // 1800).astype(np.int32),
        n_tb=ns // 600, thr_block=600, thr_window=7200, thr_minfin=3600,
        per={"disc": (0, split, 0, split // 1800), "val": (split, ns, split // 1800, ncl_all - split // 1800)},
        cost_rt=np.array([2.0 * walk[c] * 1e-4 for c in coins]), set_names=names, W=W, shifts=shifts)


# ------------------------------------------------------------------------------------------------ grid and verdict
def grid_size(blocks):
    return {b.name: len(b.bases) * len(b.gate_names) * len(QS) * len(b.eoff) * len(b.set_names) * 2 for b in blocks}


def combine(parts, nplacebo):
    """Join the per-base tables and the placebo maxima; p-values by the shifted-signal max statistic."""
    df = pd.concat([p[2] for p in parts], ignore_index=True)
    M = {}
    MS = {}
    for blkname in ("A", "B"):
        sel = [p for p in parts if p[0] == blkname]
        M[blkname] = np.max([p[3] for p in sel], axis=0) if sel else np.full(nplacebo, -np.inf)
        MS[blkname] = np.max([p[4] for p in sel], axis=0) if sel else np.full(nplacebo, -np.inf)
    joint = np.maximum(M["A"], M["B"])
    joint_s = np.maximum(MS["A"], MS["B"])
    cnt = sum(p[5] for p in parts)
    cnt2 = sum(p[6] for p in parts)

    def pval(t, dist):
        d = np.sort(dist)
        t = np.asarray(t, float)
        out = (1.0 + (len(d) - np.searchsorted(d, t, side="left"))) / (len(d) + 1.0)
        return np.where(np.isfinite(t), out, np.nan)

    t = np.where(df["eligible"], df["t_val_1x"], np.nan)
    df["p_fullgrid"] = pval(t, joint)
    df["p_block"] = np.where(df["block"] == "A", pval(t, M["A"]), pval(t, M["B"]))
    df["p_selected"] = np.where(df["disc_ok"], pval(t, joint_s), np.nan)
    df["pass_t"] = df["eligible"] & (df["t_val_1x"] >= T_PASS)
    df["pass_2x"] = df["net2x_val_bp"] > 0
    df["pass_maxstat"] = df["p_fullgrid"] <= P_PASS
    df["candidate"] = df["disc_ok"] & df["pass_t"] & df["pass_2x"] & df["pass_maxstat"]
    return df, joint, joint_s, cnt, cnt2, M


def write_outputs(df, joint, joint_s, cnt, cnt2, M, sizes, shas, nplacebo, elapsed):
    RES.mkdir(parents=True, exist_ok=True)
    num = [c for c in df.select_dtypes("float64").columns if c != "q"]
    out = df.copy()
    out[num] = out[num].astype("float32")
    out.to_csv(RES / "grid.csv.gz", index=False, compression="gzip")
    cand = df[df["candidate"]].sort_values("t_val_1x", ascending=False)
    cand.to_csv(RES / "candidates.csv", index=False)
    df[df["eligible"]].sort_values("t_val_1x", ascending=False).head(200).to_csv(RES / "top200_by_val_t.csv", index=False)
    pd.DataFrame({"b": np.arange(nplacebo), "max_t_A": M["A"], "max_t_B": M["B"], "max_t_joint": joint,
                  "max_t_selected": joint_s, "n_pass_analogue": cnt, "n_t2_eligible": cnt2}).to_csv(
        RES / "placebo.csv", index=False)
    real_pass = int((df["disc_ok"] & df["pass_t"] & df["pass_2x"]).sum())
    sv, q95 = nulls.search_verdict(real_pass, cnt)
    summary = dict(
        lane="atlas_tape_v1", registry=REG_ID, trials=int(sum(sizes.values())), sizes=sizes, placebos=nplacebo,
        eligible=int(df["eligible"].sum()), eligible_by_block=df[df["eligible"]].groupby("block").size().to_dict(),
        disc_ok=int(df["disc_ok"].sum()), min_trades=MIN_TRADES, min_clusters=MIN_CLUSTERS,
        real_pass_without_maxstat=real_pass, null_pass_mean=float(np.mean(cnt)), null_pass_q95=float(q95),
        null_pass_max=int(np.max(cnt)), null_t2_eligible_mean=float(np.mean(cnt2)),
        count_verdict=sv, candidates=int(len(cand)),
        maxstat_q95_joint=float(np.quantile(joint, 0.95)), maxstat_q95_A=float(np.quantile(M["A"], 0.95)),
        maxstat_q95_B=float(np.quantile(M["B"], 0.95)),
        best_val_t=float(df["t_val_1x"].where(df["eligible"]).max()),
        best_p_fullgrid=float(df["p_fullgrid"].min()), verdict="PARTIAL" if len(cand) else "NULL",
        elapsed_s=round(elapsed), inputs=shas)
    (RES / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary


# ------------------------------------------------------------------------------------------------ entry points
def warm_up():
    """Compile the kernels before the workers fork."""
    x = np.arange(1, 50, dtype=float)
    thr = block_thresholds(x, 10, 10, 5, np.array(QS), 5)
    G = np.zeros((len(QS), 1, 4))
    N = np.zeros_like(G)
    kernel(x, thr, np.zeros(49, np.int32), np.ones(49, np.uint8), x, x, np.zeros(49, np.int32),
           np.ones(1, np.int64), np.ones(1, np.int64), 0, 49, 0, 0, G, N)


def plumbing():
    """Counts and shapes only. No returns are computed or printed."""
    walk = walk_costs()
    log(f"walk bp {walk}")
    bars = load_block_a()
    n = len(bars["BTC"]["close"])
    split = (r349.ms(A_DISC_END) - r349.T0) // r349.MIN
    for c in COINS:
        v = np.isfinite(bars[c]["close"])
        log(f"A {c}: bars {n}, valid disc {int(v[:split].sum())}, valid val {int(v[split:].sum())}")
    tp, ns, off = load_tape()
    log(f"B slots {ns}, offsets {off}, disc/val split slot {off[B_N_DISC_DAYS]}")
    for c in COINS:
        t = tp[c]
        log(f"B {c}: binance mid {int(np.isfinite(t['bmid']).sum())}, lighter mid {int(np.isfinite(t['lmid']).sum())}, "
            f"mexc mid {int(np.isfinite(t['mmid']).sum())}, trades-sec {int(np.isfinite(t['tf']).sum())}")
    blocks = [build_block_a(bars, walk), build_block_b(tp, ns, off, walk)]
    sizes = grid_size(blocks)
    log(f"grid sizes {sizes}, total {sum(sizes.values())}")


def main(workers=3, nplacebo=NPLACEBO):
    sha = prereg.verify(LANE / "PREREG.md")
    shas = r349.frozen_inputs(LANE / "PREREG.md")
    log(f"PREREG verified {sha[:12]}; {len(shas)} inputs match")
    free = shutil.disk_usage(ROOT).free
    if free < 2e9:
        raise SystemExit(f"free disk {free / 1e9:.1f} GB < 2 GB: stop")
    workers = min(workers, 3)
    t_start = time.time()
    walk = walk_costs()
    bars = load_block_a()
    tp, ns, off = load_tape()
    BLOCKS["A"] = build_block_a(bars, walk, nplacebo=nplacebo)
    BLOCKS["B"] = build_block_b(tp, ns, off, walk, nplacebo=nplacebo)
    sizes = grid_size(list(BLOCKS.values()))
    log(f"loaded; grid {sizes}, {sum(sizes.values())} cells; {nplacebo} placebos; {workers} workers")
    warm_up()
    jobs = [("A", i, nplacebo) for i in range(len(A_BASES))] + [("B", i, nplacebo) for i in range(len(B_BASES))]
    parts = []
    with mp.get_context("fork").Pool(workers) as pool:
        for res in pool.imap_unordered(run_base, jobs):
            parts.append(res)
            log(f"done {res[0]}:{res[1]} in {res[7]:.0f}s ({len(parts)}/{len(jobs)})")
    parts.sort(key=lambda p: (p[0], p[1]))
    df, joint, joint_s, cnt, cnt2, M = combine(parts, nplacebo)
    assert len(df) == sum(sizes.values()), (len(df), sizes)
    summary = write_outputs(df, joint, joint_s, cnt, cnt2, M, sizes, shas, nplacebo, time.time() - t_start)
    log(f"done: {summary['verdict']}, {summary['candidates']} candidates, best val t {summary['best_val_t']:.2f}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--plumbing", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--placebos", type=int, default=NPLACEBO)
    a = ap.parse_args()
    if a.plumbing:
        plumbing()
    elif a.run:
        main(a.workers, a.placebos)
    else:
        ap.error("pass --run or --plumbing")
