from fractions import Fraction as F
import unittest

from lab.continuation_paper import model_mapping
from scripts.check_continuation_control import enumerate_best, one_step
from tests.test_carry_control import model


class ContinuationOracleTests(unittest.TestCase):
    def test_literal_enumeration_charges_both_legs_and_terminal_exit(self):
        m = model_mapping(model(funding=(0, 6)))
        #At the fixed2x spread,6funding minus4crossing =2.
        state, value, q, count = enumerate_best(m)
        self.assertEqual((state, value, q, count), ('VALUE', F(1002), 1, 3))

    def test_unknown_is_not_pruned_and_capital_is_not_pooled(self):
        self.assertEqual(enumerate_best(model_mapping(model(funding=(None, 6))))[0], 'UNKNOWN')
        self.assertEqual(enumerate_best(model_mapping(model(capital=(50, 950))))[1:3], (F(1000), 0))

    def test_one_step_uses_same_frozen_cost_contract(self):
        m = model_mapping(model())
        self.assertEqual(one_step(m, m['nodes'][0], 0, (F(500), F(500))), ('VALUE', 0))


if __name__ == '__main__':
    unittest.main()
