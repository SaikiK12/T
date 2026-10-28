"""Join supplied forecasts, executable-book costs and one paper capital budget.

This is an offline, single-batch allocation diagnostic. It reserves no durable
capital, infers no fills and cannot authorize trading. Callers must not submit
its plans or run concurrent batches as an execution system. Forecast components
are midpoint-to-midpoint price PnL and funding in ONE settlement asset; spread
and fees are deducted once here. Unmeasured forecast error remains unknown.
"""
from dataclasses import dataclass
from decimal import Decimal

from lab.paper_account import number, text, _precision
from lab.paper_controls import entry_threshold, PaperRisk
from lab.stream_quotes import FrameClock, StreamBook, NS, freshness
from lab.funding_values import clock_known
from lab.execution_envelope import liquidation_quote


@dataclass(frozen=True)
class Outcome:
    probability: Decimal
    price_pnl: Decimal | None
    funding_pnl: Decimal | None

    def __post_init__(self):
        p = number(self.probability, nonnegative=True)
        if p > 1: raise ValueError('probability outside [0,1]')
        object.__setattr__(self, 'probability', p)
        for field in ('price_pnl', 'funding_pnl'):
            if getattr(self, field) is not None:
                object.__setattr__(self, field, number(getattr(self, field)))


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    model_id: str
    venue: str
    asset: str
    symbol: str
    quantity: Decimal                  # signed BASE, not quote notional
    clock: FrameClock                  # original forecast first-seen clock
    horizon_utc_ns: int
    outcomes: tuple[Outcome, ...]
    error_quote: Decimal | None         # externally measured error allowance
    calibration_id: str | None
    exit_reserve_quote: Decimal | None
    payoff_basis: str = 'midpoint_price_plus_funding_excludes_costs'

    def __post_init__(self):
        for field in ('opportunity_id', 'model_id', 'venue', 'asset', 'symbol'):
            text(getattr(self, field))
        q = number(self.quantity)
        if not q: raise ValueError('nonzero signed base quantity required')
        object.__setattr__(self, 'quantity', q)
        if not isinstance(self.clock, FrameClock) or type(self.horizon_utc_ns) is not int or self.horizon_utc_ns <= self.clock.utc_ns:
            raise ValueError('forecast clock and future terminal horizon required')
        if not isinstance(self.outcomes, tuple) or not 1 <= len(self.outcomes) <= 32 or any(not isinstance(o, Outcome) for o in self.outcomes):
            raise ValueError('finite typed outcome distribution required')
        if abs(sum(o.probability for o in self.outcomes)-1) > Decimal('1e-18'):
            raise ValueError('complete probability simplex required')
        for field in ('error_quote', 'exit_reserve_quote'):
            if getattr(self, field) is not None:
                object.__setattr__(self, field, number(getattr(self, field), nonnegative=True))
        if self.calibration_id is not None: text(self.calibration_id)


@_precision
def forecast_value(opportunity):
    """A forecast never changes cash; unknown positive-mass outcomes stay unknown."""
    if not isinstance(opportunity, Opportunity): raise ValueError('typed opportunity required')
    active = [o for o in opportunity.outcomes if o.probability > 0]
    price = sum((o.probability*o.price_pnl for o in active), Decimal(0)) if all(o.price_pnl is not None for o in active) else None
    funding = sum((o.probability*o.funding_pnl for o in active), Decimal(0)) if all(o.funding_pnl is not None for o in active) else None
    return {'expected_price_quote': None if price is None else str(price),
            'expected_funding_quote': None if funding is None else str(funding),
            'expected_gross_quote': None if price is None or funding is None else str(price+funding),
            'highest_outcome_probability': str(max(o.probability for o in active)),
            'asset': opportunity.asset, 'realized_pnl': None}


