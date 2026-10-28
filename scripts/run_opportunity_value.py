"""R334 frozen offline opportunity-to-account integration; never trades or fetches.

Invented forecasts validate mechanics only. Retained R318 paired costs give
hurdles, never manufactured forecasts, filled orders or prospective PnL.
"""
import argparse
from collections import Counter
from dataclasses import replace
from decimal import Decimal as D
import gzip
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.microstructure import DepthLevel, DepthSnapshot
from lab.stream_quotes import FrameClock, StreamBook, NS
from lab.paper_account import PaperAccount
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.opportunity_value import Opportunity, Outcome, assess_batch

LANE = ROOT/'experiments/opportunity_value_v1'


def encode(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def verify(lane):
    prereg.verify(lane/'PREREG.md'); spec = (lane/'PREREG.md').read_text()
    for name in ('code_inputs.json', 'data_inputs.json', 'fixtures.json'):
        if prereg.sha256_file(lane/name) not in spec: raise ValueError('unbound input: '+name)
    code = json.loads((lane/'code_inputs.json').read_text())
    if code['python_version'] != list(sys.version_info[:3]): raise ValueError('runtime drift')
    for manifest in (code, json.loads((lane/'data_inputs.json').read_text())):
        for path, digest in manifest['sha256'].items():
            if prereg.sha256_file(ROOT/path) != digest: raise ValueError('input drift: '+path)


def constructed_case(config, case, scratch):
    anchor = FrameClock(**config['anchor']); clock = FrameClock(anchor.utc_ns+NS, anchor.mono_ns+NS)
    account = PaperAccount({('mexc', 'USDT'): 1000}, anchor, journal_path=scratch/'account.jsonl')
    policy = RiskPolicy('R334-invented', max_symbol_gross_fraction=D(case.get('max_symbol_fraction', '.25')))
    risk = PaperRisk(scratch/'risk.jsonl', policy, anchor, contract_version='R334-invented-v1',
                     initial_balances={('mexc', 'USDT'): 1000})
    risk_inputs = dict(clock=clock, complete=not case.get('risk_stop', False), session_open=True, fee_inputs_known=True,
        contract_version='R334-invented-v1', expected_contract_version='R334-invented-v1', mode='fixture')
    opportunities = []; books = {}; markets = {}; fees = {}
    for row in case['opportunities']:
        o = Opportunity(row['id'], row.get('model_id', 'invented-breakout'), 'mexc', row.get('asset', 'USDT'),
            'ETH', D(row.get('quantity', '1')), clock, clock.utc_ns+12*3600*NS,
            tuple(Outcome(*x) for x in row.get('outcomes', [['.9', '100', '0'], ['.1', '-100', '0']])),
            D(row.get('error', '2')) if row.get('error', '2') is not None else None,
            None if row.get('uncalibrated') else 'invented-calibration-not-market-evidence',
            None if row.get('reserve_unknown') else D('.5'))
        opportunities.append(o)
        b = StreamBook(o.venue, o.symbol, clock,
            DepthSnapshot(o.symbol, clock.utc_ns, clock.mono_ns,
                (DepthLevel(99.5, 20),), (DepthLevel(100.5, .5 if row.get('thin') else 20),)),
            1, 'invented-R334-book')
        if row.get('future_book'): b = replace(b, clock=FrameClock(clock.utc_ns+NS, clock.mono_ns+NS))
        books[o.opportunity_id] = b
        markets[o.opportunity_id] = {'state': 'unknown' if row.get('market_unknown') else 'pass',
            'asof_mono_ns': clock.mono_ns, 'quantity_base': str(abs(o.quantity)),
            'venue': o.venue, 'asset': o.asset, 'symbol': o.symbol,
            'contract_model': 'linear_base', 'quote_asset': o.asset, 'step_base': '.1', 'min_base': '.1', 'max_base': '20',
            'valid_from_utc_ns': clock.utc_ns, 'valid_until_utc_ns': clock.utc_ns+NS,
            **{f: 'invented-not-authenticated' for f in ('source_identity', 'fee_source_identity', 'lot_source_identity',
                                                      'session_source_identity', 'settlement_source_identity')},
            'scope': 'invented market/lot/fee/settlement contract; no actual entitlement'}
        fees[o.opportunity_id] = None if row.get('fee_unknown') else '10'
    prefix = (scratch/'account.jsonl').read_bytes()
    result = assess_batch(account, opportunities, books, fees, asof=clock.mono_ns, anchor=anchor,
        risk=risk, risk_inputs=risk_inputs, market_reports=markets)
    if (scratch/'account.jsonl').read_bytes() != prefix: raise ValueError('forecast changed financial journal')
    result['name'] = case['name']; result['journal_sha256'] = prereg.sha256_file(scratch/'account.jsonl')
    result['financial_journal_unchanged'] = True
    return result


def held_hurdles(rows):
    """Read already-published pair cost cells as conditional hurdles, not books."""
    for row in rows:
        for size in row['sizes']:
            cost = size.get('cost')
            for k in (1, 2, 3):
                known = bool(cost and cost.get('displayed_fillable'))
                hurdle = cost['scenarios'][k-1]['round_trip_cost_usd'] if known else None
                yield {'symbol': row['symbol'], 'grid_second': row['grid_second'], 'delay_ms': row['delay_ms'],
                    'leg_budget_quote': size['leg_budget_quote'], 'quantity_base': size.get('quantity_base'),
                    'cost_multiple': k, 'minimum_gross_before_error_quote_equivalent': hurdle,
                    'known_cost_state': 'conditional_quote_parity_proxy' if known else 'unavailable',
                    'expected_gross_quote': None, 'forecast_error_quote': None, 'expected_net_quote': None,
                    'model_entry_allowed': False, 'actual_order_allowed': False,
                    'input_readiness': row['readiness']['state'], 'capital_total_quote_equivalent': 10000,
                    'capital_per_venue_quote_equivalent': 5000,
                    'reasons': ['no_calibrated_forecast', 'future_exit_not_observed',
                                'source_session_fee_settlement_limits_retained'],
                    'scope': 'same retained paired round-trip reserve plus crossing; not a fresh quote or forecast'}


def report(out, lane=LANE):
    verify(lane)
    if out.exists(): raise ValueError('fresh output directory required')
    out.mkdir(parents=True)
    config = json.loads((lane/'fixtures.json').read_text())
    with tempfile.TemporaryDirectory(prefix='R334-') as directory:
        cases = []
        for i, case in enumerate(config['cases']):
            scratch = Path(directory)/str(i); scratch.mkdir()
            cases.append(constructed_case(config, case, scratch))
    source = ROOT/'experiments/paper_account_v1/observations.jsonl.gz'
    rows = [json.loads(x) for x in gzip.decompress(source.read_bytes()).splitlines()]
    held = list(held_hurdles(rows))
    result = {'registry_id': 'R334', 'verdict': 'PARTIAL', 'simulation_only': True,
        'activation_allowed': False, 'actual_net_return': None, 'new_market_requests': 0,
        'predictive_trials': 0, 'prospective_days': 0, 'cases': cases,
        'held': {'deadlines': len(rows), 'size_cost_cells': len(held),
            'known_conditional_hurdles': sum(r['minimum_gross_before_error_quote_equivalent'] is not None for r in held),
            'admissible_opportunities': 0, 'reasons': dict(Counter(r['input_readiness'] for r in held))},
        'scope': 'offline single-batch integration and already-seen cost hurdles; no new economic return observations',
        'remaining_runtime_bridge': 'Durable opportunity reservation, terminal release and fill joins must precede any repeated/concurrent paper allocator.',
        'source_sha256': prereg.sha256_file(source)}
    verify(lane)
    artifacts = {'results.json': encode(result),
        'held_hurdles.jsonl.gz': gzip.compress(b''.join(encode(r).replace(b'\n', b'')+b'\n' for r in held), mtime=0)}
    for name, raw in artifacts.items():
        with (out/name).open('xb') as h: h.write(raw)
    manifest = {name: prereg.sha256_file(out/name) for name in artifacts}
    with (out/'manifest.json').open('xb') as h: h.write(encode({'sha256': manifest}))
    return out/'results.json'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, required=True)
    print(report(p.parse_args().out))
