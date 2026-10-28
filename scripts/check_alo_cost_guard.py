"""Independent rational arithmetic check for the fixed constructed cases."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results')
    args = parser.parse_args()
    inputs = json.loads(Path('experiments/alo_cost_guard_v1/fixtures.json').read_text())
    report = json.loads(Path(args.results).read_text())
    assert report['strategy_trials'] == report['prospective_days'] == 0
    cases = {c['id']: c for c in inputs['cases']}
    assert len(report['cells']) == len(cases) * 3
    seen, checks = set(), 0
    def equal(a, b):
        nonlocal checks
        assert F(a) == b, (a, b)
        checks += 1
    for row in report['cells']:
        key = row['case'], row['multiple']
        assert key not in seen and key[1] in (1, 2, 3)
        seen.add(key)
        case = cases[key[0]]
        ac, re, unknown, cancels, paid, nfill, terminal = case['counts']
        mult = key[1]
        action = F(paid) * F(inputs['hypothetical_paid_action_usd']) * mult
        extra = F(inputs['extra_cost_usd']) * mult
        equal(row['action_cost_usd'], action)
        if unknown or not terminal:
            assert row['status'] == 'UNKNOWN_OPEN_ORDERS' and row['component_usd'] is None
            checks += 1
        elif case['fill'] is None:
            assert nfill == 0 and row['status'] == 'NO_REPORTED_FILL'
            assert row['markout_usd'] is None and row['cost_per_filled_notional_bps'] is None
            equal(row['component_usd'], -action-extra)
            checks += 1
        else:
            f = case['fill']
            q, p = F(f['quantity']), F(f['price'])
            initial, later = F(f['initial_mid']), F(f['horizon_mid'])
            n, exit_n = abs(q)*p, abs(q)*later
            entry_fee = n*F(inputs['entry_fee_bps'])*mult/10000
            exit_fee = exit_n*F(inputs['hypothetical_passive_exit_fee_bps'])*mult/10000
            spread, movement, markout = q*(initial-p), q*(later-initial), q*(later-p)
            assert spread+movement == markout and row['status'] == 'SCORED_COUNTERFACTUAL'
            equal(row['entry_notional_usd'], n)
            equal(row['markout_usd'], markout)
            equal(row['spread_component_usd'], spread)
            equal(row['midpoint_move_usd'], movement)
            equal(row['entry_fee_usd'], entry_fee)
            equal(row['exit_fee_usd'], exit_fee)
            equal(row['component_usd'], markout-entry_fee-exit_fee-action-extra)
            equal(row['cost_per_filled_notional_bps'], (entry_fee+exit_fee+action+extra)*10000/n)
            equal(row['component_per_capital_bps'], (markout-entry_fee-exit_fee-action-extra)*10000/F(inputs['capital_usd']))
    print(json.dumps({'independent_fraction_checks': checks, 'cells': len(seen), 'result': 'PASS'}))


if __name__ == '__main__':
    main()
