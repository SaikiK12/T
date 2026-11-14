"""R431 rawlead_v1 (M430 + M431): the sub-second lead of Binance's USDT perp book over its USDC perp book on the raw
event tape, and what is left of it after this machine's latency and the taker fee. Gate 0, files only, no orders.

Two clocks, each used for what it can say (experiments/rawlead_v1/PREREG.md):
- Detection runs in the order rows reached this container (`t - off`, local monotonic): an event is what this
  machine would have seen. The primary machine drains its socket first: it decides on the USDC state that includes
  every USDC row Binance had published by the trigger's E, and the time it waits for those rows is added to its
  delay. Plumbing showed why: on 10-29/10-30 most apparent stale-USDC moments had USDC rows published in the same
  Binance millisecond as the trigger and read about 0.1 ms after it (the two books moved together). A naive machine
  that acts on the first message is kept as a diagnostic cell.
- Everything after the decision runs in Binance's own clock. Both books are Binance, so the matching-engine stamp T
  and the publication stamp E of the two books share one clock. An order sent when the trigger row arrived reaches the
  matching engine at X = E + q + RTT + extra, where q is how long the trigger row queued on its way in (its feed lag
  above the minute's floor) and RTT the day's measured ping round trip. The order meets the USDC book as of T <= X.
  This removes the bias of reading the target on the local clock: when the USDC feed queues longer than the USDT
  feed, the local clock shows a stale USDC book the order would never have met.

Parts (all frozen in the PREREG):
  A  M430 label in Binance's clock: after an event, does the USDC mid cover half the predicted move before the USDT mid
     gives half of it back, before the USDC mid moves half of it the other way, and within each horizon; and how many
     ms after the trigger's matching time does the catch-up come.
  B  M431 frontier: taker entry at X, exit H ms later (both taker, the USDC touch at T <= X), net of 4 bp a fill at
     1x/2x/3x, over a grid of delays after E and this machine's own delay (drained, and naive as a diagnostic).
     One primary cell decides the verdict.
  C  The maker's side: signed markouts of USDC taker trades just after a lead crossing in its direction, against all
     other trades, and how fast the first such trade comes.

usage: python scripts/run_rawlead.py --plumbing     counts, feed quality and filter counts; reads no price after an event
       python scripts/run_rawlead.py                the frozen run (verifies the PREREG and every frozen input first)
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
from lab import prereg  # noqa: E402

LANE = ROOT / "experiments" / "rawlead_v1"
TAPE = ROOT / "data" / "rawtape"

DAYS = ("2026-10-29", "2026-10-30", "2026-11-05")
ASSETS = {"BTC": ("BTCUSDT", "BTCUSDC"), "ETH": ("ETHUSDT", "ETHUSDC")}
THETAS = (1.0, 2.0, 4.0, 8.0)        # bp: fair USDC mid beyond the USDC touch by at least this much
DELAYS = (1, 25, 50, 100, 250, 500, 1000, 1500)   # ms after the trigger's publication E, Binance's clock
MACHINE = "machine"                  # E + q + wait + RTT: this container's own delay
NAIVE = "naive_machine"              # diagnostic: detection on the first message read, this container's delay
HOLDS = (300, 1000, 3000)            # ms between the entry's and the exit's arrival
HORIZONS = (300, 500, 750, 1000, 2000, 3000)      # ms, Part A
PRIMARY = dict(theta=2.0, delay=MACHINE, hold=1000)
FEE_BP = 4.0                         # taker fee per fill, Binance USDC perps (secondary source, as in R367's PREREG)
COST_MULTS = (1, 2, 3)
NOTIONAL = 5000.0                    # USD per order, for the thin-touch diagnostic only
MIN_EVENTS, MIN_ASSET_EVENTS = 100, 20
US = 1000                            # microseconds per ms
REFRACTORY_US = 3_000_000
GAP_US = 1_000_000                   # a silence this long on the USDT book is a feed stall
PAD_BEFORE_US, PAD_AFTER_US = 7_000_000, 5_000_000   # no event this close before / after a stall
PATH_US = 7_000_000                  # an event needs this much recording after it on both books
QUEUE_MAX_MS = 100                   # decision delay cap: trigger queue above the minute's floor plus drain wait
FLOOR_Q, FLOOR_MIN_ROWS = 0.001, 200
BASIS_N, BASIS_MIN = 60, 30          # trailing seconds in the basis median, and the fewest valid ones
BLOCK_US = 900_000_000               # 15-minute blocks of local time for every dependent statistic
BOOT, SEED = 2000, 431
WINDOW_MS = 1000                     # Part C: a trade this soon after a crossing, in Binance's clock
MARKOUT_MS = (1000, 10000)
C_PAD_US = 11_000_000                # Part C: no stall this soon after a trade
TRIALS = (len(THETAS) * (len(DELAYS) + 2) * len(HOLDS) + len(THETAS) * len(HORIZONS) + 2 * len(MARKOUT_MS))
LOG = []


def log(msg):
    line = f"{time.strftime('%H:%M:%S', time.gmtime())} {msg}"
    print(line, flush=True)
    LOG.append(line)


# ---------------------------------------------------------------- data

def book(sym, day, tape=TAPE):
    """One finished day of a Binance bookTicker stream as arrays in arrival order."""
    df = pd.read_parquet(tape / "bbo" / sym / f"{day}.parquet", columns=["t", "off", "T", "dE", "bid", "bq", "sp", "aq"])
    return make_book(df.t.to_numpy(), df.off.to_numpy(), df["T"].to_numpy(), df.dE.to_numpy(), df.bid.to_numpy(),
                     df.sp.to_numpy(), df.bq.to_numpy(), df.aq.to_numpy(), f"{sym}/{day}")


def make_book(t, off, T, dE, bid, sp, bq, aq, name="book"):
    """t wall-clock receive us, off wall minus monotonic us, T/E Binance ms, prices in hundredths, sizes in
    thousandths. Refuses a tape whose local clock or Binance stamps run backwards."""
    t = np.asarray(t, np.int64)
    loc = t - np.asarray(off, np.int64)
    T = np.asarray(T, np.int64)
    E = T + np.asarray(dE, np.int64)
    for nm, x in (("local clock", loc), ("T", T), ("E", E)):
        if len(x) > 1 and (np.diff(x) < 0).any():
            raise SystemExit(f"REFUSED: {nm} runs backwards in {name}")
    bid = np.asarray(bid, np.int64)
    ask = bid + np.asarray(sp, np.int64)
    return dict(loc=loc, T=T, E=E, lag=t // 1000 - E, mn=t // 60_000_000, bid=bid, ask=ask,
                bq=np.asarray(bq, np.int64), aq=np.asarray(aq, np.int64), mid=(bid + ask) / 2.0)


def trades(sym, day, tape=TAPE):
    df = pd.read_parquet(tape / "trade" / sym / f"{day}.parquet", columns=["t", "off", "T", "p", "q", "m"])
    return dict(loc=df.t.to_numpy() - df.off.to_numpy().astype(np.int64), T=df["T"].to_numpy().astype(np.int64),
                p=df.p.to_numpy() / 100.0, q=df.q.to_numpy() / 1000.0,
                side=np.where(df.m.to_numpy() == 1, -1, 1))        # m = 1: the buyer is the maker, a sell aggressor


def rtt_ms(day, tape=TAPE):
    """Median ping round trip of connection 0 (binance_public, which carries bookTicker) inside 13:00-17:00 UTC."""
    r = pd.read_parquet(tape / "rtt" / "all" / f"{day}.parquet")
    r = r[r.c == 0]
    h = pd.to_datetime(r.t, unit="us", utc=True).dt.hour
    w = r[(h >= 13) & (h < 17)]
    use = w if len(w) >= 10 else r
    return float(use.us.median()) / 1000.0, len(use)


# ---------------------------------------------------------------- clocks and feed quality

def floor_by_minute(books):
    """Per wall-clock minute, the FLOOR_Q quantile of feed lag (local wall ms minus E) over all the day's books: the
    path delay plus clock offset of a row that did not queue. Minutes with too few rows get NaN."""
    mn = np.concatenate([b["mn"] for b in books])
    lag = np.concatenate([b["lag"] for b in books])
    g = pd.DataFrame({"mn": mn, "lag": lag}).groupby("mn").lag
    q, n = g.quantile(FLOOR_Q), g.size()
    q[n < FLOOR_MIN_ROWS] = np.nan
    return q.index.to_numpy(np.int64), q.to_numpy(float)


def queue_ms(b, rows, floor):
    """How long each row queued above its minute's floor (inf when the minute has no floor)."""
    mins, fl = floor
    k = np.searchsorted(mins, b["mn"][rows])
    ok = (k < len(mins)) & (mins[np.minimum(k, len(mins) - 1)] == b["mn"][rows])
    f = np.where(ok, fl[np.minimum(k, len(mins) - 1)], np.nan)
    q = b["lag"][rows] - f
    return np.where(np.isfinite(q), q, np.inf)


