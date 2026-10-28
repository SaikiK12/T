"""R358: one literal correction to R357's independent capital expectation.

The original financial implementation, inputs, output and checker stay intact.
Only the checker's expected-admission expression is replaced in memory. No
production accounting, quote, risk or source-score functions are imported.
"""
import ast
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'experiments/settlement_check_v1'
ORIGINAL = ROOT / 'scripts/check_settlement_account.py'
OLD_EXPR = ast.dump(ast.parse("case['id'] == 'separate_capital_shortfall'", mode='eval').body)


def expected_blocked(cell, case, config):
    """Exact independent per-venue entry notional plus fee, fixed q and capital."""
    for venue, prefix in (('mexc', 's'), ('lighter', 'h')):
        q = abs(F(cell['entry_quantities'][venue]))
        mid = F(config['entry_mid'])
        multiple = cell['cost_multiple']
        base_price = F(str(cell['constructed_entry'][prefix + '_fill']))
        price = mid + multiple * (base_price - mid)
        notional = q * price
        fee = notional * F(config['fees_bp'][venue]) * multiple / 10000
        capital = F(case.get(prefix + '_capital', config['initial_per_venue']))
        if notional + fee > capital:
            return True
    return False


def corrected_namespace(source):
    tree = ast.parse(source)
    count = 0

    class Correct(ast.NodeTransformer):
        def visit_Assign(self, node):
            nonlocal count
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'blocked':
                if ast.dump(node.value) != OLD_EXPR:
                    raise ValueError('unexpected original expected-admission expression')
                count += 1
                node.value = ast.Call(func=ast.Name(id='_r358_expected_blocked', ctx=ast.Load()),
                    args=[ast.Name(id=x, ctx=ast.Load()) for x in ('cell', 'case', 'config')], keywords=[])
            return node

    tree = Correct().visit(tree)
    if count != 1:
        raise ValueError('exactly one original expected-admission expression required')
    ast.fix_missing_locations(tree)
    namespace = {'__file__': str(ORIGINAL), '__name__': 'r358_literal_checker_correction',
                 '_r358_expected_blocked': expected_blocked}
    exec(compile(tree, str(ORIGINAL), 'exec'), namespace)
    return namespace


def verify():
    spec = (LANE / 'PREREG.md').read_bytes()
    if hashlib.sha256(spec).hexdigest() != (LANE / 'PREREG.sha256').read_text().strip():
        raise ValueError('R358 frozen spec drift')
    for name in ('PREREG.md', 'PREREG.sha256', 'inputs.json'):
        path = LANE / name
        if subprocess.check_output(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT) != path.read_bytes():
            raise ValueError('R358 specification/input identity must be committed')
    raw = (LANE / 'inputs.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() not in spec.decode():
        raise ValueError('R358 manifest not bound')
    data = json.loads(raw)
    if data['python_version'] != list(sys.version_info[:3]):
        raise ValueError('R358 Python runtime drift')
    for path, sha in data['sha256'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != sha:
            raise ValueError('R358 input drift: ' + path)
    return data


def main():
    data = verify()
    namespace = corrected_namespace(ORIGINAL.read_text())
    namespace['main']()
    verify()
    # The original parser has already validated the exact --out invocation.
    out = Path(sys.argv[sys.argv.index('--out') + 1])
    for name, expected in data['result_identity'].items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != expected:
            raise ValueError('checked result differs from frozen R357 input identity')
    audit = (out / 'audit.json').read_bytes()
    review = {'registry_id': 'R358', 'tested_registry_id': 'R357', 'status': 'PASS',
              'original_failure_retained': True, 'expected_admission_expression_corrections': 1,
              'financial_code_or_data_changes': 0, 'audit_sha256': hashlib.sha256(audit).hexdigest(),
              'original_checker_sha256': data['sha256']['scripts/check_settlement_account.py'],
              'new_predictive_trials': 0, 'prospective_strategy_days': 0}
    with (out / 'review.json').open('x') as handle:
        handle.write(json.dumps(review, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps(review, sort_keys=True))


if __name__ == '__main__':
    main()
