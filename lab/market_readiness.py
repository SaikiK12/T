"""Pure source/session readiness for a simulated account, never a trading gate.

Publication, first receipt, session permission and funding-event value binding
are separate facts. Missing evidence stays unknown. This module has no network,
order, credential, clock-refresh, proof-verification or data-repair capability.
"""
from dataclasses import dataclass
from lab.executable_quotes import positive
from lab.funding_values import (FundingContract, FundingEvent, ValuePacket,
                                assess_funding, value_flags)
from lab.stream_quotes import FrameClock, NS, StreamBook, freshness


def _ns(value):
    if type(value) is not int or value < 0:
        raise ValueError('nonnegative integer nanosecond time required')
    return value


def _text(value):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError('nonempty exact text identity required')
    return value


def _state(blocked=(), unknown=()):
    return {'state': 'blocked' if blocked else 'unknown' if unknown else 'pass',
            'reasons': list(dict.fromkeys((*blocked, *unknown)))}


def _known(clock, asof, anchor):
    _ns(asof)
    if clock.mono_ns > asof:
        return ['first_seen_after_decision']
    if abs((clock.utc_ns-anchor.utc_ns)-(clock.mono_ns-anchor.mono_ns)) > 50_000_000:
        return ['local_clock_step_over_50ms']
    return []


@dataclass(frozen=True)
class InstrumentSpec:
    venue: str
    symbol: str
    instrument_id: str
    base_asset: str | None
    quote_asset: str | None
    settlement_asset: str | None
    contract_model: str | None
    asset_class: str | None
    clock: FrameClock
    source_identity: str
    active: bool | None = None
    api_allowed: bool | None = None
    reduce_only: bool | None = None
    frozen: bool | None = None

    def __post_init__(self):
        if self.venue not in ('mexc', 'lighter') or not self.symbol or not self.instrument_id or not self.source_identity:
            raise ValueError('exact instrument/venue/source identity required')
        for name in ('symbol', 'instrument_id', 'source_identity'):
            _text(getattr(self, name))
        for name in ('base_asset', 'quote_asset', 'settlement_asset'):
            if getattr(self, name) is not None:_text(getattr(self, name))
        if not isinstance(self.clock, FrameClock):
            raise ValueError('first-seen UTC/monotonic clock required')
        for name in ('active', 'api_allowed', 'reduce_only', 'frozen'):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError('explicit boolean or unknown status required')
        if self.contract_model not in (None, 'linear_base', 'inverse_contracts'):
            raise ValueError('unsupported contract model')
        if self.asset_class not in (None, 'crypto', 'metal', 'equity', 'index', 'fx', 'other'):
            raise ValueError('explicit supported asset class or unknown required')


@dataclass(frozen=True)
class SessionWindow:
    venue: str
    symbol: str
    state: str
    clock: FrameClock
    source_identity: str
    valid_from_ns: int
    valid_until_ns: int
    raw_trading_hours: str | None = None

    def __post_init__(self):
        if self.venue not in ('mexc', 'lighter') or not self.symbol or not self.source_identity:
            raise ValueError('session instrument/source identity required')
        _text(self.symbol); _text(self.source_identity)
        if self.raw_trading_hours is not None and not isinstance(self.raw_trading_hours, str):
            raise ValueError('raw trading hours must remain text or unknown')
        if self.state not in ('open', 'closed', 'unknown') or not isinstance(self.clock, FrameClock):
            raise ValueError('explicit session state and first-seen clock required')
        _ns(self.valid_from_ns); _ns(self.valid_until_ns)
        if self.valid_from_ns >= self.valid_until_ns:
            raise ValueError('nonempty session-evidence validity interval required')


