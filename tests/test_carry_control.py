from dataclasses import replace
from fractions import Fraction as F
import unittest

from lab.carry_control import Book, Controller, Model, ModelLimit, Node, Outcome, rational


def book(reference=100, *, spread=1, fee='0', session='open'):
    reference, spread = F(reference), F(spread)
    return Book(reference, reference - spread/2, reference + spread/2, fee, session,
                buy_capacity_base=10, sell_capacity_base=10, minimum_base=0, minimum_notional=0)


def model(*, funding=(0, 4), capital=(500, 500), terminal_session='open', fee='0', spread=1):
    a = Node('a', 0, (book(spread=spread, fee=fee), book(spread=spread, fee=fee)), (0, 0), ((1, 'b'),))
    b = Node('b', 1, (book(spread=spread, fee=fee, session=terminal_session), book(spread=spread, fee=fee)), funding, ())
    return Model('a', (a, b), 1, (-1, 0, 1), '1', capital, '0.5', '0', 'invented_scenario_fixture')


class CarryControlTests(unittest.TestCase):
    def test_terminal_cost_and_old_inventory_cashflow(self):
        m = model()
        dynamic = Controller(m).solve()
        self.assertEqual(dynamic.action, 1)
        self.assertEqual(dynamic.terminal_equity, 1002)  #4funding less1entry less1exit.
        zero = Controller(model(funding=(0, 0))).solve()
        self.assertEqual((zero.action, zero.terminal_equity), (0, 1000))
        self.assertEqual(Controller(model(funding=(0, 0)), mode='hold_long').solve().terminal_equity, 998)

    def test_stressed_fill_and_fee_notional_are_counted_once(self):
        m = model(fee='0.001')
        expected = (F('0.6005'), F('1.202'), F('1.8045'))
        for k, cost in enumerate(expected, 1):
            c = Controller(m, cost_multiple=k)
            self.assertEqual(c.execution(m.nodes[0].books[0], F(1))[1], cost)
        self.assertEqual(Controller(m).solve().terminal_equity, F('1001.6'))

    def test_fee_free_spread_is_not_free_execution(self):
        c = Controller(model(funding=(0, 0)))
        self.assertEqual(c.execution(c.model.nodes[0].books[0], F(1))[1], F(1, 2))
        self.assertEqual(c.execution(c.model.nodes[0].books[0], F(-1))[1], F(1, 2))

    def test_capital_cannot_be_pooled_between_venues(self):
        m = model(capital=(50, 950))
        self.assertEqual(Controller(m).solve().action, 0)
        self.assertEqual(Controller(m, mode='hold_long').solve().state, 'INFEASIBLE')
        self.assertEqual(Controller(model(capital=(500, 500))).solve().action, 1)

    def test_closing_cannot_hide_incoming_margin_or_loss_breach(self):
        c = Controller(model(capital=(150, 850)))
        node = c.model.nodes[1]
        self.assertEqual(c.trade(node, 1, 0, (F(99), F(1000)))[0], 'INFEASIBLE')
        self.assertEqual(c.trade(node, 0, 0, (F(1), F(1000)))[0], 'INFEASIBLE')

    def test_unknown_funding_cannot_turn_into_flat_optimum_or_zero_return(self):
        m = model(funding=(None, 4))
        result = Controller(m).assessment()
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertIsNone(result['model_action_units'])
        self.assertIsNone(result['conditional_expected_net'])
        self.assertEqual(Controller(m, mode='cash').solve().terminal_equity, 1000)
        self.assertFalse(result['actual_order_allowed'])

    def test_closed_terminal_is_not_a_fabricated_fill(self):
        m = model(terminal_session='closed')
        self.assertEqual(Controller(m).solve().action, 0)
        self.assertEqual(Controller(m, mode='hold_long').solve().state, 'INFEASIBLE')
        hold = Controller(m, mode='hold_long')
        self.assertEqual(hold.decision(m.root, 0, m.initial_capital)['model_action_units'], 1)

    def test_missing_cost_or_session_does_not_pass(self):
        for missing in ('fee', 'session'):
            m = model()
            root = m.nodes[0]
            bad = replace(root.books[0], fee_fraction=None) if missing == 'fee' else replace(root.books[0], session='unknown')
            changed = replace(m, nodes=(replace(root, books=(bad, root.books[1])), m.nodes[1]))
            self.assertEqual(Controller(changed).solve().state, 'UNKNOWN')

    def test_closed_loop_continuation_can_hold_through_a_known_trading_closure(self):
        root = Node('a', 0, (book(), book()), (0, 0), ((1, 'b'),))
        middle = Node('b', 1, (book(session='closed'), book(session='closed')), (0, 0), ((1, 'c'),))
        end = Node('c', 2, (book(), book()), (0, 4), ())
        m = Model('a', (root, middle, end), 2, (-1, 0, 1), '1', (500, 500), '0.5', '0', 'invented_scenario_fixture')
        self.assertEqual(Controller(m).solve().terminal_equity, 1002)
        self.assertEqual(Controller(m, mode='myopic').solve().terminal_equity, 1000)

    def test_partial_action_is_available_without_leverage(self):
        m = model(capital=(150, 850))
        m = replace(m, inventory_units=(-2, -1, 0, 1, 2))
        self.assertEqual(Controller(m).solve().action, 1)  #2units cannot fit in first account.
        hold = Controller(replace(m, initial_capital=(500, 500)), mode='hold_long')
        self.assertEqual(hold.hold_target, 2)  #Same maximum admissible exposure, not a smaller control.

    def test_capacity_and_minimum_order_rules_are_not_infinite_or_assumed_zero(self):
        c = Controller(model())
        b = c.model.nodes[0].books[0]
        self.assertEqual(c.execution(replace(b, buy_capacity_base='0.5'), F(1))[0], 'INFEASIBLE')
        self.assertEqual(c.execution(replace(b, sell_capacity_base=None), F(-1))[0], 'UNKNOWN')
        self.assertEqual(c.execution(replace(b, minimum_notional=101), F(1))[0], 'INFEASIBLE')
        self.assertEqual(c.execution(replace(b, minimum_base=2), F(1))[0], 'INFEASIBLE')

    def test_tree_identity_complete_probabilities_and_exact_types(self):
        m = model()
        for value in (True, 0.5, None, 'NaN'):
            with self.assertRaises(ValueError):
                rational(value)
        with self.assertRaises(ValueError):
            replace(m.nodes[0], children=(('0.999', 'b'),))
        with self.assertRaises(ValueError):
            replace(m, nodes=(m.nodes[0], replace(m.nodes[1], stage=2)))
        with self.assertRaises(ValueError):
            Controller(m).solve(old_q=True)
        with self.assertRaises(ValueError):
            Book(None, None, None, '0', 'unknown')

    def test_bounded_compute_never_becomes_success(self):
        c = Controller(model())
        c.evaluated_states = 20000
        with self.assertRaises(ModelLimit):
            c.solve()
        incomplete = Controller.choose({0:Outcome('VALUE', F(1000), 0), 1:Outcome('UNKNOWN', None, None)}, 0)
        self.assertEqual(incomplete.state, 'UNKNOWN')

    def test_shared_root_action_has_no_child_foresight_and_rare_risk_is_not_averaged(self):
        root = Node('root', 0, (book(spread=0), book(spread=0)), (0, 0),
                    (('999999/1000000', 'usual'), ('1/1000000', 'rare')))
        usual = Node('usual', 1, (book(spread=0), book(spread=0)), (0, 10), ())
        rare = Node('rare', 1, (book(120, spread=0), book(120, spread=0)), (0, 10), ())
        m = Model('root', (root, usual, rare), 1, (-1, 0, 1), '1', (110, 110), '0.5', '0.01',
                  'invented_scenario_fixture')
        self.assertEqual(Controller(m).solve().action, 0)
        symmetric = replace(m, initial_capital=(500, 500), nodes=(
            replace(root, children=(('1/2', 'usual'), ('1/2', 'rare'))),
            replace(usual, funding_quote_per_base=(0, 10)),
            replace(rare, books=(book(spread=0), book(spread=0)), funding_quote_per_base=(0, -10))))
        self.assertEqual(Controller(symmetric).solve().terminal_equity, 1000)


if __name__ == '__main__':
    unittest.main()
