"""Offline markout/cost diagnostic; no provider access, orders or fill inference.

The single supplied fill and two midpoint observations must be explicitly
time-bound.  A midpoint exit is an optimistic counterfactual, not an executable
price or evidence of a positive strategy.  Action costs are kept outside the
existing paper ledger rather than misclassified as a deposit/withdrawal.
"""
from dataclasses import dataclass, replace
from decimal import Decimal, localcontext

from lab.funding_values import clock_known
from lab.paper_account import PaperAccount, PaperEvent, number
from lab.stream_quotes import FrameClock, ReferencePrice


@dataclass(frozen=True)
class RequestCounts:
    accepted: int
    rejected: int
    unresolved: int
    cancels: int
    paid_actions: int
    recorded_fill_events: int
    terminal_receipts_complete: bool

    def __post_init__(self):
        for v in (self.accepted, self.rejected, self.unresolved, self.cancels, self.paid_actions, self.recorded_fill_events):
            if type(v) is not int or v < 0:
                raise ValueError('nonnegative integer action counts required')
        if type(self.terminal_receipts_complete) is not bool or self.recorded_fill_events not in (0, 1):
            raise ValueError('explicit terminal reconciliation and zero/one fill events required')
        if self.recorded_fill_events and not self.accepted:
            raise ValueError('fill without a reported accepted order')
        if self.paid_actions > self.accepted + self.rejected + self.unresolved + self.cancels:
            raise ValueError('paid actions exceed accounted actions')

    @property
    def submitted(self):
        return self.accepted + self.rejected + self.unresolved


def _valid_mid(mid, fill, anchor, asof):
    if not isinstance(mid, ReferencePrice) or mid.source_role != 'validated_bbo_mid':
        raise ValueError('source-typed BBO midpoint required')
    if (mid.venue, mid.symbol) != (fill.venue, fill.symbol):
        raise ValueError('fill/quote venue and symbol mismatch')
    if not isinstance(mid.clock, FrameClock) or not clock_known(mid.clock, asof, anchor):
        raise ValueError('quote receipt unavailable or clock stepped')
    if type(mid.source_time_ns) is not int or not anchor.utc_ns <= mid.source_time_ns <= mid.clock.utc_ns:
        raise ValueError('invalid source and receipt clock ordering')
    number(mid.price, positive=True)


