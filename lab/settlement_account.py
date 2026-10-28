"""Fixed-inventory settlement-window adapter over the native paper ledger.

Inputs describe conditional model fills, never orders or authenticated fills.
Exit depth must cover the position actually held. Rates need event-bound values
and observed exposure; a rate sum is not a cash flow. Venue/asset capital stays
segregated, including when an explicit FX scenario reports a combined return.
"""
from dataclasses import dataclass
from decimal import Decimal as D
import hashlib

from lab.paper_account import PaperAccount, PaperEvent, number, text, _precision
from lab.stream_quotes import FrameClock, StreamBook
from lab.funding_values import FundingContract, FundingEvent, clock_known
from lab.market_readiness import assess_settlement
from lab.execution_envelope import liquidation_quote


@dataclass(frozen=True)
class EntryLeg:
    venue: str
    asset: str
    symbol: str
    quantity: D
    price: D
    mid: D
    fee_bp: D
    clock: FrameClock
    source_identity: str

    def __post_init__(self):
        for field in ('venue', 'asset', 'symbol', 'source_identity'):
            text(getattr(self, field))
        if self.venue not in ('mexc', 'lighter') or not isinstance(self.clock, FrameClock):
            raise ValueError('supported leg and explicit receive clock required')
        for field in ('quantity', 'price', 'mid', 'fee_bp'):
            object.__setattr__(self, field, number(getattr(self, field),
                positive=field in ('price', 'mid'), nonnegative=field == 'fee_bp'))
        if self.quantity == 0 or self.fee_bp > 10000:
            raise ValueError('nonzero fixed base quantity and fee <=10000bp required')
        if self.quantity * (self.price - self.mid) < 0:
            raise ValueError('entry price must preserve the supplied crossing side')


def _stressed(price, mid, multiple):
    return number(mid + multiple * (price - mid), positive=True)


def _exact_shown_notional(book, quantity):
    # The inherited sweep returns a float for descriptive quotes. Its strict
    # depth/freshness decision is reused; money uses the same supplied levels
    # as decimal strings so that a float cannot become the ledger's cash basis.
    left, total = abs(quantity), D(0)
    for level in (book.bids if quantity > 0 else book.asks):
        take = min(left, number(level.size, positive=True))
        total += take * number(level.price, positive=True)
        left -= take
        if left == 0:
            return total
    raise ValueError('validated shown depth did not cover fixed inventory')


@_precision
def nominal_exit_inventory(signed_entry_quantity, exit_price, exit_quote_notional):
    """Diagnostic only: a new fixed-dollar opposite order may not flatten q."""
    q = number(signed_entry_quantity)
    if q == 0:
        raise ValueError('original nonzero inventory required')
    p = number(exit_price, positive=True)
    usd = number(exit_quote_notional, positive=True)
    close_q = -(1 if q > 0 else -1) * usd / p
    residual = q + close_q
    return {'entry_quantity': str(q), 'nominal_close_quantity': str(close_q),
            'residual_quantity': str(residual), 'flat': residual == 0,
            'position_reversed': q * residual < 0, 'actual_fill_verified': False}


