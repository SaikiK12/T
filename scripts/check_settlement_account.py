"""Independent stdlib/Fraction reconstruction of R357 cash, inventory and inputs.

Imports no production account, quote, settlement, risk, source-rule or reporter
functions. Financial tolerance is declared before the run, separate from the
original float score's descriptive tolerance.
"""
import argparse
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / 'experiments/settlement_account_v1'


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


class Check:
    def __init__(self, tolerance):
        self.n = 0
        self.tolerance = F(tolerance)

    def eq(self, actual, expected, label):
        self.n += 1
        if actual != expected:
            raise AssertionError((label, actual, expected))

    def near(self, actual, expected, label, tolerance=None):
        self.n += 1
        if actual is None or abs(F(str(actual)) - expected) > (F(tolerance) if tolerance else self.tolerance):
            raise AssertionError((label, actual, str(expected)))


def verify_inputs(c):
    spec = (LANE / 'PREREG.md').read_bytes()
    c.eq(hashlib.sha256(spec).hexdigest(), (LANE / 'PREREG.sha256').read_text().strip(), 'frozen spec')
    for name in ('config.json', 'sources.json', 'code_inputs.json', 'inputs.json'):
        c.eq(hashlib.sha256((LANE / name).read_bytes()).hexdigest() in spec.decode(), True, 'bound manifest ' + name)
    for name in ('code_inputs.json', 'inputs.json'):
        for path, sha in load(LANE / name)['sha256'].items():
            c.eq(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), sha, 'unchanged input ' + path)


