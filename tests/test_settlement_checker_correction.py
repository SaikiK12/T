import ast
import unittest

from scripts.check_settlement_account_v2 import expected_blocked, corrected_namespace, ORIGINAL


class SettlementCheckerCorrectionTests(unittest.TestCase):
    def inputs(self, price, multiple, capital):
        cell = {'entry_quantities': {'mexc': '-10', 'lighter': '10'}, 'cost_multiple': multiple,
                'constructed_entry': {'s_fill': price, 'h_fill': '101'}}
        case = {'s_capital': str(capital)}
        config = {'entry_mid': '100', 'fees_bp': {'mexc': '3', 'lighter': '0'}, 'initial_per_venue': '5000'}
        return cell, case, config

    def test_required_capital_uses_stressed_price_and_fee_of_fixed_quantity(self):
        self.assertTrue(expected_blocked(*self.inputs('99', 1, '990')))
        self.assertFalse(expected_blocked(*self.inputs('99', 2, '990')))
        self.assertTrue(expected_blocked(*self.inputs('101', 2, '990')))

    def test_one_literal_expression_only_is_replaced_without_editing_original(self):
        before = ORIGINAL.read_bytes()
        namespace = corrected_namespace(before.decode())
        self.assertTrue(callable(namespace['main']))
        self.assertEqual(ORIGINAL.read_bytes(), before)
        source = "def result(cell,case,config):\n blocked=case['id']=='separate_capital_shortfall'\n return blocked\n"
        patched = corrected_namespace(source)
        self.assertFalse(patched['result'](*self.inputs('99', 2, '990')))

    def test_unknown_duplicate_or_missing_expression_fails_closed(self):
        for source in ('blocked = True', 'x = 1',
                       "blocked=case['id']=='separate_capital_shortfall'\nblocked=case['id']=='separate_capital_shortfall'"):
            with self.assertRaises(ValueError):
                corrected_namespace(source)


if __name__ == '__main__':
    unittest.main()
