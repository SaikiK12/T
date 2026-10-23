"""Confidence-sized cross-venue carry (method M266): R275's books with the same pairs, entered and exited by the same
rule (lab.xfund), but each open pair sized by a score instead of one equal slot.

Each day d, after the rule's exits and entries, every open pair gets a score from data up to day d only:

- `equal`: 1 (R275's book; `run` with it reproduces `xfund.replay` exactly);
- `spread`: the pair's funding spread today, annualized over the book's lookback (the rule's own signal);
- `persist`: the share of the last `lookback` days on which that spread was at or above the entry threshold;
- `spread_persist`: spread x persist;
- `inv_vol`: 1 / the standard deviation of the pair's daily price-leg return (long minus short) over the last 30 days;
- `spread_vol`: spread / that standard deviation.

The scores become weights that average 1 over the open pairs, so the book's gross notional equals the equal book's,
and no weight exceeds `cap` (the excess is spread over the others). A pair's weight is traded only when its target moves
by more than `band`; entries trade the target, exits the weight held. Costs are charged on every unit of notional traded,
on both legs. Where a score is undefined for a pair (a leg without enough fresh days), the pair takes the mean of the
defined scores, or 1 when none is.

Net on capital: (gross - cost x legs) / (2 x slots), as in R275.
"""
import math

import numpy as np
import pandas as pd

from . import xfund

SCORES = ("equal", "spread", "persist", "spread_persist", "inv_vol", "spread_vol")
CAP = 3.0
BAND = 0.2
VOL_DAYS = 30
VOL_MIN = 10


def pair_spread(u, p, d, l):
    """The pair's annualized funding spread (short venue minus long venue) over the window ending on day d, or None."""
    a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
    fa, fh = a.window(d, l), h.window(d, l)
    return None if fa is None or fh is None else (fh - fa) * 365.0 / l


def leg_vol(u, p, d, days=VOL_DAYS, min_obs=VOL_MIN):
    """Standard deviation of the pair's daily price-leg return over (d - days, d], on days both legs were fresh."""
    a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
    x = [a.ret(k - 1) - h.ret(k - 1) for k in range(max(d + 1 - days, 1), d + 1)
         if a.fresh[k] and a.fresh[k - 1] and h.fresh[k] and h.fresh[k - 1]]
    return float(np.std(x, ddof=1)) if len(x) >= min_obs else None


def score(u, p, d, book, kind):
    if kind == "equal":
        return 1.0
    l, th = book.lookback, book.threshold
    s = pair_spread(u, p, d, l)
    if kind == "spread":
        return max(s, 0.0) if s is not None else None
    if kind in ("persist", "spread_persist"):
        hist = [pair_spread(u, p, k, l) for k in range(d - l + 1, d + 1)]
        known = [x for x in hist if x is not None]
        if not known:
            return None
        per = sum(x >= th for x in known) / len(known)
        if kind == "persist":
            return per
        return per * max(s, 0.0) if s is not None else None
    v = leg_vol(u, p, d)
    if v is None or v <= 0:
        return None
    if kind == "inv_vol":
        return 1.0 / v
    if kind == "spread_vol":
        return max(s, 0.0) / v if s is not None else None
    raise ValueError(kind)


def weights(scores, cap=CAP):
    """Weights proportional to `scores` that average 1 and stay at or below `cap` (water-filling)."""
    s = np.asarray(scores, np.float64)
    n = len(s)
    if n == 0:
        return s
    if not np.isfinite(s).all() or s.sum() <= 0:
        return np.ones(n)
    w = np.zeros(n)
    free = np.ones(n, bool)
    budget = float(n)
    while True:
        tot = s[free].sum()
        if tot <= 0:
            w[free] = budget / free.sum()
            return w
        w[free] = budget * s[free] / tot
        over = free & (w > cap)
        if not over.any():
            return w
        w[over] = cap
        free &= ~over
        budget = n - cap * (~free).sum()
        if not free.any():
            return w


def run(u, book, w0, kind, cap=CAP, band=BAND):
    """Book over days [w0, nd - 1) sized by `kind`: per day gross, funding, legs (notional traded, both legs), held, and
    the largest weight. `kind` "equal" gives xfund.replay's rows."""
    if kind not in SCORES:
        raise ValueError(kind)
    rows, held = [], {}
    for d in range(w0, u.nd - 1):
        legs = 0.0
        for p, _ in book.exits(u, d):
            legs += 2.0 * held.pop(id(p))
        book.entries(u, d)
        raw = [score(u, p, d, book, kind) for p in book.open]
        known = [x for x in raw if x is not None]
        fill = sum(known) / len(known) if known else 1.0
        target = weights([fill if x is None else x for x in raw], cap)
        for p, t in zip(book.open, target):
            if id(p) not in held:
                legs += 2.0 * t
                held[id(p)] = t
            elif abs(t - held[id(p)]) > band:
                legs += 2.0 * abs(t - held[id(p)])
                held[id(p)] = t
        gross = fund = 0.0
        for p in book.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            f = h.fund_on(d + 1) - a.fund_on(d + 1)
            gross += held[id(p)] * (a.ret(d) - h.ret(d) + f)
            fund += held[id(p)] * f
        rows.append({"day": d, "gross": gross, "funding": fund, "legs": legs, "held": len(book.open),
                     "max_w": max(held.values(), default=0.0)})
    if rows:
        rows[-1]["legs"] += 2.0 * sum(held.values())
    return pd.DataFrame(rows)


net = xfund.net