@_precision
def quote_cost(opportunity, book, fee_bp, asof, anchor):
    """Same-book round-trip sweep is a baseline, NOT an observed future exit.

    Reuse the existing close-side depth/clock/fee kernel for both directions.
    Its buy cash sign is an order flow, not futures principal spent or received.
    """
    result = {'state': 'unknown', 'reasons': [], 'crossing_quote': None,
              'fee_quote': None, 'round_trip_quote': None, 'entry_notional_quote': None,
              'risk_gross_notional_quote': None,
              'actual_fill_verified': False, 'future_exit_observed': False,
              'fee_entitlement_verified': False}
    if not isinstance(book, StreamBook): return {**result, 'reasons': ['book_missing']}
    if (book.venue, book.symbol) != (opportunity.venue, opportunity.symbol):
        return {**result, 'reasons': ['book_instrument_mismatch']}
    flags = freshness(book, asof, anchor)
    if flags: return {**result, 'reasons': flags}
    fee = None if fee_bp is None else number(fee_bp, nonnegative=True)
    if fee is None: return {**result, 'reasons': ['fee_unknown']}
    if fee > 10000: raise ValueError('fee outside supported range')
    buy = liquidation_quote(book, -abs(opportunity.quantity), fee, asof, anchor)
    sell = liquidation_quote(book, abs(opportunity.quantity), fee, asof, anchor)
    if buy['state'] != 'conditional' or sell['state'] != 'conditional':
        return {**result, 'reasons': sorted(set(buy['reasons']+sell['reasons']))}
    purchase, sale = number(buy['gross_close_quote']), number(sell['gross_close_quote'])
    crossing = purchase-sale
    if crossing < 0: raise ValueError('crossed round-trip cost')
    fees = number(buy['fee_quote'])+number(sell['fee_quote'])
    return {**result, 'state': 'conditional', 'crossing_quote': str(crossing),
            'fee_quote': str(fees), 'round_trip_quote': str(crossing+fees),
            'entry_notional_quote': str(purchase if opportunity.quantity > 0 else sale),
            'risk_gross_notional_quote': str(max(purchase, sale)),
            'book_source_identity': book.source_role,
            'book_first_seen_mono_ns': book.clock.mono_ns,
            'book_source_time_ns': book.source_time_ns}


