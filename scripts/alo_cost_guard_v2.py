"""Conservative receipt and prefunding wrapper around frozen R365 arithmetic.

No quote or order is generated.  Receipt-completeness is a source attestation,
not something inferred from public order-book updates or proven by this module.
"""
from dataclasses import dataclass
from decimal import Decimal, localcontext

from lab.funding_values import clock_known
from lab.paper_account import number, text
from lab.stream_quotes import FrameClock
from scripts.alo_cost_guard import RequestCounts, evaluate as evaluate_v1


@dataclass(frozen=True)
class TerminalEvidence:
    source_identity: str
    venue: str
    asset: str
    symbol: str
    order_id: str | None
    occurred_ns: int
    clock: FrameClock
    complete_fill_history: bool
    fill_event_ids: tuple[str, ...]
    final_filled_quantity: Decimal
    reported_counts: RequestCounts
    clock_uncertainty_ns: int | None
    clock_bound_source: str | None
    action_and_extra_costs_prepaid: bool

    def __post_init__(self):
        text(self.source_identity)
        for value in (self.venue, self.asset, self.symbol):
            text(value)
        if self.order_id is not None:
            text(self.order_id)
        if type(self.occurred_ns) is not int or self.occurred_ns < 0 or not isinstance(self.clock, FrameClock):
            raise ValueError('explicit terminal source and receipt clocks required')
        if self.occurred_ns > self.clock.utc_ns:
            raise ValueError('terminal receipt cannot predate terminal source event')
        if type(self.complete_fill_history) is not bool or type(self.action_and_extra_costs_prepaid) is not bool:
            raise ValueError('explicit history and prepayment attestations required')
        if not isinstance(self.reported_counts, RequestCounts):
            raise ValueError('timestamped terminal evidence must bind action counts')
        if self.clock_uncertainty_ns is not None:
            if type(self.clock_uncertainty_ns) is not int or self.clock_uncertainty_ns < 0:
                raise ValueError('nonnegative clock uncertainty required')
            text(self.clock_bound_source)
        elif self.clock_bound_source is not None:
            raise ValueError('clock source without uncertainty bound')
        if not isinstance(self.fill_event_ids, tuple) or len(self.fill_event_ids) != len(set(self.fill_event_ids)):
            raise ValueError('unique explicit fill event identities required')
        for item in self.fill_event_ids:
            text(item)
        object.__setattr__(self, 'final_filled_quantity', number(self.final_filled_quantity))


