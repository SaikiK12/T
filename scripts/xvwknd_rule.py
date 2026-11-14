"""R466 xvwknd_v1 rule, frozen in experiments/xvwknd_v1/PREREG.md: the same US stock trades as a perp on trade.xyz
(Hyperliquid HIP-3) and on Lighter. Over the weekend both venues price it internally, each from its own order book.
On Sunday evening their prices can differ. Both return to an external price from the Blue Ocean overnight session
(Sunday 20:00 New York), so the gap should close. Does buying the cheaper venue and selling the dearer one at Sunday
19:00 pay after both venues' costs?

Pure functions over hourly candles (labelled by open time, epoch ms) and hourly funding. scripts/run_xvwknd.py feeds
it. Weekends and instants are R462's (scripts/xyzwknd_rule.weekend): E Sunday 19:00, X1 Sunday 22:00, X2 Monday 10:00
New York.

- Q(T)  a fresh trade price: the close of the candle that opens at T - 1 h, when that candle has volume > 0 and a
        positive close; nan otherwise. Both venues must have one.
- G(T)  1e4 ln(Q_xyz(T) / Q_lighter(T)), the gap in bp (+ when xyz is dearer)
- d     sign(G(E)): d = +1 sells xyz and buys Lighter; d = -1 buys xyz and sells Lighter; G(E) = 0 is dropped
- c_k   d * (G(E) - G(X_k)), the price return of the pair in bp (the gap's closure)
- f_k   d * 1e4 * (F_xyz - F_lighter), with F the sum of hourly funding rates (signed + when longs pay) settled in
        (E, X_k]: the funding the pair receives (+) or pays (-)
- g_k = c_k + f_k, the pair's return before trading costs, in bp of one leg's notional
- G_prev  G(E - 1 h), reported only: a gap made of last-trade bounce would not persist from one hour to the next
"""
import math

import numpy as np

import xyzwknd_rule as base  # noqa: F401  (R462's frozen weekends and instants)

HOUR_MS = 3_600_000
THETAS = (0, 10, 25, 50, 100)
EXITS = ("x1", "x2")
SLIPPAGE_BP = 4.0                 # per venue, round trip (R462's assumption)
LIGHTER_TAKER_BP = 0.0            # Lighter Standard account (orderBookDetails, 2026-11-11)


def fresh_price(t_open, close, volume, t):
    """Close of the candle that opens exactly at t - 1 h, if it traded; nan otherwise."""
    ix = int(np.searchsorted(t_open, t - HOUR_MS, side="left"))
    if ix < len(t_open) and t_open[ix] == t - HOUR_MS and volume[ix] > 0 and close[ix] > 0:
        return float(close[ix])
    return math.nan


def funding_sum(f_time, f_rate, start, end):
    """Sum of hourly funding rates settled in (start, end]."""
    lo = int(np.searchsorted(f_time, start, side="right"))
    hi = int(np.searchsorted(f_time, end, side="right"))
    return float(np.sum(f_rate[lo:hi]))


def gap(xyz, lt, t):
    """G(t) in bp from two (t_open, close, volume) triples; nan when either venue has no fresh trade."""
    a, b = fresh_price(*xyz, t), fresh_price(*lt, t)
    if a > 0 and b > 0:
        return 1e4 * math.log(a / b)
    return math.nan


def event_row(xyz, lt, xyz_f, lt_f, w):
    """The pair trade for one market and one weekend dict (R462's keys E, X1, X2).
    xyz, lt: (t_open, close, volume) arrays; xyz_f, lt_f: (f_time, f_rate) arrays."""
    row = {"G": math.nan, "d": 0, "G_prev": math.nan}
    for k in EXITS:
        row.update({f"G_{k}": math.nan, f"c_{k}": math.nan, f"f_{k}": math.nan, f"g_{k}": math.nan})
    g_e = gap(xyz, lt, w["E"])
    if not np.isfinite(g_e) or g_e == 0:
        return row
    d = 1 if g_e > 0 else -1
    row.update(G=g_e, d=d, G_prev=gap(xyz, lt, w["E"] - HOUR_MS))
    for k in EXITS:
        g_x = gap(xyz, lt, w[k.upper()])
        if np.isfinite(g_x):
            c = d * (g_e - g_x)
            f = d * 1e4 * (funding_sum(*xyz_f, w["E"], w[k.upper()]) - funding_sum(*lt_f, w["E"], w[k.upper()]))
            row.update({f"G_{k}": g_x, f"c_{k}": c, f"f_{k}": f, f"g_{k}": c + f})
    return row


def unit_cost(xyz_growth):
    """Round-trip cost unit of the pair in bp: two xyz taker fees, two Lighter taker fees and 4 bp of slippage on
    each venue."""
    xyz_fee = base.GROWTH_TAKER_BP if xyz_growth else base.STANDARD_TAKER_BP
    return 2 * xyz_fee + 2 * LIGHTER_TAKER_BP + 2 * SLIPPAGE_BP
