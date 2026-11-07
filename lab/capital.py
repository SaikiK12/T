"""Capital accounting for segregated, unrebalanced spot and carry sleeves.

This module performs no data access, strategy selection or market simulation.
"""
from __future__ import annotations

import numpy as np


def _scalar(value, name):
    try:
        if np.ndim(value) != 0 or np.iscomplexobj(value):
            raise ValueError
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite scalar") from exc
    if not np.isfinite(result):
        raise ValueError(f"{name} must be a finite scalar")
    return result


def segregated(spot_net, spot_gross, spot_cost, carry_gross, carry_funding, carry_cost,
               spot_weight=0.5, carry_weight=0.5, carry_entry_cost=0.0):
    """Combine two accounts without rebalancing, top-ups or compounding carry.

    All six input arrays must be finite, nonempty, one dimensional and equally
    sized. Spot inputs are returns on previous spot NAV, with
    ``spot_net = spot_gross - spot_cost`` (absolute tolerance 1e-9). Carry inputs
    are daily PnL per unit of INITIAL carry capital. ``carry_gross`` ALREADY
    includes ``carry_funding``; funding is returned as an informational component
    and never added a second time. Costs and the inherited-position entry charge
    must be nonnegative. The entry charge is paid on the first day.

    Each sleeve starts at one. Spot compounds its supplied net returns. Carry
    equity is one plus cumulative gross minus costs, including the entry charge.
    Weights are fractions of initial portfolio capital, are nonnegative and sum
    to at most one. The remainder stays in cash at zero interest. Both source
    accounts must remain strictly solvent, even if given zero allocation; one
    sleeve cannot rescue another. A carry daily loss exceeding initial capital
    is allowed if accumulated profits keep that sleeve solvent.

    Returned arrays omit the initial observation of one. ``equity`` is portfolio
    end-of-day NAV; ``spot_equity`` and ``carry_equity`` are the unweighted source
    accounts. ``dollar_net``, ``dollar_gross``, ``dollar_funding`` and
    ``dollar_cost`` are weighted daily contributions per INITIAL portfolio
    capital. Only ``net`` divides dollar PnL by previous portfolio NAV. The
    gross-minus-cost identity has the same tolerance as the supplied spot
    identity, scaled by its previous NAV and weight; other accounting identities
    differ only by floating-point rounding. No input is mutated.
    """
    names = ("spot_net", "spot_gross", "spot_cost", "carry_gross", "carry_funding", "carry_cost")
    values = (spot_net, spot_gross, spot_cost, carry_gross, carry_funding, carry_cost)
    arrays = []
    for name, value in zip(names, values):
        try:
            if np.iscomplexobj(value):
                raise ValueError
            array = np.asarray(value, dtype=np.float64)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{name} must be a finite one-dimensional array") from exc
        if array.ndim != 1 or array.size == 0 or not np.isfinite(array).all():
            raise ValueError(f"{name} must be a finite nonempty one-dimensional array")
        arrays.append(array)
    if any(array.shape != arrays[0].shape for array in arrays[1:]):
        raise ValueError("all sleeve arrays must have the same shape")
    sn, sg, sc, cg, cf, cc = arrays
    sw = _scalar(spot_weight, "spot_weight")
    cw = _scalar(carry_weight, "carry_weight")
    entry = _scalar(carry_entry_cost, "carry_entry_cost")
    if sw < 0 or cw < 0 or sw + cw > 1:
        raise ValueError("weights must be nonnegative and sum to at most one")
    if entry < 0 or (sc < 0).any() or (cc < 0).any():
        raise ValueError("costs must be nonnegative")
    if (sn <= -1).any():
        raise ValueError("spot_net must be strictly greater than -1")
    if not np.allclose(sg - sc, sn, rtol=0, atol=1e-9):
        raise ValueError("spot_gross minus spot_cost must equal spot_net within 1e-9")

    # Carry fee inputs may be a view into a saved result. Keep entry charging local.
    cc = cc.copy()
    cc[0] += entry
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        spot_equity = np.cumprod(1 + sn)
        spot_previous = np.concatenate(([1.0], spot_equity[:-1]))
        carry_net = cg - cc
        carry_equity = 1 + np.cumsum(carry_net)
        equity = sw * spot_equity + cw * carry_equity + (1 - sw - cw)
        dollar_net = sw * spot_previous * sn + cw * carry_net
        dollar_gross = sw * spot_previous * sg + cw * cg
        dollar_cost = sw * spot_previous * sc + cw * cc
        dollar_funding = cw * cf
    for name, value in (("spot", spot_equity), ("carry", carry_equity), ("portfolio", equity)):
        if not np.isfinite(value).all() or (value <= 0).any():
            raise ValueError(f"{name} NAV must remain finite and strictly positive")
    previous = np.concatenate(([1.0], equity[:-1]))
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        net = dollar_net / previous
    result = {"equity": equity, "net": net, "dollar_net": dollar_net,
              "dollar_gross": dollar_gross, "dollar_funding": dollar_funding,
              "dollar_cost": dollar_cost, "spot_equity": spot_equity, "carry_equity": carry_equity}
    if any(not np.isfinite(value).all() for value in result.values()):
        raise ValueError("accounting produced a non-finite result")
    return result
