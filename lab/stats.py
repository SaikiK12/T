"""Reference statistics. Check parity against a lane's own implementation before replacing it."""
import numpy as np


def newey_west_t(x, lag: int):
    """t-stat of the mean of a calendar-day series.

    x[d] is the net return of the day-d cell mean, NaN when the cell had no observation that day.
    The mean runs over observed days; gaps count as zero deviation in the autocovariances, which use calendar
    lags, with Bartlett weights 1 - l/(lag+1). Returns (n_observed, mean, t); t is NaN when it is undefined.
    """
    x = np.asarray(x, dtype=float)
    ok = ~np.isnan(x)
    n = int(ok.sum())
    if n < 2:
        return n, float("nan"), float("nan")
    mu = float(x[ok].mean())
    z = np.where(ok, x - mu, 0.0)
    s = float(z @ z)
    for l in range(1, min(lag, len(z) - 1) + 1):
        s += 2.0 * (1.0 - l / (lag + 1.0)) * float(z[l:] @ z[:-l])
    if s <= n * (1e-12 * float(np.abs(x[ok]).max())) ** 2:  # constant series: only float noise is left
        return n, mu, float("nan")
    return n, mu, mu / float(np.sqrt(s) / n)