def journal(c, content):
    rows = [json.loads(line) for line in content.splitlines()]
    previous = '0' * 64
    for i, row in enumerate(rows):
        h = row['sha256']
        base = {k: v for k, v in row.items() if k != 'sha256'}
        c.eq(row['sequence'], i, 'journal sequence')
        c.eq(row['previous_sha256'], previous, 'journal predecessor')
        encoded = json.dumps(base, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        c.eq(hashlib.sha256(encoded).hexdigest(), h, 'journal hash')
        previous = h
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    config = load(LANE / 'config.json')
    c = Check(config['independent_absolute_tolerance'])
    verify_inputs(c)
    result, pack = load(out / 'results.json.gz'), load(out / 'journals.json.gz')
    c.eq(result['new_predictive_trials'], 0, 'no predictive variants')
    c.eq(result['prospective_strategy_days'], 0, 'no paper days')
    c.eq(result['actual_expected_net'], None, 'no expected return certification')
    expected_ids = {case['id'] + '_d' + str(d) + '_k' + str(k) for case in config['cases']
                    for d in config['directions'] for k in config['cost_multiples']}
    c.eq({x['id'] for x in result['cells']}, expected_ids, 'all cells retained')
    c.eq(len(result['cells']), len(expected_ids), 'no duplicate cells')
    cases = {x['id']: x for x in config['cases']}
    q_by_case = {}
    for cell in result['cells']:
        case, d, k = cases[cell['case']], cell['direction'], cell['cost_multiple']
        blocked = case['id'] == 'separate_capital_shortfall'
        c.eq(cell['native_entry']['state'], 'blocked' if blocked else 'conditional_model', 'separate capital admission')
        report, native = cell['report'], cell['report']['native']
        c.eq(report['actual_execution_ready'], False, 'no execution authority')
        c.eq(report['actual_expected_net'], None, 'actual cash remains unknown')
        c.eq(native['activation_allowed'], False, 'no activation')
        c.eq(native['prospective_days'], 0, 'no new prospective days')
        qkey = cell['case'], d
        if qkey in q_by_case:
            c.eq(cell['entry_quantities'], q_by_case[qkey], 'cost tiers do not resize quantity')
        q_by_case[qkey] = cell['entry_quantities']
        expected = {}
        for venue, prefix, asset in (('mexc', 's', 'USDT'), ('lighter', 'h', 'USDC')):
            q = F(cell['entry_quantities'][venue])
            entry = cell['constructed_entry']
            base_price = F(str(entry[prefix + '_fill']))
            c.near(q, (-d if venue == 'mexc' else d) * F(config['leg_quote_budget']) / base_price, 'entry base quantity')
            p0 = F(config['entry_mid']) + k * (base_price - F(config['entry_mid']))
            initial = F(case.get(prefix + '_capital', config['initial_per_venue']))
            fee_rate = F(config['fees_bp'][venue]) * k / 10000
            fee = 0 if blocked else abs(q) * p0 * fee_rate
            realized, funding = F(0), F(0)
            pending = False
            open_q = F(0) if blocked else q
            bad_exit = prefix == 's' and case['id'] in ('thin_s_exit', 'missing_s_exit', 'future_s_exit', 'stale_s_exit')
            if not blocked and not bad_exit:
                raw = cell['constructed_exit_books'][venue]
                side = 'bids' if q > 0 else 'asks'
                c.eq(F(str(raw[side][0][1])) >= abs(q), True, 'exact quantity inside shown depth')
                mid = F(str(float(raw['bids'][0][0]) / 2 + float(raw['asks'][0][0]) / 2))
                p1 = mid + k * (F(str(raw[side][0][0])) - mid)
                c.near(cell['native_closes'][venue]['price'], p1, 'fixed inventory exit price')
                c.near(cell['native_closes'][venue]['quantity'], -q, 'close original base inventory')
                c.near(cell['native_closes'][venue]['fee'], abs(q) * p1 * fee_rate, 'fee on changed exit notional')
                realized = q * (p1 - p0)
                fee += abs(q) * p1 * fee_rate
                open_q = F(0)
            elif not blocked:
                c.eq(cell['native_closes'][venue]['state'], 'unknown', 'missing executable exit kept unknown')
            if case.get('funding') and not blocked:
                pending = case['funding'] == 'missing' or (venue == 'mexc' and case['id'] == 'nominal_plus5_exit')
                if not pending:
                    rate = F(config['source_s_rate' if venue == 'mexc' else 'source_h_rate'])
                    effective = F(config['s_effective_value' if venue == 'mexc' else 'h_effective_value'])
                    funding = -q * rate * effective
                assessment = next(x for x in cell['funding_assessments'] if x['event_id'] == 'evt:' + venue)
                if pending:
                    c.eq(assessment['cash_delta'], None, 'unknown value or inclusion is not zero cash')
                else:
                    c.near(assessment['cash_delta'], funding, 'event-bound fair/index cash')
            rows = [r for r in native['accounts'] if (r['venue'], r['asset']) == (venue, asset)]
            c.eq(len(rows), 1, 'separate account retained')
            row = rows[0]
            c.near(row['known_cash_component'], initial + realized + funding - fee, 'native cash conservation')
            c.near(row['realized_price_pnl'], realized, 'price pnl once')
            c.near(row['funding_pnl'], funding, 'funding once')
            c.near(row['fees_paid'], fee, 'fees once')
            c.near(row['locked_capital'], abs(open_q) * p0, 'open inventory capital retained')
            c.eq(bool(row['positions']), bool(open_q), 'no invisible leftover inventory')
            if open_q:
                c.near(row['positions'][0]['quantity_base'], open_q, 'native residual quantity')
            c.eq(row['cash'] is None, pending, 'pending cash withheld')
            c.eq(row['nav'] is None, pending or bool(open_q), 'no invented open-position NAV')
            if row['nav'] is not None:
                c.near(row['nav'], initial + realized + funding - fee, 'complete native NAV')
            expected[venue] = {'initial': initial, 'cash': initial + realized + funding - fee,
                               'q': open_q, 'basis': p0, 'pending': pending, 'funding': funding, 'fees': fee, 'price': realized}
            if venue in cell['legacy_nominal_inventory']:
                legacy = cell['legacy_nominal_inventory'][venue]
                px = F(str(cell['constructed_exit'][prefix + '_fill']))
                residual = q - (1 if q > 0 else -1) * F(config['leg_quote_budget']) / px
                c.near(legacy['residual_quantity'], residual, 'fixed dollar close residual')
                c.eq(legacy['position_reversed'], q * residual < 0, 'reversal is visible')
                c.eq(legacy['thin_extrapolated'], case['id'] == 'thin_s_exit' and venue == 'mexc', 'unsupported extension flag')
        complete = all(not x['q'] and not x['pending'] for x in expected.values())
        capital = sum(x['initial'] for x in expected.values())
        c.near(report['combined_initial_capital'], capital, 'all segregated capital in denominator')
        if complete:
            pnl = sum(x['cash'] - x['initial'] for x in expected.values())
            c.near(report['combined_scenario_pnl'], pnl, 'whole model pnl')
            c.near(report['whole_capital_scenario_return'], pnl / capital, 'whole capital return')
        else:
            c.eq(report['combined_scenario_pnl'], None, 'incomplete combined NAV withheld')
            c.eq(report['whole_capital_scenario_return'], None, 'incomplete return withheld')
        if cell['legacy_score'] is not None:
            en, ex = cell['constructed_entry'], cell['constructed_exit']
            mids = {(which, v): (F(str(t[v + '_bid'])) + F(str(t[v + '_ask']))) / 2
                    for which, t in (('en', en), ('ex', ex)) for v in ('s', 'h')}
            gross = d * (mids['ex', 'h'] / mids['en', 'h'] - mids['ex', 's'] / mids['en', 's'])
            book_cost = F(0)
            for v, buy0 in (('s', d < 0), ('h', d > 0)):
                for which, t, buy in (('en', en, buy0), ('ex', ex, not buy0)):
                    fraction = F(str(t[v + '_fill'])) / mids[which, v] - 1
                    book_cost += fraction if buy else -fraction
            fund = d * (F(config['source_s_rate']) - F(config['source_h_rate'])) if case.get('funding') else F(0)
            fees = 2 * (F(config['fees_bp']['mexc']) + F(config['fees_bp']['lighter'])) / 10000
            old_net = gross + fund - k * (book_cost + fees)
            c.near(cell['legacy_score'][f'net{k}_web'], old_net, 'unchanged source score', config['legacy_float_tolerance'])
            c.near(cell['legacy_normalized_quote_proxy'], old_net * F(config['leg_quote_budget']),
                   'source normalized proxy', config['legacy_quote_tolerance'])
        cash = {v: x['initial'] for v, x in expected.items()}
        quantities, basis, prices, fees, funds, pendings = {}, {}, {}, {}, {}, set()
        jr = journal(c, pack[cell['id'] + '/account.jsonl'])
        for record in jr:
            event = record['event']
            if event.get('kind') != 'paper_account_attempt':
                continue
            e = event['payload']
            v = e['venue']
            c.eq(e['simulation_only'], True, 'only model event')
            c.eq(e['occurred_ns'] <= e['clock']['utc_ns'], True, 'separate causal first receipt')
            if e['kind'] == 'fill':
                q, p, charge = F(e['quantity']), F(e['price']), F(e['fee'])
                old = quantities.get(v, F(0))
                previous_basis = basis.get(v, F(0))
                new = old + q
                realized = F(0)
                if old == 0 or old * q > 0:
                    basis[v] = (abs(old) * previous_basis + abs(q) * p) / abs(new)
                else:
                    realized = (1 if old > 0 else -1) * min(abs(old), abs(q)) * (p - previous_basis)
                    basis[v] = F(0) if new == 0 else previous_basis if old * new > 0 else p
                quantities[v] = new
                cash[v] += realized - charge
                prices[v] = prices.get(v, F(0)) + realized
                fees[v] = fees.get(v, F(0)) + charge
            elif e['kind'] == 'funding':
                if e['amount'] is None:
                    pendings.add(v)
                else:
                    cash[v] += F(e['amount'])
                    funds[v] = funds.get(v, F(0)) + F(e['amount'])
            else:
                raise AssertionError('unexpected cash event in fixed control run')
        for v, x in expected.items():
            c.near(str(cash[v]), x['cash'], 'independent journal cash')
            c.near(str(quantities.get(v, 0)), x['q'], 'independent journal quantity')
            c.eq(v in pendings, x['pending'], 'journal unknown funding retained')
        risk_rows = journal(c, pack[cell['id'] + '/risk.jsonl'])
        c.eq(len(risk_rows), 3, 'risk reopening appends and preserves original stop')
        c.eq(set(cell['risk']['stops']).issubset(set(cell['risk_after_restart']['stops'])), True, 'risk stops cannot reset')
        if not complete or any(x['cash'] - x['initial'] <= -x['initial'] * F('.03') for x in expected.values()):
            c.eq(cell['risk']['state'], 'HALTED', 'separate venue loss/unknown risk stops new entries')
    c.eq(len(pack), len(expected_ids) * 2, 'all native account and risk journals retained')
    summary = {'registry_id': 'R357', 'status': 'PASS', 'checks': c.n, 'cells': len(result['cells']),
               'new_predictive_trials': 0, 'prospective_strategy_days': 0,
               'financial_absolute_tolerance': config['independent_absolute_tolerance'],
               'original_float_score_tolerance': config['legacy_float_tolerance']}
    path = out / 'audit.json'
    with path.open('x') as handle:
        handle.write(json.dumps(summary, sort_keys=True, separators=(',', ':')) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
