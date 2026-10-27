"""Independent R338 rational/journal oracle; standard library only.

This checker validates the finite invented cases, not an exchange data source,
future forecast, fill probability, production connector or profitable strategy.
"""
import argparse
from collections import defaultdict
from fractions import Fraction as F
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT/'experiments/opportunity_execution_v1'
NS = 1_000_000_000
COMPONENT = 'opportunity_execution_v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode()).hexdigest()


def verify(lane=LANE):
    spec = (lane/'PREREG.md').read_bytes()
    if hashlib.sha256(spec).hexdigest() != (lane/'PREREG.sha256').read_text().strip():
        raise ValueError('preregistration digest mismatch')
    for name in ('code_inputs.json', 'data_inputs.json', 'fixtures.json'):
        if hashlib.sha256((lane/name).read_bytes()).hexdigest() not in spec.decode():
            raise ValueError('unbound frozen input: '+name)
    for name in ('code_inputs.json', 'data_inputs.json'):
        manifest = json.loads((lane/name).read_text())
        if 'python_version' in manifest and manifest['python_version'] != list(sys.version_info[:3]):
            raise ValueError('Python runtime drift')
        for path, expected in manifest['sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
                raise ValueError('frozen input drift: '+path)


def chain(raw):
    if not raw or not raw.endswith('\n'):
        raise ValueError('empty or incomplete journal')
    result = []; previous = '0'*64
    for i, line in enumerate(raw.splitlines()):
        row = json.loads(line); claimed = row.pop('sha256')
        if row['sequence'] != i or row['previous_sha256'] != previous or digest(row) != claimed:
            raise ValueError('invalid journal chain')
        row['sha256'] = claimed; result.append(row); previous = claimed
    return result


def numeric_event(event):
    result = dict(event)
    for key in ('quantity', 'price', 'fee', 'amount', 'reference_mid'):
        if result.get(key) is not None:
            result[key] = F(result[key])
    return result


class Money:
    """Exact linear-futures cash identity, independently written for this scope."""
    def __init__(self, initial):
        self.initial = {k: F(v) for k, v in initial.items()}
        self.positions = {}; self.seen = {}; self.pending = {}
        self.price = defaultdict(F); self.fees = defaultdict(F)
        self.funding = defaultdict(F); self.flows = defaultdict(F)

    def post(self, event):
        e = numeric_event(event); ident = e['event_id']; key = e['venue'], e['asset']
        if ident in self.seen:
            if e != self.seen[ident]:
                raise ValueError('financial revision or refreshed first-seen clock')
            return
        if key not in self.initial:
            raise ValueError('unfunded financial event')
        kind = e['kind']; pos = (*key, e['symbol'])
        if kind == 'fill':
            q, p = e['quantity'], e['price']; old, basis = self.positions.get(pos, (F(0), F(0)))
            new = old+q
            if not old or old*q > 0:
                basis = (abs(old)*basis+abs(q)*p)/abs(new)
            else:
                self.price[key] += (1 if old > 0 else -1)*min(abs(old), abs(q))*(p-basis)
                basis = F(0) if not new else basis if old*new > 0 else p
            self.positions[pos] = new, basis
            if e['fee'] is None:
                self.pending[ident] = key, 'fee'
            else:
                self.fees[key] += e['fee']
        elif kind == 'funding':
            if e['amount'] is None:
                self.pending[ident] = key, 'funding'
            else:
                self.funding[key] += e['amount']
        elif kind == 'capital_change':
            self.flows[key] += e['amount']
        elif kind in ('fee_resolution', 'funding_resolution'):
            expected = 'fee' if kind == 'fee_resolution' else 'funding'
            if self.pending.pop(e['resolves'], None) != (key, expected):
                raise ValueError('resolution without matching unknown amount')
            (self.fees if expected == 'fee' else self.funding)[key] += e['amount']
        else:
            raise ValueError('unsupported financial event')
        self.seen[ident] = e

    def cash(self, key):
        return self.initial[key]+self.price[key]+self.funding[key]-self.fees[key]+self.flows[key]


class Checks:
    def __init__(self):
        self.count = 0

    def equal(self, actual, expected, label):
        self.count += 1
        if actual != expected:
            raise AssertionError(f'{label}: {actual!r} != {expected!r}')

    def number(self, actual, expected, label):
        self.equal(None if actual is None else F(actual), expected, label)


def state(records, initial, check):
    money = Money(initial); allocations = {}; expected = {}; trades = set(); orders = {}; quantities = defaultdict(F)
    pending = None
    for row in records:
        e = row['event']
        if e['kind'] == 'paper_account_attempt':
            financial = e['payload']; ident = financial['event_id']
            check.equal(ident in expected, True, 'financial source receipt precedes posting')
            check.equal(numeric_event(financial), numeric_event(expected[ident]), 'full source/cash/first-clock join')
            money.post(financial)
        elif e['kind'] == 'paper_evidence' and e['payload'].get('component') == COMPONENT:
            e = e['payload']; action = e['action']
            if action == 'assessment_begin':
                check.equal(pending, None, 'single durable assessment')
                check.equal(digest(e['request']), e['request_sha256'], 'original request identity')
                pending = e
            elif action == 'admission':
                check.equal(e['batch_id'], pending['batch_id'], 'assessment/admission identity')
                request = pending['request']
                for allocation in e['rows']:
                    o = allocation['opportunity']; ident = o['opportunity_id']; q = F(o['quantity'])
                    book = request['books'][ident]['depth']; bid = F(book['bids'][0]['price']); ask = F(book['asks'][0]['price'])
                    fee = F(request['fees_bp'][ident])/10000
                    cost = abs(q)*(ask-bid+(ask+bid)*fee)
                    gross = None if any(x['price_pnl'] is None or x['funding_pnl'] is None
                        for x in o['outcomes'] if F(x['probability'])) else sum(
                        (F(x['probability'])*(F(x['price_pnl'])+F(x['funding_pnl'])) for x in o['outcomes']), F(0))
                    for tier in allocation['cost_tiers']:
                        known = gross is not None and o['calibration_id'] is not None
                        required = tier['cost_multiple']*(cost+F(o['exit_reserve_quote']))+F(o['error_quote'])
                        check.number(tier['required_gross_quote'], required if known else None, '1x/2x/3x common threshold')
                        check.number(tier['expected_net_lower_quote'], gross-required if known else None, 'cost/error adjusted forecast')
                    if allocation['reserved']:
                        check.equal(ident in allocations, False, 'unique durable allocation')
                        check.number(allocation['reserve_quote'], abs(q)*(ask if q > 0 else bid)+3*(cost+F(o['exit_reserve_quote'])), 'full original reserve')
                        check.number(allocation['gross_floor_quote'], abs(q)*ask, 'worst direction gross')
                        allocations[ident] = {**allocation, 'released': False}
                pending = None
            elif action == 'receipt':
                r = e['receipt']; ident = r['allocation_id']
                if ident not in allocations or r['kind'] == 'gap':
                    continue
                o = allocations[ident]['opportunity']; key = (o['venue'], o['asset'], o['symbol'], r['order_id'])
                if r['kind'] == 'submit':
                    orders[key] = {'allocation': ident, 'filled': F(0), 'terminal': False, 'final': None}
                elif r['kind'] == 'fill':
                    trade = (o['venue'], o['asset'], o['symbol'], r['trade_id'])
                    if trade in trades:
                        continue
                    trades.add(trade); orders[key]['filled'] += F(r['quantity_base'])
                    signed = F(r['quantity_base'])*(1 if F(o['quantity']) > 0 else -1)*(1 if r['purpose'] == 'open' else -1)
                    quantities[ident] += signed
                    eid = 'portfolio-fill:'+digest(trade)
                    expected[eid] = dict(event_id=eid, kind='fill', venue=o['venue'], asset=o['asset'],
                        symbol=o['symbol'], occurred_ns=r['occurred_ns'], clock=r['clock'], source_identity=r['source_identity'],
                        quantity=str(signed), price=r['price'], fee=r['fee'], amount=None, reference_mid=None,
                        resolves=None, simulation_only=True)
                elif r['kind'] in ('complete', 'cancelled', 'rejected'):
                    orders[key]['terminal'] = True
                    orders[key]['final'] = None if r['cumulative_filled_base'] is None else F(r['cumulative_filled_base'])
            elif action == 'cash_receipt':
                expected.setdefault(e['event']['event_id'], e['event'])
            elif action == 'release':
                check.equal(quantities[e['allocation_id']], 0, 'release requires own flat exposure')
                check.equal(all(o['terminal'] and o['filled'] == o['final'] for o in orders.values()
                    if o['allocation'] == e['allocation_id']), True, 'release requires final reconciled orders')
                check.equal(set(expected)-set(money.seen), set(), 'release requires all financial joins')
                check.equal(money.pending, {}, 'release requires known cash amounts')
                allocations[e['allocation_id']]['released'] = True
    return money, allocations, quantities, orders, expected, pending


def path_check(case, result, journals, multiple, check):
    account = chain(journals['account.jsonl']); risk = chain(journals['risk.jsonl'])
    chain(journals['control-risk.jsonl'])
    initial = {(r['venue'], r['asset']): F(r['cash']) for r in account[0]['event']['initial']}
    check.equal(result['state'], 'completed', 'all registered operations retained')
    check.equal(len(result['steps']), len(case['events']), 'finite event scope')
    mids = {}; spreads = {}; final = None; observations = 0; admitted = []; controls = []; previous_count = 0
    for fixture, step in zip(case['events'], result['steps']):
        check.equal(step['action'], fixture['action'], 'registered action order')
        if fixture['action'] in ('admit', 'crash_assessment'):
            symbol = fixture.get('symbol', 'ETH'); bid, ask = F(str(fixture.get('bid', '99.5'))), F(str(fixture.get('ask', '100.5')))
            mids[symbol], spreads[symbol] = (bid+ask)/2, (ask-bid)/2
        elif fixture['action'] in ('fill', 'crash_fill'):
            # All registered fill paths here use ETH. Do not infer a new instrument.
            mids['ETH'], spreads['ETH'] = F(fixture['mid']), F(fixture['half_spread'])
        elif 'mark_mid' in fixture:
            mids[fixture['symbol']] = F(fixture['mark_mid'])
        n = step['account_record_count']; prefix = account[:n]
        check.equal(prefix[-1]['sha256'], step['account_journal_head'], 'snapshot bound to journal prefix')
        money, allocations, quantities, orders, expected, pending = state(prefix, initial, check)
        received = [r['event']['payload']['receipt'] for r in prefix[previous_count:]
            if r['event']['kind'] == 'paper_evidence' and r['event']['payload'].get('action') == 'receipt']
        kind = fixture['action']
        receipt_actions = ('submit', 'ack', 'fill', 'crash_fill', 'complete', 'cancel_request', 'cancelled', 'rejected', 'gap')
        check.equal(len(received), int(kind in receipt_actions), 'received versus deferred fixture event')
        if received:
            r = received[0]; check.equal(r['kind'], 'fill' if kind == 'crash_fill' else kind, 'receipt type')
            check.equal(r['allocation_id'], fixture['allocation'], 'receipt allocation')
            check.equal(r['order_id'], fixture.get('order', 'o'), 'receipt order identity')
            check.equal(r['clock']['mono_ns'], step['asof_mono_ns'], 'original receipt clock')
            if kind in ('fill', 'crash_fill'):
                o = allocations[r['allocation_id']]['opportunity']
                side = (1 if F(o['quantity']) > 0 else -1)*(1 if fixture.get('purpose', 'open') == 'open' else -1)
                price = F(fixture['mid'])+side*F(fixture['half_spread'])*multiple
                check.number(r['quantity_base'], F(fixture['quantity']), 'registered base fill')
                check.number(r['price'], price, 'registered spread stress')
                check.number(r['fee'], None if fixture.get('fee_unknown') else F(fixture['quantity'])*price*F(multiple, 1000), 'registered fee stress')
                check.equal(r['trade_id'], fixture['trade'], 'original trade identity')
        previous_count = n
        view = step['snapshot']; missing = set(expected)-set(money.seen)
        check.equal(set(view['unapplied_fill_ids']), missing, 'every missing cash join is visible')
        check.equal(view['actual_order_allowed'], False, 'no order permission')
        check.equal(view['activation_allowed'], False, 'no activation')
        check.equal(view['actual_expected_net_return'], None, 'unknown market expectation')
        check.equal(view['prospective_days'], 0, 'no prospective evidence from toys')
        check.equal(view['conditional_budgets_known'], not bool(view['reasons']), 'qualified budget state')
        check.equal('assessment_incomplete' in view['reasons'], pending is not None, 'pending assessment retained')
        check.equal(view['pending_orders'], sum(not (o['terminal'] and o['filled'] == o['final']) for o in orders.values()), 'no inferred full-fill terminality')
        holdings = {h['allocation_id']: h for h in view['holdings']}
        active = {i: a for i, a in allocations.items() if not a['released'] or quantities[i]}
        check.equal(set(holdings), set(active), 'reservation survives until explicit release')
        for raw, capital in zip(view['account']['accounts'], view['accounts']):
            key = raw['venue'], raw['asset']; open_pnl = F(0); exit_fees = F(0); locked = F(0); extra = F(0); gross_extra = F(0)
            expected_positions = {p[2]: qb for p, qb in money.positions.items() if p[:2] == key and qb[0]}
            check.equal({p['symbol'] for p in raw['positions']}, set(expected_positions), 'financial positions identity')
            for p in raw['positions']:
                q, basis = expected_positions[p['symbol']]; mark = mids[p['symbol']]-(1 if q > 0 else -1)*spreads[p['symbol']]*multiple
                pnl = (1 if q > 0 else -1)*abs(q)*(mark-basis)
                open_pnl += pnl; exit_fees += abs(q)*mark*F(multiple, 1000); locked += abs(q)*basis
                check.number(p['quantity_base'], q, 'base quantity'); check.number(p['average_entry'], basis, 'pooled basis')
                check.number(p['unrealized_liquidation_pnl'], pnl, 'bid/ask liquidation PnL')
            known = not any(k == key for k, _ in money.pending.values())
            cash = money.cash(key); nav = cash+open_pnl-exit_fees if known else None
            for field, value in {'initial_cash': initial[key], 'known_cash_component': cash,
                'realized_price_pnl': money.price[key], 'funding_pnl': money.funding[key], 'fees_paid': money.fees[key],
                'external_capital_flows': money.flows[key], 'known_realized_net_component': cash-initial[key]-money.flows[key],
                'cash': cash if known else None, 'nav': nav, 'locked_capital': locked,
                'unrealized_liquidation_pnl': open_pnl, 'estimated_future_exit_fees': exit_fees}.items():
                check.number(raw[field], value, field)
            for ident, allocation in active.items():
                o = allocation['opportunity']
                if (o['venue'], o['asset']) != key:
                    continue
                q, basis = expected_positions.get(o['symbol'], (F(0), F(0)))
                total = sum((quantities[i] for i, a in active.items()
                    if (a['opportunity']['venue'], a['opportunity']['asset'], a['opportunity']['symbol']) == (*key, o['symbol'])), F(0))
                fraction = abs(quantities[ident]/total) if total else F(0)
                attributed = abs(q)*basis*fraction
                gross = abs(q)*max(basis, mids[o['symbol']]-(1 if q > 0 else -1)*spreads[o['symbol']]*multiple) if q else F(0)
                hold = max(F(0), F(allocation['reserve_quote'])-attributed)
                hold_gross = max(F(0), F(allocation['gross_floor_quote'])-gross*fraction)
                extra += hold; gross_extra += hold_gross
                for field, value in {'open_quantity_base': quantities[ident], 'attributed_actual_locked_quote': attributed,
                    'extra_capital_floor_quote': hold, 'extra_gross_floor_quote': hold_gross}.items():
                    check.number(holdings[ident][field], value, field)
            available = max(F(0), min(cash, nav)-locked-extra) if known else None
            check.number(capital['extra_capital_floor_quote'], extra, 'total extra capital floor')
            check.number(capital['extra_gross_floor_quote'], gross_extra, 'total extra gross floor')
            check.number(capital['computed_available_after_floors_component'], available, 'conservative capital component')
            check.number(capital['available_after_floors_quote'], None if view['reasons'] else available, 'no qualified capital during unresolved evidence')
        action_result = step['result']
        if 'admission' in action_result:
            for a in action_result['admission']['rows']:
                admitted.append((a['opportunity']['opportunity_id'], a['reserved']))
                if fixture['action'] == 'admit':
                    check.equal(a['reserved'], fixture['expected_reserve'], 'registered inclusion')
                elif fixture['action'] == 'resume_assessment':
                    original = next(e for e in case['events'] if e['action'] == 'crash_assessment')
                    check.equal(a['reserved'], original['expected_reserve'], 'registered recovery inclusion')
        if 'stateless_control' in action_result:
            controls.extend((a['id'], a['included']) for a in action_result['stateless_control'])
        if fixture['action'] == 'release':
            check.equal(action_result['release']['released'], fixture['expected_release'], 'registered release')
        # Checkpoints cannot erase the persistent risk prefix or bind another policy.
        for row in prefix:
            event = row['event']
            if event['kind'] == 'paper_evidence' and event['payload'].get('component') == COMPONENT:
                checkpoint = event['payload'].get('risk_checkpoint')
                if checkpoint:
                    check.equal(risk[checkpoint['count']-1]['sha256'], checkpoint['head'], 'bound risk prefix')
        final = view; observations += 1
    if case['case_id'] in ('cross_batch_capital_restart', 'pending_symbol_floor', 'pending_venue_floor', 'segregated_venue_and_currency'):
        check.equal(('b', True) in controls, True, 'stateless control lacks durable pending hold')
        check.equal(('b', False) in admitted, True, 'durable capital/gross constraint changes decision')
    return {'case_id': case['case_id'], 'cost_multiple': multiple, 'observations': observations,
        'admissions': admitted, 'stateless_control': controls,
        'final_accounts': [{k: a[k] for k in ('venue', 'asset', 'known_realized_net_component', 'cash', 'nav')}
            for a in final['account']['accounts']], 'final_reasons': final['reasons']}


def audit(directory, lane=LANE):
    verify(lane); fixture = json.loads((lane/'fixtures.json').read_text())
    output = json.loads((directory/'results.json').read_text())
    journals = json.loads(gzip.decompress((directory/'journals.json.gz').read_bytes()))
    wanted = {(c['case_id'], k) for c in fixture['cases'] for k in fixture['cost_multiples']}
    results = {(r['case_id'], r['cost_multiple']): r for r in output['cases']}
    check = Checks(); check.equal(set(results), wanted, 'exact registered case/tier scope')
    check.equal(len(results), len(output['cases']), 'no duplicate diagnostic path')
    rows = []; failures = []
    for case in fixture['cases']:
        for multiple in fixture['cost_multiples']:
            key = case['case_id'], multiple
            try:
                rows.append(path_check(case, results[key], journals[case['case_id']+'/'+str(multiple)], multiple, check))
            except (AssertionError, ValueError, KeyError, TypeError, ZeroDivisionError) as error:
                failures.append({'case_id': key[0], 'cost_multiple': multiple, 'error': str(error)})
    verify(lane)
    return {'scope': 'R338 finite invented rational/lifecycle diagnostic only', 'passed': not failures,
        'checks': check.count, 'paths': rows, 'failures': failures, 'actual_executable_expected_net': None,
        'predictive_strategy_trials': 0, 'prospective_days': 0, 'activation_allowed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); result = audit(args.out)
    (args.out/'audit.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'paths'}, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