def stalls(S):
    """Intervals [start, end] of local time in which the USDT book was silent for GAP_US or more."""
    d = np.diff(S["loc"])
    j = np.flatnonzero(d >= GAP_US)
    return S["loc"][j], S["loc"][j + 1]


def clean_mask(S, when, pad_before=PAD_BEFORE_US, pad_after=PAD_AFTER_US):
    """True where a local time is clear of feed stalls: none starts within pad_before after it, none ended within
    pad_after before it, and it is not inside one."""
    a, b = stalls(S)
    ok = np.ones(len(when), bool)
    if len(a):
        nxt = np.searchsorted(a, when, side="left")
        has = nxt < len(a)
        ok &= ~(has & (a[np.minimum(nxt, len(a) - 1)] - when < pad_before))
        prv = np.searchsorted(b, when, side="right") - 1
        has = prv >= 0
        ok &= ~(has & (when - b[np.maximum(prv, 0)] < pad_after))
        mid = np.searchsorted(a, when, side="right") - 1
        ok &= ~((mid >= 0) & (when <= b[np.maximum(mid, 0)]) & (when > a[np.maximum(mid, 0)]))
    return ok


def asof(x, when):
    """Index of the last element of the sorted array x at or before each value of `when` (-1 when none)."""
    return np.searchsorted(x, when, side="right") - 1


