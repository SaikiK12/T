"""Bounded evaluation API for future registered lanes; legacy APIs stay intact.

The position clock, forced exits and paid costs are those of lab.engine and
lab.slices. No data loader, search, decision rule or reserved-sample permission
is added here. Cost reuse is valid only for these fixed, cost-independent books.
"""
import numpy as np

from . import engine, slices


def rule_window(bins, ret, elig, cmat, rules, t0, t1, *, slots=10, cmult=1.0, index=None, dense=False):
    """Return [R, t1-t0, 3], with the same zero initial state as run_rules(t0,t1).

    Inputs are views of the requested interval; output allocation does not scale
    with unread hours outside it. The caller still owns sample-read permission.
    """
    if not isinstance(t0, int) or not isinstance(t1, int) or not 0 <= t0 < t1 <= ret.shape[0]:
        raise ValueError("invalid half-open evaluation interval")
    if not rules:
        return np.empty((0, t1 - t0, 3), np.float32)
    short_index = None if index is None else (index[0][t0:t1], index[1][t0:t1])
    return engine.run_rules(bins[:, t0:t1], ret[t0:t1], elig[t0:t1], cmat[t0:t1], rules,
                            0, t1 - t0, slots, cmult, index=short_index, dense=dense)


def rule_days(universe, bins, rules, t0, t1, *, slots=10, cmult=1.0, batch=128, allow_holdout=False):
    """Future-lane daily API with the existing final-price holdout boundary guard."""
    boundary = universe.holdout_row
    if not allow_holdout and (t1 > boundary or (t1 == boundary and boundary < universe.p.T)):
        raise PermissionError("final return reaches a holdout price; register permission first")
    if t0 % 24 or t1 % 24 or batch < 1:
        raise ValueError("daily boundaries and a positive batch size are required")
    days = (t1 - t0) // 24
    if days < 1:
        raise ValueError("empty/reversed daily interval")
    out = tuple(np.zeros((len(rules), days), np.float32) for _ in range(3))
    for start in range(0, len(rules), batch):
        window = rule_window(bins, universe.ret, universe.elig, universe.cmat,
                             rules[start:start + batch], t0, t1, slots=slots, cmult=cmult, index=universe.index)
        segment = window.reshape(len(window), days, 24, 3)
        out[0][start:start + batch] = segment[..., 0].sum(axis=2)
        out[1][start:start + batch] = segment[..., 1].sum(axis=2)
        out[2][start:start + batch] = segment[..., 2].mean(axis=2)
    return out


def fixed_book_costs(parts, ret, elig, cmat, *, hold, unit, t0, t1, hedge=True, missing="raise"):
    """Reuse positions for fixed slices at 1x/2x/3x, without rounding away net.

    Each cost run still calls the original accounting kernel: reusing gross by
    subtraction after float32 aggregation could change boundary decisions.
    Not valid for cost-dependent fills, sizing, liquidation or signal selection.
    """
    positions = sum(slices.positions(ind, hold, t0, t1, unit, side) for ind, side in parts)
    return {multiple: slices.run(positions, ret, elig, cmat, t0, t1, hedge=hedge,
                                 cmult=multiple, missing=missing) for multiple in (1.0, 2.0, 3.0)}
