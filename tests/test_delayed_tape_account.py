import unittest
from decimal import Decimal as D

from scripts.run_delayed_tape_account import normalized_terms


class NormalizedTradeAccountingTests(unittest.TestCase):
    def test_exit_crossing_is_in_exit_notional_units_for_long_and_short(self):
        long=normalized_terms({'side':'1','gross':'10','c_e':'1','c_x':'2'},1)
        short=normalized_terms({'side':'-1','gross':'10','c_e':'1','c_x':'2'},1)
        self.assertEqual(long['exact_pnl'],D('.6998'))
        self.assertEqual(short['exact_pnl'],D('.7002'))
        self.assertEqual(long['old_proxy_bp'],D(7))
        self.assertEqual(long['entry_notional'],D('1000.1'))
        self.assertEqual(short['entry_notional'],D('999.9'))

    def test_fixed_costs_and_no_double_spread_or_unverified_fee(self):
        for k in (1,2,3):
            v=normalized_terms({'side':'1','gross':'0','c_e':'.4','c_x':'.4'},k)
            self.assertEqual(v['exact_pnl'],-D('.08')*k)
            self.assertEqual(v['fee_assumption'],0)
            self.assertTrue(v['all_absolute_prices_and_base_units_normalized'])

    def test_invalid_return_sign_cost_or_price_domain_fails(self):
        for row in ({'side':'0','gross':'10','c_e':'1','c_x':'2'},
                    {'side':'1','gross':'-10000','c_e':'1','c_x':'2'},
                    {'side':'1','gross':'0','c_e':'-1','c_x':'2'},
                    {'side':'1','gross':'NaN','c_e':'1','c_x':'2'}):
            with self.assertRaises(ValueError):normalized_terms(row,1)


if __name__=='__main__':unittest.main()
