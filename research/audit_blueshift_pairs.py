"""Bounded source-control audit, not a platform backtest. No publisher code vendored.

Run with the pinned pair_example.py saved locally. Only trading_signal and
place_order AST definitions execute, with local order/cancellation recorders.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

SOURCE_URL = 'https://raw.githubusercontent.com/QuantInsti/blueshift-demo-strategies/8dfeb49f615dbd57acf092924fdfc1fb8c336f37/equities/pair_example.py'
SOURCE_SHA256 = 'ae3f1ffa8695abb1d6756630a93f9cd0d3d147904d7b038fd94ebdd2a4c6baa1'


def audit(source):
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('source fingerprint mismatch')
    tree = ast.parse(source)
    names = {'trading_signal', 'place_order'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if len(nodes) != 2 or {n.name for n in nodes} != names:
        raise ValueError('source execution scope changed')
    orders, cancellations = [], []
    namespace = {'get_open_orders': lambda: ['invented-open-order'],
                 'cancel_order': cancellations.append,
                 'order_target_percent': lambda asset, weight: orders.append([asset, weight])}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<pinned pair functions>', 'exec'), namespace)
    ctx = SimpleNamespace(entry_z_score=2.0, exit_z_score=0.5,
                          leverage=5, x='invented-x', y='invented-y')
    cases = []
    # Finite, fixed source-boundary cases; no market data or threshold search.
    for z, expected in [(-3, 1), (-2, 0), (-1, 0), (0, 0), (0.5, 0), (1, 0), (2, 0), (3, -1)]:
        ctx.z_score = z
        actual = namespace['trading_signal'](ctx, None)
        assert actual == expected
        cases.append({'z': z, 'signal': actual})
    weights = []
    for ratio in [0.5, 1.0, 2.0, -1.0]:
        ctx.signal, ctx.hedge_ratio = 1, ratio
        orders.clear()
        namespace['place_order'](ctx)
        assert orders == [['invented-x', -2.5 * ratio], ['invented-y', 2.5]]
        weights.append({'hedge_ratio': ratio, 'targets': [x[:] for x in orders],
                        'gross_target': sum(abs(x[1]) for x in orders)})
    ctx.signal = 999
    orders.clear()
    before = len(cancellations)
    namespace['place_order'](ctx)
    assert not orders and len(cancellations) == before
    return {'source_url': SOURCE_URL, 'source_sha256': SOURCE_SHA256,
            'execution_scope': ['trading_signal', 'place_order'],
            'signal_cases': cases, 'weight_cases': weights,
            'sentinel_999_skips_orders': True,
            'limits': 'Mocks record submitted targets only. No imports/history/hedge-ratio/z-score helper, scheduler, fills, costs or PnL execute.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.source.read_bytes()), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
