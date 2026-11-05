"""Explicit loss-at-size scenarios for new linear-futures paper consumers.

These are caller-declared stresses, not probabilities, certified maximum losses,
exchange margin, or fill evidence. Never scale a small quote to invent capacity
at a larger size. Each proposed quantity needs its own costs and scenarios.
"""
from dataclasses import dataclass, asdict
from decimal import Decimal

from lab.acquisition_budget import _locked, _read_records
from lab.paper_account import number, text, _precision


@dataclass(frozen=True)
class EntryLossPolicy:
    policy_id: str
    # (venue, settlement asset, maximum incremental scenario loss)
    account_limits: tuple
    required_scenarios: tuple

    def __post_init__(self):
        text(self.policy_id)
        if not isinstance(self.account_limits, (tuple, list)) or not isinstance(self.required_scenarios, (tuple, list)):
            raise ValueError('explicit account and scenario collections required')
        limits = tuple((text(v), text(a), number(x, positive=True)) for v, a, x in self.account_limits)
        names = tuple(text(n) for n in self.required_scenarios)
        if not limits or len(limits) > 32 or len({(v, a) for v, a, _ in limits}) != len(limits):
            raise ValueError('one to32 unique separate account loss limits required')
        if not names or len(names) > 16 or len(set(names)) != len(names):
            raise ValueError('one to16 unique predeclared scenarios required')
        object.__setattr__(self, 'account_limits', tuple(sorted(limits)))
        object.__setattr__(self, 'required_scenarios', tuple(sorted(names)))

    def mapping(self):
        return dict(policy_id=self.policy_id,
                    account_limits=[dict(venue=v, asset=a, max_loss_quote=str(x))
                                    for v, a, x in self.account_limits],
                    required_scenarios=list(self.required_scenarios))


@dataclass(frozen=True, kw_only=True)
class EntryScenario:
    scenario_id: str
    venue: str
    asset: str
    symbol: str
    quantity_base: Decimal
    entry_price: Decimal | None
    exit_price: Decimal | None
    entry_fee_quote: Decimal | None
    exit_fee_quote: Decimal | None
    funding_quote: Decimal | None
    extra_loss_quote: Decimal | None

    def __post_init__(self):
        for field in ('scenario_id', 'venue', 'asset', 'symbol'):
            text(getattr(self, field))
        q = number(self.quantity_base)
        if not q:
            raise ValueError('explicit signed nonzero scenario quantity required')
        object.__setattr__(self, 'quantity_base', q)
        for field in ('entry_price', 'exit_price', 'entry_fee_quote', 'exit_fee_quote',
                      'funding_quote', 'extra_loss_quote'):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, number(value,
                    positive=field == 'entry_price',
                    nonnegative=field in ('exit_price', 'entry_fee_quote', 'exit_fee_quote', 'extra_loss_quote')))

    def mapping(self):
        return {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(self).items()}


@_precision
def risk_headroom(risk, report, key, *, current_account):
    """Remaining native loss/drawdown room, including durable high-water marks.

    Reuse the frozen risk engine's journal/state interpretation without changing
    it. Only a current observation of that same journal is supported.
    """
    with _locked(risk.path) as handle:
        rows = _read_records(handle)
        if not rows or rows[0]['event'] != risk.header:
            raise ValueError('risk header drift')
        peaks, _, _, _ = risk._state(rows)
        if len(rows) < 2 or rows[-1]['event']['accounts'] != report['accounts']:
            raise ValueError('current native risk observation required')
    account = next(a for a in report['accounts'] if (a['venue'], a['asset']) == key)
    if (current_account['venue'], current_account['asset']) != key:
        raise ValueError('matching separate current account required')
    current_capital = [current_account.get(k) for k in ('cash', 'nav', 'available_capital')]
    if account['net_pnl'] is None or any(x is None for x in current_capital):
        return None
    base = risk.initial[key]
    net = number(account['net_pnl'])
    peak = max(Decimal(0), peaks.get(key, Decimal(0)))
    return dict(loss_stop_room_quote=str(base * risk.policy.max_loss_fraction + net),
                drawdown_stop_room_quote=str(base * risk.policy.max_drawdown_fraction - (peak - net)),
                current_solvency_room_quote=str(min(number(x) for x in current_capital)),
                high_water_net_pnl_quote=str(peak), current_net_pnl_quote=str(net))


