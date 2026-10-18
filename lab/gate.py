"""The go-real gate: the only door from paper to a small real stake. The owner places any real order, never code."""
import numpy as np

from .config import GO_REAL


def go_real(returns, entry_days=None, rules=GO_REAL):
    """returns: scored forward tickets, unlevered fractions. entry_days: optional, to report independent clusters.

    Tickets that share an entry day share the market move, so n_clusters can be far below n. It is reported, not gated
    (the rule is the owner's); see docs/AUDIT.md.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = int(r.size)
    checks = {
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
        "n_clusters": len(set(entry_days)) if entry_days is not None else None,
        "checks": checks,
        "pass": all(checks.values()),
    }
