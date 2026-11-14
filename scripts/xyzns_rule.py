"""R464 xyzns_wknd_v1 rule, frozen in experiments/xyzns_wknd_v1/PREREG.md: R462's weekend fade moved from trade.xyz
US-stock perps to its US equity-index, commodity and FX perps. These markets have no external price from the Friday
close of their reference (17:00 New York, Brent 18:00) to the Sunday reopen (18:00, FX 17:00). In between the oracle
is trade.xyz's internal 30-minute EMA of the perp's own book. Does the perp's weekend move overshoot, so that fading
it pays once the reference reopens?

Pure functions over hourly candles (labelled by open time, epoch ms) and hourly funding. scripts/run_xyzns.py feeds it.
Prices, funding, the eligibility of a weekend and the cost unit reuse R462's frozen module (scripts/xyzwknd_rule.py).

One market-weekend: F a NYSE trading Friday (not an early close) whose next trading day is the calendar Monday
F + 3 (R462's rule; it also drops every trade.xyz futures-holiday weekend in the sample). All times New York:
- R   Friday close of the market's reference (`close_et` in universe.csv), the last external print
- O   Sunday reopen of the reference (`reopen_et`)
- E   O - 1 h, entry
- X1  O + 2 h
- X2  Monday 10:00 (diagnostic)
- P(T), W, s, c_k, f_k and g_k exactly as in R462: W = 1e4 ln(P(E)/P(R)), s = -sign(W), c_k = s * 1e4 ln(P(X_k)/P(E)),
  f_k = -s * 1e4 * (hourly funding settled in (E, X_k]), g_k = c_k + f_k
"""
from datetime import time, timedelta

import numpy as np

import xyzwknd_rule as base

HOUR_MS = base.HOUR_MS
CLASSES = ("index", "metal", "energy", "fx")
GROUPS = ("all",) + CLASSES
THETAS = (0, 25, 50, 100)
EXITS = ("x1", "x2")
DECISIONS = (("all", 25, "x1"), ("all", 50, "x1"))
COST_MULTS = (1, 2, 3)
MIN_A, MIN_WEEKENDS_A = 60, 10
MIN_B, MIN_WEEKENDS_B = 20, 4
ALPHA = 0.05
SEED = 464


def hm(s):
    h, m = s.split(":")
    return time(int(h), int(m))


def instants(friday, close_et, reopen_et):
    """The weekend dict of one market (close and reopen as 'HH:MM' New York), or None when R462's rule drops it."""
    if base.weekend(friday) is None:
        return None
    o = base.ms(friday + timedelta(days=2), hm(reopen_et))
    return {"F": friday.isoformat(), "R": base.ms(friday, hm(close_et)), "O": o, "E": o - HOUR_MS,
            "X1": o + 2 * HOUR_MS, "X2": base.ms(friday + timedelta(days=3), time(10, 0))}


def friday_dates(first, last):
    out, d = [], first + timedelta(days=(4 - first.weekday()) % 7)
    while d <= last:
        out.append(d)
        d += timedelta(days=7)
    return out


def event_row(t_open, close, f_time, f_rate, w):
    """R462's event row (W, s, c, f, g for X1 and X2) on this lane's instants."""
    return base.event_row(t_open, close, f_time, f_rate, w)


def unit_cost(growth_enabled):
    """Round trip in bp: two taker fees (0.9 bp in growth mode, else 9 bp) plus 4 bp of slippage (R462's unit)."""
    return base.unit_cost(growth_enabled)


def verdict(cells):
    """cells: dicts with n_a, wk_a, mean_a, unit_a, p_holm, n_b, wk_b, mean_b, unit_b, in DECISIONS order."""
    states = []
    for c in cells:
        side = np.sign(c["mean_a"]) if np.isfinite(c["mean_a"]) else 0
        same_b = (c["n_b"] >= MIN_B and c["wk_b"] >= MIN_WEEKENDS_B and side != 0
                  and np.sign(c["mean_b"]) == side)
        if c["n_a"] < MIN_A or c["wk_a"] < MIN_WEEKENDS_A:
            states.append("INCONCLUSIVE")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > 2 * c["unit_a"] and same_b \
                and abs(c["mean_b"]) > c["unit_b"]:
            states.append("PASS")
        elif c["p_holm"] <= ALPHA and abs(c["mean_a"]) > c["unit_a"] and same_b:
            states.append("PARTIAL")
        else:
            states.append("NULL")
    rank = {"PASS": 3, "PARTIAL": 2, "NULL": 1, "INCONCLUSIVE": 0}
    best = max(states, key=lambda s: rank[s]) if states else "INCONCLUSIVE"
    text = "; ".join(f"{g} theta {th} {x}: {st}" for (g, th, x), st in zip(DECISIONS, states))
    return best, text
