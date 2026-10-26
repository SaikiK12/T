"""R322 finite source-arithmetic/account fixtures; no market collection or policy."""
import argparse
from dataclasses import asdict, replace
from decimal import Decimal as D
import gzip
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.funding_prefix import (PrefixPosition, PrefixObservation, assess, before_resize,
                                margin_component, paper_event)
from lab.paper_account import PaperAccount, PaperEvent, CloseMark
from lab.stream_quotes import FrameClock, NS

LANE = ROOT / 'experiments/funding_prefix_v1'
ANCHOR = FrameClock(1_800_000_000 * NS, 100 * NS)  # Invented clock, not a market observation.
sha = prereg.sha256_file


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def save(path, value):
    with path.open('xb') as handle:
        handle.write(encode(value))


def clock(seconds):
    return FrameClock(ANCHOR.utc_ns + seconds * NS, ANCHOR.mono_ns + seconds * NS)


def verify(lane=LANE):
    prereg.verify(lane / 'PREREG.md')
    specification = (lane / 'PREREG.md').read_text()
    for name in ('code_inputs.json', 'inputs.json', 'fixtures.json', 'contract.json', 'sources.json'):
        if sha(lane / name) not in specification:
            raise ValueError('unbound prefix model contract: ' + name)
    code = json.loads((lane / 'code_inputs.json').read_text())
    if code['python_version'] != list(sys.version_info[:3]):
        raise ValueError('prefix model runtime drift')
    for manifest in (code, json.loads((lane / 'inputs.json').read_text())):
        for name, checksum in manifest['sha256'].items():
            if sha(ROOT / name) != checksum:
                raise ValueError('prefix model input/code drift: ' + name)
    return json.loads((lane / 'fixtures.json').read_text())


def supplied_position(**kwargs):
    values = dict(account_id='invented-account', market_id=7, strategy_index=0,
                  margin_mode='cross', size_units=1_000_000, last_prefix=0,
                  quote_multiplier=100, parameter_epoch='invented-epoch', initialized=True,
                  last_update_ns=ANCHOR.utc_ns, clock=ANCHOR)
    return PrefixPosition(**{**values, **kwargs})


def supplied_observation(prefix, step=1, **kwargs):
    values = dict(event_id='invented-' + str(step), market_id=7, strategy_index=0,
                  prefix=prefix, quote_multiplier=100, parameter_epoch='invented-epoch',
                  occurred_ns=clock(step).utc_ns, clock=clock(step), source_identity='invented-receipt',
                  input_scope='invented_encoded_fixture')
    return PrefixObservation(**{**values, **kwargs})


def arithmetic_rows(fixtures):
    grid = fixtures['arithmetic']
    rows = []
    for q, Q, C, P, mode in itertools.product(grid['sizes'], grid['multipliers'], grid['checkpoints'],
                                             grid['prefixes'], grid['modes']):
        position = supplied_position(size_units=q, quote_multiplier=Q, last_prefix=C, margin_mode=mode)
        observation = supplied_observation(P, quote_multiplier=Q)
        rows.append({'size_units': q, 'quote_multiplier': Q, 'checkpoint': C, 'prefix': P,
                     'margin_mode': mode, 'assessment': assess(position, observation, clock(1).mono_ns, ANCHOR)})
    return rows


