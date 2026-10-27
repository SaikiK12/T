"""Independent R340 exact rational oracle; no production financial imports."""
import argparse
import csv
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_opportunity_execution import Checks, chain, verify as frozen_verify

LANE = ROOT/'experiments/current_inverse_v1'


def check_guard(check, observed, b, a, fee):
    delta = b-a-fee
    check.number(observed['residual_coin_delta'], delta, 'post-debit coin residual')
    check.number(observed['minimum_required_initial_coin'], a+fee, 'required collateral includes coin fee')
    check.equal(observed['all_positive_marks_1x_model_coverage'], delta >= 0, 'all-mark one-times inequality')
    check.equal(observed['actual_liquidation_immunity'], None, 'model inequality is not venue immunity')
    check.equal(observed['actual_order_allowed'], False, 'no order permission')
    return delta


def check_hurdle(check, observed, q, delta, price, delivery_rate, exit_rate, spent, capital):
    # Derive final spendable quote directly from the inverse short payoff,
    # AFTER delivery and sale commissions, plus one copy of idle cash.
    unit = (q*(1-delivery_rate)+delta*price)*(1-exit_rate)
    check.number(observed['unit_terminal_quote_before_ratio'], unit, 'terminal quote per unit sale/settlement ratio')
    check.number(observed['same_initial_capital_quote'], capital, 'whole-capital control')
    check.number(observed['idle_cash_quote'], capital-spent, 'idle capital counted once')
    check.number(observed['minimum_exit_ratio'], spent/unit if unit > 0 else None, 'same-capital cash break-even')
    check.equal(observed['conditional_total_terminal_quote'], None, 'unknown sale price stays unknown')
    check.equal(observed['conditional_net_vs_cash_benchmark_quote'], None, 'no invented terminal cash')
    check.equal(observed['actual_expected_net_quote'], None, 'no actual edge from algebra')
    if unit > 0:
        ratio = F(observed['minimum_exit_ratio'])
        check.equal(capital-spent+unit*ratio-capital, 0, 'literal break-even net cash identity')


