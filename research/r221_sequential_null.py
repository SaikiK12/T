"""Synthetic null calibration audit for the frozen R221 look boundaries.

This tests only the sampling behavior of the Newey-West statistic and the frozen
boundaries. It does not read tickets or market data and does not estimate R221's
real-world Type I error. The separate 2x-cost decision hurdle is intentionally
omitted, so reported boundary-crossing rates are diagnostic upper bounds on the
full decision's pass rate when costs are nonnegative.

Run from any directory with:
    python3 research/r221_sequential_null.py
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg  # noqa: E402
from lab.stats import newey_west_t  # noqa: E402

LOOKS = ((90, "futility", -2.0), (182, "interim", 3.558), (365, "final", 2.397))


def nw_t_batch(x: np.ndarray, lag: int) -> np.ndarray:
    """Vectorized parity implementation of lab.stats.newey_west_t's t value."""
    n = x.shape[1]
    mu = x.mean(axis=1)
    z = x - mu[:, None]
    s = np.sum(z * z, axis=1)
    for ell in range(1, min(lag, n - 1) + 1):
        weight = 1.0 - ell / (lag + 1.0)
        s += 2.0 * weight * np.sum(z[:, ell:] * z[:, :-ell], axis=1)
    return mu * n / np.sqrt(np.maximum(s, 1e-300))


def draw(kind: str, rng: np.random.Generator, count: int, days: int) -> np.ndarray:
    """Unit-marginal-variance Gaussian nulls; MA(2) is a 3-day rolling mean."""
    innovations = rng.standard_normal((count, days + 3))
    if kind == "iid":
        return innovations[:, :days]
    if kind.startswith("ar1_"):
        rho = float(kind.removeprefix("ar1_"))
        x = np.empty((count, days), dtype=float)
        x[:, 0] = innovations[:, 0]
        shock_sd = math.sqrt(1.0 - rho * rho)
        for day in range(1, days):
            x[:, day] = rho * x[:, day - 1] + shock_sd * innovations[:, day]
        return x
    if kind == "ma2_3day_overlap":
        return (
            innovations[:, :days]
            + innovations[:, 1 : days + 1]
            + innovations[:, 2 : days + 2]
        ) / math.sqrt(3.0)
    raise ValueError(f"unknown null generator: {kind}")


def statistic(x: np.ndarray, lag: int | None) -> np.ndarray:
    if lag is None:
        # The exact known-variance normal reference used to benchmark the
        # standard group-sequential z boundaries (all simulated marginal SDs=1).
        return x.mean(axis=1) * math.sqrt(x.shape[1])
    return nw_t_batch(x, lag)


def calibrate(kind: str, lag: int | None, *, simulations: int, batch: int, seed: int) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    stopped = crossed_182 = crossed_365 = raw_182 = raw_365 = 0
    done = 0
    stop_day, _, stop_boundary = LOOKS[0]
    interim_day, _, interim_boundary = LOOKS[1]
    final_day, _, final_boundary = LOOKS[2]
    while done < simulations:
        size = min(batch, simulations - done)
        x = draw(kind, rng, size, final_day)
        z90 = statistic(x[:, :stop_day], lag)
        z182 = statistic(x[:, :interim_day], lag)
        z365 = statistic(x, lag)
        stop = z90 <= stop_boundary
        pass_182 = (z182 >= interim_boundary) & ~stop
        pass_365 = (z365 >= final_boundary) & ~stop & ~pass_182
        stopped += int(stop.sum())
        crossed_182 += int(pass_182.sum())
        crossed_365 += int(pass_365.sum())
        raw_182 += int((z182 >= interim_boundary).sum())
        raw_365 += int((z365 >= final_boundary).sum())
        done += size
    return {
        "stop90": stopped / simulations,
        "raw182": raw_182 / simulations,
        "raw365": raw_365 / simulations,
        "cross182": crossed_182 / simulations,
        "cross365": crossed_365 / simulations,
        "any_cross": (crossed_182 + crossed_365) / simulations,
        "mc_se": math.sqrt(max((crossed_182 + crossed_365) / simulations * (1.0 - (crossed_182 + crossed_365) / simulations), 0.0) / simulations),
    }


def check_parity() -> None:
    rng = np.random.default_rng(12345)
    sample = rng.normal(size=(1, 182))
    expected = newey_west_t(sample[0], 10)[2]
    observed = nw_t_batch(sample, 10)[0]
    if not np.isclose(observed, expected, rtol=0.0, atol=1e-12):
        raise AssertionError(f"vector/scalar NW mismatch: {observed} vs {expected}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulations", type=int, default=100_000)
    parser.add_argument("--batch", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=917_221)
    args = parser.parse_args()
    if args.simulations < 1 or args.batch < 1:
        parser.error("--simulations and --batch must be positive")

    prereg_digest = prereg.verify(ROOT / "experiments" / "mexc_seq" / "PREREG.md")
    check_parity()
    print(f"R221 prereg={prereg_digest[:12]}; boundaries={LOOKS}; replications={args.simulations}; seed={args.seed}")
    print(f"Normal endpoint tails: sf(3.558)={norm.sf(3.558):.6f}; sf(2.397)={norm.sf(2.397):.6f}")
    scenarios = [("iid", None), ("iid", 0), ("iid", 10), ("ar1_0.1", 10), ("ar1_0.2", 10),
                 ("ar1_0.3", 10), ("ma2_3day_overlap", 10)]
    for index, (kind, lag) in enumerate(scenarios):
        result = calibrate(kind, lag, simulations=args.simulations, batch=args.batch,
                           seed=args.seed + index * 1009)
        label = "known-var" if lag is None else f"NW{lag:02d}"
        print(f"{kind:19s} {label:9s} " + " ".join(f"{key}={value:.5f}" for key, value in result.items()))


if __name__ == "__main__":
    main()