def evaluate(counts, evidence, fill, at_fill, horizon_mid, *, account_scope, **kwargs):
    """Fail closed unless a complete, first-seen, prepaid fixture is supplied."""
    if not isinstance(counts, RequestCounts) or not isinstance(kwargs.get('anchor'), FrameClock):
        raise ValueError('typed counts and anchor required')
    if not isinstance(account_scope, tuple) or len(account_scope) != 3:
        raise ValueError('explicit venue, asset and symbol scope required')
    for value in account_scope:
        text(value)
    anchor, asof = kwargs['anchor'], kwargs.get('asof')
    if type(asof) is not int or asof < 0:
        raise ValueError('nonnegative monotonic as-of required')
    multiple = kwargs.get('multiple')
    if type(multiple) is not int or multiple not in (1, 2, 3):
        raise ValueError('fixed 1x/2x/3x cost stress required')
    action = number(kwargs['paid_action_usd'], nonnegative=True)
    extra = number(kwargs['extra_cost_usd'], nonnegative=True)
    known_action = None
    known_extra = None
    def unknown(reason):
        return {'status': 'UNKNOWN_RECEIPTS_OR_ACTION_FUNDING', 'reason': reason,
                'component_usd': None, 'component_per_capital_bps': None,
                'assumed_prepaid_action_cost_usd': known_action,
                'assumed_prepaid_extra_cost_usd': known_extra}
    if asof < anchor.mono_ns:
        return unknown('asof_before_anchor')
    if not isinstance(evidence, TerminalEvidence):
        return unknown('terminal_evidence_absent')
    if (evidence.venue, evidence.asset, evidence.symbol) != account_scope:
        return unknown('terminal_account_scope_mismatch')
    if evidence.reported_counts != counts:
        return unknown('terminal_count_identity_mismatch')
    cutoff_utc = anchor.utc_ns + asof - anchor.mono_ns
    if (evidence.occurred_ns < anchor.utc_ns or evidence.clock.mono_ns < anchor.mono_ns
            or evidence.clock.utc_ns > cutoff_utc or evidence.occurred_ns > cutoff_utc
            or not clock_known(evidence.clock, asof, anchor)):
        return unknown('terminal_receipt_unavailable_or_clock_drift')
    if evidence.action_and_extra_costs_prepaid:
        known_action = str(counts.paid_actions * action * multiple)
        known_extra = str(extra * multiple)
    if evidence.clock_uncertainty_ns is None:
        return unknown('economic_clock_uncertainty_unavailable')
    uncertainty = evidence.clock_uncertainty_ns
    def coherent(source_ns, clock):
        projected = anchor.utc_ns + clock.mono_ns - anchor.mono_ns
        return abs(clock.utc_ns - projected) <= uncertainty and source_ns <= projected + uncertainty
    if not coherent(evidence.occurred_ns, evidence.clock):
        return unknown('terminal_clock_bound_inconsistent')
    if counts.accepted > 1 or (counts.accepted == 1) != (evidence.order_id is not None):
        return unknown('unsupported_or_unidentified_accepted_orders')
    if counts.unresolved or not counts.terminal_receipts_complete:
        return unknown('unresolved_order')
    if not evidence.complete_fill_history:
        return unknown('fill_history_incomplete')
    expected_ids = (fill.event_id,) if fill is not None else ()
    expected_qty = fill.quantity if fill is not None else Decimal(0)
    if (evidence.fill_event_ids != expected_ids or counts.recorded_fill_events != len(expected_ids)
            or evidence.final_filled_quantity != expected_qty):
        return unknown('fill_history_identity_mismatch')
    if fill is not None:
        if (fill.venue, fill.asset, fill.symbol) != account_scope:
            return unknown('fill_account_scope_mismatch')
        if fill.clock.mono_ns < anchor.mono_ns or fill.clock.utc_ns > cutoff_utc or fill.occurred_ns > cutoff_utc:
            return unknown('fill_economic_time_after_asof')
        if evidence.occurred_ns < fill.occurred_ns or evidence.clock.mono_ns < fill.clock.mono_ns:
            return unknown('terminal_receipt_precedes_fill')
        if (at_fill is None or at_fill.clock.mono_ns < anchor.mono_ns
                or at_fill.clock.mono_ns > fill.clock.mono_ns):
            raise ValueError('quote first seen after fill receipt')
        fill_mono_bound = anchor.mono_ns + fill.occurred_ns - anchor.utc_ns
        if at_fill.clock.mono_ns + uncertainty > fill_mono_bound:
            raise ValueError('quote may have arrived after economic fill')
        if not coherent(fill.occurred_ns, fill.clock) or not coherent(at_fill.source_time_ns, at_fill.clock):
            raise ValueError('source and receive clocks violate asserted uncertainty bound')
        if horizon_mid is not None and (horizon_mid.clock.mono_ns < anchor.mono_ns
                or horizon_mid.clock.utc_ns > cutoff_utc or horizon_mid.source_time_ns > cutoff_utc):
            return unknown('horizon_source_after_asof')
        if horizon_mid is not None:
            if not coherent(horizon_mid.source_time_ns, horizon_mid.clock):
                raise ValueError('source and receive clocks violate asserted uncertainty bound')
            target = fill.occurred_ns + kwargs['horizon_ns']
            if (fill.occurred_ns - at_fill.source_time_ns + 2*uncertainty > kwargs['max_age_ns']
                    or horizon_mid.source_time_ns < target + 2*uncertainty
                    or horizon_mid.source_time_ns > target + kwargs['max_lag_ns'] - 2*uncertainty):
                return unknown('clock_uncertainty_exceeds_quote_window')
    if not evidence.action_and_extra_costs_prepaid:
        return unknown('action_cost_funding_and_timing_unknown')
    capital = number(kwargs['capital'], positive=True)
    with localcontext() as ctx:
        ctx.prec = 80
        prepaid = (counts.paid_actions * action + extra) * multiple
        available = capital - prepaid
        if available < 0 or (available == 0 and fill is not None):
            raise ValueError('prepaid actions and extra costs exhaust segregated capital')
        if available == 0:
            return {'status': 'INSOLVENT_COUNTERFACTUAL', 'submitted':counts.submitted,
                    'unresolved':0, 'multiple':multiple,
                    'execution_status':'HYPOTHETICAL_MID_EXIT_AND_PREPAID_COSTS_ONLY',
                    'action_cost_usd':str(counts.paid_actions * action * multiple),
                    'prepaid_costs_usd':str(prepaid), 'markout_usd':None,
                    'entry_notional_usd':'0', 'cost_per_filled_notional_bps':None,
                    'component_usd':str(-prepaid), 'component_per_capital_bps':str(-prepaid*10000/capital),
                    'original_segregated_capital_usd':str(capital),
                    'counterfactual_end_capital_usd':'0', 'path_solvency_unknown':True}
        out = evaluate_v1(counts, fill, at_fill, horizon_mid, **{**kwargs, 'capital': available})
        out['prepaid_costs_usd'] = str(prepaid)
        out['original_segregated_capital_usd'] = str(capital)
        if out.get('component_usd') is not None:
            out['component_per_capital_bps'] = str(number(out['component_usd']) * 10000 / capital)
            end_capital = capital + number(out['component_usd'])
            out['counterfactual_end_capital_usd'] = str(end_capital)
            if end_capital <= 0:
                out['status'] = 'INSOLVENT_COUNTERFACTUAL'
        out['path_solvency_unknown'] = True
        out['execution_status'] = 'HYPOTHETICAL_MID_EXIT_AND_PREPAID_COSTS_ONLY'
        return out
