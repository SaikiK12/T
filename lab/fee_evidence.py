"""Offline redacted fee statements and persistent paper quota reservations.

No account/API access or provider authentication is performed. Even a complete
owner-supplied statement is a conditional paper assumption, not proof of charged
fees. Callers persist ``book.events`` in their existing append-only journal;
``replay`` restores consumption without renewing a grant on import/revision.
"""
from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import threading
import time

FIELDS = ('schema_version', 'statement_id', 'revision', 'venue', 'instrument',
          'account_scope', 'order_role', 'order_class', 'rate', 'rate_unit',
          'fee_asset', 'notional_asset', 'source_identity', 'evidence_level',
          'source_time_ns', 'valid_from_ns', 'valid_until_ns', 'promotional',
          'entitlement_attested', 'entitlement_id', 'quota_total_notional',
          'quota_used_notional')
REQUEST = ('venue', 'instrument', 'account_scope', 'order_role', 'order_class',
           'fee_asset', 'notional_asset', 'entry_ns', 'exit_ns')


def amount(value):
    if isinstance(value, bool): raise ValueError('explicit finite nonnegative amount required')
    try: x = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): raise ValueError('invalid amount') from None
    if not x.is_finite() or x < 0: raise ValueError('invalid amount')
    return x


def clock(value):
    if type(value) is not int or value < 0: raise ValueError('nonnegative integer clock required')
    return value


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('ambiguous duplicate document fields')
        result[key] = value
    return result


