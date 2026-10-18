"""Full-pipeline null: the whole search reruns on a forward panel shifted in time against the features."""
import numpy as np

from .config import NULL_SHIFT_MARGIN


def null_shifts(n_days: int, n_null: int, seed: int, margin: int = NULL_SHIFT_MARGIN):
    """[0] is the real run; the rest are common circular shifts in [margin, n_days - margin)."""
    rng = np.random.default_rng(seed)
    return [0] + [int(s) for s in rng.integers(margin, n_days - margin, n_null)]


def shift_panel(fwd, shift: int, axis: int = 1):
    """Circularly shift the forward panel along its time axis; features stay put."""
    return np.roll(fwd, -shift, axis=axis)


def search_verdict(real_count: int, null_counts):
    """SIGNAL when the real number of validation survivors beats the 95th percentile of the null counts."""
    q95 = float(np.quantile(np.asarray(null_counts, dtype=float), 0.95))
    return ("SIGNAL" if real_count > q95 else "NOISE"), q95


def familywise_p(t_real: float, null_max_t):
    """Share of null replicas whose best validation t is at least the survivor's. Resolution is 1/len(null_max_t)."""
    return float((np.asarray(null_max_t, dtype=float) >= t_real).mean())
