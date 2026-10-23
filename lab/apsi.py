"""A project-specific volatility/cost diagnostic for the MEXC alt-perp universe.

APSI is the *Altcoin Perpetual Stress Index*. It is not an implied-volatility index
and it is not a trade signal. At an hourly decision origin t, let r_s be the vector
of the most recent 168 completed hourly log returns for a point-in-time basket, with
exponentially decaying weights a_j proportional to 2**(-j / 72), where j=0 is the
newest return. The weighted covariance is Sigma_t. For normalized basket weights w_t,

    RVhat24_t = 24 * w_t' Sigma_t w_t
    sigma24_t = sqrt(RVhat24_t)
    APSI_t    = 100 * sigma24_t / median(sigma24_{t-24}, ..., sigma24_{t-720})
    FBR_i,t  = cost_rt_i,t / sigma24_i,t

The 24-hour forecast assumes the recent hourly covariance persists for one day; its
target is the sum of the next 24 squared hourly basket returns (integrated variance),
not the variance of a single compounded 24-hour return.
APSI=100 means the basket's forecast one-day standard deviation equals its own
trailing 30-day median forecast. FBR is the fraction of a coin's forecast one-sigma
move consumed by an all-in round trip; report it separately at 1x/2x/3x cost.

For a future market evaluation, freeze the universe as the top 20 active MEXC USDT
perpetuals by trailing 30-day quote volume at each origin; calculate w_t from that
origin's membership and compute historical baseline snapshots only from their own
past data. Require a complete return panel. No market results are claimed here.

This is a new lab diagnostic assembled from standard EWMA covariance and cost
normalization ideas, not a claim of a novel published volatility model. Crypto
common-volatility factors already exist in the literature (for example, COVOL), so
the research question is its point-in-time MEXC-perpetual implementation and
execution-risk usefulness. It is not Cboe VIX or Deribit's DVOL: those are
option-implied measures. APSI is a realized-returns-based, one-day basket-risk
forecast, normalized to recent history.
"""

from __future__ import annotations

import math
import numpy as np


def ewma_covariance(returns, *, half_life_hours: float = 72.0) -> np.ndarray:
    """Weighted sample covariance of a complete chronological hourly return matrix."""
    x = np.asarray(returns, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 1:
        raise ValueError("returns must be a 2D (hours, assets) matrix with at least 2 rows")
    if not np.isfinite(x).all():
        raise ValueError("returns must be finite and complete")
    if not math.isfinite(half_life_hours) or half_life_hours <= 0:
        raise ValueError("half_life_hours must be finite and positive")

    # Rows are oldest -> newest; the last row has age zero.
    age = np.arange(x.shape[0] - 1, -1, -1, dtype=np.float64)
    weight = np.exp2(-age / half_life_hours)
    weight /= weight.sum()
    mean = weight @ x
    centered = x - mean
    cov = (centered * weight[:, None]).T @ centered
    # Explicitly symmetrize against floating point round-off.
    return (cov + cov.T) * 0.5


def basket_sigma24(returns, weights, *, half_life_hours: float = 72.0) -> float:
    """Square root of forecast next-24h integrated basket variance from completed returns."""
    w = np.asarray(weights, dtype=np.float64)
    x = np.asarray(returns, dtype=np.float64)
    if w.ndim != 1 or x.ndim != 2 or w.size != x.shape[1]:
        raise ValueError("weights must have one entry per return column")
    if not np.isfinite(w).all() or np.any(w < 0) or not math.isclose(float(w.sum()), 1.0, abs_tol=1e-10):
        raise ValueError("weights must be finite, nonnegative and sum to one")
    cov = ewma_covariance(x, half_life_hours=half_life_hours)
    variance = 24.0 * float(w @ cov @ w)
    if not math.isfinite(variance) or variance < -1e-14:
        raise ValueError("forecast basket variance is invalid")
    return math.sqrt(max(variance, 0.0))


def apsi_index(current_sigma24: float, prior_daily_sigma24) -> float:
    """Normalize today's forecast by the median of the previous 30 daily forecasts."""
    hist = np.asarray(prior_daily_sigma24, dtype=np.float64)
    if hist.ndim != 1 or hist.size != 30:
        raise ValueError("exactly 30 prior daily forecast snapshots are required")
    if not math.isfinite(current_sigma24) or current_sigma24 <= 0:
        raise ValueError("current_sigma24 must be finite and positive")
    if not np.isfinite(hist).all() or np.any(hist <= 0):
        raise ValueError("prior daily forecasts must be finite and positive")
    return 100.0 * current_sigma24 / float(np.median(hist))


def fee_burden_ratio(round_trip_cost: float, sigma24: float, *, cost_multiple: float = 1.0) -> float:
    """Return the share of a one-sigma move consumed by all-in round-trip cost."""
    if not math.isfinite(round_trip_cost) or round_trip_cost < 0:
        raise ValueError("round_trip_cost must be finite and nonnegative")
    if not math.isfinite(sigma24) or sigma24 <= 0:
        raise ValueError("sigma24 must be finite and positive")
    if not math.isfinite(cost_multiple) or cost_multiple <= 0:
        raise ValueError("cost_multiple must be finite and positive")
    return cost_multiple * round_trip_cost / sigma24


def snapshot(returns, weights, prior_daily_sigma24, *, half_life_hours: float = 72.0) -> dict[str, float]:
    """Compute the current APSI snapshot; callers pass only returns known at the origin."""
    sigma24 = basket_sigma24(returns, weights, half_life_hours=half_life_hours)
    return {"sigma24": sigma24, "apsi": apsi_index(sigma24, prior_daily_sigma24)}


def snapshot_at(all_returns, origin: int, weights, prior_daily_sigma24, *,
                lookback_hours: int = 168, half_life_hours: float = 72.0) -> dict[str, float]:
    """Compute at integer origin, where rows [0:origin] are completed and later rows are unseen."""
    x = np.asarray(all_returns, dtype=np.float64)
    if isinstance(origin, bool) or not isinstance(origin, (int, np.integer)):
        raise ValueError("origin must be an integer row count")
    if isinstance(lookback_hours, bool) or not isinstance(lookback_hours, (int, np.integer)) or lookback_hours < 2:
        raise ValueError("lookback_hours must be an integer >= 2")
    if x.ndim != 2 or origin < lookback_hours or origin > x.shape[0]:
        raise ValueError("origin must contain a full lookback within the return matrix")
    return snapshot(x[origin - lookback_hours:origin], weights, prior_daily_sigma24,
                    half_life_hours=half_life_hours)
