"""R340 fee/collateral and executable-sale hurdles; current input failures stay."""
import argparse
import csv
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.inverse_offer import coverage, prefund, terminal_hurdle

LANE = ROOT/'experiments/current_inverse_v1'


def plain(x):
    if isinstance(x, F): return str(x)
    if isinstance(x, dict): return {k: plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [plain(v) for v in x]
    return x


def encoded(x):
    return (json.dumps(plain(x), sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def verify():
    prereg.verify(LANE/'PREREG.md'); spec = (LANE/'PREREG.md').read_text()
    for name in ('code_inputs.json', 'data_inputs.json', 'fixtures.json'):
        if prereg.sha256_file(LANE/name) not in spec:
            raise ValueError('unbound R340 identity '+name)
    for name in ('code_inputs.json', 'data_inputs.json'):
        manifest = json.loads((LANE/name).read_text())
        if 'python_version' in manifest and manifest['python_version'] != list(sys.version_info[:3]):
            raise ValueError('Python version drift')
        for path, expected in manifest['sha256'].items():
            if prereg.sha256_file(ROOT/path) != expected:
                raise ValueError('frozen R340 drift '+path)


def report(out):
    verify()
    if out.exists(): raise ValueError('fresh result directory required')
    out.mkdir(parents=True)
    fixture = json.loads((LANE/'fixtures.json').read_text())
    acquisition = json.loads((LANE/'evidence/sources.json').read_text())
    current = [{'coin': coin, 'contract_type': maturity, 'cost_multiple': k,
        'input_reasons': acquisition['blocked'], 'quote': None, 'executable_expected_net': None,
        'actual_order_allowed': False} for coin in fixture['coins'] for maturity in fixture['maturities']
        for k in fixture['cost_multiples']]
    # Existing published R328 conditional plans, not raw new or historical prices.
    parent = json.loads((ROOT/fixture['held_plan_path']).read_text())
    held = []
    for source in parent['rows']:
        for control in source['controls']:
            for scale in fixture['delivery_price_scales']:
                item = {'coin': source['coin'], 'profile': source['profile'],
                    'fee_control': control['fee_control'], 'cost_multiple': control['cost_multiple'],
                    'delivery_price_scale': scale, 'input_error': source['input_error'],
                    'guard': None, 'hurdle': None, 'actual_executable_expected_net': None}
                projection = control['primary_future_result']
                if projection is not None:
                    p = source['plan']; a = F(projection['stressed_hedge_coin'])
                    b = F(p['initial_coin']); fee = F(projection['entry_fee_coin'])
                    item['guard'] = coverage(b, a, fee)
                    item['hurdle'] = terminal_hurdle(F(p['face_usd']), a, b, fee,
                        F(projection['delivery_fee_rate']), F(projection['spot_fee_rate']),
                        delivery_price=F(p['future_mid_usd'])*F(scale), exit_ratio=None,
                        initial_spend_quote=F(projection['initial_spend_usdt']),
                        total_capital_quote=F(projection['total_initial_capital_usdt']),
                        cash_benchmark_factor=1, idle_cash_factor=1, other_exit_cost_quote=0)
                held.append(item)
    # All129 received rounded lock rows, including both source robustness sets.
    # S0=1 and B=1 is dimensionless algebra, not actual executable quantities.
    normalized = []
    with (ROOT/fixture['rounded_ticket_path']).open() as handle:
        tickets = list(csv.DictReader(handle))
    for index, ticket in enumerate(tickets):
        future = 1+F(ticket['gross'])/100
        for k in fixture['cost_multiples']:
            for fees in fixture['fee_controls']:
                entry_rate = F(0) if fees == 'zero_charge' else F(fixture['future_entry_rate'])*k
                spot_rate = F(0) if fees == 'zero_charge' else F(fixture['spot_rate'])*k
                fee = entry_rate  # Q/F0=1 before all spot/futures costs.
                for debit in fixture['spot_fee_assets']:
                    purchased = F(1); net = purchased*(1-spot_rate) if debit == 'base' else purchased
                    spend = purchased if debit == 'base' else purchased*(1+spot_rate)
                    base = coverage(net, 1, fee)
                    reserved = prefund(1, fee, spot_rate, fee_asset=debit)
                    reserve_spend = reserved['gross_spot_base']*reserved['quote_cost_multiplier']
                    # Zero delivery/other fees is an optimistic diagnostic floor,
                    # not a public fee or future conversion attestation.
                    hurdle = terminal_hurdle(future, 1, reserved['net_collateral_coin'], fee,
                        0, spot_rate, delivery_price=None, exit_ratio=None,
                        initial_spend_quote=reserve_spend, total_capital_quote=10,
                        cash_benchmark_factor=1, idle_cash_factor=1, other_exit_cost_quote=0)
                    normalized.append({'ticket_row': index, 'ticket_identity': {k: ticket[k]
                        for k in ('coin', 'spot', 'hurdle', 'contract', 'entry_utc')},
                        'normalized_future_price': future, 'cost_multiple': k, 'fee_control': fees,
                        'spot_fee_asset_scenario': debit, 'unreserved_spot_spend': spend,
                        'unreserved_guard': base, 'prefunded': reserved,
                        'prefunded_spend': reserve_spend, 'prefunded_hurdle': hurdle,
                        'historical_pnl_recomputed': False, 'actual_expected_net': None})
    output = {'registry_id': 'R340', 'verdict': 'PARTIAL', 'current_inputs': current,
        'held_R328_guard_cells': held, 'R335_normalized_ticket_cells': normalized,
        'acquisition': acquisition, 'source_semantic_methods_read': 0,
        'historical_request_spend_unchanged': 7757, 'historical_reported_MiB_unchanged': '229.85',
        'program_trials_entering': 9479013, 'predictive_strategy_trials': 0, 'prospective_days': 0,
        'actual_executable_expected_net': None, 'activation_allowed': False,
        'new_historical_or_model_downloads': 0}
    (out/'results.json.gz').write_bytes(gzip.compress(encoded(output), mtime=0))
    verify()
    summary = {'current_null_slots': len(current), 'held_guard_slots': len(held),
        'held_guard_known': sum(r['guard'] is not None for r in held),
        'received_rounded_tickets': len(tickets), 'normalized_cells': len(normalized),
        'unreserved_model_coverage_failures': sum(r['unreserved_guard']['all_positive_marks_1x_model_coverage'] is False for r in normalized),
        'prefunded_model_coverage_failures': sum(r['prefunded']['coverage']['all_positive_marks_1x_model_coverage'] is False for r in normalized),
        'actual_executable_expected_net': None, 'prospective_days': 0}
    (out/'summary.json').write_bytes(encoded(summary)); return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(report(parser.parse_args().out), indent=2))