# ---------------------------------------------------------------- signal (local clock)

def basis(S, D):
    """Trailing median of log(mid USDT / mid USDC) on a one-second grid of local time. Entry k covers the BASIS_N
    grid seconds before grid second k, so an event in second k uses only samples taken before that second began."""
    g0 = int(S["loc"][0] // 1_000_000) + 1
    g1 = int(S["loc"][-1] // 1_000_000)
    grid = np.arange(g0, g1 + 1, dtype=np.int64) * 1_000_000
    i, j = asof(S["loc"], grid), asof(D["loc"], grid)
    ok = (i >= 0) & (j >= 0)
    x = np.full(len(grid), np.nan)
    x[ok] = np.log(S["mid"][i[ok]]) - np.log(D["mid"][j[ok]])
    stale = ok & ((grid - S["loc"][np.maximum(i, 0)] > GAP_US) | (grid - D["loc"][np.maximum(j, 0)] > 5 * GAP_US))
    x[stale] = np.nan
    b = pd.Series(x).rolling(BASIS_N, min_periods=BASIS_MIN).median().shift(1).to_numpy()
    return g0, b


def signals(S, D):
    """Per USDT row: the USDC row used for the decision, the log fair USDC mid, and the gap in bp on each side.

    Two readings of the USDC book. `local`: the last USDC row this container had received when the trigger arrived
    (a machine that acts on the first message it reads). `drained` (the primary): the later of that row and the last
    USDC row Binance had published by the trigger's E, i.e. a machine that reads every message already published
    before it decides; `wait_us` is how long after the trigger that last published row arrived, charged to the
    decision delay."""
    iL = asof(D["loc"], S["loc"])
    iX = asof(D["E"], S["E"])
    iD = np.maximum(iL, iX)
    wait = np.where(iX > iL, D["loc"][np.maximum(iX, 0)] - S["loc"], 0)
    g0, b = basis(S, D)
    k = S["loc"] // 1_000_000 - g0
    inside = (k >= 0) & (k < len(b)) & (iL >= 0)
    bas = np.full(len(k), np.nan)
    bas[inside] = b[k[inside]]
    f = np.log(S["mid"]) - bas
    out = dict(iD=iD, iD_local=iL, iD_exch=iX, wait_us=np.maximum(wait, 0), fair=f)
    for key, j in (("", np.maximum(iD, 0)), ("_local", np.maximum(iL, 0))):
        out["up" + key] = (f - np.log(D["ask"][j])) * 1e4
        out["dn" + key] = (np.log(D["bid"][j]) - f) * 1e4
    return out


def crossings(sig, theta, key=""):
    """USDT rows at which a side's gap first reaches theta (NaN compares False), with the direction (+1 up)."""
    out = []
    for gap, d in ((sig["up" + key], 1), (sig["dn" + key], -1)):
        c = gap >= theta
        first = np.flatnonzero(c[1:] & ~c[:-1]) + 1
        out.append(np.column_stack([first, np.full(len(first), d)]))
    ev = np.vstack(out).astype(np.int64)
    return ev[np.argsort(ev[:, 0], kind="stable")]


def events(S, D, theta, sig, floor, naive=False):
    """Kept events of one asset-day at one threshold, with a count of every filter (filters are not exclusive).
    naive=True detects on the local reading and adds no wait (the diagnostic machine that acts on the first message).
    Returns row indices into S, the direction, the decision delay q in ms (the trigger's queue above the minute's
    floor, plus the drain wait for the drained machine; an event needs q <= QUEUE_MAX_MS) and the counts."""
    key = "_local" if naive else ""
    cr = crossings(sig, theta, key)
    keep, last = [], -REFRACTORY_US
    for n, i in enumerate(cr[:, 0]):
        if S["loc"][i] - last >= REFRACTORY_US:
            keep.append(n)
            last = S["loc"][i]
    ev = cr[keep]
    idx, d = ev[:, 0], ev[:, 1]
    when = S["loc"][idx]
    m_stall = clean_mask(S, when)
    q = queue_ms(S, idx, floor)
    unread = sig["iD_local"][idx] < sig["iD_exch"][idx]
    if not naive:
        q = q + sig["wait_us"][idx] / US
    m_queue = q <= QUEUE_MAX_MS
    m_path = when + PATH_US < min(S["loc"][-1], D["loc"][-1])
    ok = m_stall & m_queue & m_path
    counts = dict(crossings=len(cr), after_refractory=len(idx), stall=int((~m_stall).sum()),
                  queued=int((~m_queue).sum()), path=int((~m_path).sum()), unread_at_trigger=int(unread.sum()),
                  kept=int(ok.sum()), kept_unread=int((ok & unread).sum()))
    return idx[ok], d[ok], q[ok], counts


# ---------------------------------------------------------------- Part B (Binance's clock)

def fills(D, d, X, hold):
    """Taker entry at the USDC touch as of T <= X, taker exit at the touch as of T <= X + hold. Gross bp, and
    whether either touch held less than NOTIONAL."""
    j0, j1 = asof(D["T"], X), asof(D["T"], X + hold)
    if (j0 < 0).any():
        raise SystemExit("REFUSED: an entry before the first USDC row")
    up = d > 0
    entry = np.where(up, D["ask"][j0], D["bid"][j0]).astype(float)
    exit_ = np.where(up, D["bid"][j1], D["ask"][j1]).astype(float)
    gross = d * (np.log(exit_) - np.log(entry)) * 1e4
    sz0 = np.where(up, D["aq"][j0], D["bq"][j0]) / 1000.0 * entry / 100.0
    sz1 = np.where(up, D["bq"][j1], D["aq"][j1]) / 1000.0 * exit_ / 100.0
    return gross, (sz0 < NOTIONAL) | (sz1 < NOTIONAL)


def arrival(S, idx, q, delay, rtt):
    if delay == MACHINE:
        return S["E"][idx] + np.ceil(q).astype(np.int64) + int(round(rtt))
    return S["E"][idx] + int(delay)


# ---------------------------------------------------------------- Part A (Binance's clock)

def label(S, D, sig, idx, d, horizon_max=max(HORIZONS)):
    """Per event: the first time (ms after the trigger's T) at which the USDC mid covers half the predicted move
    (catch), the USDT mid gives half of it back (reversal), or the USDC mid moves half of it the other way (adverse);
    inf when it does not happen within horizon_max. Ties count against the catch-up."""
    out = np.full((len(idx), 3), np.inf)
    for n, (i, dd) in enumerate(zip(idx, d)):
        T0 = S["T"][i]
        c0 = sig["iD"][i]
        lm0 = np.log(D["mid"][c0])
        half = 0.5 * dd * (sig["fair"][i] - lm0)
        j1 = np.searchsorted(D["T"], T0 + horizon_max, side="right")
        if j1 > c0 + 1:
            x = dd * (np.log(D["mid"][c0 + 1:j1]) - lm0)
            tt = np.maximum(D["T"][c0 + 1:j1] - T0, 0)
            k = np.flatnonzero(x >= half)
            if len(k):
                out[n, 0] = tt[k[0]]
            k = np.flatnonzero(x <= -half)
            if len(k):
                out[n, 2] = tt[k[0]]
        i1 = np.searchsorted(S["T"], T0 + horizon_max, side="right")
        if i1 > i + 1:
            y = dd * (np.log(S["mid"][i + 1:i1]) - np.log(S["mid"][i]))
            k = np.flatnonzero(y <= -half)
            if len(k):
                out[n, 1] = S["T"][i + 1 + k[0]] - T0
    return out


def first_outcome(times):
    """0 catch, 1 reversal, 2 adverse, 3 none; ties go to reversal or adverse."""
    c, r, a = times[:, 0], times[:, 1], times[:, 2]
    other = np.minimum(r, a)
    res = np.full(len(times), 3)
    res[np.isfinite(other)] = np.where(r[np.isfinite(other)] <= a[np.isfinite(other)], 1, 2)
    res[c < other] = 0
    return res


# ---------------------------------------------------------------- Part C (Binance's clock)

def markouts(D, tr, h):
    j = asof(D["T"], tr["T"] + h)
    ok = (j >= 0) & (tr["T"] + h <= D["T"][-1])
    m = np.full(len(tr["T"]), np.nan)
    m[ok] = tr["side"][ok] * (np.log(D["mid"][j[ok]]) - np.log(tr["p"][ok] * 100.0)) * 1e4
    return m


def classify(tr, T_cross, d_cross):
    """1 with: within WINDOW_MS after the latest crossing, in its direction; -1 against; 0 outside every window."""
    k = np.searchsorted(T_cross, tr["T"], side="left") - 1
    has = k >= 0
    kk = np.maximum(k, 0)
    inside = has & (tr["T"] - T_cross[kk] <= WINDOW_MS) & (tr["T"] > T_cross[kk])
    same = tr["side"] == d_cross[kk]
    return np.where(inside, np.where(same, 1, -1), 0)


def first_trade_ms(tr, T0, d):
    """Per event, ms from the trigger's T to the first USDC trade in its direction within WINDOW_MS (inf if none)."""
    out = np.full(len(T0), np.inf)
    for n, (t0, dd) in enumerate(zip(T0, d)):
        a, b = np.searchsorted(tr["T"], t0, side="left"), np.searchsorted(tr["T"], t0 + WINDOW_MS, side="right")
        k = np.flatnonzero(tr["side"][a:b] == dd)
        if len(k):
            out[n] = tr["T"][a + k[0]] - t0
    return out


# ---------------------------------------------------------------- statistics

def block_boot(values, blocks, rng, boot=BOOT):
    """Mean, 95% percentile interval and one-sided p (share of resampled means <= 0) by resampling whole blocks."""
    v = np.asarray(values, float)
    ok = np.isfinite(v)
    v, blocks = v[ok], np.asarray(blocks)[ok]
    if len(v) == 0:
        return dict(n=0, mean=None, lo=None, hi=None, p_le0=None, blocks=0)
    u, inv = np.unique(blocks, return_inverse=True)
    s, c = np.bincount(inv, v, len(u)), np.bincount(inv, None, len(u))
    pick = rng.integers(0, len(u), (boot, len(u)))
    means = s[pick].sum(1) / np.maximum(c[pick].sum(1), 1)
    return dict(n=int(len(v)), mean=float(v.mean()), lo=float(np.percentile(means, 2.5)),
                hi=float(np.percentile(means, 97.5)), p_le0=float((means <= 0).mean()), blocks=int(len(u)))


def block_boot_diff(v, cls, blocks, rng, boot=BOOT):
    """Mean of class 1 minus mean of class 0, resampling whole blocks (both classes move together)."""
    ok = np.isfinite(v) & ((cls == 1) | (cls == 0))
    v, cls, blocks = v[ok], cls[ok], np.asarray(blocks)[ok]
    u, inv = np.unique(blocks, return_inverse=True)
    s1 = np.bincount(inv, np.where(cls == 1, v, 0.0), len(u))
    n1 = np.bincount(inv, (cls == 1).astype(float), len(u))
    s0 = np.bincount(inv, np.where(cls == 0, v, 0.0), len(u))
    n0 = np.bincount(inv, (cls == 0).astype(float), len(u))
    pick = rng.integers(0, len(u), (boot, len(u)))
    diff = s1[pick].sum(1) / np.maximum(n1[pick].sum(1), 1) - s0[pick].sum(1) / np.maximum(n0[pick].sum(1), 1)
    point = s1.sum() / max(n1.sum(), 1) - s0.sum() / max(n0.sum(), 1)
    return dict(diff=float(point), lo=float(np.percentile(diff, 2.5)), hi=float(np.percentile(diff, 97.5)),
                n_with=int(n1.sum()), n_out=int(n0.sum()))


def verdict(net1, asset, n_min=MIN_EVENTS, n_asset=MIN_ASSET_EVENTS, ci=None):
    """PASS needs n >= n_min, mean net > 0, the bootstrap lower bound > 0 and a positive mean on each asset with at
    least n_asset events; fewer than n_min events is INCONCLUSIVE; anything else NULL."""
    net1, asset = np.asarray(net1, float), np.asarray(asset)
    if len(net1) < n_min:
        return "INCONCLUSIVE"
    per = {a: net1[asset == a] for a in np.unique(asset)}
    ok_assets = all(len(x) >= n_asset and x.mean() > 0 for x in per.values()) and len(per) == len(ASSETS)
    if net1.mean() > 0 and ci is not None and ci["lo"] > 0 and ok_assets:
        return "PASS"
    return "NULL"


def crossing_delay(D_grid, ev, level):
    """Smallest delay at which the EV curve falls to `level`, by linear interpolation; 0 if it starts below, None if
    it never gets there on the grid."""
    D_grid, ev = np.asarray(D_grid, float), np.asarray(ev, float)
    if ev[0] <= level:
        return 0.0
    for k in range(1, len(ev)):
        if ev[k] <= level:
            return float(D_grid[k - 1] + (ev[k - 1] - level) / (ev[k - 1] - ev[k]) * (D_grid[k] - D_grid[k - 1]))
    return None


# ---------------------------------------------------------------- runs

def day_books(day):
    bk = {a: (book(s, day), book(c, day)) for a, (s, c) in ASSETS.items()}
    floor = floor_by_minute([b for pair in bk.values() for b in pair])
    return bk, floor


def plumbing():
    """Counts, feed quality and filter counts. No price after an event is read."""
    out = {"trials": TRIALS, "days": {}, "filters": {}}
    for day in DAYS:
        bk, floor = day_books(day)
        rtt, nr = rtt_ms(day)
        out["days"][day] = {"rtt_ms": rtt, "rtt_rows": nr, "floor_minutes": int(np.isfinite(floor[1]).sum())}
        for a, (S, D) in bk.items():
            qS = queue_ms(S, np.arange(len(S["loc"])), floor)
            qD = queue_ms(D, np.arange(len(D["loc"])), floor)
            out["days"][day][a] = dict(
                rows_usdt=len(S["loc"]), rows_usdc=len(D["loc"]),
                hours=round((S["loc"][-1] - S["loc"][0]) / 3.6e9, 3),
                queue_ms_usdt_q50_q90_q99=[round(float(x), 1) for x in np.percentile(qS[np.isfinite(qS)], [50, 90, 99])],
                queue_ms_usdc_q50_q90_q99=[round(float(x), 1) for x in np.percentile(qD[np.isfinite(qD)], [50, 90, 99])],
                share_usdt_rows_queued_over_100ms=round(float((qS > QUEUE_MAX_MS).mean()), 4),
                share_usdt_rows_queued_over_1s=round(float((qS > 1000).mean()), 4))
            sig = signals(S, D)
            for th in THETAS:
                for naive in (False, True):
                    _, _, _, cnt = events(S, D, th, sig, floor, naive=naive)
                    out["filters"][f"{day}/{a}/{th}/{'naive' if naive else 'drained'}"] = cnt
    out["kept_by_theta"] = {f"{th}/{r}": sum(v["kept"] for k, v in out["filters"].items() if k.endswith(f"/{th}/{r}"))
                            for th in THETAS for r in ("drained", "naive")}
    print(json.dumps(out, indent=1))


def run():
    sha = prereg.verify(LANE / "PREREG.md")
    from scripts.run_clockflow import check_inputs
    log(f"PREREG verified {sha[:12]}; {len(check_inputs(LANE / 'PREREG.md'))} inputs match; trials {TRIALS}")
    rng = np.random.default_rng(SEED)
    res = LANE / "results"
    res.mkdir(parents=True, exist_ok=True)
    B, A, C, F, evrows, rtts = [], [], [], [], [], {}
    for day in DAYS:
        bk, floor = day_books(day)
        rtt, _ = rtt_ms(day)
        rtts[day] = rtt
        for a, (S, D) in bk.items():
            sig = signals(S, D)
            tr = trades(ASSETS[a][1], day)
            kept1 = None
            for th in THETAS:                       # the naive machine: one diagnostic cell per theta and hold
                idx, d, q, cnt = events(S, D, th, sig, floor, naive=True)
                F.append(dict(day=day, asset=a, theta=th, reading="naive", **cnt))
                X = arrival(S, idx, q, MACHINE, rtt)
                for h in HOLDS:
                    gross, thin = fills(D, d, X, h) if len(idx) else (np.array([]), np.array([]))
                    for n in range(len(idx)):
                        B.append(dict(day=day, asset=a, theta=th, delay=NAIVE, hold=h,
                                      block=f"{day}/{S['loc'][idx[n]] // BLOCK_US}", gross=gross[n],
                                      thin=bool(thin[n]), d=int(d[n]), delay_ms=int(X[n] - S["E"][idx[n]])))
            for th in THETAS:
                idx, d, q, cnt = events(S, D, th, sig, floor)
                F.append(dict(day=day, asset=a, theta=th, reading="drained", **cnt))
                if th == THETAS[0]:
                    kept1 = (idx, d)
                if not len(idx):
                    continue
                blk = [f"{day}/{x}" for x in S["loc"][idx] // BLOCK_US]
                times = label(S, D, sig, idx, d)
                for n in range(len(idx)):
                    A.append(dict(day=day, asset=a, theta=th, block=blk[n], catch_ms=times[n, 0], rev_ms=times[n, 1],
                                  adv_ms=times[n, 2], outcome=int(first_outcome(times[n:n + 1])[0])))
                for delay in DELAYS + (MACHINE,):
                    X = arrival(S, idx, q, delay, rtt)
                    for h in HOLDS:
                        gross, thin = fills(D, d, X, h)
                        for n in range(len(idx)):
                            B.append(dict(day=day, asset=a, theta=th, delay=str(delay), hold=h, block=blk[n],
                                          gross=gross[n], thin=bool(thin[n]), d=int(d[n]),
                                          delay_ms=int(X[n] - S["E"][idx[n]])))
            # Part C on this asset-day
            T_cross_all = crossings(sig, THETAS[0])
            Tc, dc = S["T"][T_cross_all[:, 0]], T_cross_all[:, 1]
            o = np.argsort(Tc, kind="stable")
            Tc, dc = Tc[o], dc[o]
            cls = classify(tr, Tc, dc)
            clean = clean_mask(S, tr["loc"], pad_before=C_PAD_US)
            blk = np.array([f"{day}/{x}" for x in tr["loc"] // BLOCK_US])
            mo = {h: markouts(D, tr, h) for h in MARKOUT_MS}
            ftm = first_trade_ms(tr, S["T"][kept1[0]], kept1[1]) if kept1 is not None else np.array([])
            C.append(dict(day=day, asset=a, cls=cls[clean], blk=blk[clean], q=tr["q"][clean] * tr["p"][clean],
                          mo={h: m[clean] for h, m in mo.items()}, first_trade_ms=ftm))
            log(f"{day} {a}: rtt {rtt:.1f} ms; kept events by theta (naive, then drained) "
                f"{[f['kept'] for f in F if f['day'] == day and f['asset'] == a]}; USDC trades {int(clean.sum())}")
        del bk
    Bdf, Adf, Fdf = pd.DataFrame(B), pd.DataFrame(A), pd.DataFrame(F)
    for m in COST_MULTS:
        Bdf[f"net_{m}x"] = Bdf.gross - m * 2 * FEE_BP
    Fdf.to_csv(res / "filters.csv", index=False)

    # Part B grid
    cells = []
    for (th, delay, h), g in Bdf.groupby(["theta", "delay", "hold"], sort=True):
        ci = block_boot(g.net_1x, g.block, rng)
        cells.append(dict(theta=th, delay=delay, hold=h, n=len(g), gross=g.gross.mean(),
                          gross_med=g.gross.median(), net_1x=g.net_1x.mean(), net_2x=g.net_2x.mean(),
                          net_3x=g.net_3x.mean(), net_1x_lo=ci["lo"], net_1x_hi=ci["hi"], share_thin=g.thin.mean(),
                          delay_ms_med=g.delay_ms.median(), hit=(g.gross > 0).mean(),
                          breakeven_fee_bp=g.gross.mean() / 2))
    cdf = pd.DataFrame(cells)
    cdf.to_csv(res / "cells.csv", index=False, float_format="%.6g")
    P = Bdf[(Bdf.theta == PRIMARY["theta"]) & (Bdf.delay == PRIMARY["delay"]) & (Bdf.hold == PRIMARY["hold"])]
    P.to_csv(res / "events_primary.csv", index=False, float_format="%.6g")
    ci = block_boot(P.net_1x, P.block, rng)
    v = verdict(P.net_1x.to_numpy(), P.asset.to_numpy(), ci=ci)
    prim = dict(n=len(P), gross=float(P.gross.mean()) if len(P) else None, ci_net_1x=ci,
                net={f"{m}x": float(P[f"net_{m}x"].mean()) if len(P) else None for m in COST_MULTS},
                by_asset={a: dict(n=int((P.asset == a).sum()), net_1x=float(P[P.asset == a].net_1x.mean())
                                  if (P.asset == a).any() else None) for a in ASSETS},
                by_day={dy: dict(n=int((P.day == dy).sum()), net_1x=float(P[P.day == dy].net_1x.mean())
                                 if (P.day == dy).any() else None) for dy in DAYS},
                gross_ci=block_boot(P.gross, P.block, rng), share_thin=float(P.thin.mean()) if len(P) else None,
                delay_ms_median=float(P.delay_ms.median()) if len(P) else None)

    # frontier at the primary theta and hold
    fr = cdf[(cdf.theta == PRIMARY["theta"]) & (cdf.hold == PRIMARY["hold"]) & cdf.delay.str.isdigit()].copy()
    fr["dms"] = fr.delay.astype(int)
    fr = fr.sort_values("dms")
    frontier = dict(delays=fr.dms.tolist(), gross=fr.gross.tolist(), n=fr.n.tolist())
    if len(fr):
        g0 = fr.gross.iloc[0]
        frontier["tau_50_ms"] = crossing_delay(fr.dms, fr.gross, 0.5 * g0) if g0 > 0 else 0.0
        frontier["tau_be_ms_1x"] = crossing_delay(fr.dms, fr.gross, 2 * FEE_BP)
        frontier["tau_zero_ms"] = crossing_delay(fr.dms, fr.gross, 0.0)
    frontier["rtt_ms_by_day"] = rtts

    # Part A
    Atab = []
    for th, g in Adf.groupby("theta"):
        c = g.catch_ms.to_numpy()
        first = g.outcome.to_numpy()
        row = dict(theta=th, n=len(g), p_catch_first_3000=float((first == 0).mean()),
                   p_rev_first=float((first == 1).mean()), p_adv_first=float((first == 2).mean()),
                   p_none=float((first == 3).mean()))
        for h in HORIZONS:
            row[f"p_catch_{h}"] = float(((first == 0) & (c <= h)).mean())
        cf = c[(first == 0)]
        for qq in (10, 25, 50, 75, 90):
            row[f"catch_ms_q{qq}"] = float(np.percentile(cf, qq)) if len(cf) else None
        for lim in (5, 25, 50, 100, 250):
            row[f"share_catch_within_{lim}ms"] = float((cf <= lim).mean()) if len(cf) else None
        Atab.append(row)
    pd.DataFrame(Atab).to_csv(res / "partA.csv", index=False, float_format="%.6g")
    Adf.to_csv(res / "partA_events.csv", index=False, float_format="%.6g")

    # Part C
    cls = np.concatenate([c["cls"] for c in C])
    blk = np.concatenate([c["blk"] for c in C])
    notional = np.concatenate([c["q"] for c in C])
    partC = dict(trades=int(len(cls)), share_with=float((cls == 1).mean()), share_against=float((cls == -1).mean()),
                 notional_share_with=float(notional[cls == 1].sum() / notional.sum()), markout={})
    for h in MARKOUT_MS:
        mo = np.concatenate([c["mo"][h] for c in C])
        partC["markout"][str(h)] = dict(
            with_mean=float(np.nanmean(mo[cls == 1])), against_mean=float(np.nanmean(mo[cls == -1])),
            out_mean=float(np.nanmean(mo[cls == 0])),
            with_minus_out=block_boot_diff(mo, cls, blk, rng),
            against_minus_out=block_boot_diff(mo, np.where(cls == -1, 1, np.where(cls == 0, 0, 2)), blk, rng))
    ftm = np.concatenate([c["first_trade_ms"] for c in C])
    fin = ftm[np.isfinite(ftm)]
    partC["first_trade_after_event"] = dict(
        events=int(len(ftm)), share_with_trade_within_window=float(len(fin) / max(len(ftm), 1)),
        ms_q10_q25_q50_q75_q90=[float(x) for x in np.percentile(fin, [10, 25, 50, 75, 90])] if len(fin) else None,
        share_within={str(l): float((ftm <= l).mean()) for l in (5, 25, 50, 100, 250)})

    nv = Bdf[(Bdf.theta == PRIMARY["theta"]) & (Bdf.delay == NAIVE) & (Bdf.hold == PRIMARY["hold"])]
    naive = dict(n=len(nv), gross=float(nv.gross.mean()) if len(nv) else None,
                 net_1x=float(nv.net_1x.mean()) if len(nv) else None, gross_ci=block_boot(nv.gross, nv.block, rng))
    out = dict(prereg_sha256=sha, trials=TRIALS, verdict=v, naive_at_primary=naive, primary=dict(PRIMARY, **prim), frontier=frontier,
               partA=Atab, partC=partC, fee_bp_per_fill=FEE_BP)
    (res / "summary.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    log(f"primary n {prim['n']}, gross {prim['gross']}, net 1x {prim['net']['1x']} CI {ci['lo']}..{ci['hi']}; "
        f"verdict {v}")
    log(f"frontier gross by delay {dict(zip(frontier['delays'], [round(x, 3) for x in frontier['gross']]))}")
    (LANE / "run.log").write_text("\n".join(LOG) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plumbing", action="store_true")
    args = ap.parse_args()
    if args.plumbing:
        plumbing()
    else:
        run()