def instrument_from_metadata(venue, symbol, metadata, clock, source_identity,
                             *, base_asset=None, asset_class=None):
    """Field adapter only; never infers crypto class, sessions or owner access.

    Lighter's USD_quote labels the model quote unit, not an attested settlement
    asset. Canonical base/class can be supplied from a separately bound registry.
    """
    if venue == 'mexc':
        active = metadata.get('state') == 0 if type(metadata.get('state')) is int else None
        return InstrumentSpec(venue, symbol, str(metadata.get('symbol', 'missing')),
            base_asset, metadata.get('quoteCoin') or (metadata.get('settleCoin') if metadata.get('type') == 1 else None),
            metadata.get('settleCoin'), 'linear_base' if type(metadata.get('type')) is int and metadata['type'] == 1 else None,
            asset_class, clock, source_identity, active=active,
            api_allowed=metadata.get('apiAllowed') if type(metadata.get('apiAllowed')) is bool else None)
    if venue == 'lighter':
        config = metadata.get('market_config') or {}
        status = metadata.get('status')
        return InstrumentSpec(venue, symbol, str(metadata.get('symbol', 'missing')),
            base_asset, 'USD_quote', None, 'linear_base' if metadata.get('market_type') == 'perp' else None,
            asset_class, clock, source_identity,
            active=status == 'active' if isinstance(status, str) else None,
            frozen=metadata.get('is_frozen') if type(metadata.get('is_frozen')) is bool else None,
            reduce_only=config.get('force_reduce_only') if type(config.get('force_reduce_only')) is bool else None)
    raise ValueError('unsupported venue')


def assess_session(spec, session, asof, anchor):
    if session is None:
        return _state(unknown=('session_contract_missing_or_unparsed',))
    if not isinstance(session, SessionWindow):
        raise ValueError('typed session evidence or unknown required')
    blocked = _known(session.clock, asof, anchor)
    if (session.venue, session.symbol) != (spec.venue, spec.symbol):
        blocked.append('session_instrument_mismatch')
    now = anchor.utc_ns+asof-anchor.mono_ns
    unknown = []
    current = session.valid_from_ns <= now < session.valid_until_ns
    if not current:
        unknown.append('session_evidence_outside_validity')
    if current and session.state == 'closed':
        blocked.append('session_closed')
    elif session.state == 'unknown':
        unknown.append('session_state_unknown')
    return {**_state(blocked, unknown), 'source_identity': session.source_identity,
            'reported_state': session.state, 'raw_trading_hours': session.raw_trading_hours,
            'account_permission_verified': False}


def assess_instrument(spec, session, asof, anchor):
    if spec is None:
        return {**_state(unknown=('instrument_contract_missing',)), 'session': _state(unknown=('session_contract_missing',))}
    if not isinstance(spec, InstrumentSpec):
        raise ValueError('typed instrument contract or unknown required')
    blocked = _known(spec.clock, asof, anchor)
    expected = spec.symbol+'_USDT' if spec.venue == 'mexc' else spec.symbol
    if spec.instrument_id != expected:
        blocked.append('instrument_id_mismatch')
    if spec.active is False:
        blocked.append('instrument_inactive')
    if spec.api_allowed is False:
        blocked.append('instrument_API_disabled')
    if spec.reduce_only is True:
        blocked.append('instrument_reduce_only')
    if spec.frozen is True:
        blocked.append('instrument_frozen')
    if spec.contract_model == 'inverse_contracts' and spec.settlement_asset is not None and spec.base_asset is not None and spec.settlement_asset != spec.base_asset:
        blocked.append('inverse_settlement_base_asset_mismatch')
    unknown = []
    for name in ('base_asset', 'quote_asset', 'settlement_asset', 'contract_model', 'asset_class'):
        if getattr(spec, name) is None:
            unknown.append(name+'_unknown')
    if spec.contract_model == 'linear_base' and spec.quote_asset is not None and spec.settlement_asset is not None and spec.quote_asset != spec.settlement_asset:
        unknown.append('quote_settlement_conversion_unverified')
    if spec.active is None:
        unknown.append('instrument_active_status_unknown')
    if spec.venue == 'mexc' and spec.api_allowed is None:
        unknown.append('instrument_API_status_unknown')
    if spec.venue == 'lighter':
        if spec.frozen is None: unknown.append('instrument_freeze_status_unknown')
        if spec.reduce_only is None: unknown.append('instrument_reduce_only_status_unknown')
    session_state = assess_session(spec, session, asof, anchor)
    return {**_state(blocked, unknown), 'venue': spec.venue, 'symbol': spec.symbol,
            'instrument_id': spec.instrument_id, 'source_identity': spec.source_identity,
            'base_asset': spec.base_asset, 'quote_asset': spec.quote_asset,
            'settlement_asset': spec.settlement_asset, 'contract_model': spec.contract_model,
            'asset_class': spec.asset_class, 'session': session_state,
            'account_permission_verified': False, 'execution_ready': False}


