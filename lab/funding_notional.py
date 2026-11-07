"""Conditional funding-notional audit for one fixed-base-quantity linear position.

Compare the sum-of-rates convention with settlement-value-weighted cash. Inputs
are supplied declarations, not authenticated payments or executable returns.
Missing settlement values/eligibility/coverage never become zero funding.
"""
from dataclasses import dataclass
from decimal import Decimal

from lab.paper_account import number, text, _precision


BASES = {'settlement_mark', 'settlement_fair', 'settlement_index'}


@dataclass(frozen=True, kw_only=True)
class FundingTerm:
    venue: str
    symbol: str
    asset: str
    event_id: str
    funding_ns: int
    rate: Decimal | None
    rate_unit: str
    rate_stage: str
    settlement_price: Decimal | None
    value_basis: str
    source_identity: str
    eligible: bool | None = None
    payment_kind: str = 'unknown'

    def __post_init__(self):
        for field in ('venue', 'symbol', 'asset', 'event_id', 'rate_unit', 'rate_stage',
                      'value_basis', 'source_identity', 'payment_kind'):
            text(getattr(self, field))
        if type(self.funding_ns) is not int or self.funding_ns < 0:
            raise ValueError('explicit nonnegative nanosecond funding time required')
        if self.eligible is not None and type(self.eligible) is not bool:
            raise ValueError('explicit eligibility or unknown required')
        object.__setattr__(self, 'payment_kind', self.payment_kind.casefold())
        if self.rate is not None:
            object.__setattr__(self, 'rate', number(self.rate))
        if self.settlement_price is not None:
            object.__setattr__(self, 'settlement_price', number(self.settlement_price, positive=True))


@_precision
def audit_notional(*, venue, symbol, asset, quantity_base, entry_price, exit_price,
                   entry_ns, exit_ns, events, round_trip_cost_quote,
                   expected_value_basis, schedule_complete=False):
    """Compare conventions in quote units and bp of fixed entry notional.

    Event eligibility, rate stage, complete schedule and value basis must be
    explicitly supplied. These assertions are not independently verified here.
    Regular and special payments keep distinct identities; unknown kinds cannot
    certify a cash component. Dividend/snapshot eligibility is not inferred.
    The interval convention is (entry, exit], conditional on supplied eligibility;
    an exit at a settlement time does not itself prove venue ownership.
    Costs are one nonnegative all-in round trip, scaled at1x/2x/3x only once.
    No fills, margin/liquidation path, allocation or real-account credit is proved.
    """
    venue, symbol, asset = text(venue), text(symbol), text(asset)
    q = number(quantity_base)
    if not q:
        raise ValueError('nonzero fixed base quantity required')
    p0 = number(entry_price, positive=True)
    p1 = None if exit_price is None else number(exit_price, positive=True)
    cost = None if round_trip_cost_quote is None else number(round_trip_cost_quote, nonnegative=True)
    if (type(entry_ns) is not int or type(exit_ns) is not int or not 0 <= entry_ns < exit_ns
            or type(schedule_complete) is not bool or expected_value_basis not in BASES):
        raise ValueError('explicit interval, coverage and settlement-value basis required')
    if not isinstance(events, (tuple, list)) or any(not isinstance(e, FundingTerm) for e in events):
        raise ValueError('explicit typed funding observations required')
    keys = set(); ids = set(); common = []; value_flags = []; rate_total = Decimal(0); weighted = Decimal(0)
    if not schedule_complete:
        common.append('settlement_schedule_incomplete_or_unverified')
    for e in events:
        if (e.venue, e.symbol, e.asset) != (venue, symbol, asset):
            raise ValueError('funding venue/symbol/asset mismatch; no cross-account netting')
        if not entry_ns < e.funding_ns <= exit_ns:
            raise ValueError('event outside the declared (entry, exit] interval')
        key = e.venue, e.symbol, e.asset, e.funding_ns, e.payment_kind
        if key in keys or e.event_id in ids:
            raise ValueError('duplicate funding event or settlement slot')
        keys.add(key); ids.add(e.event_id)
        if e.payment_kind not in ('regular', 'special'):
            common.append(e.event_id + ':payment_kind_not_classified')
        if e.eligible is not True:
            common.append(e.event_id + ':position_eligibility_not_confirmed')
        if e.rate_stage != 'settled':
            common.append(e.event_id + ':rate_not_settled')
        rate = None
        if e.rate is None or e.rate_unit not in ('fraction', 'percent'):
            common.append(e.event_id + ':rate_or_unit_unknown')
        else:
            rate = e.rate / (100 if e.rate_unit == 'percent' else 1)
            rate_total += rate
        if e.settlement_price is None or e.value_basis != expected_value_basis:
            value_flags.append(e.event_id + ':settlement_value_missing_or_wrong_basis')
        elif rate is not None:
            weighted += e.settlement_price * rate
    entry_notional = abs(q) * p0
    approximate = None if common else -q * p0 * rate_total
    fixed = None if common or value_flags else -q * weighted
    gross = None if p1 is None else q * (p1 - p0)
    flags = common + value_flags
    if p1 is None:
        flags.append('exit_price_unknown')
    if cost is None:
        flags.append('round_trip_cost_unknown')
    string = lambda x: None if x is None else str(x)
    tiers = []
    for multiple in (1, 2, 3):
        old_net = None if approximate is None or gross is None or cost is None else gross + approximate - multiple * cost
        fixed_net = None if fixed is None or gross is None or cost is None else gross + fixed - multiple * cost
        tiers.append(dict(cost_multiple=multiple, rate_sum_net_quote=string(old_net),
                          fixed_quantity_net_quote=string(fixed_net),
                          rate_sum_net_bp=string(None if old_net is None else 10000 * old_net / entry_notional),
                          fixed_quantity_net_bp=string(None if fixed_net is None else 10000 * fixed_net / entry_notional)))
    return dict(state='CONDITIONAL_MODEL' if not flags else 'UNSCORED', venue=venue, symbol=symbol, asset=asset,
                quantity_base=str(q), entry_notional_quote=str(entry_notional),
                payment_kinds=sorted({e.payment_kind for e in events}),
                gross_price_pnl_quote=string(gross), rate_sum_funding_quote=string(approximate),
                fixed_quantity_funding_quote=string(fixed),
                funding_difference_quote=string(None if approximate is None or fixed is None else fixed - approximate),
                flags=sorted(set(flags)), tiers=tiers, simulation_only=True,
                model_new_entries_allowed=False, actual_order_allowed=False, activation_allowed=False,
                real_account_credit_verified=False, settlement_sources_independently_verified=False,
                scope='Conditional linear fixed-quantity arithmetic only; no executable strategy, account or source certification.')