class SettlementAccount:
    """Stateless execution adapter; the native ledger owns every financial state."""
    def __init__(self, account, cost_multiple=1):
        if not isinstance(account, PaperAccount):
            raise ValueError('native PaperAccount required')
        if type(cost_multiple) is not int or cost_multiple not in (1, 2, 3):
            raise ValueError('fixed 1x/2x/3x cost tier required')
        self.account, self.multiple = account, cost_multiple

    @_precision
    def enter_pair(self, hop, legs, asof):
        text(hop)
        if len(legs) != 2 or any(not isinstance(x, EntryLeg) for x in legs):
            raise ValueError('two typed entry legs required')
        if {x.venue for x in legs} != {'mexc', 'lighter'} or legs[0].symbol != legs[1].symbol:
            raise ValueError('one matching instrument on each venue required')
        if legs[0].quantity * legs[1].quantity >= 0:
            raise ValueError('opposite fixed inventory signs required')
        snapshot = self.account.snapshot(asof)
        balances = {(r['venue'], r['asset']): r for r in snapshot['accounts']}
        events, reasons = [], []
        for leg in legs:
            price = _stressed(leg.price, leg.mid, self.multiple)
            fee = abs(leg.quantity) * price * leg.fee_bp * self.multiple / 10000
            event = PaperEvent(hop + ':' + leg.venue + ':entry', 'fill', leg.venue,
                leg.asset, leg.symbol, leg.clock.utc_ns, leg.clock, leg.source_identity,
                quantity=leg.quantity, price=price, fee=fee, reference_mid=leg.mid)
            events.append(event)
            key = leg.venue, leg.asset
            row = balances.get(key)
            if not clock_known(leg.clock, asof, self.account.anchor):
                reasons.append(leg.venue + ':entry_not_known_at_asof')
            if leg.clock.utc_ns < self.account.anchor.utc_ns:
                reasons.append(leg.venue + ':entry_before_flat_baseline')
            if key not in balances:
                reasons.append(leg.venue + ':unfunded_asset')
            elif event.event_id not in self.account.seen:
                free = row['available_capital']
                if free is None or abs(leg.quantity) * price + fee > number(free):
                    reasons.append(leg.venue + ':separate_capital_insufficient_or_unknown')
                if self.account.positions.get((leg.venue, leg.asset, leg.symbol), (D(0),))[0] != 0:
                    reasons.append(leg.venue + ':existing_inventory_requires_reconciliation')
        if reasons:
            return {'state': 'blocked', 'reasons': reasons, 'events': [],
                    'actual_order_allowed': False}
        # Validation above is for both legs before either model event is posted.
        posted = [self.account.post(e, asof) for e in events]
        reconciled = all(e['status'] in ('applied', 'duplicate') for e in posted)
        return {'state': 'conditional_model' if reconciled else 'unknown', 'events': posted,
                'reasons': [] if reconciled else ['financial_event_reconciliation_required'],
                'actual_order_allowed': False}

    @_precision
    def close_fixed(self, venue, asset, symbol, book, fee_bp, asof):
        for value in (venue, asset, symbol):
            text(value)
        if (venue, asset) not in self.account.initial:
            raise ValueError('explicit funded venue/asset required')
        self.account.snapshot(asof)
        key = venue, asset, symbol
        q = self.account.positions.get(key, (D(0),))[0]
        if q == 0:
            return {'state': 'already_flat', 'quantity': '0', 'actual_fill_verified': False}
        if book is not None and (not isinstance(book, StreamBook) or (book.venue, book.symbol) != (venue, symbol)):
            return {'state': 'unknown', 'reasons': ['exit_book_identity_mismatch']}
        if fee_bp is None:
            return {'state': 'unknown', 'reasons': ['exit_fee_unknown']}
        quote = liquidation_quote(book, q, fee_bp, asof, self.account.anchor)
        if quote['state'] != 'conditional':
            return {**quote, 'inventory_retained': str(q)}
        exact_notional = _exact_shown_notional(book, q)
        price = _stressed(exact_notional / abs(q),
                          number(book.mid, positive=True), self.multiple)
        fee = abs(q) * price * number(fee_bp, nonnegative=True) * self.multiple / 10000
        last = self.account.last_fill.get(key)
        identity = hashlib.sha256(f'{venue}:{asset}:{symbol}:{last}:{q}'.encode()).hexdigest()[:24]
        event = PaperEvent('close:' + identity, 'fill', venue, asset, symbol,
            book.clock.utc_ns, book.clock, 'conditional_fixed_quantity_book:' + str(book.version),
            quantity=-q, price=price, fee=fee, reference_mid=number(book.mid))
        posted = self.account.post(event, asof)
        return {'state': 'conditional_model' if posted['status'] == 'applied' else 'unknown',
                'quantity': str(-q), 'price': str(price),
                'fee': str(fee), 'quote': quote, 'exact_shown_quote_notional': str(exact_notional), 'event': posted,
                'actual_fill_verified': False}

    @_precision
    def funding(self, contract, event, packet, observed_clock, *, index_basis=None):
        if not isinstance(contract, FundingContract) or not isinstance(event, FundingEvent):
            raise ValueError('typed source contract and event required')
        if contract.model != 'linear_base' or (contract.venue, contract.symbol) != (event.venue, event.symbol):
            raise ValueError('matching linear contract/event required')
        if not isinstance(observed_clock, FrameClock) or not clock_known(observed_clock, observed_clock.mono_ns, self.account.anchor):
            raise ValueError('causal observed coverage clock required')
        key = contract.venue, contract.settlement_asset
        if key not in self.account.initial:
            raise ValueError('separate funding asset must match an existing account')
        spans = self.account.position_spans(*key, contract.symbol, observed_clock)
        result = assess_settlement(contract, event, spans, packet,
            observed_clock.mono_ns, self.account.anchor, index_basis=index_basis)
        self.account.record_evidence('funding_assessment', result)
        if event.funding_ns > observed_clock.utc_ns:
            return {**result, 'posting': 'future_economic_event_not_posted'}
        # Canonical economic key deduplicates provider aliases, not just delivery ids.
        identity = f'settlement:{contract.venue}:{contract.settlement_asset}:{contract.symbol}:{event.funding_ns}'
        amount = result['cash_delta']
        known = identity in self.account.seen
        pending = identity in self.account.pending
        resolution = amount is not None and (pending or identity + ':resolution' in self.account.seen)
        if known and not pending and amount is None:
            return {**result, 'posting': 'existing_known_event_not_replaced_by_missing_evidence'}
        if known and pending and amount is None:
            return {**result, 'posting': 'still_pending'}
        pe = PaperEvent(identity + (':resolution' if resolution else ''),
            'funding_resolution' if resolution else 'funding', contract.venue,
            contract.settlement_asset, contract.symbol, event.funding_ns,
            observed_clock, 'conditional_event_bound_funding:' + contract.source_version,
            amount=amount, resolves=identity if resolution else None)
        posted = self.account.post(pe, observed_clock.mono_ns)
        return {**result, 'posting': posted}

    @_precision
    def report(self, asof, *, fx=None):
        snapshot = self.account.snapshot(asof)
        total_initial = D(0)
        total_nav = D(0)
        missing = []
        fx_missing = False
        for row in snapshot['accounts']:
            if fx is None or row['asset'] not in fx:
                missing.append(row['asset'] + ':fx_scenario_missing')
                fx_missing = True
                continue
            rate = number(fx[row['asset']], positive=True)
            total_initial += number(row['initial_cash']) * rate
            if row['nav'] is None:
                missing.append(row['venue'] + ':account_nav_unknown')
            else:
                total_nav += number(row['nav']) * rate
        combined = None if missing or total_initial <= 0 else total_nav - total_initial
        return {'native': snapshot, 'combined_scenario_pnl': None if combined is None else str(combined),
                'combined_initial_capital': str(total_initial) if not fx_missing else None,
                'whole_capital_scenario_return': None if combined is None else str(combined / total_initial),
                'fx_scenario': None if fx is None else {k: str(v) for k, v in fx.items()},
                'reasons': missing, 'actual_expected_net': None, 'actual_execution_ready': False,
                'prospective_strategy_days': 0, 'cost_multiple': self.multiple}
