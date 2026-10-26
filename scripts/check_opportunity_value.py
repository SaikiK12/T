"""Independent Fraction checks for R334, without its production value functions.

Checks the finite invented input contract and retained published paired hurdles.
Not raw-market decoding, authenticated execution, forecast validity or alpha.
"""
import argparse
from fractions import Fraction as F
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(out):
    data = json.loads((out/'results.json').read_text())
    config = json.loads((ROOT/'experiments/opportunity_value_v1/fixtures.json').read_text())
    checks = 0

    def require(value, message):
        nonlocal checks
        if not value: raise ValueError(message)
        checks += 1

    require(len(data['cases']) == len(config['cases']), 'case coverage')
    for case, spec in zip(data['cases'], config['cases']):
        require(case['name'] == spec['name'], 'case identity')
        require(case['account_before'] == case['account_after'] and case['financial_journal_unchanged'], 'forecast changed money')
        require(not case['activation_allowed'] and not case['durable_reservation_created'], 'scope upgrade')
        require(len(case['rows']) == len(spec['opportunities']), 'opportunity coverage')
        budget = F(1000); gross = F(0)
        for row, original in zip(case['rows'], spec['opportunities']):
            require(row['opportunity_id'] == original['id'], 'opportunity identity')
            outcomes = original.get('outcomes', [['.9', '100', '0'], ['.1', '-100', '0']])
            known = all(x is not None and y is not None for p, x, y in outcomes if F(p))
            expected = sum((F(p)*(F(x)+F(y)) for p, x, y in outcomes if F(p)), F(0)) if known else None
            delivered = row['forecast']['expected_gross_quote']
            require((delivered is None) == (expected is None) and (expected is None or F(delivered) == expected), 'expected payoff')
            q = F(original.get('quantity', '1')); crossing = abs(q); fee = abs(q)/5
            cost_known = not any(original.get(k) for k in ('fee_unknown', 'future_book', 'thin'))
            require((row['cost']['round_trip_quote'] is not None) == cost_known, 'cost availability')
            if cost_known:
                require(F(row['cost']['round_trip_quote']) == crossing+fee, 'depth plus fee once')
                require(F(row['cost']['entry_notional_quote']) == abs(q)*F('100.5' if q > 0 else '99.5'), 'directional reservation notional')
            error = original.get('error', '2'); reserve_known = not original.get('reserve_unknown')
            threshold_known = known and cost_known and error is not None and not original.get('uncalibrated') and reserve_known
            for k, tier in enumerate(row['cost_tiers'], 1):
                require((tier['expected_net_lower_quote'] is not None) == threshold_known, 'unknown threshold retained')
                if threshold_known:
                    require(F(tier['expected_net_lower_quote']) == expected-F(error)-k*(crossing+fee+F('.5')), '1x2x3x exact value')
            allowed = threshold_known and expected-F(error)-3*(crossing+fee+F('.5')) > 0
            allowed = allowed and not spec.get('risk_stop') and not original.get('market_unknown') and original.get('asset', 'USDT') == 'USDT'
            needed = abs(q)*F('100.5' if q > 0 else '99.5')+3*(crossing+fee+F('.5'))
            size = abs(q)*F('100.5')
            allowed = bool(allowed and needed <= budget and gross+size <= 1000*F(spec.get('max_symbol_fraction', '.25')))
            require(row['conditional_batch_inclusion'] == allowed, 'ordered risk/capital admission')
            if allowed:
                budget -= needed; gross += size
                require(F(row['planned_capital_quote']) == needed, 'planned capital')
            require(row['actual_order_allowed'] is False, 'actual order enabled')
        require(F(case['budgets'][0]['remaining_after_batch_plan']) == budget, 'batch budget conservation')
    old = [json.loads(x) for x in gzip.decompress((ROOT/'experiments/paper_account_v1/observations.jsonl.gz').read_bytes()).splitlines()]
    new = [json.loads(x) for x in gzip.decompress((out/'held_hurdles.jsonl.gz').read_bytes()).splitlines()]
    expected_count = sum(len(x['sizes'])*3 for x in old)
    require(len(new) == expected_count, 'held coverage')
    i = 0
    for row in old:
        for size in row['sizes']:
            c = size.get('cost')
            for k in (1, 2, 3):
                target = new[i]; i += 1
                require((target['symbol'], target['grid_second'], target['delay_ms'], target['leg_budget_quote'], target['cost_multiple']) ==
                        (row['symbol'], row['grid_second'], row['delay_ms'], size['leg_budget_quote'], k), 'held input identity')
                expected = c['scenarios'][k-1]['round_trip_cost_usd'] if c and c.get('displayed_fillable') else None
                require(target['minimum_gross_before_error_quote_equivalent'] == expected, 'retained hurdle changed')
                require(target['expected_net_quote'] is None and target['expected_gross_quote'] is None and not target['model_entry_allowed'], 'invented held edge')
    require(data['predictive_trials'] == data['prospective_days'] == data['new_market_requests'] == 0, 'scope drift')
    return {'passed': True, 'checks': checks, 'invented_cases': len(config['cases']), 'held_cells': len(new),
            'scope': 'Fraction oracle on fixed supplied fixtures and published held cost-cell identity; not source authentication or forecast/return validation'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('out', type=Path)
    print(json.dumps(check(p.parse_args().out), sort_keys=True))
