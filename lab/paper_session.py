"""Single-writer paper admission and explicit-receipt bridge for new consumers.

Admission records an intent, never a fill. Pending intents block further model
entries across restart. Only caller-supplied PaperEvents reach the native cash
ledger, including unexpected receipts after a risk stop. No market adapter,
order connector, source authentication or prospective evidence is implemented.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal
import fcntl
import json
import os
from pathlib import Path

from lab.paper_account import PaperAccount, PaperEvent, number, text, _precision
from lab.paper_controls import PaperRisk, RiskPolicy, entry_threshold
from lab.paper_solvency import PaperSolvencyGuard
from lab.stream_quotes import FrameClock


FLAGS = dict(simulation_only=True, actual_order_allowed=False, activation_allowed=False,
             new_prospective_paper_days=0)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True, kw_only=True)
class EntryIntent:
    intent_id: str
    venue: str
    asset: str
    symbol: str
    quantity_base: Decimal
    reference_price: Decimal
    expected_gross_quote: Decimal | None
    round_trip_cost_quote: Decimal | None
    error_bound_quote: Decimal | None
    error_calibrated: bool = False
    extra_reserve_quote: Decimal | None = Decimal(0)

    def __post_init__(self):
        for field in ('intent_id', 'venue', 'asset', 'symbol'):
            text(getattr(self, field))
        for field in ('quantity_base', 'reference_price', 'expected_gross_quote',
                      'round_trip_cost_quote', 'error_bound_quote', 'extra_reserve_quote'):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, number(value, positive=field == 'reference_price',
                    nonnegative=field in ('round_trip_cost_quote', 'error_bound_quote', 'extra_reserve_quote')))
        if self.quantity_base is None or self.quantity_base == 0 or self.reference_price is None:
            raise ValueError('explicit nonzero proposed quantity and positive reference required')
        if type(self.error_calibrated) is not bool:
            raise ValueError('explicit conditional calibration declaration required')

    def mapping(self):
        return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(self).items()}


class PaperSession:
    """Dedicated native account/risk journals with a cooperative writer lease.

    Reference price/reserves describe a proposed model entry, not execution.
    Admission is not reusable: a repeated intent only reports durable state.
    Partial or unjoined execution retains exposure and blocks new entries.
    General order cancellation/retry belongs to the existing execution layer;
    this bridge cannot infer that a pending intent was cancelled or filled.
    """
    def __init__(self, directory, initial_balances, anchor, policy, *, contract_version):
        if not isinstance(anchor, FrameClock) or not isinstance(policy, RiskPolicy):
            raise ValueError('typed common anchor and frozen risk policy required')
        self.directory = Path(directory)
        self.closed = False
        self.lease = None
        if any(p.is_symlink() for p in (self.directory, *self.directory.parents)):
            raise ValueError('session directory symlinks are unsupported')
        self.directory.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.directory / 'session-writer.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            self.lease = os.fdopen(fd, 'a+')
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.account = PaperAccount(initial_balances, anchor, journal_path=self.directory / 'account.jsonl')
            self.risk = PaperRisk(self.directory / 'risk.jsonl', policy, anchor,
                                  contract_version=contract_version, initial_balances=initial_balances)
            self.guard = PaperSolvencyGuard(self.risk)
            self._rebuild()
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.lease is not None:
            self.lease.close()
            self.lease = None
        self.closed = True

    def __enter__(self): return self
    def __exit__(self, *exc): self.close()

    def _open(self):
        if self.closed:
            raise ValueError('paper session is closed')

    @_precision
    def _rebuild(self):
        self.intents, self.joins, self.issues = {}, {}, set()
        for record in self.account.evidence:
            if record['namespace'] != 'recovery':
                continue
            p = record['payload']
            component = p.get('component')
            if component == 'paper_session_entry':
                intent = EntryIntent(**p['intent'])
                if intent.intent_id in self.intents:
                    raise ValueError('duplicate session intent declaration')
                count = p.get('accepted_events_before_intent')
                if type(count) is not int or not 0 <= count <= len(self.account.accepted_events):
                    raise ValueError('explicit accepted-receipt watermark required')
                self.intents[intent.intent_id] = p
            elif component == 'paper_session_join':
                if p['event_id'] in self.joins:
                    raise ValueError('duplicate session receipt join')
                self.joins[p['event_id']] = p['intent_id']
            elif component == 'paper_session_issue':
                self.issues.add(p['issue'])
        accepted = {e.event_id: e for e in self.account.accepted_events}
        self.event_indices = {e.event_id: n for n, e in enumerate(self.account.accepted_events)}
        self.filled = {key: Decimal(0) for key in self.intents}
        for event_id, intent_id in self.joins.items():
            if intent_id not in self.intents or event_id not in accepted:
                raise ValueError('session join lacks durable intent or explicit accepted receipt')
            p, e = self.intents[intent_id], accepted[event_id]
            i = EntryIntent(**p['intent'])
            if (p['admitted'] is not True or e.kind != 'fill' or
                    (e.venue, e.asset, e.symbol) != (i.venue, i.asset, i.symbol) or
                    e.quantity * i.quantity_base <= 0 or not self._receipt_after_intent(p, e)):
                raise ValueError('invalid session intent-to-receipt identity')
            self.filled[intent_id] += e.quantity
            if abs(self.filled[intent_id]) > abs(i.quantity_base):
                raise ValueError('session joined quantity exceeds intent')

    def _pending(self):
        return sorted(key for key, p in self.intents.items() if p['admitted'] is True
                      and self.filled[key] != number(p['intent']['quantity_base']))

    def _receipt_after_intent(self, declaration, event):
        # Use the native accepted event, whose first-seen clock is immutable.
        # A duplicate old fill must not discharge a later model reservation,
        # even when its caller supplies a fresh delivery clock.
        return (self.event_indices[event.event_id] >= declaration['accepted_events_before_intent']
                and event.clock.mono_ns >= declaration['clock']['mono_ns']
                and event.occurred_ns >= declaration['clock']['utc_ns'])

    def status(self, asof, marks=()):
        self._open()
        snapshot = self.account.snapshot(asof, marks)
        self._rebuild()
        return {**FLAGS, 'model_new_entries_allowed': False, 'snapshot': snapshot,
                'pending_intents': self._pending(), 'issues': sorted(self.issues),
                'scope': 'explicit receipts only; admission is not a fill or executable market evidence'}

    def _save_intent(self, intent, asof, clock, reasons, threshold=None, risk=None):
        admitted = not reasons
        result = {**FLAGS, 'state': 'INTENT_ADMITTED' if admitted else 'ENTRY_BLOCKED',
                  'intent_id': intent.intent_id, 'intent_admitted': admitted,
                  'model_new_entries_allowed': admitted, 'receipt_required': admitted,
                  'reasons': sorted(set(reasons)), 'threshold': threshold, 'risk': risk}
        self.account.record_evidence('recovery', {'component': 'paper_session_entry', 'intent': intent.mapping(),
            'admitted': admitted, 'asof_mono_ns': asof, 'clock': asdict(clock), 'report': result,
            'accepted_events_before_intent': len(self.account.accepted_events)})
        self._rebuild()
        return result

    @_precision
    def propose_entry(self, intent, *, asof, clock, marks=(), complete, session_open,
                      fee_inputs_known, expected_contract_version, mode='historical', cost_multiple=1):
        """Record one fresh conditional admission, with no financial posting.

        Supplied forecasts/calibration/fees are not authenticated by this API.
        Entries are restricted to a currently flat instrument; scales/reversals
        need another explicit execution design. A reserve includes entry
        notional and supplied round-trip costs/buffer, with no currency netting.
        """
        self._open()
        if not isinstance(intent, EntryIntent):
            raise ValueError('typed proposed entry required')
        if not isinstance(clock, FrameClock):
            raise ValueError('explicit proposed decision clock required')
        snapshot = self.account.snapshot(asof, marks)
        self._rebuild()
        if intent.intent_id in self.intents:
            old = self.intents[intent.intent_id]
            if canonical(old['intent']) != canonical(intent.mapping()):
                raise ValueError('intent identity cannot be reused for a changed proposal')
            return {**FLAGS, 'state': 'EXISTING_INTENT', 'intent_id': intent.intent_id,
                    'intent_admitted': old['admitted'], 'model_new_entries_allowed': False,
                    'pending_intents': self._pending(), 'receipt_required': intent.intent_id in self._pending()}
        reasons = []
        key = intent.venue, intent.asset
        if key not in self.account.initial:
            raise ValueError('intent names an unfunded venue or settlement asset')
        if self._pending(): reasons.append('earlier_intent_requires_explicit_receipts')
        if self.issues: reasons.append('session_receipt_join_requires_reconciliation')
        if self.account.positions.get((*key, intent.symbol), (Decimal(0), Decimal(0)))[0] != 0:
            reasons.append('new_entry_requires_flat_instrument')
        if reasons:
            # An already-ineligible proposal is not a new observation of risk.
            # In particular a pending admission must not accidentally turn a
            # missing interim mark into a persistent legacy data stop.
            return self._save_intent(intent, asof, clock, reasons)
        threshold = entry_threshold(intent.expected_gross_quote, intent.round_trip_cost_quote,
            intent.error_bound_quote, asset=intent.asset, cost_multiple=cost_multiple,
            error_calibrated=intent.error_calibrated, extra_reserve_quote=intent.extra_reserve_quote)
        if threshold['model_entry_allowed'] is not True:
            reasons.append('conditional_forecast_cost_or_error_not_admissible')
        notional = abs(intent.quantity_base) * intent.reference_price
        reserves = None
        if intent.round_trip_cost_quote is not None and intent.extra_reserve_quote is not None:
            reserves = {key: notional + cost_multiple * (intent.round_trip_cost_quote + intent.extra_reserve_quote)}
        else:
            reasons.append('proposed_reserve_unknown')
        risk = self.guard.observe(snapshot, required_reserves=reserves, asof=asof, clock=clock,
            complete=complete, session_open=session_open, fee_inputs_known=fee_inputs_known,
            contract_version=self.risk.contract_version, expected_contract_version=expected_contract_version, mode=mode)
        if risk['model_new_entries_allowed'] is not True:
            reasons.append('current_risk_or_capital_veto')
        existing = next(a for a in risk['legacy_risk']['accounts'] if (a['venue'], a['asset']) == key)
        if existing['gross_notional'] is None:
            reasons.append('projected_gross_exposure_unknown')
        else:
            base = self.account.initial[key]
            if number(existing['gross_notional']) + notional > base * self.risk.policy.max_venue_gross_fraction:
                reasons.append('proposed_venue_gross_limit')
            gross = number(existing['symbol_gross'].get(intent.symbol, '0')) + notional
            if gross > base * self.risk.policy.max_symbol_gross_fraction:
                reasons.append('proposed_symbol_gross_limit')
        return self._save_intent(intent, asof, clock, reasons, threshold, risk)

    def _issue(self, issue):
        if issue not in self.issues:
            self.account.record_evidence('recovery', {'component': 'paper_session_issue', 'issue': issue})
            self.issues.add(issue)

    @_precision
    def record_receipt(self, event, asof, *, intent_id=None):
        """Always book supplied receipts through the native ledger, even halted.

        No fill follows from admission alone. A crash after native posting but
        before the join leaves the intent pending; explicitly retrying the same
        receipt is cash-idempotent and finishes the join. No journal is repaired.
        """
        self._open()
        if intent_id is not None: text(intent_id)
        posted = self.account.post(event, asof)
        self._rebuild()
        joined = False
        if intent_id is not None and posted['status'] in ('applied', 'duplicate'):
            old = self.joins.get(event.event_id)
            if old is not None:
                joined = old == intent_id
                if not joined: self._issue(event.event_id + ':receipt_already_joined_to_other_intent')
            else:
                p = self.intents.get(intent_id)
                i = None if p is None else EntryIntent(**p['intent'])
                native = next(e for e in self.account.accepted_events if e.event_id == event.event_id)
                if (i is None or p['admitted'] is not True or event.kind != 'fill' or
                        (event.venue, event.asset, event.symbol) != (i.venue, i.asset, i.symbol) or
                        event.quantity * i.quantity_base <= 0 or
                        abs(self.filled[intent_id] + event.quantity) > abs(i.quantity_base) or
                        not self._receipt_after_intent(p, native)):
                    self._issue(event.event_id + ':intent_receipt_identity_or_quantity_mismatch')
                else:
                    self.account.record_evidence('recovery', {'component': 'paper_session_join',
                        'intent_id': intent_id, 'event_id': event.event_id})
                    joined = True
        self._rebuild()
        return {**FLAGS, 'model_new_entries_allowed': False, 'financial_receipt': posted,
                'joined_to_intent': joined, 'pending_intents': self._pending(), 'issues': sorted(self.issues)}

    @_precision
    def plan_close(self, venue, asset, symbol, *, exit_price, fee_rate_fraction, asof):
        """Read-only close arithmetic: held base quantity and exit-notional fee.

        This is not a close fill or an executable instruction. Unknown fee rate
        stays unknown; an explicit close receipt may still record unknown cash.
        """
        self._open()
        self.account.snapshot(asof)
        key = text(venue), text(asset), text(symbol)
        if key[:2] not in self.account.initial: raise ValueError('funded close account required')
        q = self.account.positions.get(key, (Decimal(0), Decimal(0)))[0]
        if not q: raise ValueError('an explicit held position is required')
        price = number(exit_price, positive=True)
        rate = None if fee_rate_fraction is None else number(fee_rate_fraction, nonnegative=True)
        notional = abs(q) * price
        return {**FLAGS, 'model_new_entries_allowed': False, 'venue': venue, 'asset': asset, 'symbol': symbol,
                'quantity_base': str(-q), 'exit_price': str(price), 'exit_notional_quote': str(notional),
                'estimated_fee_quote': None if rate is None else str(notional * rate),
                'explicit_close_receipt_required': True}
