"""Literal quote-cash examples; no market outcomes or strategy statistics."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from lab.funding_notional import FundingTerm, audit_notional
from scripts.audit_funding_notional import demo


def term(**changes):
    values = dict(venue='invented', symbol='FIXTURE', asset='USDT', event_id='one', funding_ns=2,
                  rate='-0.003', rate_unit='fraction', rate_stage='settled', settlement_price='200',
                  value_basis='settlement_mark', source_identity='invented fixture',
                  eligible=True, payment_kind='regular')
    return FundingTerm(**{**values, **changes})


def audit(**changes):
    values = dict(venue='invented', symbol='FIXTURE', asset='USDT', quantity_base='1',
                  entry_price='100', exit_price='100', entry_ns=1, exit_ns=3, events=[term()],
                  round_trip_cost_quote='0.4', expected_value_basis='settlement_mark', schedule_complete=True)
    return audit_notional(**{**values, **changes})


class FundingNotionalTests(unittest.TestCase):
    def test_rate_sum_and_fixed_quantity_can_have_opposite_net_signs(self):
        x = demo()
        self.assertEqual(D(x['rate_sum_funding_quote']), D('.3'))
        self.assertEqual(D(x['fixed_quantity_funding_quote']), D('.6'))
        self.assertEqual(D(x['tiers'][0]['rate_sum_net_bp']), D(-10))
        self.assertEqual(D(x['tiers'][0]['fixed_quantity_net_bp']), D(20))
        self.assertEqual([D(t['fixed_quantity_net_bp']) for t in x['tiers']], [D(20), D(-20), D(-60)])
        self.assertFalse(x['actual_order_allowed']); self.assertFalse(x['real_account_credit_verified'])
        self.assertFalse(x['model_new_entries_allowed'])

    def test_approximation_can_also_overstate_funding(self):
        x = audit(events=[term(settlement_price='50')])
        self.assertEqual(D(x['fixed_quantity_funding_quote']), D('.15'))
        self.assertEqual(D(x['funding_difference_quote']), D('-.15'))
        self.assertEqual(D(x['tiers'][0]['fixed_quantity_net_bp']), D(-25))

    def test_short_direction_and_explicit_percentage_units(self):
        x = audit(quantity_base='-1', events=[term(rate='.3', rate_unit='percent')])
        self.assertEqual(D(x['fixed_quantity_funding_quote']), D('.6'))
        paid = audit(events=[term(rate='.003')])
        self.assertEqual(D(paid['fixed_quantity_funding_quote']), D('-.6'))

    def test_constant_entry_value_matches_rate_sum_and_quantity_scales_cash(self):
        x = audit(quantity_base='2', exit_price='105', events=[term(settlement_price='100')])
        self.assertEqual(D(x['gross_price_pnl_quote']), D(10))
        self.assertEqual(D(x['fixed_quantity_funding_quote']), D('.6'))
        self.assertEqual(x['fixed_quantity_funding_quote'], x['rate_sum_funding_quote'])

    def test_missing_value_and_wrong_basis_leave_cash_unknown(self):
        for e in (term(settlement_price=None), term(value_basis='bar_close')):
            x = audit(events=[e])
            self.assertEqual(x['state'], 'UNSCORED')
            self.assertIsNone(x['fixed_quantity_funding_quote'])
            self.assertIsNone(x['tiers'][0]['fixed_quantity_net_quote'])
            self.assertIsNotNone(x['rate_sum_funding_quote'])

    def test_incomplete_schedule_unknown_unit_stage_or_eligibility_never_become_zero(self):
        cases = [dict(schedule_complete=False, events=[]), dict(events=[term(rate_unit='unknown')]),
                 dict(events=[term(rate=None)]), dict(events=[term(rate_stage='estimated')]),
                 dict(events=[term(eligible=None)])]
        for changes in cases:
            x = audit(**changes)
            self.assertEqual(x['state'], 'UNSCORED')
            self.assertIsNone(x['fixed_quantity_funding_quote'])
        known_zero = audit(events=[])
        self.assertEqual(D(known_zero['fixed_quantity_funding_quote']), 0)

    def test_missing_exit_or_cost_preserves_components_without_inventing_net(self):
        for changes in (dict(exit_price=None), dict(round_trip_cost_quote=None)):
            x = audit(**changes)
            self.assertIsNotNone(x['fixed_quantity_funding_quote'])
            self.assertTrue(all(t['fixed_quantity_net_quote'] is None for t in x['tiers']))

    def test_no_duplicate_settlement_credit_or_cross_account_netting(self):
        for events in ([term(), term()], [term(), term(event_id='other')],
                       [term(venue='other')], [term(asset='USDC')], [term(symbol='OTHER')]):
            with self.assertRaises(ValueError):
                audit(events=events)
        with self.assertRaises(ValueError): audit(events=[term(funding_ns=1)])
        with self.assertRaises(ValueError): audit(events=[term(funding_ns=4)])

    def test_regular_and_special_components_keep_separate_economic_identities(self):
        x = audit(events=[term(payment_kind='Regular'),
                          term(event_id='dividend', payment_kind='Special', rate='-.01')])
        self.assertEqual(x['payment_kinds'], ['regular', 'special'])
        self.assertEqual(D(x['fixed_quantity_funding_quote']), D('2.6'))
        unknown = audit(events=[term(payment_kind='unknown')])
        self.assertIsNone(unknown['fixed_quantity_funding_quote'])

    def test_invalid_units_numbers_and_zero_quantity_are_rejected(self):
        for changes in (dict(quantity_base=0), dict(quantity_base=True), dict(entry_price='NaN'),
                        dict(round_trip_cost_quote=-1), dict(expected_value_basis='bar_close'),
                        dict(entry_ns=True), dict(schedule_complete=1)):
            with self.assertRaises(ValueError): audit(**changes)
        with self.assertRaises(ValueError): replace(term(), settlement_price='Infinity')


if __name__ == '__main__':
    unittest.main()
