from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from lab.carry_control import Controller
from lab.continuation_paper import build_plan, decimal, model_from_mapping, model_mapping, replay
from tests.test_carry_control import model


class ContinuationPaperTests(unittest.TestCase):
    def test_same2x_reference_actions_are_replayed_without_tier_winner_switch(self):
        m = model()  #4funding: exactly offsets2x round-trip spread.
        p = build_plan(m, 'dynamic')
        self.assertEqual(p['nodes'][m.root]['decision']['model_action_units'], 0)
        self.assertEqual(Controller(m, cost_multiple=1).solve().action, 1)
        with tempfile.TemporaryDirectory() as temporary:
            for k in (1, 2, 3):
                r = replay(m, p, k, Path(temporary) / str(k))
                self.assertEqual(r['conditional_expected_net'], '0')
                self.assertEqual(r['policy_sha256'], p['policy_sha256'])

    def test_ledger_matches_exact_expected_cash_at_all_costs(self):
        m = model(funding=(0, 6))
        p = build_plan(m, 'dynamic')
        self.assertEqual(p['nodes'][m.root]['decision']['model_action_units'], 1)
        with tempfile.TemporaryDirectory() as temporary:
            for k, expected in ((1, 4), (2, 2), (3, 0)):
                r = replay(m, p, k, Path(temporary) / str(k))
                self.assertEqual(F(r['conditional_expected_net']), expected)
                self.assertEqual(F(r['conditional_return_on_total_capital']), F(expected, 1000))
                self.assertEqual(r['paths'][0]['terminal_inventory_units'], 0)
                self.assertTrue(r['paths'][0]['journal_reopened_identical'])
                self.assertIsNone(r['executable_market_expected_net_return'])

    def test_higher_cost_risk_failure_cannot_select_a_smaller_profitable_action(self):
        m = model(funding=(0, 6), capital=(101, 899))
        p = build_plan(m, 'dynamic')
        self.assertEqual(p['nodes'][m.root]['decision']['model_action_units'], 1)
        with tempfile.TemporaryDirectory() as temporary:
            r = replay(m, p, 3, temporary)
            self.assertEqual(r['state'], 'INCONCLUSIVE')
            self.assertIsNone(r['conditional_expected_net'])
            self.assertEqual(r['paths'][0]['records'][0]['planned_action'], 1)
            self.assertIsNone(r['paths'][0]['records'][0]['executed_model_action'])
            self.assertTrue(r['paths'][0]['failures'])

    def test_unknown_policy_inactivity_is_not_a_successful_zero_expectancy(self):
        m = model(funding=(None, 6))
        p = build_plan(m, 'dynamic')
        with tempfile.TemporaryDirectory() as temporary:
            r = replay(m, p, 2, temporary)
            self.assertIsNone(r['conditional_expected_net'])
            self.assertEqual(r['paths'][0]['known_liquidation_net_component'], '0')
            self.assertEqual(r['state'], 'INCONCLUSIVE')
            self.assertFalse(r['actual_order_allowed'])

    def test_explicit_model_identity_and_exact_decimal_contract(self):
        m = model()
        self.assertEqual(model_from_mapping(model_mapping(m)), m)
        self.assertEqual(F(decimal(F(1, 8))), F(1, 8))
        with self.assertRaises(ValueError):
            decimal(F(1, 3))
        bad = model_mapping(m)
        bad['nodes'][0]['rate'] = '0.01'
        with self.assertRaises(ValueError):
            model_from_mapping(bad)
        p = build_plan(m, 'cash')
        p['nodes'][m.root]['decision']['model_action_units'] = 1
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                replay(m, p, 2, temporary)


if __name__ == '__main__':
    unittest.main()
