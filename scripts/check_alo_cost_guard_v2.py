"""Independent exact-rational comparison of corrected constructed cases."""
import argparse
from fractions import Fraction as F
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('results')
    args = parser.parse_args()
    data = json.loads(Path('experiments/alo_cost_guard_v1/fixtures.json').read_text())
    out = json.loads(Path(args.results).read_text())
    cases = {c['id']:c for c in data['cases']}
    assert out['strategy_trials'] == out['prospective_days'] == 0 and len(out['cells']) == 12
    seen, checks = set(), 0
    def eq(x, y):
        nonlocal checks
        assert F(x) == y, (x, y)
        checks += 1
    for row in out['cells']:
        case = cases[row['case']]
        k = row['multiple']
        assert (row['case'], k) not in seen and k in (1,2,3)
        seen.add((row['case'], k))
        accepted, rejected, unresolved, cancels, paid, nfill, complete = case['counts']
        if unresolved or not complete:
            assert row['status'] == 'UNKNOWN_RECEIPTS_OR_ACTION_FUNDING' and row['component_usd'] is None
            eq(row['assumed_prepaid_action_cost_usd'], F(paid)*F(data['hypothetical_paid_action_usd'])*k)
            eq(row['assumed_prepaid_extra_cost_usd'], F(data['extra_cost_usd'])*k)
            checks += 1
            continue
        action = F(paid)*F(data['hypothetical_paid_action_usd'])*k
        extra = F(data['extra_cost_usd'])*k
        eq(row['prepaid_costs_usd'], action+extra)
        if case['fill'] is None:
            assert row['status'] == 'NO_REPORTED_FILL' and row['markout_usd'] is None
            component = -action-extra
        else:
            f = case['fill']
            q, price, mid0, midh = map(F, (f['quantity'],f['price'],f['initial_mid'],f['horizon_mid']))
            notional, end_notional = abs(q)*price, abs(q)*midh
            entry_fee = notional*F(data['entry_fee_bps'])*k/10000
            exit_fee = end_notional*F(data['hypothetical_passive_exit_fee_bps'])*k/10000
            mark = q*(midh-price)
            component = mark-entry_fee-exit_fee-action-extra
            eq(row['markout_usd'], mark)
            eq(row['spread_component_usd'], q*(mid0-price))
            eq(row['midpoint_move_usd'], q*(midh-mid0))
            eq(row['entry_fee_usd'], entry_fee)
            eq(row['exit_fee_usd'], exit_fee)
            eq(row['cost_per_filled_notional_bps'], (entry_fee+exit_fee+action+extra)*10000/notional)
            assert F(data['capital_usd'])-action-extra >= notional+entry_fee
            checks += 1
        eq(row['component_usd'], component)
        eq(row['component_per_capital_bps'], component*10000/F(data['capital_usd']))
        eq(row['counterfactual_end_capital_usd'], F(data['capital_usd'])+component)
        assert row['path_solvency_unknown'] is True
        checks += 1
    expected = {
        'quote_received_late': ('SCORED_COUNTERFACTUAL','REJECTED'),
        'quote_after_economic_fill': ('SCORED_COUNTERFACTUAL','REJECTED'),
        'inconsistent_source_receipt_clock': ('SCORED_COUNTERFACTUAL','REJECTED'),
        'asof_before_anchor': ('NO_REPORTED_FILL','UNKNOWN_RECEIPTS_OR_ACTION_FUNDING'),
        'cancel_partial_history_unknown': ('NO_REPORTED_FILL','UNKNOWN_RECEIPTS_OR_ACTION_FUNDING'),
        'prepaid_capital_shortfall': ('SCORED_COUNTERFACTUAL','REJECTED'),
        'end_capital_insolvent': ('SCORED_COUNTERFACTUAL','INSOLVENT_COUNTERFACTUAL'),
        'no_fill_capital_exhausted': ('NO_REPORTED_FILL','INSOLVENT_COUNTERFACTUAL')}
    assert len(out['adversarial']) == len(expected)
    names = [row['name'] for row in out['adversarial']]
    assert len(set(names)) == len(expected) and set(names) == set(expected)
    for row in out['adversarial']:
        assert (row['v1']['status'], row['v2']['status']) == expected[row['name']]
        checks += 1
    print(json.dumps({'result':'PASS','cells':len(seen),'independent_checks':checks,'adversarial':len(expected)}))


if __name__ == '__main__':
    main()
