"""Margin arithmetic for a two-venue hedged book: how far the market can move before one venue's cross-margin account
is liquidated, and how much collateral to move between venues to restore the buffer. Pure functions; no venue call,
no order. Used by scripts/stress_dhl.py and the stake plan.

A venue account holds legs (signed notional: + long, - short) at maintenance rates mm (fraction of notional).
For a uniform market move m (fraction, the same for every coin on that venue):
  equity(m) = E + sum(N_i) * m
  maintenance(m) = sum(|N_i| * (1 + m) * mm_i)
The account is liquidated when equity(m) <= maintenance(m). Legs on one venue are long or short together in a
design-gap book (long the floorless venue, short the floor venue), so the adverse direction is known.
"""
import math


def liq_move(equity, legs):
    """Smallest adverse uniform move (fraction, > 0) that liquidates the account; math.inf if none.
    legs: [(signed notional, mm)]. Adverse means down for a net-long account and up for a net-short one."""
    net = sum(n for n, _ in legs)
    gross_mm = sum(abs(n) * mm for n, mm in legs)
    if equity <= gross_mm:
        return 0.0
    if net == 0:
        return math.inf
    sign = -1.0 if net > 0 else 1.0
    # equity + net*m = gross_mm*(1+m), with m = sign*x, x > 0  ->  x = (equity - gross_mm) / (|net| + sign*gross_mm)
    den = abs(net) + sign * gross_mm
    return (equity - gross_mm) / den if den > 0 else math.inf


def split(capital, notional, mm_long, mm_short, buffer_long=1.0):
    """Equities (long venue, short venue) that equalise both venues' liquidation moves for a pair book of `notional`
    per leg. buffer_long scales the long venue's share (1 = equal moves)."""
    lo, hi = 0.0, capital
    for _ in range(100):
        e = (lo + hi) / 2
        a = liq_move(e, [(notional, mm_long)]) * buffer_long
        b = liq_move(capital - e, [(-notional, mm_short)])
        lo, hi = (e, hi) if a < b else (lo, e)
    return e, capital - e


def rebalance(e_long, e_short, notional, mm_long, mm_short, target_move):
    """Collateral to transfer (positive: from the short venue to the long venue) so that both venues are at least
    target_move from liquidation, or None if the total equity cannot reach it."""
    need_long = notional * mm_long + notional * (1 - mm_long) * target_move     # long: equity >= N*mm*(1-x) + N*x
    need_short = notional * mm_short + notional * (1 + mm_short) * target_move   # short: equity >= N*mm*(1+x) + N*x
    if e_long + e_short < need_long + need_short:
        return None
    if e_long < need_long:
        return need_long - e_long
    if e_short < need_short:
        return -(need_short - e_short)
    return 0.0
