"""Full-pipeline null: the whole search reruns on a forward panel shifted in time against the features."""
import numpy as np

from .config import NULL_SHIFT_MARGIN


def null_shifts(n_days: int, n_null: int, seed: int, margin: int = NULL_SHIFT_MARGIN):
    """[0] is the real run; the rest are common circular shifts in [margin, n_days - margin)."""
    choices = np.arange(margin, n_days - margin, dtype=np.int64)
    if n_null > len(choices):
        raise ValueError("n_null exceeds the number of admissible unique shifts")
    rng = np.random.default_rng(seed)
    return [0] + [int(s) for s in rng.choice(choices, size=n_null, replace=False)]


def shift_panel(fwd, shift: int, axis: int = 1):
    """Circularly shift the forward panel along its time axis; features stay put."""
    return np.roll(fwd, -shift, axis=axis)


def search_verdict(real_count: int, null_counts):
    """SIGNAL when the real number of validation survivors beats the 95th percentile of the null counts."""
    q95 = float(np.quantile(np.asarray(null_counts, dtype=float), 0.95))
    return ("SIGNAL" if real_count > q95 else "NOISE"), q95


def familywise_p(t_real: float, null_max_t):
    """Finite-sample corrected share of null maxima at least as large as ``t_real``.

    The plus-one correction prevents a finite null from reporting an impossible
    zero p-value.  Its smallest attainable value is therefore ``1/(B+1)``.
    """
    a = np.asarray(null_max_t, dtype=float)
    if a.size == 0:
        return float("nan")
    return float((1 + np.count_nonzero(a >= t_real)) / (a.size + 1))
