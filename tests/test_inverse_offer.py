from fractions import Fraction as F
import unittest

from lab.inverse_offer import coverage, prefund, equity_coin, terminal_hurdle


class InverseOfferTests(unittest.TestCase):
    def test_fee_breaks_the_exact_unreserved_one_times_proof(self):
        c = coverage('1', '1', '.001')
        self.assertFalse(c['all_positive_marks_1x_model_coverage'])
        self.assertEqual(c['residual_coin_delta'], -F(1, 1000))
        self.assertLess(equity_coin(100, 1, 1, '.001', 200000), 0)
        self.assertIsNone(c['actual_liquidation_immunity'])
        self.assertIsNone(coverage(1, 1, None)['residual_coin_delta'])

    def test_same_net_collateral_requires_different_spot_fee_asset_debits(self):
        quote = prefund(1, '.001', '.01', fee_asset='quote')
        base = prefund(1, '.001', '.01', fee_asset='base')
        self.assertEqual(quote['gross_spot_base'], F('1.001'))
        self.assertEqual(base['gross_spot_base'], F('1.001')/F('.99'))
        self.assertEqual(quote['net_collateral_coin'], base['net_collateral_coin'])
        self.assertEqual(base['coverage']['residual_coin_delta'], 0)
        rounded = prefund(1, '.001', '.01', fee_asset='base', base_step='.1')
        self.assertEqual(rounded['gross_spot_base'], F('1.1'))
        self.assertGreaterEqual(rounded['coverage']['residual_coin_delta'], 0)
        self.assertIsNone(prefund(1, '.001', '.01', fee_asset=None)['gross_spot_base'])

    def hurdle(self, **overrides):
        params = dict(face_usd=110, hedge_coin=1, initial_coin=1, entry_fee_coin=0,
            delivery_fee_rate=0, spot_exit_rate=0, initial_spend_quote=100,
            total_capital_quote=1000, cash_benchmark_factor=1, idle_cash_factor=1,
            other_exit_cost_quote=0)
        return terminal_hurdle(**(params|overrides))

    def test_full_capital_benchmark_and_idle_interest_are_not_omitted(self):
        self.assertEqual(self.hurdle()['minimum_exit_ratio'], F(10, 11))
        # Whole1000 earns5percent in the control, only900 remains idle at0.
        r = self.hurdle(cash_benchmark_factor='1.05', exit_ratio=1)
        self.assertEqual(r['minimum_exit_ratio'], F(15, 11))
        self.assertEqual(r['conditional_net_vs_cash_benchmark_quote'], -40)
        both = self.hurdle(cash_benchmark_factor='1.05', idle_cash_factor='1.05')
        self.assertEqual(both['minimum_exit_ratio'], F(21, 22))

    def test_missing_future_price_is_only_cancellable_at_exact_zero_residual(self):
        self.assertIsNotNone(self.hurdle()['minimum_exit_ratio'])
        self.assertIsNone(self.hurdle(initial_coin='1.01')['minimum_exit_ratio'])
        self.assertIsNone(self.hurdle(initial_coin='.99')['minimum_exit_ratio'])
        self.assertIsNotNone(self.hurdle(initial_coin='1.01', delivery_price=100)['minimum_exit_ratio'])
        self.assertIsNone(self.hurdle(other_exit_cost_quote=None)['minimum_exit_ratio'])
        self.assertIsNone(self.hurdle()['conditional_total_terminal_quote'])

    def test_unknown_fee_or_sale_ratio_never_becomes_profit_or_activation(self):
        for field in ('entry_fee_coin', 'delivery_fee_rate', 'spot_exit_rate'):
            r = self.hurdle(**{field: None})
            self.assertIsNone(r['minimum_exit_ratio'])
            self.assertIsNone(r['actual_expected_net_quote'])
            self.assertFalse(r['actual_order_allowed'])
        self.assertIsNone(self.hurdle()['conditional_net_vs_cash_benchmark_quote'])

    def test_strictly_matching_cash_hurdle_has_zero_excess_even_after_costs(self):
        r = self.hurdle(delivery_fee_rate='.0025', spot_exit_rate='.001', delivery_price=100)
        exact = self.hurdle(delivery_fee_rate='.0025', spot_exit_rate='.001', delivery_price=100,
            exit_ratio=r['minimum_exit_ratio'])
        self.assertEqual(exact['conditional_net_vs_cash_benchmark_quote'], 0)
        with self.assertRaises(ValueError): self.hurdle(initial_spend_quote=1001)