@dataclass(frozen=True)
class FeeStatement:
    schema_version: int
    statement_id: str
    revision: int
    venue: str
    instrument: str
    account_scope: str
    order_role: str
    order_class: str
    rate: Decimal | None
    rate_unit: str
    fee_asset: str | None
    notional_asset: str | None
    source_identity: str
    evidence_level: str
    source_time_ns: int | None
    valid_from_ns: int | None
    valid_until_ns: int | None
    promotional: bool
    entitlement_attested: bool
    entitlement_id: str | None
    quota_total_notional: Decimal | None
    quota_used_notional: Decimal | None
    received_ns: int
    document_sha256: str = field(init=False)

    def __post_init__(self):
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError('unsupported fee statement schema')
        for k in ('statement_id', 'instrument', 'account_scope', 'order_class', 'source_identity'):
            v = getattr(self, k)
            if not isinstance(v, str) or not v or len(v) > 256 or any(ord(c) < 32 for c in v):
                raise ValueError('nonempty redacted identity required')
        if type(self.revision) is not int or self.revision < 1: raise ValueError('positive revision required')
        if self.venue not in ('mexc', 'lighter') or self.order_role not in ('maker', 'taker'):
            raise ValueError('explicit venue and matching role required')
        if self.rate_unit not in ('fraction', 'percent', 'bp', 'unverified'):
            raise ValueError('explicit supported rate unit required')
        if self.evidence_level not in ('owner_supplied_redacted', 'public_schedule', 'synthetic'):
            raise ValueError('unsigned evidence level required')
        for k in ('promotional', 'entitlement_attested'):
            if type(getattr(self, k)) is not bool: raise ValueError('explicit entitlement booleans required')
        for k in ('fee_asset', 'notional_asset', 'entitlement_id'):
            v = getattr(self, k)
            if v is not None and (not isinstance(v, str) or not v or len(v) > 128):
                raise ValueError('explicit asset or redacted entitlement identifier required')
        clock(self.received_ns)
        for k in ('source_time_ns', 'valid_from_ns', 'valid_until_ns'):
            if getattr(self, k) is not None: clock(getattr(self, k))
        if self.source_time_ns is not None and self.source_time_ns > self.received_ns:
            raise ValueError('source publication cannot follow first receipt')
        if self.valid_from_ns is not None and self.valid_until_ns is not None and self.valid_from_ns >= self.valid_until_ns:
            raise ValueError('nonempty half-open validity interval required')
        for k in ('rate', 'quota_total_notional', 'quota_used_notional'):
            if getattr(self, k) is not None: object.__setattr__(self, k, amount(getattr(self, k)))
        if self.fraction() is not None and self.fraction() > 1: raise ValueError('unsupported fee magnitude')
        if self.quota_total_notional is not None and self.quota_used_notional is not None and self.quota_used_notional > self.quota_total_notional:
            raise ValueError('quota usage exceeds total')
        digest = hashlib.sha256(json.dumps(self.to_mapping(), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        object.__setattr__(self, 'document_sha256', digest)

    def fraction(self):
        if self.rate is None or self.rate_unit == 'unverified': return None
        return self.rate / {'fraction': Decimal(1), 'percent': Decimal(100), 'bp': Decimal(10000)}[self.rate_unit]

    def to_mapping(self):
        return {k: str(v) if isinstance((v := getattr(self, k)), Decimal) else v for k in FIELDS}

    @classmethod
    def from_mapping(cls, payload, *, received_ns):
        if type(payload) is not dict or set(payload) != set(FIELDS):
            raise ValueError('redacted fee statement contains missing or unrecognized fields')
        return cls(**payload, received_ns=received_ns)


def import_fee_statement(path, *, received_ns=None):
    """Read ONLY the explicitly supplied regular .json file, bounded to64KiB.

    Local first-seen time comes from the importer/caller, never document fields.
    No file discovery, credentials, symlinks or source-value printing occurs.
    """
    p = Path(path).absolute()
    forbidden = {'secret', 'secrets', 'credential', 'credentials', 'private', 'key',
                 'keys', 'token', 'tokens', 'password', 'seed', 'mnemonic', 'wallet'}
    if p.suffix.lower() != '.json' or forbidden.intersection(re.split(r'[^a-z0-9]+', p.stem.lower())):
        raise ValueError('explicit redacted fee JSON required')
    if any(x.is_symlink() for x in (p, *p.parents)): raise ValueError('symlink fee inputs are unsupported')
    try:
        fd = os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= 65536:
                raise ValueError('fee document size/type unsupported')
            raw = stream.read(65536); after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('fee document changed during import')
        observed = time.time_ns() if received_ns is None else received_ns
        statement = FeeStatement.from_mapping(json.loads(raw, object_pairs_hook=unique_fields), received_ns=observed)
        object.__setattr__(statement, 'document_sha256', hashlib.sha256(raw).hexdigest())
        return statement
    except (OSError, ValueError, TypeError):
        raise ValueError('invalid redacted fee statement document') from None


def _result(statement, reasons=(), state='unknown', **extra):
    return {'state': state, 'reasons': list(reasons), 'rate_fraction': None,
            'source_identity': statement.source_identity if statement else None,
            'statement_id': statement.statement_id if statement else None,
            'revision': statement.revision if statement else None,
            'evidence_level': statement.evidence_level if statement else None,
            'document_sha256': statement.document_sha256 if statement else None,
            'provider_authenticated': False, 'account_effective_fee_verified': False,
            'usable_for_paper_assumption': False, **extra}


def request_schema(request):
    if type(request) is not dict or set(request) != set(REQUEST): raise ValueError('fee request identity/interval schema required')
    if clock(request['entry_ns']) > clock(request['exit_ns']): raise ValueError('ordered entry/exit clocks required')


def assess_fee(statement, request, asof_ns, entry_notional, exit_notional, *, used_notional=None):
    """Evaluate a two-leg fee assumption; valid_until is exclusive for BOTH fills."""
    clock(asof_ns)
    request_schema(request); start, end = request['entry_ns'], request['exit_ns']
    entry, exit = amount(entry_notional), amount(exit_notional)
    if entry == 0 or exit == 0: raise ValueError('both entry and exit notional must be positive')
    if statement is None: return _result(None, ['fee_statement_missing'])
    if not isinstance(statement, FeeStatement): raise ValueError('typed fee statement required')
    if any(request[k] != getattr(statement, k) for k in REQUEST[:-2]):
        return _result(statement, ['fee_request_identity_or_asset_mismatch'], 'blocked')
    reasons = []
    if statement.received_ns > min(asof_ns, start): reasons.append('statement_not_known_before_decision_and_entry')
    if statement.source_time_ns is None: reasons.append('source_publication_unknown')
    if statement.valid_from_ns is None or statement.valid_until_ns is None:
        reasons.append('fee_validity_interval_unknown')
    elif start < statement.valid_from_ns or end >= statement.valid_until_ns:
        reasons.append('entry_or_exit_outside_fee_validity')
    if statement.fraction() is None: reasons.append('fee_rate_or_unit_unknown')
    if statement.fee_asset is None or statement.notional_asset is None: reasons.append('fee_or_notional_asset_unknown')
    elif statement.fee_asset != statement.notional_asset: reasons.append('fee_asset_conversion_unverified')
    remaining = None
    quota = statement.promotional or statement.quota_total_notional is not None or statement.quota_used_notional is not None
    if statement.promotional and (not statement.entitlement_attested or statement.evidence_level == 'public_schedule'):
        reasons.append('promotional_account_entitlement_unattested')
    if quota:
        if statement.entitlement_id is None or statement.quota_total_notional is None or statement.quota_used_notional is None:
            reasons.append('round_trip_quota_or_grant_unknown')
        else:
            used = max(statement.quota_used_notional, amount(used_notional)) if used_notional is not None else statement.quota_used_notional
            remaining = statement.quota_total_notional - used - entry - exit
            if remaining < 0: reasons.append('round_trip_quota_insufficient')
    if reasons: return _result(statement, reasons)
    rate = statement.fraction()
    return _result(statement, ['unsigned_statement_not_provider_authenticated'], 'conditional',
                   rate_fraction=str(rate), usable_for_paper_assumption=True, fee_asset=statement.fee_asset,
                   entry_fee=str(entry*rate), exit_fee=str(exit*rate), total_fee=str((entry+exit)*rate),
                   quota_remaining_after_round_trip=str(remaining) if remaining is not None else None)


class FeeEvidenceBook:
    """Append-only paper assumptions/reservations, replayable by the caller's journal."""
    def __init__(self):
        self._statements, self._reserved, self._reservations, self._events, self._grant_scopes = {}, {}, {}, [], {}
        self._last_asof = -1; self._lock = threading.RLock()

    @property
    def events(self): return deepcopy(tuple(self._events))

    def add(self, statement):
        if not isinstance(statement, FeeStatement): raise ValueError('typed fee statement required')
        with self._lock:
            history = self._statements.setdefault(statement.statement_id, [])
            same = next((s for s in history if s.revision == statement.revision), None)
            grant = self.grant_key(statement)
            grant_scope = (statement.notional_asset, statement.quota_total_notional, statement.valid_from_ns, statement.valid_until_ns)
            stable = ('venue', 'instrument', 'account_scope', 'order_role', 'order_class', 'fee_asset',
                      'notional_asset', 'valid_from_ns', 'valid_until_ns', 'promotional', 'entitlement_id', 'quota_total_notional')
            if grant and grant in self._grant_scopes and self._grant_scopes[grant] != grant_scope:
                result = {'state': 'blocked', 'reasons': ['existing_entitlement_scope_or_cap_changed']}
            elif same:
                result = {'state': 'duplicate' if same.to_mapping() == statement.to_mapping() else 'blocked',
                          'reasons': [] if same.to_mapping() == statement.to_mapping() else ['conflicting_statement_revision']}
            elif history and (statement.revision <= history[-1].revision or statement.received_ns < history[-1].received_ns
                              or (statement.source_time_ns is not None and history[-1].source_time_ns is not None
                                  and statement.source_time_ns < history[-1].source_time_ns)
                              or any(getattr(statement, k) != getattr(history[-1], k) for k in stable)
                              or (statement.quota_used_notional is not None and history[-1].quota_used_notional is not None
                                  and statement.quota_used_notional < history[-1].quota_used_notional)):
                result = {'state': 'blocked', 'reasons': ['stale_revision_changed_scope_or_reduced_quota_usage']}
            else:
                history.append(statement); result = {'state': 'added', 'reasons': []}
                if grant: self._grant_scopes[grant] = grant_scope
            self._events.append({'operation': 'add', 'payload': statement.to_mapping(), 'received_ns': statement.received_ns,
                                 'document_sha256': statement.document_sha256, 'result': deepcopy(result)})
            return result

    @staticmethod
    def grant_key(statement):
        return ((statement.venue, statement.account_scope, statement.entitlement_id)
                if statement and statement.entitlement_id else None)

    def assess(self, statement_id, request, asof_ns, entry_notional, exit_notional, *, reserve=False, reservation_id=None):
        with self._lock:
            clock(asof_ns)
            request_schema(request)
            if not isinstance(statement_id, str) or not statement_id: raise ValueError('statement identifier required')
            entry, exit = amount(entry_notional), amount(exit_notional)
            if type(reserve) is not bool or (reserve and (not isinstance(reservation_id, str) or not reservation_id)):
                raise ValueError('explicit reserve flag and stable reservation id required')
            known = [s for s in self._statements.get(statement_id, []) if s.received_ns <= asof_ns]
            statement = known[-1] if known else None
            signature = (statement_id, json.dumps(request, sort_keys=True), str(entry), str(exit))
            prior = self._reservations.get(reservation_id) if reserve else None
            grant = self.grant_key(statement)
            if asof_ns < self._last_asof: result = _result(statement, ['assessment_clock_regressed'], 'blocked')
            elif prior:
                result = ({**deepcopy(prior[1]), 'reservation_state': 'duplicate', 'reserved_notional_delta': '0',
                           'quota_reserved_notional_delta': '0', 'assessment_replayed': True}
                          if prior[0] == signature else _result(statement, ['conflicting_reservation_id'], 'blocked'))
            else:
                known_usage = [s.quota_used_notional for hh in self._statements.values() for s in hh
                               if self.grant_key(s) == grant and grant is not None and s.received_ns <= asof_ns
                               and s.quota_used_notional is not None]
                used = (max(known_usage, default=statement.quota_used_notional or Decimal(0))
                        + self._reserved.get(grant, Decimal(0))) if statement else None
                result = assess_fee(statement, request, asof_ns, entry, exit, used_notional=used)
                if reserve and result['state'] == 'conditional':
                    if grant: self._reserved[grant] = self._reserved.get(grant, Decimal(0)) + entry + exit
                    result.update(reservation_state='reserved', reserved_notional_delta=str(entry+exit),
                                  quota_reserved_notional_delta=str(entry+exit) if grant else '0')
                    self._reservations[reservation_id] = (signature, deepcopy(result))
            self._last_asof = max(self._last_asof, asof_ns)
            self._events.append({'operation': 'assess', 'statement_id': statement_id, 'request': deepcopy(request),
                                 'asof_ns': asof_ns, 'entry_notional': str(entry), 'exit_notional': str(exit),
                                 'reserve': reserve, 'reservation_id': reservation_id, 'result': deepcopy(result)})
            return result

    @classmethod
    def replay(cls, events):
        book = cls()
        for event in events:
            if event.get('operation') == 'add':
                s = FeeStatement.from_mapping(event['payload'], received_ns=event['received_ns'])
                digest = event['document_sha256']
                if not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest): raise ValueError('invalid document digest')
                object.__setattr__(s, 'document_sha256', digest); book.add(s)
            elif event.get('operation') == 'assess':
                book.assess(event['statement_id'], event['request'], event['asof_ns'], event['entry_notional'], event['exit_notional'],
                            reserve=event['reserve'], reservation_id=event['reservation_id'])
            else: raise ValueError('unknown fee evidence operation')
            if book._events[-1] != event: raise ValueError('fee evidence replay mismatch')
        return book