@_precision
def assess_batch(account, opportunities, books, fees_bp, *, asof, anchor,
                 risk, risk_inputs, market_reports, marks=()):
    """One ordered plan against ONE account; 3x admission is shared by all tiers.

    No ranking is learned here. Caller order is explicit. Each plan consumes its
    own venue/asset's 1x entry notional plus the full 3x cost/reserve budget.
    Unrealized gains cannot fund entries; adverse marked equity can reduce it.
    Missing market/lot/fee/calibration evidence blocks, even at high confidence.
    Receipts, quotes and forecasts never become fills or earned cash.
    """
    if type(asof) is not int or not isinstance(anchor, FrameClock) or anchor != account.anchor:
        raise ValueError('common account clock required')
    if not isinstance(risk, PaperRisk) or risk.anchor != anchor or risk.initial != account.initial:
        raise ValueError('same-account persistent risk controls required')
    risk_policy = risk.policy
    if set(risk_inputs) != {'clock', 'complete', 'session_open', 'fee_inputs_known',
                            'contract_version', 'expected_contract_version', 'mode'}:
        raise ValueError('explicit risk observation inputs required')
    opportunities = tuple(opportunities)
    if len(opportunities) > 128 or any(not isinstance(o, Opportunity) for o in opportunities):
        raise ValueError('finite typed batch required')
    ids = [o.opportunity_id for o in opportunities]
    if len(set(ids)) != len(ids): raise ValueError('duplicate opportunity identity')
    if any(set(m) != set(ids) for m in (books, fees_bp, market_reports)):
        raise ValueError('exact per-opportunity evidence scope required')
    before = account.snapshot(asof, marks)
    risk_report = risk.observe(before, asof=asof, **risk_inputs)
    balances = {(a['venue'], a['asset']): a for a in before['accounts']}
    remaining = {}
    for key, a in balances.items():
        amounts = (a['available_capital'], a['nav'], a['cash'])
        remaining[key] = None if any(x is None for x in amounts) else max(Decimal(0), min(
            number(a['available_capital']), number(a['nav'])-number(a['locked_capital'])))
    initial_budget = {k: v for k, v in remaining.items()}
    risk_ok = (isinstance(risk_report, dict) and risk_report.get('model_new_entries_allowed') is True
               and risk_report.get('actual_order_allowed') is False
               and risk_report.get('stops') == []
               and {(a['venue'], a['asset']) for a in risk_report.get('accounts', [])} == set(balances))
    projected = {}
    if risk_ok:
        for a in risk_report['accounts']:
            key = a['venue'], a['asset']; current = balances[key]
            if (a.get('gross_notional_complete') is not True or a.get('gross_notional') is None
                or a.get('net_pnl') is None or current['nav'] is None
                or number(a['initial_cash']) != number(current['initial_cash'])
                or number(a['net_pnl']) != number(current['nav'])-number(current['initial_cash'])-number(current['external_capital_flows'])):
                risk_ok = False; break
            projected[key] = {'gross': number(a['gross_notional'], nonnegative=True),
                'symbols': {s: number(x, nonnegative=True) for s, x in a['symbol_gross'].items()}}
    rows = []
    for o in opportunities:
        reasons = []
        if not risk_ok: reasons.append('account_risk_stop_or_scope_unknown')
        if not clock_known(o.clock, asof, anchor) or not 0 <= asof-o.clock.mono_ns <= NS:
            reasons.append('forecast_not_fresh_at_decision')
        if o.horizon_utc_ns <= anchor.utc_ns+asof-anchor.mono_ns: reasons.append('forecast_horizon_expired')
        if o.payoff_basis != 'midpoint_price_plus_funding_excludes_costs': reasons.append('payoff_cost_convention_unknown')
        market = market_reports[o.opportunity_id]
        now = anchor.utc_ns+asof-anchor.mono_ns
        source_fields = ('source_identity', 'fee_source_identity', 'lot_source_identity',
                         'session_source_identity', 'settlement_source_identity')
        if (not isinstance(market, dict) or market.get('state') != 'pass'
            or market.get('asof_mono_ns') != asof
            or market.get('quantity_base') != str(abs(o.quantity))
            or (market.get('venue'), market.get('asset'), market.get('symbol')) != (o.venue, o.asset, o.symbol)
            or market.get('contract_model') != 'linear_base' or market.get('quote_asset') != o.asset
            or any(not isinstance(market.get(f), str) or not market[f].strip() for f in source_fields)
            or type(market.get('valid_from_utc_ns')) is not int or type(market.get('valid_until_utc_ns')) is not int
            or not market['valid_from_utc_ns'] <= now < market['valid_until_utc_ns']):
            reasons.append('market_session_units_lots_or_fee_evidence_missing')
        else:
            try:
                step = number(market['step_base'], positive=True)
                minimum = number(market['min_base'], positive=True)
                maximum = number(market['max_base'], positive=True)
                if minimum > maximum or abs(o.quantity) % step or not minimum <= abs(o.quantity) <= maximum:
                    reasons.append('quantity_outside_supplied_lot_contract')
            except (KeyError, ValueError, ArithmeticError):
                reasons.append('lot_contract_unknown')
        key = o.venue, o.asset
        if key not in remaining or remaining.get(key) is None: reasons.append('segregated_account_budget_unknown')
        value = forecast_value(o); cost = quote_cost(o, books[o.opportunity_id], fees_bp[o.opportunity_id], asof, anchor)
        if cost['state'] != 'conditional': reasons.extend('cost:'+r for r in cost['reasons'])
        tiers = [entry_threshold(value['expected_gross_quote'], cost['round_trip_quote'], o.error_quote,
            asset=o.asset, cost_multiple=k, error_calibrated=o.calibration_id is not None,
            extra_reserve_quote=o.exit_reserve_quote) for k in (1, 2, 3)]
        if not tiers[2]['model_entry_allowed']: reasons.append('not_positive_with_error_and_3x_costs')
        reserve = None
        if cost['round_trip_quote'] is not None and o.exit_reserve_quote is not None:
            reserve = number(cost['entry_notional_quote'])+3*(number(cost['round_trip_quote'])+o.exit_reserve_quote)
            if key in remaining and remaining[key] is not None and reserve > remaining[key]:
                reasons.append('batch_segregated_capital_exceeded')
            if risk_ok and key in projected:
                size = number(cost['risk_gross_notional_quote']); base = number(balances[key]['initial_cash'])
                if projected[key]['gross']+size > base*risk_policy.max_venue_gross_fraction:
                    reasons.append('planned_venue_gross_limit')
                if projected[key]['symbols'].get(o.symbol, Decimal(0))+size > base*risk_policy.max_symbol_gross_fraction:
                    reasons.append('planned_symbol_concentration_limit')
        allowed = not reasons
        if allowed:
            remaining[key] -= reserve
            projected[key]['gross'] += number(cost['risk_gross_notional_quote'])
            symbols = projected[key]['symbols']
            symbols[o.symbol] = symbols.get(o.symbol, Decimal(0))+number(cost['risk_gross_notional_quote'])
        rows.append({'opportunity_id': o.opportunity_id, 'model_id': o.model_id,
            'venue': o.venue, 'asset': o.asset, 'symbol': o.symbol, 'quantity_base': str(o.quantity),
            'forecast': value, 'calibration_evidence_pointer': o.calibration_id,
            'market_evidence': market,
            'calibration_authenticity_verified': False, 'cost': cost, 'cost_tiers': tiers,
            'planned_capital_quote': str(reserve) if allowed else None,
            'conditional_batch_inclusion': allowed, 'reasons': list(dict.fromkeys(reasons)),
            'actual_order_allowed': False})
    after = account.snapshot(asof, marks)
    if before != after: raise ValueError('account changed during allocation; retry from new snapshot')
    return {'simulation_only': True, 'activation_allowed': False, 'rows': rows,
            'account_before': before, 'account_after': after,
            'budgets': [{'venue': v, 'asset': a,
                'initial_available': None if initial_budget[v, a] is None else str(initial_budget[v, a]),
                'remaining_after_batch_plan': None if remaining[v, a] is None else str(remaining[v, a])}
                for v, a in sorted(balances)],
            'actual_net_return': None, 'prospective_days': 0,
            'risk_assessment': risk_report,
            'durable_reservation_created': False,
            'scope': 'one offline allocation batch; supplied evidence is not authenticated; no fills, durable reservations or cross-batch execution support'}
