#!/usr/bin/env python3
"""Audit one pinned public demo on invented values; no backtest or network IO.

Download only the named 14,350-byte Python source separately, then run:
    python -m research.audit_blueshift_no_regret /tmp/no_regret_portfolio.py

The whole-file hash is checked before compiling selected original definitions.
No imports, top-level statements, orders or platform callbacks are executed.
This checks source fidelity and accounting, not profitability or no-regret bounds.
"""

import argparse
import ast
import hashlib
import json
from pathlib import Path
import platform
from types import SimpleNamespace
import warnings

import numpy as np
import pandas as pd


COMMIT = "8dfeb49f615dbd57acf092924fdfc1fb8c336f37"
URL = ("https://raw.githubusercontent.com/QuantInsti/"
       f"blueshift-demo-strategies/{COMMIT}/portfolio/no_regret_portfolio.py")
SHA256 = "f78baa1cda81234fdb84d5ba43c1c2abc4369ede4d6a6279f0694ce5316784a9"


def definitions(raw):
    """Return only the two accounting/weight methods, from the exact source."""
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError("Source version mismatch; nothing compiled or executed")
    parsed = ast.parse(raw)
    selected = []
    for class_name, method in (("Advisor", "update_performance"),
                               ("Agent", "weighing_function")):
        owner, = [node for node in parsed.body
                  if isinstance(node, ast.ClassDef) and node.name == class_name]
        fn, = [node for node in owner.body
               if isinstance(node, ast.FunctionDef) and node.name == method]
        selected.append(fn)
    namespace = {"np": np}
    exec(compile(ast.Module(body=selected, type_ignores=[]), URL, "exec"), namespace)
    return namespace["update_performance"], namespace["weighing_function"]


def audit(raw):
    update_performance, weighing_function = definitions(raw)
    checks = []

    def tracker(label, returns):
        n = len(returns)
        # Matches the source's default leverage=1 and rounded 1/N targets.
        weight = round(1 / n, 2)
        state = SimpleNamespace(
            n_assets=n, last_weights=dict.fromkeys(range(n), weight),
            last_px=dict.fromkeys(range(n), 100.0),
            current_px={i: 100 * (1 + r) for i, r in enumerate(returns)},
            perf=100.0)
        update_performance(state)
        target_wealth = 100 * (1 + sum(weight * r for r in returns))
        source_formula = 100 * np.prod([1 + weight * r / n for r in returns])
        np.testing.assert_allclose(state.perf, source_formula, rtol=0, atol=1e-12)
        assert not np.isclose(state.perf, target_wealth, rtol=0, atol=1e-10)
        checks.append(dict(
            case=label, kind="accounting_discrepancy", returns=list(returns),
            submitted_weights=[weight] * n, starting_wealth=100.0,
            source_wealth=state.perf, simultaneous_target_wealth=target_wealth,
            source_lines="323-344"))

    tracker("two_equal_risers", (.10, .10))
    tracker("offsetting_equal_positions", (.10, -.10))
    tracker("four_equal_risers", (.10, .10, .10, .10))

    def allocation(frame, *, method=1, previous=(.9, .1)):
        keys = list(frame.columns)
        state = SimpleNamespace(
            perfs=frame, lookback=60, method=method, learning_rate=.35,
            advisors=[SimpleNamespace(name=k) for k in keys],
            advisors_keys=keys, n_advisors=len(keys),
            current_weights=dict(zip(keys, previous)))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return weighing_function(state)

    flat = pd.DataFrame({"a": [100.] * 60, "b": [100.] * 60})
    weights = allocation(flat)
    np.testing.assert_allclose(list(weights.values()), (.5, .5), rtol=0, atol=1e-12)
    checks.append(dict(
        case="flat_wealth_resets_prior_weights", kind="algorithm_identity",
        previous_weights=[.9, .1], source_weights=weights,
        interpretation="Custom normalized exponential scores; equal wealth resets to equal weights. "
                       "A multiplicative Hedge update with equal rewards preserves prior weights. "
                       "This difference alone is not evidence of a defect or loss.",
        source_lines="245-288"))

    alternate = allocation(flat, method=0)
    assert all(np.isnan(v) for v in alternate.values())
    checks.append(dict(
        case="method0_flat_history", kind="numeric_degeneracy",
        method=0, source_weights={key: None for key in alternate},
        nonfinite_keys=list(alternate),
        interpretation="Zero return divided by zero sample volatility propagates NaN. "
                       "JSON null here denotes an observed nonfinite result, not zero weight.",
        source_lines="261-288"))

    common = pd.DataFrame({"a": np.linspace(100, 120, 61),
                           "b": np.linspace(100, 100, 61)})
    changed = common.copy()
    changed.loc[0, "a"] = 50.
    assert common.iloc[-60:].equals(changed.iloc[-60:])
    first, second = allocation(common), allocation(changed)
    assert not np.isclose(first["a"], second["a"], rtol=0, atol=1e-10)
    checks.append(dict(
        case="lookback60_is_not_rolling_window", kind="algorithm_identity",
        history_rows=61, identical_last_rows=60,
        source_weights_first=first, source_weights_changed_first_row=second,
        interpretation="lookback controls minimum sample count only; first/last wealth "
                       "and pct_change use all stored rows.", source_lines="245-268"))

    early = allocation(flat.iloc[:59])
    np.testing.assert_allclose(list(early.values()), (.5, .5), rtol=0, atol=1e-12)
    checks.append(dict(
        case="warmup59", kind="control", history_rows=59, source_weights=early,
        source_lines="245-248"))

    return dict(
        schema_version=1, source_url=URL, source_commit=COMMIT,
        source_sha256=SHA256, source_bytes=len(raw),
        runtime=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        execution_scope=["Advisor.update_performance", "Agent.weighing_function"],
        checks=checks, checks_passed=len(checks), market_trials=0,
        cost_sensitivity="Not applicable to source arithmetic; no executable portfolio "
                         "or 1x/2x/3x market-cost result computed.",
        limits=["No TA-Lib, Blueshift scheduler, order or fill callback executed.",
                "No market data or original platform backtest received.",
                "Simultaneous fixed target-weight wealth is the accounting comparator; "
                "it omits fees, funding and fills, exactly as these invented arithmetic cases do.",
                "This audit neither implements a corrected strategy nor tests its alpha."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Locally received pinned Python source")
    args = parser.parse_args()
    print(json.dumps(audit(args.source.read_bytes()), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