def run_path(config, multiple, control, fixtures, out):
    p = supplied_position(size_units=config['initial_size'], margin_mode=config['mode'])
    path = out / 'model_journals' / (config['id'] + '-' + str(multiple) + '-' + control + '.jsonl')
    path.parent.mkdir(exist_ok=True)
    if path.exists():
        raise ValueError('existing model journal retained')
    balances = {('mexc-model', 'USDT'): fixtures['capital_per_bucket'], p.bucket(): fixtures['capital_per_bucket']}
    account = PaperAccount(balances, ANCHOR, journal_path=path)
    unit = D(fixtures['fixture_size_units_per_physical_base'])
    price = D(fixtures['flat_fixture_price'])
    fee_fraction = D(fixtures['fee_fraction']) * multiple
    bucket = p.bucket()

    def fill(quantity, step, label):
        if not quantity:
            return
        event = PaperEvent(label, 'fill', *bucket, str(p.market_id), clock(step).utc_ns,
                           clock(step), 'invented-flat-fill/base-mapping/fee',
                           quantity=quantity, price=price, fee=abs(quantity) * price * fee_fraction)
        if account.post(event, clock(step).mono_ns)['status'] != 'applied':
            raise ValueError('fixture fill rejected')

    fill(D(p.size_units) / unit, 0, 'invented-open')
    records = []
    for step, (prefix, delta) in enumerate(config['updates'], 1):
        o = supplied_observation(prefix, step, input_scope=config.get('input_scope', 'invented_encoded_fixture'))
        assessment = assess(p, o, clock(step).mono_ns, ANCHOR)
        transition = before_resize(p, o, delta, clock(step).mono_ns, ANCHOR)
        event = paper_event(p, o, assessment, clock(step).mono_ns, ANCHOR)
        if control == 'same_fixture_no_funding':
            event = replace(event, amount=D(0), source_identity='invented-zero-funding-reference')
        status = account.post(event, clock(step).mono_ns)['status']
        # A new provider label/receipt for the same economic start cannot pay twice.
        alias = replace(o, event_id='alias-' + o.event_id, source_identity='alias-receipt')
        duplicate = paper_event(p, alias, assess(p, alias, clock(step).mono_ns, ANCHOR), clock(step).mono_ns, ANCHOR)
        if control == 'same_fixture_no_funding':
            duplicate = replace(duplicate, amount=D(0), source_identity='invented-zero-funding-reference')
        duplicate_status = account.post(duplicate, clock(step).mono_ns)['status']
        if status != 'applied' or duplicate_status != 'duplicate':
            raise ValueError('fixture funding receipt/dedup failed')
        records.append({'old_position': asdict(p), 'observation': asdict(o), 'provider_alias': asdict(alias),
                        'assessment': assessment, 'ledger_status': status, 'alias_status': duplicate_status,
                        'transition_state': transition['state'], 'size_delta_units': delta,
                        'posting_amount': None if event.amount is None else str(event.amount)})
        if transition['next_position'] is not None:
            fill(D(delta) / unit, step, 'invented-resize-' + str(step))
            p = transition['next_position']
    at = clock(10)
    marks = []
    if p.size_units:
        q = D(p.size_units) / unit
        marks = [CloseMark(*bucket, str(p.market_id), q, abs(q) * price,
                           abs(q) * price * fee_fraction, at, at.utc_ns, 'invented-flat-liquidation')]
    snapshot = account.snapshot(at.mono_ns, marks)
    reopened = PaperAccount(balances, ANCHOR, journal_path=path)
    if reopened.snapshot(at.mono_ns, marks) != snapshot:
        raise ValueError('existing common account replay mismatch')
    accounts = snapshot['accounts']
    complete = all(a['nav'] is not None for a in accounts)
    net = (sum(D(a['nav']) - D(a['initial_cash']) - D(a['external_capital_flows'])
               for a in accounts) if complete else None)
    return {'id': config['id'], 'cost_multiple': multiple, 'control': control,
            'records': records, 'snapshot': snapshot,
            'funding_known_component': str(sum(account.funding.values())),
            'fees_paid': str(sum(account.fees.values())),
            'component_fixture_net': None if net is None else str(net),
            'component_fixture_return_on_total_capital': None if net is None else str(net / D(fixtures['total_capital'])),
            'journal': str(path.relative_to(out)), 'journal_sha256': sha(path), 'reopened_identical': True,
            'actual_market_cash_or_return': None, 'scope': 'Invented matched flat-price funding/account fixture only'}


def report(lane=LANE, out=None):
    fixtures = verify(lane)
    out = Path(out) if out is not None else lane
    if (out / 'results.json').exists() or (out / 'model_journals').exists():
        raise ValueError('existing outcome retained; explicit new --out required for reproduction')
    out.mkdir(parents=True, exist_ok=True)
    arithmetic = arithmetic_rows(fixtures)
    rounding = [{'old_collateral': old, 'funding_delta': delta, 'result': margin_component(old, delta)}
                for old, delta in itertools.product(fixtures['rounding']['old_collateral'],
                                                    fixtures['rounding']['funding_delta'])]
    paths = [run_path(path, k, control, fixtures, out) for path, k, control in
             itertools.product(fixtures['paths'], fixtures['cost_multiples'], fixtures['cashflow_controls'])]
    counts = dict(arithmetic=len(arithmetic), rounding=len(rounding), path_cost_control_accounts=len(paths))
    if counts != fixtures['expected_counts']:
        raise ValueError('registered finite scope drift')
    payload = {'arithmetic': arithmetic, 'rounding': rounding, 'paths': paths}
    raw = gzip.compress(encode(payload), mtime=0)
    with (out / 'observations.json.gz').open('xb') as handle:
        handle.write(raw)
    summary = {'registry_id': 'R322', 'verdict': 'PARTIAL', 'scope': 'Source-level funding-component adapter only',
               'counts': counts, 'contract_sha256': sha(lane / 'contract.json'), 'fixtures_sha256': sha(lane / 'fixtures.json'),
               'code_identity_sha256': sha(lane / 'code_inputs.json'), 'observations_sha256': sha(out / 'observations.json.gz'),
               'paths': [{k: p[k] for k in ('id', 'cost_multiple', 'control', 'funding_known_component', 'fees_paid',
                           'component_fixture_net', 'component_fixture_return_on_total_capital', 'reopened_identical')}
                         for p in paths],
               'source_application_located': True, 'API_cash_bridge_verified': False,
               'actual_cash_decoder': False, 'strategy_trials': 0, 'new_prospective_paper_days': 0,
               'new_market_requests': 0, 'actual_order_allowed': False, 'net_market_return': None,
               'cost_sensitivity': [{'multiple': k, 'net_market_return': None, 'fixture_only': True} for k in (1, 2, 3)],
               'inference': 'Deterministic component fixtures, no sample inference or profitability claim',
               'old_market_results_reclassified': False, 'historical_requests_spent': 7757, 'reported_mib_spent': '229.85'}
    verify(lane)
    save(out / 'results.json', summary)
    return out / 'results.json'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    print(report(out=parser.parse_args().out))
