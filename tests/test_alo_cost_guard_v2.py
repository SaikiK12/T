from dataclasses import replace
from decimal import Decimal as D
import unittest

from lab.stream_quotes import FrameClock, NS
from scripts.alo_cost_guard import RequestCounts, evaluate as old_evaluate
from scripts.alo_cost_guard_v2 import TerminalEvidence, evaluate
from tests.test_alo_cost_guard import A, U, clock, setup


def evidence(f=None, c=None, **kwargs):
    if c is None:
        c = RequestCounts(1, 0, 0, 0, 0, 1, True) if f else RequestCounts(0, 10, 0, 0, 10, 0, True)
    v = dict(source_identity='invented complete terminal and fill history',
             venue='hl', asset='USDC', symbol='BTC', order_id='order-1' if f else None,
             occurred_ns=U+NS+1, clock=clock(NS+1), complete_fill_history=True,
             fill_event_ids=(f.event_id,) if f else (),
             final_filled_quantity=f.quantity if f else D('0'),
             reported_counts=c, clock_uncertainty_ns=0, clock_bound_source='constructed exact clock',
             action_and_extra_costs_prepaid=True)
    return TerminalEvidence(**{**v, **kwargs})


class AloGuardV2Tests(unittest.TestCase):
    def test_adversarial_monotonic_quote_lookahead_is_rejected(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        bad = replace(a, clock=FrameClock(a.clock.utc_ns, f.clock.mono_ns+10_000_000))
        self.assertEqual(old_evaluate(c, f, bad, b, **k)['status'], 'SCORED_COUNTERFACTUAL')
        with self.assertRaisesRegex(ValueError, 'after fill receipt'):
            evaluate(c, evidence(f), f, bad, b, account_scope=('hl','USDC','BTC'), **k)

    def test_untimed_and_incomplete_terminal_evidence_remain_unknown(self):
        _, _, _, k = setup()
        c = RequestCounts(1, 0, 0, 1, 1, 0, True)
        ev = evidence(None, c, order_id='canceled-order', complete_fill_history=False)
        self.assertEqual(old_evaluate(c, None, None, None, **k)['status'], 'NO_REPORTED_FILL')
        self.assertEqual(evaluate(c, ev, None, None, None, account_scope=('hl','USDC','BTC'), **k)['reason'], 'fill_history_incomplete')
        self.assertEqual(evaluate(c, ev, None, None, None, account_scope=('hl','USDC','BTC'), **{**k,'asof':0})['reason'], 'asof_before_anchor')
        self.assertEqual(evaluate(c, replace(ev, clock=clock(3*NS)), None, None, None,
                                  account_scope=('hl','USDC','BTC'), **k)['reason'], 'terminal_receipt_unavailable_or_clock_drift')

    def test_prefunded_actions_block_entry_when_capital_is_too_small(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 9, 0, 0, 10, 1, True)
        k['capital'] = '200.02'
        self.assertEqual(old_evaluate(c, f, a, b, **k)['status'], 'SCORED_COUNTERFACTUAL')
        with self.assertRaisesRegex(ValueError, 'capital cannot fund'):
            evaluate(c, evidence(f, c), f, a, b, account_scope=('hl','USDC','BTC'), **k)

    def test_no_fill_cost_has_original_capital_denominator(self):
        _, _, _, k = setup()
        c = RequestCounts(0, 10, 0, 0, 10, 0, True)
        out = evaluate(c, evidence(), None, None, None, account_scope=('hl','USDC','BTC'), **k)
        self.assertEqual(D(out['component_usd']), D('-.01'))
        self.assertEqual(D(out['component_per_capital_bps']), D('-.1'))
        self.assertTrue(out['path_solvency_unknown'])

    def test_mismatched_quantity_scope_ids_and_unknown_funding_fail_closed(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        for ev in (replace(evidence(f), final_filled_quantity=D('1')),
                   replace(evidence(f), fill_event_ids=('unrelated',)),
                   replace(evidence(f), venue='other'),
                   replace(evidence(f), reported_counts=RequestCounts(1, 1, 0, 0, 0, 1, True)),
                   replace(evidence(f), clock_uncertainty_ns=None, clock_bound_source=None),
                   replace(evidence(f), action_and_extra_costs_prepaid=False)):
            self.assertIsNone(evaluate(c, ev, f, a, b, account_scope=('hl','USDC','BTC'), **k)['component_usd'])

    def test_hypothetical_insolvency_is_retained_not_certified_as_valid_path(self):
        f, a, b, k = setup('-2')
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        k.update(capital='200', entry_fee_bps='0', exit_fee_bps='0')
        b = replace(b, price=D('300'))
        out = evaluate(c, evidence(f), f, a, b, account_scope=('hl','USDC','BTC'), **k)
        self.assertEqual(out['status'], 'INSOLVENT_COUNTERFACTUAL')
        self.assertEqual(D(out['component_usd']), D('-400'))
        self.assertEqual(D(out['counterfactual_end_capital_usd']), D('-200'))
        self.assertTrue(out['path_solvency_unknown'])

    def test_delayed_fill_receipt_does_not_allow_post_fill_quote(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        f = replace(f, clock=clock(NS+40_000_000))
        a = replace(a, clock=FrameClock(a.clock.utc_ns, A.mono_ns+NS+10_000_000))
        ev = evidence(f, c, occurred_ns=U+1_500_000_000, clock=clock(1_500_000_000))
        with self.assertRaisesRegex(ValueError, 'after economic fill'):
            evaluate(c, ev, f, a, b, account_scope=('hl','USDC','BTC'), **k)

    def test_unfilled_prepaid_cost_can_exhaust_capital_without_hiding_loss(self):
        _, _, _, k = setup()
        c = RequestCounts(0, 10, 0, 0, 10, 0, True)
        out = evaluate(c, evidence(None, c), None, None, None,
                       account_scope=('hl','USDC','BTC'), **{**k,'capital':'.01'})
        self.assertEqual(out['status'], 'INSOLVENT_COUNTERFACTUAL')
        self.assertEqual(D(out['component_usd']), D('-.01'))
        self.assertEqual(D(out['component_per_capital_bps']), D('-10000'))

    def test_source_event_cannot_follow_its_first_receipt_under_clock_bound(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        inconsistent = replace(a, clock=FrameClock(a.clock.utc_ns, A.mono_ns+980_000_000))
        self.assertEqual(old_evaluate(c, f, inconsistent, b, **k)['status'], 'SCORED_COUNTERFACTUAL')
        with self.assertRaisesRegex(ValueError, 'uncertainty bound'):
            evaluate(c, evidence(f, c), f, inconsistent, b, account_scope=('hl','USDC','BTC'), **k)

    def test_unknown_orders_keep_only_timestamped_assumed_cost_components(self):
        _, _, _, k = setup()
        c = RequestCounts(2, 1, 1, 0, 3, 0, False)
        ev = evidence(None, c, order_id='one-of-two')
        out = evaluate(c, ev, None, None, None, account_scope=('hl','USDC','BTC'), **{**k,'extra_cost_usd':'3'})
        self.assertIsNone(out['component_usd'])
        self.assertEqual(D(out['assumed_prepaid_action_cost_usd']), D('.003'))
        self.assertEqual(D(out['assumed_prepaid_extra_cost_usd']), D('3'))
        no_bound = replace(ev, clock_uncertainty_ns=None, clock_bound_source=None)
        out = evaluate(c, no_bound, None, None, None, account_scope=('hl','USDC','BTC'), **{**k,'extra_cost_usd':'3'})
        self.assertIsNone(out['component_usd'])
        self.assertEqual(D(out['assumed_prepaid_action_cost_usd']), D('.003'))
        self.assertEqual(D(out['assumed_prepaid_extra_cost_usd']), D('3'))


if __name__ == '__main__':
    unittest.main()
