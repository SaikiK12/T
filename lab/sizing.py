"""Leverage for a small market-neutral carry book: risk-constrained Kelly, capped by each leg's liquidation risk.

Sources: research/intake/library_digest_20261119.md.
- Busseti, Ryu & Boyd (2016), risk-constrained Kelly.
  - Maximise E log(1 + L r) subject to E[(1 + L r)^(-lam)] <= 1, with lam = ln(beta) / ln(alpha).
  - This bounds P(wealth ever falls below alpha) by beta.
- Frazzini-Pedersen / Roncalli: per-venue margin.
  - A two-venue pair holds half the capital on each venue, so each leg runs at 2L.
  - A leg is liquidated when an adverse move g exceeds 1/(2L) - m (m: the maintenance margin).
  - So L <= 1 / (2 (g + m)).

The returns fed in should be shrunk (scale_mean) before sizing: in-sample means overstate the edge
(research/intake/large_scale_inference_20261119.md). Fractional Kelly (`fraction`) is a further haircut, by choice.
Nothing here places an order; it is an input to the owner's decision through lab.gate.go_real().
"""
import math

import numpy as np


def rck_lambda(alpha, beta):
    """lam with P(min wealth < alpha) < beta; alpha and beta in (0, 1)."""
    return math.log(beta) / math.log(alpha)


def scale_mean(r, factor):
    """The returns with their mean scaled by `factor` (0..1) and their deviations kept: a shrunk edge."""
    r = np.asarray(r, float)
    return r - (1 - factor) * r.mean()


def rck_leverage(r, alpha=0.8, beta=0.05, grid=None):
    """(leverage, expected log growth per period) maximising mean log(1 + L r) under the risk constraint, over a grid.
    Returns (0.0, 0.0) when no positive leverage both grows and meets the constraint."""
    r = np.asarray(r, float)
    lam = rck_lambda(alpha, beta)
    grid = np.linspace(0.0, 20.0, 2001) if grid is None else np.asarray(grid, float)
    best = (0.0, 0.0)
    for L in grid:
        w = 1.0 + L * r
        if (w <= 0).any():
            break
        g = float(np.mean(np.log(w)))
        if float(np.mean(w ** (-lam))) <= 1.0 and g > best[1]:
            best = (float(L), g)
    return best


def liquidation_cap(adverse_move, maintenance=0.03, legs_share=0.5):
    """Book leverage L at which a leg survives an adverse move of `adverse_move` (fraction of price).
    Each venue holds `legs_share` of the capital, so the leg's leverage is L / legs_share."""
    return legs_share / (adverse_move + maintenance)


def size(r, adverse_move, shrink=0.5, fraction=0.5, alpha=0.8, beta=0.05, maintenance=0.03):
    """The leverage to use: fraction x min(risk-constrained Kelly on the shrunk returns, liquidation cap)."""
    lev, growth = rck_leverage(scale_mean(r, shrink), alpha, beta)
    cap = liquidation_cap(adverse_move, maintenance)
    use = fraction * min(lev, cap)
    return {"rck_leverage": lev, "rck_log_growth": growth, "liquidation_cap": cap, "leverage": use,
            "binding": "liquidation" if cap < lev else "risk-constrained Kelly", "lambda": rck_lambda(alpha, beta),
            "shrink": shrink, "fraction": fraction}
