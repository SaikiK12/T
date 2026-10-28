"""Independent R360 money arithmetic + original byte/timeliness preservation.

Only the standard library is imported. Source-state equality uses the frozen
assembler in the benchmark; this checker does not claim a second venue parser.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'experiments/live_pair_controls_v1'
LANE = ROOT / 'experiments/incremental_pair_control_v1'


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


class Check:
    def __init__(self): self.n = 0

    def eq(self, a, b, label):
        self.n += 1
        if a != b: raise AssertionError((label, a, b))

    def near(self, actual, expected, label):
        self.n += 1
        if actual is None or abs(F(str(actual)) - expected) > F('1e-60'):
            raise AssertionError((label, actual, str(expected)))


def sweep(book, signed):
    remaining, total = abs(signed), F(0)
    for price, size in book['asks' if signed > 0 else 'bids']:
        take = min(remaining, F(str(size)))
        total += take * F(str(price)); remaining -= take
        if remaining == 0: return total / abs(signed)
    raise AssertionError('component fill exceeds displayed capacity')


def check_money(core, config, check=None):
    c = check or Check()
    c.eq(core['registry_id'], 'R359', 'original identity is preserved')
    c.eq(len(core['cells']), 36, 'all old cost cells retained')
    c.eq(core['prospective_strategy_days'], 0, 'no new strategy days')
    c.eq(core['full_net_pnl'], None, 'no fabricated complete net')
    receipts = {r['stage']: r for r in core['online_receipts']}
    quantities, outcomes = {}, []
    for cell in core['cells']:
        for key in ('full_net_pnl', 'funding_cash', 'full_account_nav', 'actual_expected_net'):
            c.eq(cell[key], None, key + ' remains unknown')
        c.eq(cell['price_fee_fx_scenario'], {'USDC': '1', 'USDT': '1'}, 'explicit original FX scenario')
        c.eq(cell['cost_multiple'] in (1, 2, 3), True, 'fixed costs')
        accounts = cell['price_fee_only_native_snapshot']['accounts']
        c.eq({(a['venue'], a['asset']) for a in accounts},
             {('mexc', 'USDT'), ('lighter', 'USDC')}, 'separate native venue assets')
        for account in accounts:
            c.near(account['initial_cash'], F(config['capital_per_venue']), 'full segregated capital')
        if cell['closed_price_fee_subtotal'] is None: continue
        symbol, direction, k = cell['symbol'], cell['direction'], cell['cost_multiple']
        q = F(cell['quantity']); c.eq(q > 0, True, 'original positive quantity')
        identity = symbol, direction
        if identity in quantities: c.eq(q, quantities[identity], 'same quantity at all cost tiers')
        quantities[identity] = q
        total = F(0)
        entry = receipts['entry_execution']['views'][symbol]['books']
        exit_ = receipts['exit_execution']['views'][symbol]['books']
        for venue, signed, a, b in zip(('mexc', 'lighter'), (-direction*q, direction*q), entry, exit_):
            pa, pb = sweep(a, signed), sweep(b, -signed)
            ma = (F(str(a['bids'][0][0])) + F(str(a['asks'][0][0]))) / 2
            mb = (F(str(b['bids'][0][0])) + F(str(b['asks'][0][0]))) / 2
            pa, pb = ma+k*(pa-ma), mb+k*(pb-mb)
            fees = q * (pa+pb) * F(config['fees_bp'][venue]) * k / 10000
            expected = signed*(pb-pa) - fees
            native = next(r for r in accounts if r['venue'] == venue)
            c.near(native['known_realized_net_component'], expected, 'independent native price-minus-fee cash')
            c.eq(native['positions'], [], 'exit flattens exact original inventory')
            close = cell['exit'][venue]
            c.near(close['quantity'], -signed, 'exact opposite exit quantity')
            c.eq(close['model_action_clock'], receipts['exit_execution']['decision_clock'], 'actual old action clock')
            c.eq(close['source_first_seen_clock'], b['clock'], 'old quote receipt unchanged')
            total += expected
        c.near(cell['closed_price_fee_subtotal'], total, 'independent summed price-fee component')
        c.near(cell['funding_needed_to_break_even'], -total, 'funding break-even component only')
        outcomes.append({'id': cell['id'], 'quantity': cell['quantity'],
                         'closed_price_fee_subtotal': cell['closed_price_fee_subtotal'],
                         'funding_needed_to_break_even': cell['funding_needed_to_break_even']})
    return c, outcomes


def run(directory, out):
    out.mkdir(exist_ok=False)
    c = Check()
    identity = json.loads((LANE / 'input_identity.json').read_text())
    for path, expected in identity['sha256'].items():
        c.eq(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected, 'old input identity:' + path)
    benchmark = json.loads((directory / 'benchmark.json').read_text())
    c.eq(benchmark['registry_id'], 'R360', 'outer validation identity')
    c.eq(benchmark['new_alpha_variants'], 0, 'no new predictive trial')
    c.eq(benchmark['new_prospective_tickets'], 0, 'no new first-seen proof')
    c.eq(len(benchmark['runs']), 10, 'all fixed five paired repetitions')
    source_result = (SOURCE / 'results.json').read_bytes()
    expected_files = {p.name: p.read_bytes() for p in (SOURCE / 'evidence/online').iterdir() if p.is_file()}
    config = json.loads((SOURCE / 'config.json').read_text())
    outcomes = None
    for run in benchmark['runs']:
        path = directory / f"{run['repetition']:02d}_{run['profile']}"
        raw = (path / 'core_result.json').read_bytes()
        c.eq(raw, source_result, 'complete old report bytes including missed/late/inactive states')
        c.eq(hashlib.sha256(raw).hexdigest(), run['core_result_sha256'], 'measured core hash')
        files = {p.name:p.read_bytes() for p in (path/'online').iterdir() if p.is_file()}
        c.eq(set(files), set(expected_files), 'complete old journal/receipt inventory')
        for name, data in files.items():
            c.eq(data, expected_files[name], 'exact native/evidence journal:' + name)
            c.eq(hashlib.sha256(data).hexdigest(), run['journal_and_receipt_sha256'][name], 'reported journal hash')
        core = json.loads(raw)
        c, outcomes = check_money(core, config, c)
        for actual, old in zip(run['stages'], core['online_receipts']):
            c.eq(actual['original_on_time'], old['on_time'], 'timeliness is never repaired offline')
            c.eq(actual['original_issued_clock'], old['issued_clock'], 'completion clock unchanged')
            c.eq(actual['timeliness_reclassified'], False, 'old late stays late')
            c.eq(actual['processing_and_io_ns'] > 0, True, 'actual local timer measurement')
    result = {'registry_id': 'R360', 'status': 'PASS', 'checks': c.n,
              'benchmark_sha256': hashlib.sha256((directory / 'benchmark.json').read_bytes()).hexdigest(),
              'all_ten_reports_and_38_files_per_report_exact': True,
              'independent_money': 'Fraction level sweeps, fixed q, price/fee stress and segregated native accounts',
              'independent_venue_parser': False, 'closed_components': outcomes,
              'actual_expected_net': None, 'full_net_pnl': None,
              'new_prospective_tickets': 0, 'new_alpha_variants': 0}
    with (out/'audit.json').open('xb') as f: f.write(encoded(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.run, args.out)
    print(json.dumps({'registry_id': 'R360', 'status': result['status'], 'checks': result['checks']}))
