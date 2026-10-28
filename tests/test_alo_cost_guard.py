from dataclasses import replace
from decimal import Decimal as D
import unittest

from lab.paper_account import PaperEvent
from lab.stream_quotes import FrameClock, ReferencePrice, NS
from scripts.alo_cost_guard import RequestCounts, evaluate

U = 1_790_000_000 * NS
A = FrameClock(U, 10 * NS)


def clock(s):
    return FrameClock(U + s, A.mono_ns + s)


def setup(q='2'):
    fill = PaperEvent('fixture', 'fill', 'hl', 'USDC', 'BTC', U + NS,
                      clock(NS), 'invented receipt', quantity=D(q), price=D('100'), fee=None)
    before = ReferencePrice('hl', 'BTC', clock(NS-1), U+NS-1, D('100.1'), 'validated_bbo_mid')
    later = ReferencePrice('hl', 'BTC', clock(2*NS), U+2*NS, D('100.2'), 'validated_bbo_mid')
    kw = dict(anchor=A, asof=clock(2*NS).mono_ns, horizon_ns=NS, max_age_ns=10,
              max_lag_ns=10, capital='1000', entry_fee_bps='1', exit_fee_bps='1',
              paid_action_usd='.001', extra_cost_usd='0', multiple=1)
    return fill, before, later, kw


class AloGuardTests(unittest.TestCase):
    def test_markout_decomposes_once_and_matches_paper_cash(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 9, 0, 0, 10, 1, True)
        out = evaluate(c, f, a, b, **k)
        self.assertEqual(D(out['spread_component_usd']), D('.2'))
        self.assertEqual(D(out['midpoint_move_usd']), D('.2'))
        self.assertEqual(D(out['markout_usd']), D('.4'))
        self.assertEqual(D(out['entry_fee_usd']), D('.02'))
        self.assertEqual(D(out['exit_fee_usd']), D('.02004'))
        self.assertEqual(D(out['component_usd']), D('.34996'))

    def test_short_and_partial_quantity_have_signed_markout(self):
        f, a, b, k = setup('-.5')
        out = evaluate(RequestCounts(1, 1, 0, 0, 0, 1, True), f, a, b, **k)
        self.assertEqual(D(out['markout_usd']), D('-.1'))
        self.assertEqual(D(out['spread_component_usd']), D('-.05'))

    def test_unresolved_order_is_unknown_not_zero(self):
        f, a, b, k = setup()
        for c in (RequestCounts(1, 1, 1, 0, 0, 1, True),
                  RequestCounts(1, 1, 0, 0, 0, 1, False)):
            out = evaluate(c, f, a, b, **k)
            self.assertEqual(out['status'], 'UNKNOWN_OPEN_ORDERS')
            self.assertIsNone(out['component_usd'])

    def test_reconciled_inactivity_includes_paid_actions(self):
        _, _, _, k = setup()
        out = evaluate(RequestCounts(0, 10, 0, 0, 10, 0, True), None, None, None, **k)
        self.assertEqual(out['status'], 'NO_REPORTED_FILL')
        self.assertEqual(D(out['component_usd']), D('-.01'))
        self.assertIsNone(out['cost_per_filled_notional_bps'])

    def test_lookahead_stale_unknown_and_wrong_instrument_fail_closed(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 0, 0, 0, 0, 1, True)
        invalid = [(replace(a, clock=clock(NS+1)), b, k),
                   (replace(a, source_time_ns=U+NS-11), b, k),
                   (a, replace(b, source_time_ns=U+2*NS+11, clock=clock(2*NS+11)), {**k,'asof':clock(2*NS+11).mono_ns}),
                   (a, replace(b, symbol='ETH'), k),
                   (a, replace(b, source_role='last_trade'), k),
                   (a, b, {**k,'asof':clock(2*NS-1).mono_ns})]
        for x, y, kw in invalid:
            with self.assertRaises(ValueError):
                evaluate(c, f, x, y, **kw)

    def test_entry_capital_and_all_costs_stress_together(self):
        f, a, b, k = setup()
        c = RequestCounts(1, 9, 0, 0, 10, 1, True)
        base = evaluate(c, f, a, b, **k)
        stress = evaluate(c, f, a, b, **{**k, 'multiple': 3})
        self.assertEqual(D(stress['markout_usd']), D(base['markout_usd']))
        self.assertEqual(D(stress['action_cost_usd']), 3*D(base['action_cost_usd']))
        self.assertEqual(D(stress['entry_fee_usd']), 3*D(base['entry_fee_usd']))
        with self.assertRaises(ValueError):
            evaluate(c, f, a, b, **{**k, 'capital': '200'})

    def test_malformed_counts_or_missing_fill_are_rejected(self):
        f, a, b, k = setup()
        with self.assertRaises(ValueError):
            RequestCounts(1, 0, 0, 0, 2, 1, True)
        with self.assertRaises(ValueError):
            evaluate(RequestCounts(1, 0, 0, 0, 0, 1, True), None, None, None, **k)
        with self.assertRaises(ValueError):
            evaluate(RequestCounts(1, 0, 0, 0, 0, 0, True), f, a, b, **k)


if __name__ == '__main__':
    unittest.main()
