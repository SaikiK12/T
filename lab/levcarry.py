"""Leverage and liquidation on cross-venue carry books (method M265): R275's rule, run with lab.xfund, where each leg
sits on its venue at leverage L and can be liquidated by an intraday move.

A pair is two legs of equal notional (one unit each, as in lab.xfund). At leverage L each leg is backed by 1/L of
margin on its own venue. Each day's high and low decide whether a leg's margin survives the day:

- `iso_hold`: isolated margin, never topped up. A leg's equity is 1/L plus its returns since entry.
- `iso_daily`: isolated margin, reset to 1/L at every 00:00 (profits moved between venues once a day).
- `cross_daily`: one cross-margin account per venue, reset at every 00:00 to 1/L per leg it holds. It is liquidated
  when the sum of its legs' worst moves of the day, all assumed to happen at the same moment, reaches its equity. That
  assumption is a bound: it overstates the risk.

A leg is liquidated when its equity at the start of the day, minus the funding it pays that day, minus its worst adverse
move of the day (long: down to the low, short: up to the high, from the day's opening close) is at or below the
maintenance margin `mm`. Charging the whole day's funding before the extreme is conservative. In `iso_hold` a leg's
equity carries its price returns and its funding since entry. A liquidated leg loses all of its equity that day and
earns no funding. The other leg of its pair is closed at that day's close, and the book frees the slot: the pair exits
(two legs of cost), and the rule may enter it again later.

A venue's day range comes from its bars that end in the day. Where a leg has no range for a day, its adverse move is
the close-to-close move against it, a lower bound, and the day is counted in the `unknown` column, so coverage is
reported next to every result.

Net on capital at leverage L: L x (gross - cost x legs) / (2 x slots), because the book's capital is 2 x slots / L
units of margin.
"""
import math

import numpy as np
import pandas as pd

from . import xfund

DAY, H = xfund.DAY, xfund.H
POLICIES = ("iso_hold", "iso_daily", "cross_daily")


def daily_range(t, high, low, bar_ms, t0, nd):
    """(high, low) per day d over the bars that end in (day d - 1, day d], NaN where none traded."""
    t, high, low = (np.asarray(x, np.float64) for x in (t, high, low))
    ok = np.isfinite(t) & np.isfinite(high) & np.isfinite(low) & (low > 0)
    ti = np.where(ok, t, 0).astype(np.int64)
    ok &= ti >= t0
    d = (ti + bar_ms - t0 + DAY - 1) // DAY
    ok &= (d >= 0) & (d < nd)
    hi = np.full(nd, -np.inf)
    lo = np.full(nd, np.inf)
    np.maximum.at(hi, d[ok], high[ok])
    np.minimum.at(lo, d[ok], low[ok])
    hi[~np.isfinite(hi)] = np.nan
    lo[~np.isfinite(lo)] = np.nan
    return hi, lo


def adverse(series, rng, side, d):
    """(worst move against the leg over day d -> d + 1 from day d's close, whether the day's range was known).

    With the range unknown (rng None or NaN that day), the move is the close-to-close move against the leg: a lower
    bound. With it known, the range includes the closing bar, so the close-to-close move never exceeds it."""
    c, c1 = series.close[d], series.close[d + 1]
    if not (math.isfinite(c) and c > 0):
        return 0.0, False
    floor = max(0.0, -side * (c1 / c - 1.0)) if math.isfinite(c1) and c1 > 0 else 0.0
    if rng is None:
        return floor, False
    x = rng[1][d + 1] if side > 0 else rng[0][d + 1]
    if not math.isfinite(x):
        return floor, False
    return max(floor, 1.0 - x / c if side > 0 else x / c - 1.0), True


