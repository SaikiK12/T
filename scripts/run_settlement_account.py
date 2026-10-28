"""R357: frozen R355 counterexamples and native fixed-inventory accounting.

No network, live journal, strategy selection, historical replay or activation.
"""
import argparse
from dataclasses import asdict
from decimal import Decimal as D, localcontext
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.paper_account import PaperAccount
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.settlement_account import EntryLeg, SettlementAccount, nominal_exit_inventory
from lab.funding_values import FundingContract, FundingEvent, ValuePacket
from lab.stream_quotes import FrameClock, NS, StreamBook
from lab.microstructure import DepthLevel, DepthSnapshot

LANE = ROOT / 'experiments/settlement_account_v1'
UTC = 1_790_000_000 * NS
ANCHOR = FrameClock(UTC, 10 * NS)


def clock(s):
    return FrameClock(UTC + s * NS, ANCHOR.mono_ns + s * NS)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def verify():
    prereg.verify(LANE / 'PREREG.md')
    spec = (LANE / 'PREREG.md').read_text()
    for name in ('PREREG.md', 'PREREG.sha256', 'config.json', 'sources.json', 'code_inputs.json', 'inputs.json'):
        path = LANE / name
        if name.endswith('.json') and sha(path) not in spec:
            raise ValueError('manifest not bound in prereg: ' + name)
        if subprocess.check_output(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT) != path.read_bytes():
            raise ValueError('spec/input must be committed before outcomes')
    for manifest in ('code_inputs.json', 'inputs.json'):
        data = json.loads((LANE / manifest).read_text())
        for path, expected in data['sha256'].items():
            if sha(ROOT / path) != expected:
                raise ValueError('frozen input drift: ' + path)
    if json.loads((LANE / 'code_inputs.json').read_text())['python_version'] != list(sys.version_info[:3]):
        raise ValueError('Python runtime differs from frozen identity')
    return json.loads((LANE / 'config.json').read_text())


