"""Literal rational audit of R322 saved component fixtures; no market validation."""
import argparse
from decimal import Decimal as D
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_funding_prefix import LANE, verify, save, sha


def audit(directory=LANE):
    fixtures = verify()
    directory = Path(directory)
    report = json.loads((directory / 'results.json').read_text())
    if report['observations_sha256'] != sha(directory / 'observations.json.gz'):
        raise ValueError('saved observations changed')
    data = json.loads(gzip.decompress((directory / 'observations.json.gz').read_bytes()))
    checked = {'arithmetic': 0, 'rounding': 0, 'accounts': 0, 'funding_updates': 0}
    for r in data['arithmetic']:
        exact = F(r['size_units']) * r['quote_multiplier'] * (r['checkpoint'] - r['prefix'])
        a = r['assessment']
        if a['collateral_delta'] != exact or F(a['conditional_collateral_usdc']) != exact / 10**12:
            raise ValueError('rational encoded-collateral arithmetic mismatch')
        if a['settled_cash_verified'] or a['cash_delta'] is not None:
            raise ValueError('component result promoted to actual cash')
        checked['arithmetic'] += 1
    for r in data['rounding']:
        old, delta = F(r['old_collateral']), F(r['funding_delta'])
        old_floor = old // 10**6
        new_floor = (old + delta) // 10**6
        if r['result']['component_delta_micro_usdc'] != new_floor - old_floor:
            raise ValueError('partial rounding-component mismatch')
        if r['result']['wallet_credit_verified']:
            raise ValueError('partial rounding promoted to wallet credit')
        checked['rounding'] += 1
    for p in data['paths']:
        key = next(x for x in fixtures['paths'] if x['id'] == p['id'])
        q, C = key['initial_size'], 0
        fee = abs(F(q, fixtures['fixture_size_units_per_physical_base'])) * F(fixtures['flat_fixture_price']) * F(fixtures['fee_fraction']) * p['cost_multiple']
        funding, unknown = F(0), False
        for r in p['records']:
            P = r['observation']['prefix']
            known = P is not None and key.get('input_scope', 'invented_encoded_fixture') == 'invented_encoded_fixture'
            if p['control'] == 'registered_prefix_model' and not known:
                unknown = True
            expected = (F(q) * fixtures['fixture_quote_multiplier'] * (C - P) / 10**12
                        if known and p['control'] == 'registered_prefix_model' else F(0))
            if not known and p['control'] == 'registered_prefix_model':
                if r['posting_amount'] is not None:
                    raise ValueError('unverified cash posted')
            elif F(r['posting_amount']) != expected:
                raise ValueError('old-inventory funding mismatch')
            funding += expected
            if r['alias_status'] != 'duplicate':
                raise ValueError('renamed receipt paid twice')
            if P is not None:
                fee += abs(F(r['size_delta_units'], fixtures['fixture_size_units_per_physical_base'])) * F(fixtures['flat_fixture_price']) * F(fixtures['fee_fraction']) * p['cost_multiple']
                q += r['size_delta_units']
                C = P
            checked['funding_updates'] += 1
        # An unclosed fixture retains a separately marked future exit fee.
        future_exit = abs(F(q, fixtures['fixture_size_units_per_physical_base'])) * F(fixtures['flat_fixture_price']) * F(fixtures['fee_fraction']) * p['cost_multiple']
        expected_net = funding - fee - future_exit
        if F(p['funding_known_component']) != funding or F(p['fees_paid']) != fee:
            raise ValueError('funding/fee account decomposition mismatch')
        if unknown:
            if p['component_fixture_net'] is not None:
                raise ValueError('missing cash became a complete net result')
        elif F(p['component_fixture_net']) != expected_net:
            raise ValueError('literal net component mismatch')
        elif F(p['component_fixture_return_on_total_capital']) != expected_net / F(fixtures['total_capital']):
            raise ValueError('capital denominator mismatch')
        if sha(directory / p['journal']) != p['journal_sha256'] or not p['reopened_identical']:
            raise ValueError('common account journal/replay mismatch')
        checked['accounts'] += 1
    if [checked[k] for k in ('arithmetic', 'rounding', 'accounts')] != [216, 25, 48]:
        raise ValueError('incomplete fixed audit scope')
    result = {'checks': checked, 'exact_rational_matches': True,
              'scope': 'Independent arithmetic from saved inputs; shared source interpretation/generator, not a Rust circuit execution or authentic market audit',
              'actual_market_return': None, 'strategy_activation_allowed': False}
    verify()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=LANE)
    args = parser.parse_args()
    target = args.directory / 'audit.json'
    save(target, audit(args.directory))
    print(target)