@_precision
def assess_entry_loss(intent, scenarios, policy, headroom, *, cost_multiple=1):
    """Veto proposed size against every declared scenario; no interpolation.

    Fees are charged on both legs of the round trip at the requested cost tier.
    Funding is signed and extra loss is a separate nonnegative stress allowance.
    Price moves already embedded in entry/exit prices are not charged twice.
    Budget at least the gross cash debits, without crediting future gains.
    Equality to a native persistent stop is blocked, just as in PaperRisk.
    """
    if not isinstance(policy, EntryLossPolicy):
        raise ValueError('typed predeclared entry loss policy required')
    if type(cost_multiple) is not int or cost_multiple not in (1, 2, 3):
        raise ValueError('fixed1x/2x/3x cost tier required')
    if not isinstance(scenarios, (tuple, list)) or len(scenarios) > 16:
        raise ValueError('bounded explicit scenario collection required')
    if any(not isinstance(s, EntryScenario) for s in scenarios):
        raise ValueError('typed entry scenarios required')
    limits = {(v, a): x for v, a, x in policy.account_limits}
    key = intent.venue, intent.asset
    if key not in limits:
        raise ValueError('entry has no registered account loss limit')
    reasons = []
    names = [s.scenario_id for s in scenarios]
    if len(set(names)) != len(names):
        raise ValueError('duplicate entry scenario')
    if set(names) != set(policy.required_scenarios):
        reasons.append('required_loss_scenarios_incomplete_or_changed')
    if headroom is None:
        reasons.append('native_loss_headroom_unknown')
    else:
        for name in ('loss_stop_room_quote', 'drawdown_stop_room_quote', 'current_solvency_room_quote'):
            number(headroom[name])
    rows = []
    for s in scenarios:
        flags = []
        if (s.venue, s.asset, s.symbol, s.quantity_base) != (
                intent.venue, intent.asset, intent.symbol, intent.quantity_base):
            flags.append('scenario_instrument_asset_side_or_size_mismatch')
        monetary = (s.entry_price, s.exit_price, s.entry_fee_quote, s.exit_fee_quote,
                    s.funding_quote, s.extra_loss_quote)
        net = loss = None
        if any(x is None for x in monetary):
            flags.append('scenario_money_unknown')
        if not flags:
            price_pnl = s.quantity_base * (s.exit_price - s.entry_price)
            net = (price_pnl + s.funding_quote
                   - cost_multiple * (s.entry_fee_quote + s.exit_fee_quote) - s.extra_loss_quote)
            # Unknown timing cannot finance cash debits with a future favorable
            # price move or funding receipt. This is a conservative debit budget,
            # not a model of the full intratrade price/margin path.
            debits = (max(Decimal(0), -price_pnl) + cost_multiple * (s.entry_fee_quote + s.exit_fee_quote)
                      + max(Decimal(0), -s.funding_quote) + s.extra_loss_quote)
            loss = max(Decimal(0), -net, debits)
            if loss > limits[key]:
                flags.append('proposed_scenario_loss_limit')
            if headroom is not None:
                if loss >= number(headroom['loss_stop_room_quote']):
                    flags.append('proposed_loss_stop_reached')
                if loss >= number(headroom['drawdown_stop_room_quote']):
                    flags.append('proposed_drawdown_stop_reached')
                if loss >= number(headroom['current_solvency_room_quote']):
                    flags.append('proposed_current_capital_exhausted')
        rows.append(dict(scenario_id=s.scenario_id, net_pnl_quote=None if net is None else str(net),
                         loss_quote=None if loss is None else str(loss), reasons=flags))
        reasons.extend(flags)
    known = len(rows) == len(policy.required_scenarios) and all(r['loss_quote'] is not None for r in rows)
    worst = max((number(r['loss_quote']) for r in rows), default=None) if known else None
    prices = [s.entry_price for s in scenarios if s.entry_price is not None]
    entry_fees = [s.entry_fee_quote for s in scenarios if s.entry_fee_quote is not None]
    return dict(state='CONDITIONAL_PASS' if not reasons else 'BLOCKED',
                model_size_within_loss_limits=not reasons, actual_order_allowed=False, activation_allowed=False,
                policy_id=policy.policy_id, cost_multiple=cost_multiple, account_loss_limit_quote=str(limits[key]),
                native_headroom=headroom, worst_declared_loss_quote=None if worst is None else str(worst),
                entry_price_floor=None if len(prices) != len(scenarios) or not prices else str(min(prices)),
                entry_price_ceiling=None if len(prices) != len(scenarios) or not prices else str(max(prices)),
                entry_fee_budget_quote=None if len(entry_fees) != len(scenarios) or not entry_fees else
                    str(cost_multiple * max(entry_fees)),
                scenarios=rows, reasons=sorted(set(reasons)),
                scope='caller-declared linear price/fee/funding stresses only; not a guaranteed loss bound, '
                      'probability, fill, exchange margin, portfolio stress or profitable strategy certificate')
