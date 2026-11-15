"""Capacity-optimal sizing: solve for the notional that maximises dollars, not basis points.

Every lane in this lab asks "is mean gross > cost?" at a FIXED size (1x notional, cost 1x/2x/3x).
That treats size as a constant. It is not: measured cost rises with notional while gross per unit
does not. So dollar profit has an interior maximum, and nobody here has solved for it.

    P(n) = n * g - a * n^(1+beta)          dollars per trade, n = notional per leg
    dP/dn = 0  ->  n* = ( g / (a * (1+beta)) )^(1/beta)

with cost(n) = a * n^beta fitted from the measured book walk (R495). At that optimum the cost share
of gross is exactly 1/(1+beta) -- a venue constant, independent of the signal. That identity is the
useful part: it turns "is the edge big enough?" into "what size is this edge worth?".

Three constraints make n* tradable rather than a calculus artifact:
  1. the fit is only valid inside the measured size range (1k..10k);
  2. the shown book must actually contain the notional (depth cap);
  3. the owner's per-book capital cap.

Pure functions; no data loading, no network, no order. A caller owns its gates.
"""
import numpy as np

SIZES_DEFAULT = (1_000, 5_000, 10_000)


def fit_cost_curve(sizes, costs_bp):
    """Fit cost_bp(n) = a_bp * n^beta on the measured points. Returns (a_bp, beta, r2).

    Needs at least two finite, positive points. A venue whose cost does not rise with size gives
    beta near 0, and the caller must then treat size as free rather than pretend there is an optimum.
    """
    s = np.asarray(sizes, dtype=float)
    y = np.asarray(costs_bp, dtype=float)
    ok = np.isfinite(s) & np.isfinite(y) & (s > 0) & (y > 0)
    if ok.sum() < 2:
        raise ValueError("need at least two positive measured points")
    ls, ly = np.log(s[ok]), np.log(y[ok])
    beta, log_a = np.polyfit(ls, ly, 1)
    pred = beta * ls + log_a
    ss_res = float(((ly - pred) ** 2).sum())
    ss_tot = float(((ly - ly.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(np.exp(log_a)), float(beta), r2


def cost_bp(n, a_bp, beta):
    return a_bp * np.asarray(n, dtype=float) ** beta


def optimal_notional(gross, a_bp, beta):
    """Unconstrained n* in dollars. gross is a fraction of notional (0.02 = 2%).

    Returns NaN when there is no interior optimum: non-positive gross, or beta <= 0 (cost flat or
    falling in size, so bigger is always better and the depth cap is the only limit).
    """
    if not np.isfinite(gross) or gross <= 0 or beta <= 0 or a_bp <= 0:
        return float("nan")
    a = a_bp / 1e4
    return float((gross / (a * (1.0 + beta))) ** (1.0 / beta))


def cost_share_at_optimum(beta):
    """The invariant: at n*, cost / gross = 1 / (1 + beta), whatever the signal is."""
    return 1.0 / (1.0 + beta) if beta > 0 else float("nan")


def constrained_notional(gross, a_bp, beta, *, depth_usd, fit_range=SIZES_DEFAULT, capital_cap=None):
    """n* clipped to what can actually be traded, with the reason it was clipped.

    The fit is trusted only inside `fit_range`; beyond it the curve is an extrapolation, not a
    measurement. `depth_usd` is the shown notional within the near band on the side being crossed.
    """
    raw = optimal_notional(gross, a_bp, beta)
    lo, hi = min(fit_range), max(fit_range)
    caps = {"fit_range": hi, "depth": float(depth_usd) if np.isfinite(depth_usd) else hi}
    if capital_cap is not None:
        caps["capital"] = float(capital_cap)
    if not np.isfinite(raw):
        # no interior optimum: take the largest tradable size, since cost never catches gross
        n = min(caps.values())
        return {"n": n, "raw_n": raw, "binding": "no_optimum", "caps": caps}
    n = min(raw, *caps.values())
    binding = "interior" if n == raw else min(caps, key=caps.get)
    return {"n": float(n), "raw_n": raw, "binding": binding, "caps": caps}


def dollars_per_trade(n, gross, a_bp, beta):
    """Net dollars at notional n: n * (gross - cost(n)). Negative when cost exceeds gross."""
    n = float(n)
    return n * (gross - cost_bp(n, a_bp, beta) / 1e4)


def breakeven_notional(gross, a_bp, beta):
    """Largest n with non-negative net: n_be = (gross / a)^(1/beta). Above it the trade loses."""
    if gross <= 0 or beta <= 0 or a_bp <= 0:
        return float("nan")
    return float((gross / (a_bp / 1e4)) ** (1.0 / beta))
