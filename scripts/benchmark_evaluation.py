"""Bounded synthetic engineering benchmark, never an edge/outcome search.

Fixed seed, workload and three warmed repetitions; record output bytes rather
than pretending array size measures resident process memory. No market loaders.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def benchmark():
    import numpy as np
    from lab import engine, evaluation, runtime, slices
    rng = np.random.default_rng(81)
    T, S, R, start, stop = 16384, 16, 128, 4096, 5120
    bins = rng.integers(-1, 4, (2, T, S), dtype=np.int8)
    returns = rng.normal(0, .001, (T, S)).astype(np.float32)
    eligible = rng.random((T, S)) > .15
    costs = np.full((T, S), .0008, np.float32)
    rules = [engine.Rule((i % 2,), (0,), (i % 3,), 1, -1 if i % 2 else 1, 1 + i % 7) for i in range(R)]
    index = engine.eligible_index(eligible)
    old = lambda: engine.run_rules(bins, returns, eligible, costs, rules, start, stop, index=index)
    new = lambda: evaluation.rule_window(bins, returns, eligible, costs, rules, start, stop, index=index)
    before, after = old(), new()  # JIT warm-up excluded from measured repetitions.
    np.testing.assert_array_equal(before[:, start:stop], after)
    sizes = {"legacy_output_bytes": before.nbytes, "window_output_bytes": after.nbytes}
    del before, after

    def timed_pair(left, right):
        samples = {"legacy": [], "shared": []}
        # Alternate order to reduce a consistent order advantage.
        for i in range(3):
            pair = (("legacy", left), ("shared", right))
            for name, function in pair if i % 2 == 0 else pair[::-1]:
                started = time.perf_counter()
                value = function()
                samples[name].append(time.perf_counter() - started)
                del value
        return {"samples_seconds": samples, "median_seconds": {k: statistics.median(v) for k, v in samples.items()}}

    window = timed_pair(old, new)
    # Position construction is cost-independent in these fixed-slice books.
    parts = [(rng.random((T, S)) > .85, 1), (rng.random((T, S)) > .9, -1)]
    ret = np.nan_to_num(returns.astype(np.float64))
    elig = np.ones_like(eligible)
    def legacy_costs():
        result = {}
        for cm in (1., 2., 3.):
            p = sum(slices.positions(ind, 72, start, stop, .001, side) for ind, side in parts)
            result[cm] = slices.run(p, ret, elig, costs, start, stop, cmult=cm, missing="raise")
        return result
    def shared_costs():
        return evaluation.fixed_book_costs(parts, ret, elig, costs, hold=72, unit=.001, t0=start, t1=stop)
    left, right = legacy_costs(), shared_costs()
    for cm in left:
        for field in left[cm]:
            np.testing.assert_array_equal(left[cm][field], right[cm][field])
    return {"scope": "invented engineering fixture only; no strategy claim or production RSS estimate",
            "seed": 81, "T": T, "S": S, "R": R, "interval": [start, stop], "repetitions": 3,
            "parity": "exact array equality for net/cost/positions and fixed-book accounting",
            "environment": runtime.environment(ROOT), "window": {**sizes, **window},
            "fixed_book_costs": timed_pair(legacy_costs, shared_costs)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.report.exists() or args.report.resolve().is_relative_to(ROOT):
        parser.error("report must be a new file outside the repository")
    report = benchmark()
    with args.report.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
