from fractions import Fraction as F
import unittest

from scripts.check_current_inverse import Checks, check_hurdle as old_hurdle
from scripts.check_current_inverse_v2 import exact, check_hurdle


class CurrentInverseOracleV2Tests(unittest.TestCase):
    def row(self):
        return {'unit_terminal_quote_before_ratio': str(F(25941, 25000)),
            'same_initial_capital_quote': '10', 'idle_cash_quote': '9',
            'minimum_exit_ratio': str(F(25000, 25941)),
            'conditional_total_terminal_quote': None,
            'conditional_net_vs_cash_benchmark_quote': None, 'actual_expected_net_quote': None}

    def test_original_failure_and_exact_same_value_repair(self):
        args = (F(25941, 25000), F(0), F(1), F(0), 0, 1.0, F(10))
        with self.assertRaises(AssertionError):old_hurdle(Checks(), self.row(), *args)
        check_hurdle(Checks(), self.row(), *args)

    def test_no_tolerance_or_noninteger_float_bypass(self):
        self.assertEqual(exact(1.0), F(1))
        for value in (.1, .9637253768166224, float('nan'), float('inf')):
            with self.assertRaises(ValueError):exact(value)
        row = self.row(); row['minimum_exit_ratio'] = '1'
        with self.assertRaises(AssertionError):
            check_hurdle(Checks(), row, F(25941, 25000), 0, 1, 0, 0, 1.0, 10)