def audit(out):
    frozen_verify(LANE)
    fixture = json.loads((LANE/'fixtures.json').read_text())
    result = json.loads(gzip.decompress((out/'results.json.gz').read_bytes()))
    check = Checks()
    check.equal(result['registry_id'], 'R340', 'round identity')
    check.equal(result['actual_executable_expected_net'], None, 'unknown current return')
    check.equal(result['activation_allowed'], False, 'no activation')
    check.equal(result['predictive_strategy_trials'], 0, 'no predictive variant counted')
    check.equal(result['prospective_days'], 0, 'no reconstructed paper evidence')
    received = result['acquisition']; check.equal(received['blocked'] != [], True, 'access failure preserved')
    check.equal([(r['name'], r['http_status']) for r in received['records']],
        [('coinm_info_doc', 302), ('coinm_info', 451)], 'no replacement after access stops')
    journal = chain((LANE/'evidence/budget.jsonl').read_text())
    charged = [r['event'] for r in journal if r['event'].get('kind') == 'reserve']
    check.equal(len(charged), 2, 'one accumulated source/current budget')
    check.equal(sum(r['body_limit_bytes'] for r in charged), 1024**2, 'conservative byte charges retained')
    check.equal(sum(r['duration_ns'] for r in charged), 16*10**9, 'failed duration charges retained')
    check.equal(sum(r['accepted_body_bytes'] for r in received['records']), 362, 'actual failed response bytes')
    wanted = {(c, m, k) for c in fixture['coins'] for m in fixture['maturities'] for k in fixture['cost_multiples']}
    check.equal({(r['coin'], r['contract_type'], r['cost_multiple']) for r in result['current_inputs']}, wanted, 'all missing current slots retained')
    for r in result['current_inputs']:
        check.equal(r['quote'], None, 'no fake price after metadata failure')
        check.equal(r['executable_expected_net'], None, 'missing current price is not profitable zero')
    parent = json.loads((ROOT/fixture['held_plan_path']).read_text())
    keys = {(s['coin'], s['profile'], c['fee_control'], c['cost_multiple'], x): (s, c)
        for s in parent['rows'] for c in s['controls'] for x in fixture['delivery_price_scales']}
    observed_keys = {(r['coin'], r['profile'], r['fee_control'], r['cost_multiple'], r['delivery_price_scale'])
        for r in result['held_R328_guard_cells']}
    check.equal(observed_keys, set(keys), 'exact old-plan fee/depth/cost/price scope')
    check.equal(len(observed_keys), len(result['held_R328_guard_cells']), 'no duplicated held-plan row')
    for row in result['held_R328_guard_cells']:
        key = row['coin'], row['profile'], row['fee_control'], row['cost_multiple'], row['delivery_price_scale']
        source, control = keys[key]; p = source['plan']; r = control['primary_future_result']
        check.equal(row['input_error'], source['input_error'], 'parent unavailable scope retained')
        if r is None:
            check.equal(row['guard'], None, 'missing depth is not zero exposure')
            check.equal(row['hurdle'], None, 'missing cost is not free'); continue
        q, a, b, fee = F(p['face_usd']), F(r['stressed_hedge_coin']), F(p['initial_coin']), F(r['entry_fee_coin'])
        delta = check_guard(check, row['guard'], b, a, fee)
        check_hurdle(check, row['hurdle'], q, delta, F(p['future_mid_usd'])*F(row['delivery_price_scale']),
            F(r['delivery_fee_rate']), F(r['spot_fee_rate']), F(r['initial_spend_usdt']), F(r['total_initial_capital_usdt']))
    with (ROOT/fixture['rounded_ticket_path']).open() as handle: tickets = list(csv.DictReader(handle))
    expected = {(i, k, f, debit) for i in range(len(tickets)) for k in fixture['cost_multiples']
        for f in fixture['fee_controls'] for debit in fixture['spot_fee_assets']}
    rows = result['R335_normalized_ticket_cells']
    observed = {(r['ticket_row'], r['cost_multiple'], r['fee_control'], r['spot_fee_asset_scenario']) for r in rows}
    check.equal(observed, expected, 'all published rounded tickets/controls retained')
    check.equal(len(observed), len(rows), 'no duplicated normalized ticket scenario')
    for row in rows:
        ticket = tickets[row['ticket_row']]; k = row['cost_multiple']; debit = row['spot_fee_asset_scenario']
        q = 1+F(ticket['gross'])/100
        check.number(row['normalized_future_price'], q, 'normalized rounded published gross')
        fee = 0 if row['fee_control'] == 'zero_charge' else F(fixture['future_entry_rate'])*k
        spot_fee = 0 if row['fee_control'] == 'zero_charge' else F(fixture['spot_rate'])*k
        b = 1-spot_fee if debit == 'base' else F(1)
        d = check_guard(check, row['unreserved_guard'], b, F(1), fee)
        if d < 0:
            adversarial_mark = -2*q/d
            check.equal(q/adversarial_mark+d < 0, True, 'unreserved fee yields explicit positive-mark counterexample')
        bought = (1+fee)/(1-spot_fee) if debit == 'base' else 1+fee
        net = bought*(1-spot_fee) if debit == 'base' else bought
        spent = bought if debit == 'base' else bought*(1+spot_fee)
        check.number(row['prefunded']['gross_spot_base'], bought, 'spot buy includes exact fee reserve')
        check.number(row['prefunded']['net_collateral_coin'], net, 'post-spot-fee collateral')
        check.number(row['prefunded_spend'], spent, 'exact fee-asset debit cash outlay')
        check_guard(check, row['prefunded']['coverage'], net, F(1), fee)
        check_hurdle(check, row['prefunded_hurdle'], q, F(0), F(1), F(0), spot_fee, spent, F(10))
        check.equal(row['historical_pnl_recomputed'], False, 'rounded metadata is not a historical replay')
    frozen_verify(LANE)
    return {'registry_id': 'R340', 'passed': True, 'independent_checks': check.count,
        'current_null_slots': len(result['current_inputs']), 'held_guard_slots': len(keys),
        'normalized_ticket_cells': len(rows), 'actual_executable_expected_net': None,
        'predictive_strategy_trials': 0, 'prospective_days': 0, 'activation_allowed': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    args = p.parse_args(); result = audit(args.out)
    (args.out/'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(result, indent=2))
