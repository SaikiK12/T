"""The go-real screen: one input to the owner's decision, never an order.

NaN returns remain unscored for compatibility with partial paper records. Infinite
returns are invalid observations: they must not turn a broken calculation into a
positive mean or a false gate pass. When entry-day clusters are supplied, they
must align to the original return vector and are counted only for scored returns.
"""
import numpy as np

from .config import GO_REAL


def go_real(returns, entry_days=None, rules=GO_REAL):
    """returns: scored forward tickets, unlevered fractions. entry_days: optional, to report independent clusters.

    Tickets that share an entry day share the market move, so n_clusters can be far below n. It is reported, not gated
    (the rule is the owner's); see docs/AUDIT.md. NaNs are missing/unscored as
    before; positive or negative infinity blocks the result. If ``entry_days`` is
    supplied it must have one key per original return, including missing slots.
    """
    try:
        raw = np.asarray(returns, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("returns must be a one-dimensional numeric sequence") from exc
    if raw.ndim != 1:
        raise ValueError("returns must be a one-dimensional numeric sequence")

    scored = np.isfinite(raw)
    invalid_n = int(np.isinf(raw).sum())
    r = raw[scored]
    n = int(r.size)

    n_clusters = None
    if entry_days is not None:
        try:
            days = list(entry_days)
        except TypeError as exc:
            raise ValueError("entry_days must be a one-dimensional sequence") from exc
        if len(days) != len(raw):
            raise ValueError("entry_days must align one-for-one with the original returns")
        scored_days = []
        for day, keep in zip(days, scored):
            if not keep:
                continue
            if day is None:
                raise ValueError("entry_days cannot be missing for a scored return")
            try:
                if bool(day != day):  # catches float NaN and datetime NaT without importing pandas
                    raise ValueError("entry_days cannot be missing for a scored return")
                hash(day)
            except (TypeError, ValueError) as exc:
                raise ValueError("entry_days must contain nonmissing, hashable keys") from exc
            scored_days.append(day)
        n_clusters = len(set(scored_days))

    checks = {
        "finite_returns": invalid_n == 0,
        "enough_scored": n >= rules["min_scored"],
        "mean_positive": n > 0 and float(r.mean()) > rules["min_mean"],
        "hit_rate": n > 0 and float((r > 0).mean()) >= rules["min_hit"],
        "no_tail_event": n > 0 and float(r.min()) >= rules["worst_event"],
    }
    return {
        "n": n,
        "mean": float(r.mean()) if n else float("nan"),
        "hit": float((r > 0).mean()) if n else float("nan"),
        "worst": float(r.min()) if n else float("nan"),
        "invalid_n": invalid_n,
        "n_clusters": n_clusters,
        "checks": checks,
        "pass": all(checks.values()),
    }
