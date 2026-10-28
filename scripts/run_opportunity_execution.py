"""R338 frozen synthetic component diagnostic. No market acquisition or orders."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab import prereg
from lab.opportunity_execution import plain, digest
from lab.opportunity_value import Outcome, assess_batch
from lab.paper_account import CloseMark, PaperEvent
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.stream_quotes import NS
from experiments.opportunity_execution_v1.fixture_support import Fixture, clock

LANE = ROOT/'experiments/opportunity_execution_v1'


def encoded(value):
    return (json.dumps(plain(value), indent=2, sort_keys=True, allow_nan=False)+'\n').encode()


def verify(lane=LANE):
    prereg.verify(lane/'PREREG.md'); spec = (lane/'PREREG.md').read_text()
    for filename in ('code_inputs.json', 'data_inputs.json', 'fixtures.json'):
        if prereg.sha256_file(lane/filename) not in spec:
            raise ValueError('unbound frozen input: '+filename)
    code = json.loads((lane/'code_inputs.json').read_text())
    if code['python_version'] != list(sys.version_info[:3]):
        raise ValueError('Python runtime drift')
    for manifest in (code, json.loads((lane/'data_inputs.json').read_text())):
        for path, expected in manifest['sha256'].items():
            if prereg.sha256_file(ROOT/path) != expected:
                raise ValueError('frozen input drift: '+path)


class Scenario:
    def __init__(self, case, multiple, directory):
        self.case, self.multiple = case, multiple
        balances = {(r['venue'], r['asset']): D(r['cash']) for r in case.get('balances',
            [{'venue': 'mexc', 'asset': 'USDT', 'cash': '1000'}])}
        options = {'max_symbol_gross_fraction': D(1),
            **{k: D(v) for k, v in case.get('policy', {}).items()}}
        self.fixture = Fixture(directory, balances, RiskPolicy('R338-invented', **options))
        f = self.fixture
        self.control_risk = PaperRisk(directory/'control-risk.jsonl', f.policy, f.account.anchor,
            contract_version='R338-invented', initial_balances=balances)
        self.mids = {}; self.spreads = {}; self.trades = {}; self.steps = []; self.t = 0

    def risk_inputs(self):
        return dict(clock=clock(self.t), complete=True, session_open=True, fee_inputs_known=True,
            contract_version='R338-invented', expected_contract_version='R338-invented', mode='fixture')

    def marks(self):
        result = []
        with localcontext() as context:
            context.prec = 80
            for (venue, asset, symbol), (quantity, entry) in self.fixture.account.positions.items():
                if quantity == 0:
                    continue
                mid = self.mids.get(symbol, entry)
                spread = self.spreads.get(symbol, D('.5'))
                price = mid-(1 if quantity > 0 else -1)*spread*self.multiple
                notional = abs(quantity)*price
                result.append(CloseMark(venue, asset, symbol, quantity, notional,
                    notional*D(10)*self.multiple/10000, clock(self.t), clock(self.t).utc_ns,
                    'invented-current-liquidation-quote-not-observed-market'))
        return result

    def request(self, event):
        names = {'quantity': 'q', 'venue': 'venue', 'asset': 'asset', 'symbol': 'symbol',
            'bid': 'bid', 'ask': 'ask', 'reserve': 'reserve'}
        arguments = {dest: event[key] for key, dest in names.items() if key in event}
        request = self.fixture.request(event['id'], t=self.t, **arguments)
        op = request['opportunities'][0]
        if event.get('profile') == 'weak':
            op = replace(op, outcomes=(Outcome('.7', '1', '0'), Outcome('.3', '-1', '0')))
        elif event.get('profile') == 'unknown_funding':
            op = replace(op, outcomes=(Outcome('1', '100', None),))
        elif event.get('profile') == 'uncalibrated':
            op = replace(op, calibration_id=None)
        request['opportunities'] = (op,)
        book = request['books'][op.opportunity_id]
        self.mids[op.symbol] = (D(str(book.bids[0].price))+D(str(book.asks[0].price)))/2
        self.spreads[op.symbol] = (D(str(book.asks[0].price))-D(str(book.bids[0].price)))/2
        request['marks'] = self.marks()
        return request

    def receipt(self, event):
        action = event['action']; kind = {'crash_fill': 'fill', 'deferred_ack': 'ack'}.get(action, action)
        ident = event['allocation']; allocation = self.fixture.execution.allocations[ident]['opportunity']
        purpose = event.get('purpose', 'open'); price = fee = None
        if kind == 'fill':
            side = (1 if D(allocation['quantity']) > 0 else -1)*(1 if purpose == 'open' else -1)
            mid, half = D(event['mid']), D(event['half_spread'])
            price = mid+side*half*self.multiple
            fee = abs(D(event['quantity']))*price*D(10)*self.multiple/10000
            self.mids[allocation['symbol']], self.spreads[allocation['symbol']] = mid, half
            self.trades[(ident, event['trade'])] = {'price': price,
                'quantity': D(event['quantity']), 'fee': fee,
                'event_id': 'portfolio-fill:'+digest((allocation['venue'], allocation['asset'], allocation['symbol'], event['trade']))}
            if event.get('fee_unknown'):
                fee = None
        return self.fixture.receipt(ident, event.get('order', 'o'), kind,
            purpose=purpose, q=event.get('quantity'), price=price, fee=fee,
            total=event.get('total'), trade=event.get('trade'), t=self.t)

    def operation(self, event):
        f = self.fixture; action = event['action']; at = clock(self.t).mono_ns
        if action in ('admit', 'crash_assessment'):
            request = self.request(event)
            before = f.account.journal_path.read_bytes()
            control = assess_batch(f.account, request['opportunities'], request['books'], request['fees_bp'],
                asof=at, anchor=f.account.anchor, risk=self.control_risk,
                risk_inputs=request['risk_inputs'], market_reports=request['market_reports'], marks=request['marks'])
            if f.account.journal_path.read_bytes() != before:
                raise ValueError('stateless control changed account evidence/cash')
            baseline = [{'id': r['opportunity_id'], 'included': r['conditional_batch_inclusion'],
                'capital_quote': r['planned_capital_quote']} for r in control['rows']]
            if action == 'crash_assessment':
                original = f.execution._commit
                def loss(payload, head):
                    if payload['action'] == 'admission':
                        raise RuntimeError('registered process-loss injection after risk observation')
                    return original(payload, head)
                with patch.object(f.execution, '_commit', side_effect=loss):
                    try:
                        f.execution.admit('batch-'+event['id'], **request)
                    except RuntimeError:
                        return {'state': 'injected_process_loss', 'stateless_control': baseline}
                raise ValueError('registered fault was not exercised')
            result = f.execution.admit('batch-'+event['id'], **request)
            return {'state': 'recorded', 'admission': result, 'stateless_control': baseline}
        if action == 'reopen':
            f.reopen(); return {'state': 'reopened'}
        if action == 'recover':
            return {'state': 'recovered', 'financial': f.execution.recover(at)}
        if action == 'resume_assessment':
            return {'state': 'resumed', 'admission': f.execution.resume_assessment()}
        if action == 'release':
            return {'state': 'release_observation', 'release': f.release(event['allocation'], self.t)}
        if action == 'snapshot':
            if 'mark_mid' in event:
                self.mids[event['symbol']] = D(event['mark_mid'])
            return {'state': 'observation_only'}
        if action in ('funding_unknown', 'resolve_funding', 'resolve_fee'):
            op = f.execution.allocations[event['allocation']]['opportunity']
            if action == 'resolve_fee':
                trade = self.trades[(event['allocation'], event['trade'])]
                kind, ident, amount, resolves = 'fee_resolution', 'resolve-fee-'+event['trade'], trade['fee'], trade['event_id']
            else:
                kind = 'funding' if action == 'funding_unknown' else 'funding_resolution'
                ident = event['event_id'] if action == 'funding_unknown' else 'resolve-'+event['event_id']
                amount = None if action == 'funding_unknown' else D(event['amount'])
                resolves = None if action == 'funding_unknown' else event['event_id']
            cash = PaperEvent(ident, kind, op['venue'], op['asset'], op['symbol'],
                clock(self.t).utc_ns, clock(self.t), 'invented-cash-receipt', amount=amount, resolves=resolves)
            return {'state': 'cash_observation', 'financial': f.execution.post_cash(cash, at)}
        receipt, _ = self.receipt(event)
        if action == 'crash_fill':
            with patch.object(f.account, 'post', side_effect=RuntimeError('registered loss before financial join')):
                try:
                    f.execution.post(receipt, at)
                except RuntimeError:
                    return {'state': 'injected_process_loss'}
            raise ValueError('registered fill fault was not exercised')
        if action == 'deferred_ack':
            before = f.account.journal_path.read_bytes()
            try:
                f.execution.post(receipt, at)
            except ValueError as error:
                if f.account.journal_path.read_bytes() != before:
                    raise ValueError('deferred receipt mutated pending financial journal')
                return {'state': 'deferred_until_explicit_recovery', 'reason': str(error)}
            raise ValueError('unjoined receipt did not block later write')
        return {'state': 'receipt_observation', 'financial': f.execution.post(receipt, at)}

    def capture(self, index, event, result):
        f = self.fixture; at = clock(self.t).mono_ns
        view = f.execution.snapshot(at, self.marks())
        watched = None
        if f.execution.pending is None and not view['unapplied_fill_ids']:
            inputs = self.risk_inputs()
            watched = f.execution.observe_risk('watch-'+str(index), asof=at,
                risk_inputs=inputs, marks=self.marks())['risk_stops']
            control_inputs = dict(inputs)
            control_inputs['complete'] = not bool(view['reasons'])
            self.control_risk.observe(view['account'], asof=at, **control_inputs)
            view = f.execution.snapshot(at, self.marks())
        raw = f.account.journal_path.read_bytes()
        self.steps.append({'index': index, 'action': event['action'], 'asof_mono_ns': at,
            'result': result, 'snapshot': view, 'risk_stops': watched,
            'account_record_count': len(raw.splitlines()), 'account_journal_head': f.execution.head})

    def run(self):
        try:
            for index, event in enumerate(self.case['events']):
                self.t = event.get('jump_ns', self.t+100)
                result = self.operation(event); self.capture(index, event, result)
            return {'case_id': self.case['case_id'], 'cost_multiple': self.multiple,
                'state': 'completed', 'steps': self.steps, 'source_authentication_verified': False,
                'actual_expected_net_return': None, 'prospective_days': 0}
        finally:
            self.fixture.execution.close()


def report(out, lane=LANE):
    verify(lane)
    if out.exists():
        raise ValueError('fresh diagnostic output path required')
    out.mkdir(parents=True)
    fixture = json.loads((lane/'fixtures.json').read_text())
    rows = []; journals = {}
    for case in fixture['cases']:
        for multiple in fixture['cost_multiples']:
            name = case['case_id']+'/'+str(multiple); directory = out/'states'/case['case_id']/str(multiple)
            directory.mkdir(parents=True)
            try:
                result = Scenario(case, multiple, directory).run()
            except Exception as error:
                result = {'case_id': case['case_id'], 'cost_multiple': multiple,
                    'state': 'failed', 'error': type(error).__name__+': '+str(error)}
            rows.append(result)
            journals[name] = {p.name: p.read_text() for p in sorted(directory.glob('*.jsonl'))}
    output = {'scope': 'R338 invented finite accounting/lifecycle diagnostics only',
        'market_requests': 0, 'predictive_strategy_trials': 0, 'prospective_days': 0,
        'actual_executable_expected_net': None, 'cases': rows}
    (out/'results.json').write_bytes(encoded(output))
    (out/'journals.json.gz').write_bytes(gzip.compress(encoded(journals), mtime=0))
    verify(lane)
    return {'cases': len(fixture['cases']), 'cost_paths': len(rows),
        'completed': sum(r['state'] == 'completed' for r in rows),
        'failed': sum(r['state'] == 'failed' for r in rows),
        'actual_executable_expected_net': None, 'prospective_days': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.out), indent=2))


if __name__ == '__main__':
    main()
