"""Durable, conditional paper allocations over the existing financial journal.

One local writer; same-sign model sleeves only. No orders, source authentication,
price prediction or activation. R334 remains unchanged. Reservations are capital
and gross-exposure floors, not PnL expenses or newly earned cash.
"""
from dataclasses import asdict, dataclass, is_dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
import fcntl
import hashlib
import json
import os
from pathlib import Path

from lab.acquisition_budget import _locked, _read_records, _append_record
from lab.funding_values import clock_known
from lab.microstructure import DepthLevel, DepthSnapshot
from lab.opportunity_value import Opportunity, Outcome, assess_batch
from lab.paper_account import PaperAccount, PaperEvent, CloseMark, number, text, _precision
from lab.paper_controls import PaperRisk
from lab.stream_quotes import FrameClock, StreamBook, NS

COMPONENT = 'opportunity_execution_v1'
MAX_BATCH = 4
MAX_ACTIVE = 64
MAX_ORDERS = 8
MAX_QUANTITY_DECIMALS = 40
MAX_HORIZON_NS = 12*3600*NS


def plain(value):
    if isinstance(value, Decimal):
        with localcontext() as context:
            context.prec = max(80, len(value.as_tuple().digits))
            return str(value.normalize())
    if isinstance(value, Fraction):
        return str(value)
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def rational(value):
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str) and '/' in value:
        return Fraction(value)
    return Fraction(number(value))


def quantity_resolution(value):
    value = number(value)
    with localcontext() as context:
        context.prec = max(80, len(value.as_tuple().digits))
        if value.normalize().as_tuple().exponent < -MAX_QUANTITY_DECIMALS:
            raise ValueError('base quantity resolution exceeds40decimal places')
    return value


def economic(event):
    result = plain(event)
    result.pop('clock', None)
    return result


def restore_request(request):
    opportunities = []
    for row in request['opportunities']:
        row = dict(row)
        row['clock'] = FrameClock(**row['clock'])
        row['outcomes'] = tuple(Outcome(**x) for x in row['outcomes'])
        opportunities.append(Opportunity(**row))
    books = {}
    for key, row in request['books'].items():
        if row is None:
            books[key] = None
            continue
        row = dict(row); depth = dict(row['depth'])
        for side in ('bids', 'asks'):
            depth[side] = tuple(DepthLevel(**x) for x in depth[side])
        row['depth'] = DepthSnapshot(**depth)
        row['clock'] = FrameClock(**row['clock'])
        books[key] = StreamBook(**row)
    inputs = dict(request['risk_inputs'])
    inputs['clock'] = FrameClock(**inputs['clock'])
    marks = tuple(CloseMark(**{**x, 'clock': FrameClock(**x['clock'])}) for x in request['marks'])
    return opportunities, books, inputs, marks


@dataclass(frozen=True)
class ExecutionReceipt:
    allocation_id: str
    receipt_id: str
    order_id: str
    kind: str
    occurred_ns: int
    clock: FrameClock
    source_identity: str
    purpose: str = 'open'
    quantity_base: Decimal | None = None
    trade_id: str | None = None
    price: Decimal | None = None
    fee: Decimal | None = None
    cumulative_filled_base: Decimal | None = None

    def __post_init__(self):
        for field in ('allocation_id', 'receipt_id', 'order_id', 'source_identity'):
            text(getattr(self, field))
        if self.kind not in ('submit', 'ack', 'fill', 'cancel_request', 'cancelled', 'rejected', 'complete', 'gap'):
            raise ValueError('explicit lifecycle kind required')
        if self.purpose not in ('open', 'close'):
            raise ValueError('explicit open/close purpose required')
        if type(self.occurred_ns) is not int or not isinstance(self.clock, FrameClock) or not 0 <= self.occurred_ns <= self.clock.utc_ns:
            raise ValueError('separate economic and first-seen clocks required')
        for field in ('quantity_base', 'price', 'fee', 'cumulative_filled_base'):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, number(value,
                    positive=field in ('quantity_base', 'price'),
                    nonnegative=field in ('fee', 'cumulative_filled_base')))
        for field in ('quantity_base', 'cumulative_filled_base'):
            if getattr(self, field) is not None:
                quantity_resolution(getattr(self, field))
        if self.kind in ('submit', 'fill') and self.quantity_base is None:
            raise ValueError('explicit base quantity required')
        if self.kind == 'fill':
            text(self.trade_id)
            if self.price is None:
                raise ValueError('explicit fill price required')
        elif any(getattr(self, f) is not None for f in ('trade_id', 'price', 'fee')):
            raise ValueError('fill-only financial fields')
        if self.kind not in ('submit', 'fill') and self.quantity_base is not None:
            raise ValueError('quantity only belongs to submit/fill')
        if self.kind not in ('complete', 'cancelled', 'rejected') and self.cumulative_filled_base is not None:
            raise ValueError('final cumulative total only belongs to terminal report')

    @classmethod
    def restore(cls, data):
        return cls(**{**data, 'clock': FrameClock(**data['clock'])})