def assess_pair(books, specs, sessions, values, asof, anchor):
    """Separate input readiness from execution permission and settlement cash."""
    if any(len(x) != 2 for x in (books, specs, sessions, values)):
        raise ValueError('two ordered MEXC/Lighter inputs required')
    _ns(asof)
    if not isinstance(anchor, FrameClock) or any(b is not None and not isinstance(b, (str, StreamBook)) for b in books):
        raise ValueError('typed source clocks/books or explicit fault required')
    if any(p is not None and not isinstance(p, ValuePacket) for p in values):
        raise ValueError('typed values or unknown required')
    observations = []
    blocked, unknown = [], []
    for venue, kind, book, spec, session, packet in zip(('mexc', 'lighter'), ('fair', 'index'), books, specs, sessions, values):
        inst = assess_instrument(spec, session, asof, anchor)
        if spec is not None and spec.venue != venue:
            inst = {**inst, **_state(blocked=('ordered_instrument_venue_mismatch',))}
        bf = freshness(book, asof, anchor)
        missing_book = not isinstance(book, StreamBook)
        if not missing_book and (book.venue != venue or spec is not None and (book.symbol != spec.symbol or spec.venue != venue)):
            bf.append('book_instrument_mismatch')
        vf = value_flags(packet, asof, anchor)
        if packet is not None and (packet.venue != venue or packet.kind != kind or
           spec is not None and packet.symbol != spec.symbol or not missing_book and packet.symbol != book.symbol):
            vf.append('value_instrument_or_kind_mismatch')
        books_state = _state(unknown=bf) if book is None else _state(blocked=bf)
        values_state = _state(unknown=vf) if packet is None else _state(blocked=vf)
        components = {'instrument': inst, 'session': inst['session'], 'book': books_state, 'publication': values_state}
        for name, component in components.items():
            (blocked if component['state'] == 'blocked' else unknown if component['state'] == 'unknown' else []).extend(
                venue+':'+name+':'+f for f in component['reasons'])
        observations.append({'venue': venue, 'symbol': getattr(spec, 'symbol', None), 'components': components,
            'value_clock_role': getattr(packet, 'clock_role', None),
            'effective_value_state': 'unknown', 'settlement_value_state': 'unknown'})
    if all(isinstance(s, InstrumentSpec) for s in specs):
        if specs[0].symbol != specs[1].symbol:
            blocked.append('paired_contract_symbol_mismatch')
        if specs[0].base_asset is not None and specs[1].base_asset is not None and specs[0].base_asset != specs[1].base_asset:
            blocked.append('paired_base_asset_mismatch')
        if specs[0].asset_class is not None and specs[1].asset_class is not None and specs[0].asset_class != specs[1].asset_class:
            blocked.append('paired_asset_class_mismatch')
    for label, items in (('book', books), ('value', values)):
        expected_type = StreamBook if label == 'book' else ValuePacket
        if all(isinstance(x, expected_type) for x in items):
            if items[0].symbol != items[1].symbol: blocked.append(label+':paired_symbol_mismatch')
            if abs(items[0].clock.mono_ns-items[1].clock.mono_ns) > NS: blocked.append(label+':receive_skew_over_1s')
            if abs(items[0].source_time_ns-items[1].source_time_ns) > NS: blocked.append(label+':source_skew_over_1s')
    return {**_state(blocked, unknown), 'observations': observations,
            'input_contract_pass': not blocked and not unknown, 'execution_ready': False,
            'account_permission_verified': False, 'settlement_cash_verified': False,
            'unresolved': ['actual_order_fill_and_latency', 'owner_account_permission',
                           'source_effective_value_contract', 'funding_event_value_binding']}


def event_value_from_mapping(data):
    """Strict supplied event-value declaration, not a proof/source adapter.

    The caller must supply the event binding and each distinct clock. This does
    not establish that a Lighter pre-update index/proof or account credit exists.
    """
    names = {'venue', 'symbol', 'kind', 'price', 'clock', 'source_time_ns', 'clock_role',
             'source_identity', 'effective_value_ns', 'settlement_event_id'}
    if set(data) != names or data['clock_role'] != 'settlement_value':
        raise ValueError('complete explicit settlement-value declaration required')
    clock = data['clock']
    if not isinstance(clock, dict) or set(clock) != {'utc_ns', 'mono_ns'}:
        raise ValueError('separate first-seen UTC/monotonic clocks required')
    return ValuePacket(**{**data, 'price': positive(data['price']), 'clock': FrameClock(**clock)})


