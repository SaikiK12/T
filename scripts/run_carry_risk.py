"""R346 frozen read-only marked-carry and segregated-margin diagnostic."""
import argparse
from decimal import Decimal
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.inverse_cash import InverseContract, InverseCashAccount, unwire
from lab.inverse_risk import FlatInverseMargin, marked_view, portfolio_mark, basis_frontier
from lab.spot_cash import SpotCashAccount
from lab.stream_quotes import FrameClock
from scripts.run_same_venue_v2 import verify as verify_parent

LANE = ROOT / 'experiments/carry_risk_v1'
PARENT = ROOT / 'experiments/same_venue_carry_v2'
RAW = ROOT / 'experiments/same_venue_carry_v1/evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, (F, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def encoded(value):
    return (json.dumps(plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def load(path):
    content = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return json.loads(content, parse_float=Decimal)


def committed(path):
    name = str(path.relative_to(ROOT))
    if subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT) != path.read_bytes():
        raise ValueError('committed identity required: ' + name)


def verify():
    spec = (LANE / 'PREREG.md').read_text()
    prereg.verify(LANE / 'PREREG.md')
    for name in ('code_inputs.json', 'inputs.json', 'fixtures.json', 'source_review.json', 'margin_contract.json'):
        if sha(LANE / name) not in spec:
            raise ValueError('unbound frozen identity: ' + name)
        committed(LANE / name)
    for name in ('code_inputs.json', 'inputs.json'):
        manifest = load(LANE / name)
        for p, digest in manifest['sha256'].items():
            if sha(ROOT / p) != digest:
                raise ValueError('frozen input drift: ' + p)
    code = load(LANE / 'code_inputs.json')
    if code['python_version'] != list(sys.version_info[:3]):
        raise ValueError('runtime drift')
    for name in ('PREREG.md', 'PREREG.sha256'):
        committed(LANE / name)
    verify_parent(data=True)
    return load(LANE / 'fixtures.json'), load(LANE / 'margin_contract.json')


def reopen_model(model, packed, out):
    prefix = 'states/' + model['id'] + '/'
    texts = {k: v for k, v in packed.items() if k.startswith(prefix)}
    for name, content in texts.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as h:
            h.write(content.encode())
    spot_path = out / prefix / 'spot.jsonl'
    config = json.loads(texts[prefix + 'spot.jsonl'].splitlines()[0])['event']
    spot = SpotCashAccount(config['venue'], config['quote_asset'], config['initial_cash'], config['markets'],
                           FrameClock(**config['anchor']), journal_path=spot_path)
    if spot.cash != F(model['cash_usdc']) or spot.initial != 10000 or spot.pending or spot.reconciliation:
        raise ValueError('parent quote cash/account reconciliation drift')
    inverses = {}
    for coin, ownership in model['ownership'].items():
        path = out / prefix / (coin + '-inverse.jsonl')
        c = json.loads(texts[prefix + coin + '-inverse.jsonl'].splitlines()[0])['event']
        contract = dict(c['contract'])
        for field in ('face_step_usd', 'minimum_face_usd'):
            contract[field] = unwire(contract[field])
        account = InverseCashAccount(InverseContract(**contract), unwire(c['initial_coin']), FrameClock(**c['anchor']),
                                     journal_path=path)
        if (account.face >= 0 or account.pending or account.conflicts or account.delivered
                or account.coin != F(ownership['inverse_coin_after_fee'])
                or account.initial != F(ownership['same_coin_earmarked'])
                or account.initial != spot.holdings[coin + '_USDC'] or F(ownership['unearmarked_coin']) != 0):
            raise ValueError('parent same-coin ownership, fee or direction drift')
        inverses[coin] = account
    for name, content in texts.items():
        if (out / name).read_bytes() != content.encode():
            raise ValueError('read-only replay changed an existing journal')
    return spot, inverses, texts


def report(out):
    config, contract = verify()
    if out.exists():
        raise ValueError('fresh output directory required')
    out.mkdir(parents=True)
    parent = load(PARENT / 'results.json.gz')
    packed = load(PARENT / 'journals.json.gz')
    capture = load(RAW / 'capture.json')
    receipts = {r['name']: r for r in capture['records']}
    sources = tuple(contract['source_sha256'])
    rules = {coin: FlatInverseMargin(coin, 'S:SM', contract['maximum_face_usd'], contract['flat_share'],
        contract['start_leverage'], F(contract['maintenance_share_of_initial']), sources) for coin in config['coins']}
    publications = {}
    for coin in config['coins']:
        receipt = receipts[coin + '_future_book']
        raw = load(RAW / receipt['body'])['result']
        for field in ('mark_price', 'index_price'):
            value = raw.get(field)
            if type(value) not in (int, str, Decimal) or F(value) <= 0:
                raise ValueError('source-native positive exact ' + field + ' required')
        publications[coin] = {'mark_usd': F(raw['mark_price']), 'index_usd': F(raw['index_price']),
                              'publication_ns': raw['timestamp'] * 10**6,
                              'body_sha256': receipt['body_sha256'], 'received_utc_ns': receipt['received_utc_ns'],
                              'own_effective_clock_verified': False, 'historical_snapshot_not_current': True}
    portfolios = {x['id']: x for x in parent['portfolios']}
    models, worlds, frontiers, unchanged_journals = [], [], [], {}
    for model in parent['models']:
        spot, accounts, texts = reopen_model(model, packed, out)
        unchanged_journals.update(texts)
        plans = {x['coin']: x['plan'] for x in portfolios[model['portfolio']]['decisions'] if x['plan'] is not None}
        before = {coin: a.snapshot() for coin, a in accounts.items()}
        # Supplied mark/index/spot are from the ORIGINAL first-seen batch, not now.
        views = {}
        for denominator in config['denominator_controls'] + ['unknown']:
            legs = [marked_view(a, publications[coin]['mark_usd'], F(plans[coin]['spot_mid_usdc']),
                    publications[coin]['index_usd'], rules[coin], denominator=denominator,
                    seconds_to_expiry=F(a.contract.expiry_ns-a.anchor.utc_ns, 10**9)) for coin, a in accounts.items()]
            views[denominator] = {'legs': legs, 'portfolio': portfolio_mark(spot.cash, legs,
                source_input_complete=model['source_input_complete'], initial_capital=spot.initial)}
        residual = sum(((a.coin + a.face*a.entry_reciprocal) * F(plans[coin]['spot_mid_usdc'])
                         for coin, a in accounts.items()), F(0))
        reciprocal = sum((-a.face * F(plans[coin]['spot_mid_usdc']) / publications[coin]['mark_usd']
                           for coin, a in accounts.items()), F(0))
        passive_initial = {coin: a.initial for coin, a in accounts.items()}
        models.append({'id': model['id'], 'parent_portfolio': model['portfolio'], 'cost_multiple': model['cost_multiple'],
            'fee_control': model['fee_control'], 'spot_fee_asset': model['fee_asset'], 'cash_usdc': spot.cash,
            'source_input_complete': model['source_input_complete'], 'source_snapshot_views': views,
            'residual_spot_value_usdc': residual, 'reciprocal_mark_value_usdc': reciprocal,
            'initial_owned_coin': passive_initial, 'actual_risk_ready': False})
        for scale in config['coin_price_scales']:
            scale_f = F(scale)
            passive = spot.cash + sum((a.initial * F(plans[coin]['spot_mid_usdc']) * scale_f
                                        for coin, a in accounts.items()), F(0))
            for beta in config['common_future_mark_factors']:
                beta_f = F(beta)
                for denominator in config['denominator_controls']:
                    legs = [marked_view(a, publications[coin]['mark_usd'] * scale_f * beta_f,
                        F(plans[coin]['spot_mid_usdc']) * scale_f, publications[coin]['index_usd'] * scale_f,
                        rules[coin], denominator=denominator,
                        seconds_to_expiry=F(a.contract.expiry_ns-a.anchor.utc_ns, 10**9)) for coin, a in accounts.items()]
                    total = portfolio_mark(spot.cash, legs, source_input_complete=model['source_input_complete'],
                                           initial_capital=spot.initial)
                    worlds.append({'model': model['id'], 'coin_price_scale': scale,
                        'common_future_mark_factor': beta, 'denominator_control': denominator,
                        'kind': 'fixed_conditional_state_not_market_path', 'legs': legs, 'portfolio': total,
                        'cash_control_usdc': spot.initial,
                        'matched_spot_only_control_usdc': passive if model['source_input_complete'] else None,
                        'actual_expected_net': None})
            for loss in config['loss_floor_fractions']:
                boundary = basis_frontier(spot.cash, residual*scale_f, reciprocal, spot.initial, loss)
                frontiers.append({'model': model['id'], 'coin_price_scale': scale, 'loss_floor_fraction': loss,
                    'source_input_complete': model['source_input_complete'],
                    'conditional_boundary': boundary if model['source_input_complete'] else None,
                    'actual_policy_risk_limit': None})
        if {coin: a.snapshot() for coin, a in accounts.items()} != before:
            raise ValueError('risk observation mutated financial state')
    result = {'registry_id': 'R346', 'source_publications': publications, 'models': models, 'worlds': worlds,
              'frontiers': frontiers, 'capital_usdc_per_alternative': config['capital_usdc'],
              'predictive_trials': 0, 'new_prospective_strategy_days': 0, 'activation_allowed': False,
              'actual_margin_certification': None, 'actual_executable_expected_net': None,
              'historical_price_path_replayed': False, 'historical_acquisition_requests_unchanged': 7757}
    with (out / 'results.json.gz').open('xb') as h:
        h.write(gzip.compress(encoded(result), mtime=0))
    with (out / 'journals.json.gz').open('xb') as h:
        h.write(gzip.compress(encoded(unchanged_journals), mtime=0))
    verify()
    return {'models': len(models), 'conditional_states': len(worlds), 'loss_frontiers': len(frontiers),
            'unchanged_parent_journals': len(unchanged_journals), 'actual_risk_ready': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    print(json.dumps(report(p.parse_args().out), indent=2))
