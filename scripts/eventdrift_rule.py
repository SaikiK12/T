"""R368 eventdrift_v1 rule, frozen in experiments/eventdrift_v1/PREREG.md: after an EIA release, does the market keep
moving in the direction of its own first-minute reaction for long enough to pay a taker round trip?

Pure functions over 1-minute bars (Binance USD-M TradFi perpetuals, labelled by bar open time). Nothing here reads a
file or a price by itself; scripts/run_eventdrift.py feeds it.

Timeline of one release at instant T (the open time of bar T):
- reference   close of bar T-1  (the last price before the release)
- reaction    r0 = 1e4 ln(close_T / close_{T-1})   the first minute, known at T + 60 s
- entry       open of bar T+1   (the first trade after the first minute; a late variant enters at close_{T+1})
- exit        close of bar T+h, h minutes held
- move_h      1e4 ln(close_{T+h} / open_{T+1})
- continuation x_h = sign(r0) * move_h, in bp, before costs
"""
import math

import numpy as np

MINUTE_MS = 60_000
HORIZONS = (1, 2, 5, 10)
DECISION_H = 5
SUBSETS = ("all", "neg", "pos")
# (event type, symbol, subset): the two cells the verdict reads, both at DECISION_H
DECISIONS = (("wpsr", "CLUSDT", "neg"), ("ngs", "NATGASUSDT", "all"))
EVENT_SYMBOL = {"wpsr": "CLUSDT", "ngs": "NATGASUSDT"}
UNIT_COST_BP = 12.0       # one round-trip cost unit, in bp of price
COST_MULTS = (1, 2, 3)
MIN_EVENTS = 10           # a cell with fewer usable events is not decided on
EXACT_MAX = 18            # sign-flip test enumerates every assignment up to this many events
DRAWS = 200_000
ALPHA = 0.05
SEED = 368
Z_MDE = 2.8               # z(0.975) + z(0.80): 80% power at the smaller Holm threshold (0.025, one-sided)
BARS_BEFORE, BARS_AFTER = 1, max(HORIZONS)   # bars T-1 .. T+10 must all exist for an event to be usable


def lookup(bars, times):
    """(open, close) arrays for the bar open times `times`; NaN where the bar does not exist. `bars` has t, open, close
    sorted by t."""
    t = bars["t"].to_numpy()
    ix = np.searchsorted(t, times)
    ix_c = np.clip(ix, 0, len(t) - 1)
    found = (ix < len(t)) & (t[ix_c] == times)
    o = np.where(found, bars["open"].to_numpy()[ix_c], np.nan)
    c = np.where(found, bars["close"].to_numpy()[ix_c], np.nan)
    return o, c


def event_row(bars, release_ms):
    """One event's reaction and moves. `usable` is false (and the numbers NaN) unless bars T-1 .. T+10 all exist and
    every price in them is positive."""
    offsets = np.arange(-BARS_BEFORE, BARS_AFTER + 1)
    o, c = lookup(bars, release_ms + offsets * MINUTE_MS)
    pos = {int(k): i for i, k in enumerate(offsets)}
    usable = bool(np.isfinite(o).all() and np.isfinite(c).all() and (o > 0).all() and (c > 0).all())
    row = {"release_ms": int(release_ms), "usable": usable, "r0": math.nan, "late5": math.nan}
    for h in HORIZONS:
        row[f"move{h}"] = math.nan
    if not usable:
        return row
    close = lambda k: c[pos[k]]       # noqa: E731
    row["r0"] = 1e4 * math.log(close(0) / close(-1))
    entry = o[pos[1]]
    for h in HORIZONS:
        row[f"move{h}"] = 1e4 * math.log(close(h) / entry)
    row["late5"] = 1e4 * math.log(close(DECISION_H) / close(1))
    return row


def subset_mask(r0, subset):
    r0 = np.asarray(r0, dtype=float)
    ok = np.isfinite(r0) & (r0 != 0)
    if subset == "neg":
        return ok & (r0 < 0)
    if subset == "pos":
        return ok & (r0 > 0)
    if subset == "all":
        return ok
    raise ValueError(subset)


def continuation(r0, move, subset):
    """sign(r0) * move over the events of the subset that have both numbers."""
    r0, move = np.asarray(r0, dtype=float), np.asarray(move, dtype=float)
    m = subset_mask(r0, subset) & np.isfinite(move)
    return np.sign(r0[m]) * move[m]


def sign_flip_p(x, rng, draws=DRAWS, exact_max=EXACT_MAX):
    """One-sided p that the mean of x is above 0 if each continuation were as likely to go either way: the share of
    sign assignments whose mean is at least the observed mean (every assignment up to `exact_max` events, otherwise
    `draws` random ones with the observed counted once)."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return math.nan
    obs = x.sum()
    tol = 1e-9 * max(1.0, float(np.abs(x).sum()))
    if n <= exact_max:
        bits = (np.arange(2 ** n)[:, None] >> np.arange(n)) & 1
        sums = (2 * bits - 1) @ x
        return float((sums >= obs - tol).mean())
    signs = rng.integers(0, 2, size=(draws, n)) * 2 - 1
    return float((1 + ((signs @ x) >= obs - tol).sum()) / (1 + draws))


def holm(p):
    """Holm-adjusted p-values, in the input order."""
    p = np.asarray(p, dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (len(p) - rank) * p[i]))
        adj[i] = run
    return adj


def summarize(x):
    """n, mean, sd, t and the 80%-power minimum detectable mean of a continuation sample, in bp."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    mean = float(x.mean()) if n else math.nan
    sd = float(x.std(ddof=1)) if n > 1 else math.nan
    t = mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else math.nan
    mde = Z_MDE * sd / math.sqrt(n) if n > 1 else math.nan
    return {"n": n, "mean": mean, "sd": sd, "t": t, "mde80": mde, "hit": float((x > 0).mean()) if n else math.nan}


def verdict(decisions):
    """decisions: one dict per decision cell with n, mean, p_holm. PASS needs n >= MIN_EVENTS, p_holm <= ALPHA and a
    mean above 2 cost units; PARTIAL is the same with only 1 cost unit cleared; INCONCLUSIVE when no cell has
    MIN_EVENTS events; NULL otherwise."""
    live = [d for d in decisions if d["n"] >= MIN_EVENTS]
    if not live:
        return "INCONCLUSIVE", f"no decision cell has {MIN_EVENTS} usable events"
    sig = [d for d in live if d["p_holm"] <= ALPHA]
    if any(d["mean"] > 2 * UNIT_COST_BP for d in sig):
        return "PASS", "a decision cell is significant after Holm and clears 2 cost units"
    if any(d["mean"] > UNIT_COST_BP for d in sig):
        return "PARTIAL", "a decision cell is significant after Holm and clears 1 cost unit but not 2"
    return "NULL", "no decision cell is significant and above cost"