def assess_settlement(contract, event, spans, packet, asof, anchor, *, index_basis=None):
    """Check supplied funding inputs using the frozen accounting kernel.

    ``index_basis='pre_update_event_index'`` is an explicit caller declaration,
    not cryptographic verification. No current/publication price is promoted.
    """
    if not isinstance(contract, FundingContract) or not isinstance(event, FundingEvent):
        return {**_state(unknown=('funding_contract_or_event_missing',)), 'cash_delta': None,
                'settlement_cash_verified': False, 'source_bridge_verified': False}
    if packet is not None and not isinstance(packet, ValuePacket):
        return {**_state(unknown=('event_value_not_a_typed_contract',)), 'cash_delta': None,
                'settlement_cash_verified': False, 'source_bridge_verified': False, 'execution_ready': False}
    model = assess_funding(contract, event, [] if spans is None else spans, packet, asof, anchor)
    reasons = list(model['flags'])
    if contract.venue == 'lighter' and model['status'] != 'inactive' and index_basis != 'pre_update_event_index':
        reasons.append('lighter_preupdate_event_index_basis_unverified')
    state = 'pass' if not reasons else 'unknown'
    return {'state': state, 'reasons': list(dict.fromkeys(reasons)),
            'rate_stage': event.stage, 'rate_unit': event.rate_unit,
            'event_id': event.event_id, 'funding_ns': event.funding_ns,
            'model_status': model['status'], 'cash_delta': str(model['cash_delta']) if not reasons and model['cash_delta'] is not None else None,
            'asset': contract.settlement_asset, 'evidence_scope': 'supplied model contracts only',
            'source_bridge_verified': False, 'settlement_cash_verified': False,
            'actual_lighter_index_proof_bridge': 'not acquired or verified by this module',
            'execution_ready': False}


def compare_funding_estimate(announcement, settlement, asof, anchor, *,
                             announcement_source=None, settlement_source=None,
                             previous_settlement=None):
    """Forecast error only for an on-time estimate and original matching event.

    No nearest-hour matching, correction substitution, cash or alpha inference.
    Optional source identities are caller provenance, never provider proof.
    """
    _ns(asof)
    for source in (announcement_source, settlement_source):
        if source is not None:_text(source)
    result = {'estimated_fraction': None, 'settled_fraction': None, 'error_fraction': None,
              'announcement_source': announcement_source, 'settlement_source': settlement_source,
              'cash_delta': None, 'settlement_cash_verified': False, 'execution_ready': False}
    if not isinstance(announcement, FundingEvent) or not isinstance(settlement, FundingEvent):
        return {**result, **_state(unknown=('announcement_or_settlement_missing',))}
    blocked, unknown = [], []
    for name, event in (('announcement', announcement), ('settlement', settlement)):
        blocked.extend(name+':'+f for f in _known(event.clock, asof, anchor))
    key = lambda e:(e.venue, e.symbol, e.event_id, e.funding_ns)
    if any(not isinstance(e.event_id, str) or not e.event_id.strip() for e in (announcement, settlement)) or key(announcement) != key(settlement):
        blocked.append('funding_economic_event_identity_mismatch')
    if announcement.stage != 'estimated':unknown.append('announcement_stage_not_original_estimate')
    if settlement.stage != 'settled':unknown.append('settlement_stage_not_original_settled')
    if announcement.clock.utc_ns > announcement.funding_ns:
        blocked.append('announcement_first_seen_after_funding')
    if previous_settlement is not None:
        if not isinstance(previous_settlement, FundingEvent) or key(previous_settlement) != key(settlement):
            blocked.append('previous_settlement_identity_mismatch')
        else:
            try:
                if previous_settlement.fraction() != settlement.fraction():
                    unknown.append('settlement_rate_revision_unresolved')
            except ValueError:unknown.append('previous_settlement_rate_unit_unverified')
    try:estimate, actual = announcement.fraction(), settlement.fraction()
    except ValueError:
        estimate = actual = None;unknown.append('rate_unit_unverified')
    result.update(_state(blocked, unknown))
    result['event_id'] = settlement.event_id
    result['funding_ns'] = settlement.funding_ns
    if not blocked and not unknown:
        result.update(estimated_fraction=str(estimate), settled_fraction=str(actual),
                      error_fraction=str(actual-estimate))
    return result