def source_rule():
    path = LANE / 'source/scripts__settlehop_rule.py'
    spec = importlib.util.spec_from_file_location('r357_unchanged_r355_rule', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def levels(mid, half, size):
    return {'bids': [(float(mid - half), float(size))], 'asks': [(float(mid + half), float(size))]}


def typed_book(venue, raw, second):
    c = clock(second)
    depth = DepthSnapshot('BTC', c.utc_ns, c.mono_ns,
        tuple(DepthLevel(*x) for x in raw['bids']), tuple(DepthLevel(*x) for x in raw['asks']))
    return StreamBook(venue, 'BTC', c, depth, 1, 'R357 invented complete depth')


def run_cell(out, config, case, direction, multiple, rule):
    name = case['id'] + '_d' + str(direction) + '_k' + str(multiple)
    folder = out / name
    folder.mkdir()
    half, mid, usd = map(D, (config['half_spread'], config['entry_mid'], config['leg_quote_budget']))
    raw_entry = {v: levels(mid, half, D(100)) for v in ('mexc', 'lighter')}
    raw_exit = {v: levels(D(case.get(p + '_mid', mid)), half, D(case.get(p + '_size', 100)))
                for v, p in (('mexc', 's'), ('lighter', 'h'))}
    if case.get('missing_s'):
        raw_exit['mexc'] = None
    second = case.get('exit_second', config['exit_second'])
    ticket = {'hop': name, 'venue': 'mexc', 'd': direction, 'ms': clock(1).utc_ns // 1_000_000,
              'fee_s_bp': config['fees_bp']['mexc'], 'fee_h_bp': config['fees_bp']['lighter']}
    exit_ticket = {**ticket, 'ms': clock(second).utc_ns // 1_000_000}
    entry_legs, source_inventory = [], {}
    for venue, prefix, buy, asset in (('mexc', 's', direction < 0, 'USDT'), ('lighter', 'h', direction > 0, 'USDC')):
        p, got, thin = rule.side_fill(raw_entry[venue], buy=buy)
        if thin or D(str(got)) != usd:
            raise ValueError('invented entry unexpectedly lacks depth')
        q = (1 if buy else -1) * usd / D(str(p))
        ticket.update({prefix + '_bid': raw_entry[venue]['bids'][0][0], prefix + '_ask': raw_entry[venue]['asks'][0][0],
                       prefix + '_fill': p, prefix + '_usd': got})
        entry_legs.append(EntryLeg(venue, asset, 'BTC', q, D(str(p)), mid,
                                   D(config['fees_bp'][venue]), clock(1), 'R357 invented entry:' + venue))
        if raw_exit[venue] is not None:
            px, filled, thin = rule.side_fill(raw_exit[venue], buy=not buy, complete=False)
            exit_ticket.update({prefix + '_bid': raw_exit[venue]['bids'][0][0], prefix + '_ask': raw_exit[venue]['asks'][0][0],
                                prefix + '_fill': px, prefix + '_usd': filled})
            source_inventory[venue] = {**nominal_exit_inventory(q, D(str(px)), usd), 'thin_extrapolated': thin,
                                       'legacy_reported_quote_filled': str(filled)}
    initial = {('mexc', 'USDT'): D(case.get('s_capital', config['initial_per_venue'])),
               ('lighter', 'USDC'): D(case.get('h_capital', config['initial_per_venue']))}
    account = PaperAccount(initial, ANCHOR, journal_path=folder / 'account.jsonl')
    adapter = SettlementAccount(account, multiple)
    entry_result = adapter.enter_pair(name, entry_legs, clock(1).mono_ns)
    close_results = {}
    if entry_result['state'] == 'conditional_model':
        for venue, asset, prefix in (('mexc', 'USDT', 's'), ('lighter', 'USDC', 'h')):
            b = None if raw_exit[venue] is None else typed_book(venue, raw_exit[venue], case.get(prefix + '_receive_second', second))
            close_results[venue] = adapter.close_fixed(venue, asset, 'BTC', b,
                D(config['fees_bp'][venue]), clock(second).mono_ns)
    assessments = []
    s_rates, h_rates = [], []
    if case.get('funding'):
        event_second = config['funding_second']
        for venue, asset, rate, effective in (('mexc', 'USDT', config['source_s_rate'], config['s_effective_value']),
                                              ('lighter', 'USDC', config['source_h_rate'], config['h_effective_value'])):
            (s_rates if venue == 'mexc' else h_rates).append((clock(event_second).utc_ns // 1_000_000, float(rate)))
            contract = FundingContract(venue, 'BTC', 'linear_base', asset, True, 'R357 invented dimension contract',
                'BTC', asset, 15 * NS if venue == 'mexc' else 0)
            event = FundingEvent('evt:' + venue, venue, 'BTC', clock(event_second).utc_ns,
                D(rate), 'fraction', 'settled', clock(40))
            packet = None if case['funding'] == 'missing' else ValuePacket(venue, 'BTC',
                'fair' if venue == 'mexc' else 'index', D(effective), clock(40), clock(40).utc_ns,
                'settlement_value', 'R357 invented effective event value', event.funding_ns, event.event_id)
            if entry_result['state'] == 'conditional_model':
                assessments.append(adapter.funding(contract, event, packet, clock(40),
                    index_basis='pre_update_event_index' if venue == 'lighter' else None))
    legacy = None if raw_exit['mexc'] is None else rule.score(ticket, exit_ticket, s_rates, h_rates)
    report = adapter.report(clock(40).mono_ns, fx=config['fx_scenario'])
    risk_args = dict(asof=clock(40).mono_ns, clock=clock(40), complete=True, session_open=True,
                     fee_inputs_known=True, contract_version='R357-fixture', expected_contract_version='R357-fixture', mode='fixture')
    policy = RiskPolicy('R357 fixed policy')
    risk = PaperRisk(folder / 'risk.jsonl', policy, ANCHOR, contract_version='R357-fixture', initial_balances=initial)
    risk_result = risk.observe(report['native'], **risk_args)
    reopened = PaperAccount(initial, ANCHOR, journal_path=folder / 'account.jsonl')
    restored = SettlementAccount(reopened, multiple).report(clock(40).mono_ns, fx=config['fx_scenario'])
    if restored != report:
        raise ValueError('native account restart did not reproduce state')
    restored_risk = PaperRisk(folder / 'risk.jsonl', policy, ANCHOR, contract_version='R357-fixture', initial_balances=initial)
    risk_restart = restored_risk.observe(restored['native'], **risk_args)
    return {'id': name, 'case': case['id'], 'direction': direction, 'cost_multiple': multiple,
            'constructed_entry': ticket, 'constructed_exit': exit_ticket, 'constructed_exit_books': raw_exit,
            'entry_quantities': {x.venue: str(x.quantity) for x in entry_legs},
            'legacy_nominal_inventory': source_inventory, 'legacy_score': legacy,
            'legacy_normalized_quote_proxy': None if legacy is None else str(D(str(legacy[f'net{multiple}_web'])) * usd),
            'native_entry': entry_result, 'native_closes': close_results, 'funding_assessments': assessments,
            'report': report, 'risk': risk_result, 'risk_after_restart': risk_restart,
            'source_receipt_or_actual_fill_verified': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    config = verify()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    rule = source_rule()
    with localcontext() as context:
        context.prec = config['precision']
        cells = [run_cell(out, config, case, d, k, rule) for case in config['cases']
                 for d in config['directions'] for k in config['cost_multiples']]
    verify()
    result = {'registry_id': 'R357', 'kind': config['kind'], 'cells': cells,
              'new_predictive_trials': 0, 'prospective_strategy_days': 0, 'actual_expected_net': None}
    pack = {str(p.relative_to(out)): p.read_text() for p in sorted(out.rglob('*.jsonl'))}
    for name, value in (('results.json.gz', result), ('journals.json.gz', pack)):
        with (out / name).open('xb') as handle:
            handle.write(gzip.compress(encode(value), mtime=0))
    print(json.dumps({'registry_id': 'R357', 'cells': len(cells), 'out': str(out), 'actual_expected_net': None}))


if __name__ == '__main__':
    main()
