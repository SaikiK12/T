from fractions import Fraction as F
import unittest

from scripts.check_current_inverse import Checks, check_guard, check_hurdle


class CurrentInverseOracleTests(unittest.TestCase):
    def test_oracle_rejects_false_liquidation_guarantee_even_with_correct_cash(self):
        guard = {'residual_coin_delta': '-.001', 'minimum_required_initial_coin': '1.001',
            'all_positive_marks_1x_model_coverage': False, 'actual_liquidation_immunity': None,
            'actual_order_allowed': False}
        self.assertEqual(check_guard(Checks(), guard, F(1), F(1), F('.001')), F('-.001'))
        guard['actual_liquidation_immunity'] = True
        with self.assertRaises(AssertionError):check_guard(Checks(), guard, F(1), F(1), F('.001'))

    def test_oracle_rejects_cash_target_on_only_a_fraction_of_capital(self):
        h = {'unit_terminal_quote_before_ratio': '110', 'same_initial_capital_quote': '1000',
            'idle_cash_quote': '900', 'minimum_exit_ratio': str(F(10, 11)),
            'conditional_total_terminal_quote': None, 'conditional_net_vs_cash_benchmark_quote': None,
            'actual_expected_net_quote': None}
        check_hurdle(Checks(), h, F(110), F(0), F(100), F(0), F(0), F(100), F(1000))
        h['idle_cash_quote'] = '1000'
        with self.assertRaises(AssertionError):
            check_hurdle(Checks(), h, F(110), F(0), F(100), F(0), F(0), F(100), F(1000))