class OpportunityExecution:
    """A paper-only local coordinator, not an exchange connector.

    The account and risk journals must be dedicated to this coordinator. Bind
    their relative identity and risk-chain checkpoint; moving both together is
    possible, replacing only the risk history is not. Partial and adverse fills
    remain visible even when a financial join is rejected by the frozen account.
    """
    def __init__(self, account, risk, *, account_id):
        if not isinstance(account, PaperAccount) or account.journal_path is None or not isinstance(risk, PaperRisk):
            raise ValueError('durable existing account and risk objects required')
        text(account_id)
        if account.anchor != risk.anchor or account.initial != risk.initial:
            raise ValueError('same registered account/risk baseline required')
        self.account, self.risk = account, risk
        self.closed = False; self.lease = None
        try:
            risk_relative = Path(risk.path).resolve().relative_to(account.journal_path.parent.resolve()).as_posix()
            if risk_relative == account.journal_path.name:
                raise ValueError('separate existing account and risk journal files required')
            self.header = {'account_id': account_id, 'risk_relative_path': risk_relative,
                'risk_header': risk.header, 'max_batch': MAX_BATCH,
                'max_active': MAX_ACTIVE, 'max_orders_per_allocation': MAX_ORDERS,
                'max_horizon_ns': MAX_HORIZON_NS, 'max_quantity_decimals': MAX_QUANTITY_DECIMALS}
            fd = os.open(account.journal_path.with_suffix('.pair-writer.lock'),
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.lease = os.fdopen(fd, 'a+')
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._refresh()
            headers = [e for e in self.events if e['action'] == 'header']
            if not headers:
                if account.accepted_events or any(e['namespace'] == 'recovery' and
                        e['payload'].get('component') == 'paired_execution_plan' for e in account.evidence):
                    raise ValueError('fresh dedicated shared account required')
                rows = self._read_risk()
                self._commit({'action': 'header', 'config': self.header,
                    'risk_checkpoint': self._checkpoint(rows)}, self.head)
            elif len(headers) != 1 or headers[0]['config'] != plain(self.header):
                raise ValueError('allocation account/risk identity or policy cannot reset')
            self._check_risk()
        except BaseException:
            self.close(); raise

    def _read_risk(self):
        with _locked(self.risk.path) as handle:
            rows = _read_records(handle)
        if not rows or rows[0]['event'] != self.risk.header:
            raise ValueError('risk history/header missing or changed')
        return rows

    @staticmethod
    def _checkpoint(rows):
        return {'count': len(rows), 'head': rows[-1]['sha256']}

    def _check_risk(self):
        rows = self._read_risk()
        checkpoint = self.checkpoint
        if checkpoint is None:
            return rows
        n = checkpoint['count']
        if len(rows) < n or rows[n-1]['sha256'] != checkpoint['head']:
            raise ValueError('risk history lost/replaced; no reset or new entry')
        if self.pending is None and len(rows) != n:
            raise ValueError('unbound external risk observations require reconciliation')
        if self.pending is not None:
            request = self.pending['request']
            for row in rows[n:]:
                event = row['event']
                if (event['asof_mono_ns'] != request['asof'] or
                        event['clock'] != request['risk_inputs']['clock'] or
                        event['mode'] != request['risk_inputs']['mode']):
                    raise ValueError('foreign risk event during incomplete assessment')
        return rows

    def _commit(self, payload, expected_head):
        if self.closed:
            raise ValueError('coordinator closed')
        payload = plain({'component': COMPONENT, **payload})
        if len(json.dumps(payload, allow_nan=False).encode()) > 65536:
            raise ValueError('existing account evidence64KiB limit exceeded')
        with _locked(self.account.journal_path) as handle:
            rows = self.account._load(handle)
            if rows[-1]['sha256'] != expected_head:
                raise ValueError('account changed since assessment; no stale commit')
            _append_record(handle, rows, {'kind': 'paper_evidence',
                'namespace': 'recovery', 'payload': payload})
        self._refresh()

    def _refresh(self):
        with _locked(self.account.journal_path) as handle:
            rows = self.account._load(handle)
        self.head = rows[-1]['sha256']
        self.events = [x['payload'] for x in self.account.evidence if
            x['namespace'] == 'recovery' and x['payload'].get('component') == COMPONENT]
        self.allocations = {}; self.batches = {}; self.orders = {}; self.trades = {}
        self.opportunity_specs = {}
        self.receipts = {}; self.issues = set(); self.expected = []; self.pending = None
        self.releases = {}
        if any(e['namespace'] == 'recovery' and e['payload'].get('component') == 'paired_execution_plan'
                for e in self.account.evidence):
            self.issues.add('foreign_execution_coordinator_bound')
        self.checkpoint = None; self.last_asof = -1; cash_receipts = {}
        for event in self.events:
            action = event['action']
            if action == 'header':
                self.checkpoint = event['risk_checkpoint']
            elif action == 'assessment_begin':
                if self.pending is not None:
                    raise ValueError('overlapping incomplete assessment')
                self.pending = event
            elif action == 'admission':
                if self.pending is None or self.pending['batch_id'] != event['batch_id']:
                    raise ValueError('admission without durable assessment intent')
                self.batches[event['batch_id']] = event
                for row in event['rows']:
                    ident = row['opportunity']['opportunity_id']
                    if ident not in self.opportunity_specs:
                        self.opportunity_specs[ident] = row['opportunity']
                    if row['reserved']:
                        if ident in self.allocations:
                            raise ValueError('reused reservation identity')
                        self.allocations[ident] = {**row, 'released': False}
                self.pending = None; self.checkpoint = event['risk_checkpoint']
                if event.get('scope_conflict'):
                    self.issues.add('opportunity_identity_conflict')
            elif action == 'receipt':
                self._apply_receipt(ExecutionReceipt.restore(event['receipt']), event['asof'])
            elif action == 'cash_receipt':
                cash = PaperEvent.from_mapping(event['event'])
                if cash.event_id not in cash_receipts:
                    cash_receipts[cash.event_id] = cash
                    self.expected.append(cash)
                elif economic(cash_receipts[cash.event_id]) != economic(cash):
                    self.issues.add('cash_receipt_identity_conflict')
            elif action == 'release':
                self.allocations[event['allocation_id']]['released'] = True
                if event['release_id'] in self.releases:
                    raise ValueError('reused durable release identity')
                self.releases[event['release_id']] = event
            elif action == 'fault':
                self.issues.add(event['reason'])
            else:
                raise ValueError('unknown coordinator evidence')
            self.last_asof = max(self.last_asof, event.get('asof', -1))
        self.last_asof = max(self.last_asof, self.account.last_asof)

    def _quantity(self, ident, *, opened=False):
        values = [r for r in self.trades.values() if r.allocation_id == ident]
        return sum((rational(r.quantity_base) * (1 if r.purpose == 'open' else -1)
            for r in values if not opened or r.purpose == 'open'), Fraction(0))

    @staticmethod
    def _terminal(order):
        return order['terminal'] and order['final'] is not None and order['final'] == order['filled']

    def _apply_receipt(self, r, asof):
        signature = digest(economic(r))
        if r.receipt_id in self.receipts:
            if self.receipts[r.receipt_id] != signature:
                self.issues.add('receipt_identity_conflict')
            return
        self.receipts[r.receipt_id] = signature
        if (asof < self.last_asof or not clock_known(r.clock, asof, self.account.anchor)
                or r.occurred_ns < self.account.anchor.utc_ns):
            self.issues.add('receipt_clock_or_ordering_unknown'); return
        allocation = self.allocations.get(r.allocation_id)
        if allocation is None:
            self.issues.add('receipt_without_allocation'); return
        o = allocation['opportunity']
        key = (o['venue'], o['asset'], o['symbol'], r.order_id)
        order = self.orders.get(key)
        if r.kind == 'gap':
            self.issues.add('source_gap_requires_reconciliation'); return
        if r.kind == 'submit':
            if order is not None:
                self.issues.add('order_identity_reused'); return
            own = [v for v in self.orders.values() if v['allocation_id'] == r.allocation_id]
            if len(own) >= MAX_ORDERS:
                self.issues.add('order_attempt_budget_exceeded')
            if any(not self._terminal(v) for v in own):
                self.issues.add('new_order_before_previous_terminal_reconciliation')
            remaining = abs(rational(o['quantity'])) - self._quantity(r.allocation_id, opened=True)
            if r.purpose == 'close':
                remaining = abs(self._quantity(r.allocation_id))
            elif (any(v['purpose'] == 'close' for v in own) or
                    asof > o['clock']['mono_ns']+NS or
                    self.account.anchor.utc_ns+asof-self.account.anchor.mono_ns >= o['horizon_utc_ns']):
                self.issues.add('entry_after_exit_intent_or_horizon')
            if rational(r.quantity_base) > remaining:
                self.issues.add('submission_exceeds_remaining_quantity')
            if allocation['released']:
                self.issues.add('submission_after_release')
            self.orders[key] = {'allocation_id': r.allocation_id, 'order_id': r.order_id,
                'purpose': r.purpose, 'requested': rational(r.quantity_base), 'filled': Fraction(0),
                'terminal': False, 'final': None, 'terminal_ns': None, 'cancel_requested': False}
            return
        if order is None:
            self.issues.add('order_without_submission')
            order = self.orders[key] = {'allocation_id': r.allocation_id, 'order_id': r.order_id,
                'purpose': r.purpose, 'requested': None, 'filled': Fraction(0),
                'terminal': False, 'final': None, 'terminal_ns': None, 'cancel_requested': False}
        if (order['allocation_id'], order['purpose']) != (r.allocation_id, r.purpose):
            self.issues.add('order_owner_or_purpose_conflict')
        if r.kind == 'fill':
            trade_key = (o['venue'], o['asset'], o['symbol'], r.trade_id)
            if trade_key in self.trades:
                prior = self.trades[trade_key]
                fields = ('allocation_id', 'order_id', 'purpose', 'quantity_base', 'price', 'fee', 'occurred_ns', 'source_identity')
                if any(getattr(prior, f) != getattr(r, f) for f in fields):
                    self.issues.add('trade_identity_or_owner_conflict')
                return
            self.trades[trade_key] = r; order['filled'] += rational(r.quantity_base)
            if order['requested'] is None or order['filled'] > order['requested']:
                self.issues.add('observed_overfill_or_unknown_requested_total')
            if order['terminal_ns'] is not None and r.occurred_ns > order['terminal_ns']:
                self.issues.add('fill_economic_time_after_terminal')
            if allocation['released']:
                self.issues.add('fill_after_release')
            if r.occurred_ns >= o['horizon_utc_ns']:
                self.issues.add('observed_fill_after_model_horizon')
            ident = 'portfolio-fill:' + digest(trade_key)
            negative = (rational(o['quantity']) < 0) == (r.purpose == 'open')
            signed_quantity = r.quantity_base.copy_negate() if negative else r.quantity_base
            self.expected.append(PaperEvent(ident, 'fill', o['venue'], o['asset'], o['symbol'],
                r.occurred_ns, r.clock, r.source_identity,
                quantity=signed_quantity, price=r.price, fee=r.fee))
        elif r.kind in ('complete', 'cancelled', 'rejected'):
            final = None if r.cumulative_filled_base is None else rational(r.cumulative_filled_base)
            if order['final'] is not None and final != order['final']:
                self.issues.add('terminal_total_conflict')
            order['terminal'] = True; order['final'] = final
            if order['terminal_ns'] is None:
                order['terminal_ns'] = r.occurred_ns
            if final is not None and (final < order['filled'] or
                    (order['requested'] is not None and final > order['requested'])):
                self.issues.add('terminal_total_contradicts_received_quantity')
        elif r.kind == 'cancel_request':
            order['cancel_requested'] = True

    def _joins(self):
        actual = {e.event_id: e for e in self.account.accepted_events}
        expected = {}; missing = []; issues = set(self.issues)
        for e in self.expected:
            if e.event_id in expected and plain(e) != plain(expected[e.event_id]):
                issues.add('financial_receipt_identity_conflict')
            expected[e.event_id] = e
            if e.event_id not in actual:
                missing.append(e)
            elif plain(actual[e.event_id]) != plain(e):
                issues.add('financial_join_payload_or_first_clock_mismatch')
        if set(actual) - set(expected):
            issues.add('unattributed_financial_event')
        if missing:
            issues.add('receipt_to_cash_join_incomplete')
        return missing, issues

    def recover(self, asof):
        self._refresh(); self._check_risk()
        if self.pending is not None:
            raise ValueError('finish identical pending assessment before financial writes')
        if type(asof) is not int or asof < self.last_asof:
            raise ValueError('current nonregressing recovery as-of required')
        missing, issues = self._joins(); results = []
        if issues - self.issues - {'receipt_to_cash_join_incomplete'}:
            return {'recovered': results, 'reasons': sorted(issues)}
        for event in missing:
            result = self.account.post(event, asof); results.append(result)
            if result['status'] not in ('applied', 'duplicate'):
                break
        self._refresh()
        return {'recovered': results, 'reasons': sorted(self._joins()[1])}

    def post(self, receipt, asof):
        if not isinstance(receipt, ExecutionReceipt) or type(asof) is not int or asof < 0:
            raise ValueError('typed paper receipt/as-of required')
        self._refresh(); self._check_risk()
        if self.pending is not None:
            raise ValueError('incomplete assessment must resolve before receipt writes')
        if self._joins()[0]:
            raise ValueError('recover incomplete receipt-to-cash joins before later receipts')
        self._commit({'action': 'receipt', 'receipt': receipt, 'asof': asof}, self.head)
        return self.recover(max(asof, self.last_asof))

    def post_cash(self, event, asof):
        if not isinstance(event, PaperEvent) or event.kind == 'fill' or type(asof) is not int or asof < 0:
            raise ValueError('existing non-fill PaperEvent required')
        self._refresh(); self._check_risk()
        if self.pending is not None:
            raise ValueError('incomplete assessment must resolve before cash writes')
        if self._joins()[0]:
            raise ValueError('recover incomplete receipt-to-cash joins before later cash writes')
        self._commit({'action': 'cash_receipt', 'event': event.mapping(), 'asof': asof}, self.head)
        return self.recover(max(asof, self.last_asof))

    @_precision
    def _view(self, asof, marks):
        raw = self.account.snapshot(asof, marks); self._refresh()
        missing, issues = self._joins()
        if self.pending is not None:
            issues.add('assessment_incomplete')
        if any(o['terminal'] and not self._terminal(o) for o in self.orders.values()):
            issues.add('terminal_fill_totals_missing_or_unreconciled')
        groups = {}
        now_utc = self.account.anchor.utc_ns+asof-self.account.anchor.mono_ns
        for ident, a in self.allocations.items():
            o = a['opportunity']; q = self._quantity(ident)
            if a['released'] and not q and not any(v['allocation_id'] == ident and not self._terminal(v) for v in self.orders.values()):
                continue
            signed = q*(1 if rational(o['quantity']) > 0 else -1)
            if q and now_utc >= o['horizon_utc_ns']:
                issues.add('mandatory_horizon_exit_unobserved')
            if asof > o['clock']['mono_ns']+NS and any(v['allocation_id'] == ident
                    and v['purpose'] == 'open' and not self._terminal(v) for v in self.orders.values()):
                issues.add('expired_entry_intent_with_unresolved_orders')
            groups.setdefault((o['venue'], o['asset'], o['symbol']), []).append((ident, signed))
        output = []; holdings = []
        for account in raw['accounts']:
            venue, asset = account['venue'], account['asset']
            extra = Fraction(0); extra_gross = Fraction(0); symbols = {}
            position = {p['symbol']: p for p in account['positions']}
            weights = {symbol: abs(rational(p['quantity_base']))*rational(p['average_entry'])
                for symbol, p in position.items()}
            weight_total = sum(weights.values(), Fraction(0))
            # Conserve the actual kernel's reported collateral even when its
            # 80-digit weighted-average basis has a nonterminating expansion.
            locked_scale = rational(account['locked_capital'])/weight_total if weight_total else Fraction(0)
            names = set(position) | {k[2] for k in groups if k[:2] == (venue, asset)}
            for symbol in sorted(names):
                members = groups.get((venue, asset, symbol), [])
                total = sum((q for _, q in members), Fraction(0))
                p = position.get(symbol); actual = rational(p['quantity_base']) if p else Fraction(0)
                if total != actual or any(q*total < 0 for _, q in members):
                    issues.add('model_inventory_not_equal_to_same_sign_account')
                locked = weights.get(symbol, Fraction(0))*locked_scale
                entry = abs(number(p['quantity_base']))*number(p['average_entry']) if p else Decimal(0)
                gross = rational(entry)
                if p and p['unrealized_liquidation_pnl'] is not None:
                    close = entry+(1 if actual > 0 else -1)*number(p['unrealized_liquidation_pnl'])
                    gross = rational(max(entry, close))
                elif p:
                    issues.add('actual_gross_mark_unknown')
                for ident, q in members:
                    a = self.allocations[ident]
                    fraction = abs(q/total) if total else Fraction(0)
                    held = max(Fraction(0), rational(a['reserve_quote'])-locked*fraction)
                    held_gross = max(Fraction(0), rational(a['gross_floor_quote'])-gross*fraction)
                    extra += held; extra_gross += held_gross
                    symbols[symbol] = symbols.get(symbol, Fraction(0))+held_gross
                    holdings.append({'allocation_id': ident, 'model_id': a['opportunity']['model_id'],
                        'open_quantity_base': str(q), 'attributed_actual_locked_quote': str(locked*fraction),
                        'extra_capital_floor_quote': str(held), 'extra_gross_floor_quote': str(held_gross),
                        'released': a['released']})
            available = None
            if account['cash'] is not None and account['nav'] is not None:
                available = max(Fraction(0),
                    min(rational(account['cash']), rational(account['nav']))
                    - rational(account['locked_capital']) - extra)
            else:
                issues.add('cash_or_liquidation_equity_unknown')
            output.append({'venue': venue, 'asset': asset, 'extra_capital_floor_quote': str(extra),
                'extra_gross_floor_quote': str(extra_gross),
                'symbol_extra_gross_quote': {k: str(v) for k, v in symbols.items()},
                'computed_available_after_floors_component': None if available is None else str(available)})
        for entry in output:
            entry['available_after_floors_quote'] = None if issues else entry['computed_available_after_floors_component']
        return {'account': raw, 'accounts': output, 'holdings': holdings,
            'reasons': sorted(issues), 'unapplied_fill_ids': [e.event_id for e in missing],
            'pending_orders': sum(not self._terminal(v) for v in self.orders.values()),
            'actual_order_allowed': False, 'activation_allowed': False,
            'conditional_budgets_known': not bool(issues), 'source_reports_authenticated': False,
            'actual_expected_net_return': None, 'prospective_days': 0}

    def snapshot(self, asof, marks=()):
        self._refresh(); self._check_risk()
        if type(asof) is not int or asof < self.last_asof:
            raise ValueError('snapshot as-of cannot regress')
        return self._view(asof, tuple(marks))

    def admit(self, batch_id, opportunities, books, fees_bp, *, asof, risk_inputs, market_reports, marks=()):
        text(batch_id); opportunities = tuple(opportunities); marks = tuple(marks)
        if not 0 <= len(opportunities) <= MAX_BATCH or any(not isinstance(o, Opportunity) for o in opportunities):
            raise ValueError('finite typed allocation batch required')
        ids = {o.opportunity_id for o in opportunities}
        if len(ids) != len(opportunities) or any(set(m) != ids for m in (books, fees_bp, market_reports)):
            raise ValueError('exact unique per-opportunity evidence scope required')
        fields = {'clock', 'complete', 'session_open', 'fee_inputs_known',
            'contract_version', 'expected_contract_version', 'mode'}
        if (set(risk_inputs) != fields or not isinstance(risk_inputs['clock'], FrameClock)
                or risk_inputs['mode'] not in ('prospective', 'fixture', 'historical')):
            raise ValueError('explicit typed risk inputs required')
        for o in opportunities:
            quantity_resolution(o.quantity)
            if o.horizon_utc_ns-o.clock.utc_ns > MAX_HORIZON_NS:
                raise ValueError('this coordinator supports horizons at most12hours')
        for fee in fees_bp.values():
            if fee is not None and number(fee, nonnegative=True) > 10000:
                raise ValueError('fee outside supported range')
        request = plain({'opportunities': opportunities, 'books': books, 'fees_bp': fees_bp,
            'asof': asof, 'risk_inputs': risk_inputs, 'market_reports': market_reports, 'marks': marks})
        if len(json.dumps(request, allow_nan=False).encode()) > 24576:
            raise ValueError('bounded allocation evidence required')
        restore_request(request)  # Validate the durable round-trip before any intent.
        signature = digest(request)
        self._refresh(); self._check_risk()
        if self._joins()[0]:
            raise ValueError('recover receipt-to-cash joins before allocation')
        if batch_id in self.batches:
            old = self.batches[batch_id]
            if old['request_sha256'] != signature:
                self._commit({'action': 'fault', 'reason': 'batch_identity_conflict', 'asof': asof}, self.head)
                raise ValueError('batch identity cannot refresh or change')
            return {**old, 'duplicate': True, 'actual_order_allowed': False}
        if self.pending is not None:
            if self.pending['batch_id'] != batch_id or self.pending['request_sha256'] != signature:
                raise ValueError('only identical pending batch may resume')
        else:
            if type(asof) is not int or asof < self.last_asof:
                raise ValueError('nonregressing allocation as-of required')
            before = self._view(asof, marks)
            self._commit({'action': 'assessment_begin', 'batch_id': batch_id,
                'request_sha256': signature, 'request': request,
                'account_state_sha256': digest(before['account']), 'asof': asof}, self.head)
        return self._finish_assessment()

    def observe_risk(self, observation_id, *, asof, risk_inputs, marks=()):
        """Explicit durable risk observation; snapshots alone never write risk.

        It uses the same intent/checkpoint protocol and zero allocation rows.
        Callers must supply every required risk observation; no intrabar or
        scheduled monitoring is inferred from an occasional snapshot.
        """
        return self.admit(observation_id, (), {}, {}, asof=asof,
            risk_inputs=risk_inputs, market_reports={}, marks=marks)

    def resume_assessment(self):
        self._refresh(); self._check_risk()
        if self.pending is None:
            raise ValueError('no pending assessment')
        return self._finish_assessment()

    def _finish_assessment(self):
        begin = self.pending; request = begin['request']; asof = request['asof']
        opportunities, books, risk_inputs, marks = restore_request(request)
        view = self._view(asof, marks)
        if digest(view['account']) != begin['account_state_sha256']:
            raise ValueError('financial state changed during incomplete assessment')
        effective_inputs = dict(risk_inputs)
        if set(view['reasons']) - {'assessment_incomplete'}:
            effective_inputs['complete'] = False
        assessment = assess_batch(self.account, opportunities, books, request['fees_bp'],
            asof=asof, anchor=self.account.anchor, risk=self.risk,
            risk_inputs=effective_inputs, market_reports=request['market_reports'], marks=marks)
        if digest(assessment['account_before']) != begin['account_state_sha256']:
            raise ValueError('financial state changed while evaluating allocation')
        risk_rows = self._check_risk(); extra = risk_rows[self.checkpoint['count']:]
        if not extra or any(r['event'] != extra[-1]['event'] for r in extra):
            raise ValueError('unbound risk observations during assessment')
        available = {(r['venue'], r['asset']): None if r['computed_available_after_floors_component'] is None
            else Fraction(r['computed_available_after_floors_component']) for r in view['accounts']}
        pending_gross = {(r['venue'], r['asset']): Fraction(r['extra_gross_floor_quote']) for r in view['accounts']}
        symbol_pending = {(r['venue'], r['asset']): {k: Fraction(v) for k, v in r['symbol_extra_gross_quote'].items()} for r in view['accounts']}
        actual_risk = {(r['venue'], r['asset']): r for r in assessment['risk_assessment']['accounts']}
        active = sum(not a['released'] for a in self.allocations.values())
        directions = {}
        for allocation in self.allocations.values():
            o = allocation['opportunity']
            if not allocation['released']:
                directions[(o['venue'], o['asset'], o['symbol'])] = rational(o['quantity'])
        rows = []
        for opportunity, old in zip(opportunities, assessment['rows']):
            key = opportunity.venue, opportunity.asset; symbol = opportunity.symbol
            reasons = list(old['reasons']) + [r for r in view['reasons'] if r != 'assessment_incomplete']
            market = request['market_reports'][opportunity.opportunity_id]
            if not isinstance(market, dict) or market.get('instrument_type') != 'perpetual':
                reasons.append('perpetual_product_identity_unverified')
            prior = self.allocations.get(opportunity.opportunity_id)
            if prior is not None:
                reasons.append('opportunity_identity_already_accounted')
            original = self.opportunity_specs.get(opportunity.opportunity_id)
            if original is not None and original != plain(opportunity):
                reasons.append('opportunity_identity_conflict')
            if active >= MAX_ACTIVE:
                reasons.append('active_allocation_limit')
            if directions.get((*key, symbol), Fraction(0))*rational(opportunity.quantity) < 0:
                reasons.append('opposite_model_inventory_requires_separate_contract')
            reserve = None if old['planned_capital_quote'] is None else rational(old['planned_capital_quote'])
            gross = None if old['cost']['risk_gross_notional_quote'] is None else rational(old['cost']['risk_gross_notional_quote'])
            if reserve is not None:
                if available.get(key) is None or reserve > available[key]:
                    reasons.append('durable_segregated_capital_exceeded')
                risk = actual_risk.get(key)
                if gross is None or risk is None or not risk['gross_notional_complete']:
                    reasons.append('gross_scope_unknown')
                else:
                    base = rational(self.account.initial[key])
                    if rational(risk['gross_notional'])+pending_gross[key]+gross > base*rational(self.risk.policy.max_venue_gross_fraction):
                        reasons.append('durable_venue_gross_limit')
                    if rational(risk['symbol_gross'].get(symbol, '0'))+symbol_pending[key].get(symbol, Fraction(0))+gross > base*rational(self.risk.policy.max_symbol_gross_fraction):
                        reasons.append('durable_symbol_gross_limit')
            allowed = old['conditional_batch_inclusion'] and not reasons
            if allowed:
                available[key] -= reserve; pending_gross[key] += gross
                symbol_pending[key][symbol] = symbol_pending[key].get(symbol, Fraction(0))+gross; active += 1
                directions[(*key, symbol)] = rational(opportunity.quantity)
            rows.append({'opportunity': plain(opportunity), 'reserved': allowed,
                'reserve_quote': str(reserve) if allowed else None,
                'gross_floor_quote': str(gross) if allowed else None,
                'forecast': old['forecast'], 'cost_tiers': old['cost_tiers'],
                'reasons': sorted(set(reasons)), 'actual_order_allowed': False})
        event = {'action': 'admission', 'batch_id': begin['batch_id'], 'request_sha256': begin['request_sha256'],
            'rows': rows, 'asof': asof, 'risk_checkpoint': self._checkpoint(risk_rows),
            'risk_stops': assessment['risk_assessment']['stops'],
            'simulation_only': True, 'activation_allowed': False}
        if any('opportunity_identity_conflict' in r['reasons'] for r in rows):
            event['scope_conflict'] = True
        self._commit(event, self.head)
        return event

    def release(self, allocation_id, *, release_id, clock, source_identity, asof):
        text(allocation_id); text(release_id); text(source_identity)
        if not isinstance(clock, FrameClock) or not clock_known(clock, asof, self.account.anchor):
            raise ValueError('causal release evidence required')
        self._refresh(); self._check_risk()
        if type(asof) is not int or asof < self.last_asof:
            raise ValueError('release as-of cannot regress')
        if release_id in self.releases:
            old = self.releases[release_id]
            if old['allocation_id'] != allocation_id or old['source_identity'] != source_identity:
                self._commit({'action': 'fault', 'reason': 'release_identity_conflict', 'asof': asof}, self.head)
                raise ValueError('release identity cannot change ownership')
            return {'released': True, 'duplicate': True, 'actual_order_allowed': False}
        allocation = self.allocations[allocation_id]
        if allocation['released']:
            return {'released': True, 'duplicate': True, 'actual_order_allowed': False}
        view = self._view(asof, ())
        own_orders = [o for o in self.orders.values() if o['allocation_id'] == allocation_id]
        # Other open allocations may lack marks in this nonfinancial release.
        money_known = all(a['cash'] is not None for a in view['account']['accounts'])
        issues = set(view['reasons']) - {'actual_gross_mark_unknown', 'cash_or_liquidation_equity_unknown'}
        if issues or not money_known or self._quantity(allocation_id) or any(not self._terminal(o) for o in own_orders):
            return {'released': False, 'reasons': sorted(issues | {'allocation_not_flat_terminal_and_cash_reconciled'}), 'actual_order_allowed': False}
        self._commit({'action': 'release', 'allocation_id': allocation_id, 'release_id': release_id,
            'clock': plain(clock), 'source_identity': source_identity, 'asof': asof}, self.head)
        return {'released': True, 'duplicate': False, 'actual_order_allowed': False}

    def close(self):
        if self.lease is not None:
            fcntl.flock(self.lease, fcntl.LOCK_UN); self.lease.close(); self.lease = None
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