def run(u, ranges, book, w0, lev, policy, mm=0.01, moves=None):
    """R275's book over days [w0, nd - 1) at leverage `lev` under `policy`.

    ranges[c][v] = (high, low) arrays (or None), aligned with u.series. Returns (days, events): days has per-day gross,
    legs and held, in units of one leg's notional (net on capital via `net`), plus `exposed` (legs held over the day)
    and `unknown` (those of them whose range was unknown); events lists each liquidated leg, with `adverse` its move
    plus the funding it paid that day.
    If `moves` is a list, each held pair-day appends its legs' worst adverse moves (long, short).
    """
    if policy not in POLICIES:
        raise ValueError(policy)
    rows, events, cum = [], [], {}
    pending_legs = 0.0
    for d in range(w0, u.nd - 1):
        legs = pending_legs
        pending_legs = 0.0
        for p, _ in book.exits(u, d):
            legs += 2.0
            cum.pop(id(p), None)
        for p in book.entries(u, d):
            legs += 2.0
            cum[id(p)] = [0.0, 0.0]                    # long, short returns since entry (iso_hold)
        # the interval d -> d + 1, leg by leg
        info, unknown = [], 0
        for p in book.open:
            a, h = u.series[p.coin][p.lo], u.series[p.coin][p.hi]
            ra, rh = a.ret(d), h.ret(d)
            fa, fh = a.fund_on(d + 1), h.fund_on(d + 1)
            wa, ka = adverse(a, ranges[p.coin][p.lo], +1, d)
            wh, kh = adverse(h, ranges[p.coin][p.hi], -1, d)
            unknown += (not ka) + (not kh)
            # the risk a leg's margin bears that day: its adverse move plus the funding it pays
            info.append((p, ra, -rh, -fa, fh, wa + max(0.0, fa), wh + max(0.0, -fh)))
            if moves is not None:
                moves.append((wa, wh))
        exposed = 2 * len(info)
        dead = set()                                   # (id(pos), leg) with leg 0 = long, 1 = short
        if policy == "cross_daily":
            for v in sorted({x for p in book.open for x in (p.lo, p.hi)}):
                mine = [(p, 0, wa) for p, _, _, _, _, wa, _ in info if p.lo == v] + \
                       [(p, 1, wh) for p, _, _, _, _, _, wh in info if p.hi == v]
                n = len(mine)
                if n and n / lev - sum(w for _, _, w in mine) <= mm * n:
                    dead |= {(id(p), k) for p, k, _ in mine}
                    events += [{"day": d + 1, "coin": u.keys[p.coin], "venue": u.names[v],
                                "leg": ("long", "short")[k], "adverse": w, "account": True} for p, k, w in mine]
        else:
            for p, _, _, _, _, wa, wh in info:
                eq = [1.0 / lev, 1.0 / lev]
                if policy == "iso_hold":
                    eq = [1.0 / lev + cum[id(p)][0], 1.0 / lev + cum[id(p)][1]]
                for k, w in ((0, wa), (1, wh)):
                    if eq[k] - w <= mm:
                        dead.add((id(p), k))
                        events.append({"day": d + 1, "coin": u.keys[p.coin], "venue": u.names[(p.lo, p.hi)[k]],
                                       "leg": ("long", "short")[k], "adverse": w, "account": False})
        gross = fund = 0.0
        gone = []
        for p, pl, ps, fl, fs, _, _ in info:
            eq = [1.0 / lev + cum[id(p)][0], 1.0 / lev + cum[id(p)][1]] if policy == "iso_hold" else \
                [1.0 / lev, 1.0 / lev]
            out = [(id(p), 0) in dead, (id(p), 1) in dead]
            leg = [-eq[0] if out[0] else pl + fl, -eq[1] if out[1] else ps + fs]
            gross += leg[0] + leg[1]
            fund += (0.0 if out[0] else fl) + (0.0 if out[1] else fs)
            if any(out):
                gone.append(p)
            else:
                cum[id(p)][0] += pl + fl                # iso_hold equity: price and funding since entry
                cum[id(p)][1] += ps + fs
        if gone:                                       # the pair is closed at day d + 1: its exit legs book then
            book.open = [p for p in book.open if p not in gone]
            for p in gone:
                cum.pop(id(p), None)
            pending_legs = 2.0 * len(gone)
        rows.append({"day": d, "gross": gross, "funding": fund, "legs": legs, "held": len(book.open),
                     "exposed": exposed, "unknown": unknown})
    if rows:
        rows[-1]["legs"] += 2.0 * len(book.open) + pending_legs
    return pd.DataFrame(rows), events


def net(days, slots, cost, lev):
    return lev * (days.gross - cost * days.legs) / (2.0 * slots)
