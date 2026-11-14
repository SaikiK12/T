"""Fee-aware fixed-quantity inverse carry, with conditional terminal bounds.

Displayed books and caller-declared fees/exit ratios are model inputs, not fills
or authenticated account terms. No margin path, orders or strategy activation.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from lab.inverse_cash import InverseContract, rational, walk, terminal_conversion, wire
from lab.paper_account import text


def fee_rate(value):
    if value is None:
        raise ValueError('fee unknown; an explicit rate is required')
    value = rational(value, nonnegative=True)
    if value >= 1:
        raise ValueError('fee rate must be below one')
    return value


def tier(value):
    if type(value) is not int or value not in (1, 2, 3):
        raise ValueError('explicit1x/2x/3x cost tier required')
    return value


@dataclass(frozen=True)
class SpotContract:
    instrument: str
    coin: str
    quote: str
    step_base: F
    minimum_base: F
    minimum_quote: F
    source_identity: str

    def __post_init__(self):
        for field in ('instrument', 'coin', 'quote', 'source_identity'):
            text(getattr(self, field))
        for field in ('step_base', 'minimum_base'):
            object.__setattr__(self, field, rational(getattr(self, field), positive=True))
        object.__setattr__(self, 'minimum_quote', rational(self.minimum_quote, nonnegative=True))


@dataclass(frozen=True)
class CarryFees:
    spot_buy: F
    spot_buy_basis: str
    future_entry: F
    delivery: F
    spot_sell: F
    spot_sell_basis: str
    source_identity: str

    def __post_init__(self):
        text(self.source_identity)
        for field in ('spot_buy', 'future_entry', 'delivery', 'spot_sell'):
            object.__setattr__(self, field, fee_rate(getattr(self, field)))
        if self.spot_buy_basis not in ('base_received', 'quote_in_addition'):
            raise ValueError('explicit spot buy fee asset/basis required')
        if self.spot_sell_basis not in ('quote_received', 'base_in_addition'):
            raise ValueError('explicit spot sell fee asset/basis required')

    def at(self, multiple):
        k = tier(multiple)
        return tuple(fee_rate(k * getattr(self, field))
                     for field in ('spot_buy', 'future_entry', 'delivery', 'spot_sell'))


@dataclass(frozen=True)
class CarryPlan:
    spot: SpotContract
    future: InverseContract
    fees: CarryFees
    sizing_cost_multiple: int
    budget_quote: F
    spot_order_base: F
    spot_order_quote: F
    face_usd: F
    inverse_entry_coin_basis: F
    next_face_coin_requirement: F | None


def _levels(levels, side):
    if not isinstance(levels, (list, tuple)) or not 1 <= len(levels) <= 1000:
        raise ValueError('one to1000 explicit shown levels required')
    if any(not isinstance(row, (list, tuple)) or len(row) != 2 for row in levels):
        raise ValueError('price/amount level pairs required')
    rows = tuple(tuple(rational(x, positive=True) for x in row) for row in levels)
    # The shared walker checks shape and strict sorting, including unused tail.
    walk(rows, rows[0][1], side=side, unit='base')
    return rows


def _buy_base(asks, quote):
    left, base = quote, F(0)
    for price, size in asks:
        take = min(left, price * size)
        base += take / price
        left -= take
        if not left:
            return base
    raise ValueError('insufficient shown spot depth for declared budget')


def plan_carry(spot, future, fees, spot_asks, future_bids, budget_quote, *,
               sizing_cost_multiple=3, maximum_face_usd=None):
    """Fix spot order and maximal fee-covered face at the chosen stress tier.

    Largest face on the declared grid satisfying B >= (1+entry_fee)*sum(q_i/p_i).
    Lower cost tiers keep BOTH orders fixed; quote fee savings remain cash.
    This maximizes fee-covered shown face, not profit, risk-adjusted size or fills.
    """
    if not isinstance(spot, SpotContract) or not isinstance(future, InverseContract) or not isinstance(fees, CarryFees):
        raise ValueError('typed spot/inverse contracts and explicit fees required')
    if spot.coin != future.coin:
        raise ValueError('spot and inverse settlement coin mismatch')
    buy_fee, entry_fee, _, _ = fees.at(sizing_cost_multiple)
    budget = rational(budget_quote, positive=True)
    asks, bids = _levels(spot_asks, 'buy'), _levels(future_bids, 'sell')
    gross_budget = budget / (1 + buy_fee) if fees.spot_buy_basis == 'quote_in_addition' else budget
    base = (_buy_base(asks, gross_budget) // spot.step_base) * spot.step_base
    if base < spot.minimum_base or not base:
        raise ValueError('spot quantity below declared minimum after grid rounding')
    _, quote = walk(asks, base, side='buy', unit='base')
    if quote < spot.minimum_quote:
        raise ValueError('spot entry below declared quote minimum')
    coin = base * (1 - buy_fee) if fees.spot_buy_basis == 'base_received' else base
    step = future.face_step_usd
    shown_face = sum((size for _, size in bids), F(0))
    cap = shown_face if maximum_face_usd is None else min(shown_face, rational(maximum_face_usd, positive=True))
    lo, hi = 0, int(cap // step)
    if hi > 10**12:
        raise ValueError('declared face-grid search exceeds supported bound')
    def requirement(units):
        _, a = walk(bids, units * step, side='sell', unit='USD_face')
        return (1 + entry_fee) * a
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if requirement(mid) <= coin:
            lo = mid
        else:
            hi = mid - 1
    face = lo * step
    if not face or face < future.minimum_face_usd:
        raise ValueError('no fee-covered inverse quantity meeting declared minimum')
    _, a = walk(bids, face, side='sell', unit='USD_face')
    next_required = requirement(lo + 1) if (lo + 1) * step <= cap else None
    return CarryPlan(spot, future, fees, sizing_cost_multiple, budget, base, quote,
                     face, a, next_required)


def evaluate_carry(plan, *, cost_multiple=1, delivery_price=None, exit_ratio=None,
                   exit_ratio_floor=None, delivery_price_ceiling=None):
    """Evaluate the SAME orders; unknown exit price/ratio yields no payout.

    ratio is quote/coin exit price divided by USD/coin delivery price. A supplied
    positive floor is a conditional assumption; it is never inferred from entry.
    Actual model exits respect the supplied spot grid/minima and retain dust.
    A continuous conversion is a separately labelled reference. A cash floor
    also needs an explicit delivery-price ceiling to bound rounding/minimums.
    """
    if not isinstance(plan, CarryPlan):
        raise ValueError('typed fixed carry plan required')
    k = tier(cost_multiple)
    if k > plan.sizing_cost_multiple:
        raise ValueError('cost tier exceeds predeclared sizing stress; no later resizing')
    buy, entry, delivery, sell = plan.fees.at(k)
    base, spent = plan.spot_order_base, plan.spot_order_quote
    coin = base * (1 - buy) if plan.fees.spot_buy_basis == 'base_received' else base
    spent *= (1 + buy) if plan.fees.spot_buy_basis == 'quote_in_addition' else 1
    cash = plan.budget_quote - spent
    entry_coin_fee = entry * plan.inverse_entry_coin_basis
    residual = coin - entry_coin_fee - plan.inverse_entry_coin_basis
    if residual < 0 or cash < 0:
        raise ValueError('fixed plan violates its declared coin/cash fee budget')
    base_factor = 1 / (1 + sell) if plan.fees.spot_sell_basis == 'base_in_addition' else F(1)
    quote_factor = 1 - sell if plan.fees.spot_sell_basis == 'quote_received' else F(1)
    factor = base_factor * quote_factor
    floor = None if exit_ratio_floor is None else rational(exit_ratio_floor, positive=True)
    ceiling = None if delivery_price_ceiling is None else rational(delivery_price_ceiling, positive=True)
    continuous_lower = None if floor is None else cash + floor * plan.face_usd * (1 - delivery) * factor
    lower, lower_reasons = None, []
    if floor is None:
        lower_reasons.append('exit_ratio_floor_unknown')
    if ceiling is None:
        lower_reasons.append('delivery_price_ceiling_unknown_for_exit_grid')
    if not lower_reasons:
        min_coin = plan.face_usd * (1 - delivery) / ceiling + residual
        min_order = (min_coin * base_factor // plan.spot.step_base) * plan.spot.step_base
        value = base_factor * plan.face_usd * (1 - delivery)
        value += min(F(0), (base_factor * residual - plan.spot.step_base) * ceiling)
        gross_lower = floor * max(F(0), value)
        if min_order < plan.spot.minimum_base:
            lower_reasons.append('exit_base_minimum_not_proven_over_price_range')
        if gross_lower < plan.spot.minimum_quote:
            lower_reasons.append('exit_quote_minimum_not_proven_over_price_range')
        if not lower_reasons:
            lower = cash + gross_lower * quote_factor
    terminal = terminal_conversion(plan.face_usd, plan.inverse_entry_coin_basis, coin,
        entry_coin_fee, delivery, delivery_price, exit_ratio, 0)
    continuous = None if terminal is None else cash + terminal['usdt_proceeds_before_spot_fee'] * factor
    actual = order = dust = None
    exit_admissible = None
    if terminal is not None:
        p, ratio = rational(delivery_price, positive=True), rational(exit_ratio, positive=True)
        coin_end = terminal['coin_after_delivery']
        order = (coin_end * base_factor // plan.spot.step_base) * plan.spot.step_base
        exit_admissible = order >= plan.spot.minimum_base and order * p * ratio >= plan.spot.minimum_quote
        if not exit_admissible:
            order = F(0)
        dust = coin_end - order / base_factor
        actual = cash + order * p * ratio * quote_factor
    floor_satisfied = None if floor is None or exit_ratio is None else rational(exit_ratio, positive=True) >= floor
    ceiling_satisfied = None if ceiling is None or delivery_price is None else rational(delivery_price, positive=True) <= ceiling
    return dict(cost_multiple=k, fixed_spot_order_base=wire(base), fixed_face_usd=wire(plan.face_usd),
        leftover_quote=wire(cash), entry_fee_coin=wire(entry_coin_fee), residual_coin=wire(residual),
        continuous_payoff_price_independent=residual == 0,
        continuous_lower_reference_quote=None if continuous_lower is None else wire(continuous_lower),
        conditional_lower_proceeds_quote=None if lower is None else wire(lower),
        conditional_lower_return=None if lower is None else wire(lower / plan.budget_quote - 1),
        continuous_terminal_reference_quote=None if continuous is None else wire(continuous),
        terminal_proceeds_quote=None if actual is None else wire(actual),
        terminal_return=None if actual is None or dust != 0 else wire(actual / plan.budget_quote - 1),
        exit_order_base=None if order is None else wire(order), unsold_dust_coin=None if dust is None else wire(dust),
        exit_order_meets_declared_minima=exit_admissible,
        exit_ratio_floor_assumed=exit_ratio_floor is not None,
        observed_exit_ratio_satisfies_floor=floor_satisfied,
        delivery_price_ceiling_assumed=ceiling is not None,
        observed_delivery_price_satisfies_ceiling=ceiling_satisfied,
        lower_bound_missing=lower_reasons,
        source_fills_verified=False, actual_order_allowed=False, activation_allowed=False,
        scope='conditional terminal arithmetic only; exit conversion, fees, matching, access and margin path unverified')