def evaluate(counts, fill, at_fill, horizon_mid, *, anchor, asof, horizon_ns,
             max_age_ns, max_lag_ns, capital, entry_fee_bps, exit_fee_bps,
             paid_action_usd, extra_cost_usd, multiple):
    """One fill, or an explicit zero-fill record, with fixed cost assumptions.

    Unknown terminal orders or missing fill/mark evidence never become zero PnL.
    The returned quantity is an illustrative midpoint-exit component; it is
    neither actual fills nor prospective paper evidence.
    """
    if not isinstance(counts, RequestCounts) or not isinstance(anchor, FrameClock):
        raise ValueError('typed counts and clock anchor required')
    for v in (asof, horizon_ns, max_age_ns, max_lag_ns):
        if type(v) is not int or v < 0:
            raise ValueError('nonnegative integer timing required')
    if multiple not in (1, 2, 3) or type(multiple) is not int:
        raise ValueError('fixed 1x/2x/3x cost stress required')
    capital = number(capital, positive=True)
    entry_fee_bps = number(entry_fee_bps, nonnegative=True)
    exit_fee_bps = number(exit_fee_bps, nonnegative=True)
    paid_action_usd = number(paid_action_usd, nonnegative=True)
    extra_cost_usd = number(extra_cost_usd, nonnegative=True)
    with localcontext() as ctx:
        ctx.prec = 80
        actions_cost = counts.paid_actions * paid_action_usd * multiple
        base = {'submitted': counts.submitted, 'unresolved': counts.unresolved,
                'action_cost_usd': str(actions_cost), 'multiple': multiple,
                'execution_status': 'HYPOTHETICAL_MID_EXIT_ONLY'}
        if counts.unresolved or not counts.terminal_receipts_complete:
            return {**base, 'status': 'UNKNOWN_OPEN_ORDERS', 'component_usd': None}
        if fill is None:
            if counts.recorded_fill_events:
                raise ValueError('recorded fill must be supplied')
            if at_fill is not None or horizon_mid is not None:
                raise ValueError('marks cannot manufacture an unreported fill')
            cost = actions_cost + extra_cost_usd * multiple
            return {**base, 'status': 'NO_REPORTED_FILL', 'component_usd': str(-cost),
                    'markout_usd': None, 'entry_notional_usd': '0',
                    'cost_per_filled_notional_bps': None}
        if not isinstance(fill, PaperEvent) or fill.kind != 'fill' or fill.fee is not None or counts.recorded_fill_events != 1:
            raise ValueError('explicit simulated fill, unknown actual fee and accepted order required')
        if not clock_known(fill.clock, asof, anchor) or fill.occurred_ns < anchor.utc_ns:
            raise ValueError('fill was not available at the as-of time')
        _valid_mid(at_fill, fill, anchor, asof)
        _valid_mid(horizon_mid, fill, anchor, asof)
        if at_fill.clock.utc_ns > fill.occurred_ns or at_fill.source_time_ns > fill.occurred_ns:
            raise ValueError('pre-fill quote must be known by the economic fill time')
        if fill.occurred_ns - at_fill.source_time_ns > max_age_ns:
            raise ValueError('pre-fill midpoint stale')
        target = fill.occurred_ns + horizon_ns
        if not target <= horizon_mid.source_time_ns <= target + max_lag_ns:
            raise ValueError('mark observation outside fixed horizon tolerance')
        if horizon_mid.clock.mono_ns < fill.clock.mono_ns:
            raise ValueError('mark receipt precedes fill receipt')
        if fill.reference_mid is not None and fill.reference_mid != number(at_fill.price):
            raise ValueError('fill midpoint conflicts with source observation')
        q, p = fill.quantity, fill.price
        mid0, midh = number(at_fill.price, positive=True), number(horizon_mid.price, positive=True)
        notional, exit_notional = abs(q) * p, abs(q) * midh
        spread, move = q * (mid0 - p), q * (midh - mid0)
        markout = q * (midh - p)
        fee_entry = notional * entry_fee_bps * multiple / Decimal(10000)
        fee_exit = exit_notional * exit_fee_bps * multiple / Decimal(10000)
        if spread + move != markout:
            raise AssertionError('spread counted exactly once')
        account = PaperAccount({(fill.venue, fill.asset): capital}, anchor)
        simulated_entry = replace(fill, fee=fee_entry, reference_mid=mid0)
        if account.post(simulated_entry, fill.clock.mono_ns)['status'] != 'applied':
            raise ValueError('entry receipt rejected by existing paper ledger')
        entry_state = account.snapshot(fill.clock.mono_ns)['accounts'][0]
        if 'simulated_collateral_shortfall' in entry_state['reasons']:
            raise ValueError('segregated capital cannot fund simulated entry')
        close = PaperEvent(event_id=fill.event_id + ':midpoint_exit', kind='fill',
            venue=fill.venue, asset=fill.asset, symbol=fill.symbol,
            occurred_ns=horizon_mid.clock.utc_ns, clock=horizon_mid.clock,
            source_identity='HYPOTHETICAL midpoint exit; not a venue fill',
            quantity=-q, price=midh, fee=fee_exit, reference_mid=midh)
        if account.post(close, horizon_mid.clock.mono_ns)['status'] != 'applied':
            raise ValueError('counterfactual exit rejected by paper ledger')
        report = account.snapshot(asof)['accounts'][0]
        if report['reconciliation_required'] or report['realized_net_pnl'] is None:
            raise ValueError('paper ledger incomplete')
        ledger_component = number(report['realized_net_pnl'])
        component = ledger_component - actions_cost - extra_cost_usd * multiple
        if ledger_component != markout - fee_entry - fee_exit:
            raise AssertionError('paper-ledger and signed markout decomposition differ')
        return {**base, 'status': 'SCORED_COUNTERFACTUAL',
                'entry_notional_usd': str(notional), 'markout_usd': str(markout),
                'spread_component_usd': str(spread), 'midpoint_move_usd': str(move),
                'entry_fee_usd': str(fee_entry), 'exit_fee_usd': str(fee_exit),
                'extra_cost_usd': str(extra_cost_usd * multiple),
                'cost_per_filled_notional_bps': str((fee_entry + fee_exit + actions_cost + extra_cost_usd * multiple) * 10000 / notional),
                'component_usd': str(component), 'component_per_capital_bps': str(component * 10000 / capital)}
