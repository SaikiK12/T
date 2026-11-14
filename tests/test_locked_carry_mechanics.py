"""Independent invented inverse-carry quantities, fee assets and payoff bounds."""
from dataclasses import replace
from fractions import Fraction as F
import unittest

from lab.inverse_cash import InverseContract, unwire
from lab.locked_carry import SpotContract, CarryFees, plan_carry, evaluate_carry


SPOT = SpotContract('TOY_QUOTE', 'TOY', 'QUOTE', F(1, 100), F(1, 100), 0, 'invented metadata')
FUTURE = InverseContract('TOY-DATED', 'TOY', 10, 10, 1_900_000_000_000_000_000, 'invented metadata')
FREE = CarryFees(0, 'base_received', 0, 0, 0, 'quote_received', 'invented explicit fees')


def plan(**changes):
    values = dict(spot=SPOT, future=FUTURE, fees=FREE,
                  spot_asks=[('100', '100')], future_bids=[('100', '10000')], budget_quote='100')
    return plan_carry(**{**values, **changes})


class LockedCarryTests(unittest.TestCase):
    def test_zero_residual_is_exactly_price_independent(self):
        p = plan()
        self.assertEqual((p.spot_order_base, p.face_usd, p.inverse_entry_coin_basis), (1, 100, 1))
        for price in (1, 50, 100, 1000):
            r = evaluate_carry(p, delivery_price=str(price), exit_ratio=1, exit_ratio_floor=1,
                               delivery_price_ceiling=1000)
            self.assertTrue(r['continuous_payoff_price_independent'])
            self.assertEqual(unwire(r['terminal_proceeds_quote']), 100)
            self.assertEqual(unwire(r['continuous_lower_reference_quote']), 100)
            self.assertGreaterEqual(unwire(r['terminal_proceeds_quote']), unwire(r['conditional_lower_proceeds_quote']))

    def test_depth_and_fees_determine_maximal_grid_hedge_not_best_bid(self):
        p = plan(fees=replace(FREE, future_entry=F(1, 100)),
                 future_bids=[('100', '50'), ('50', '1000')])
        self.assertEqual(p.face_usd, 70)
        self.assertEqual(p.inverse_entry_coin_basis, F(9, 10))
        self.assertEqual(p.next_face_coin_requirement, F(1133, 1000))
        rows = [evaluate_carry(p, cost_multiple=k, delivery_price=300, exit_ratio=1, exit_ratio_floor=1,
                               delivery_price_ceiling=300)
                for k in (1, 2, 3)]
        self.assertEqual([unwire(r['residual_coin']) for r in rows], [F(91, 1000), F(82, 1000), F(73, 1000)])
        self.assertTrue(all(unwire(r['fixed_face_usd']) == 70 for r in rows))
        self.assertTrue(all(unwire(r['terminal_proceeds_quote']) >= unwire(r['conditional_lower_proceeds_quote']) for r in rows))

    def test_delivery_fee_uses_delivery_face_value_not_entry_coin_basis(self):
        p = plan(fees=replace(FREE, delivery=F(1, 1000)))
        for price in (10, 100, 1000):
            r = evaluate_carry(p, delivery_price=str(price), exit_ratio=1)
            self.assertEqual(unwire(r['continuous_terminal_reference_quote']), F(999, 10))

    def test_spot_quote_fees_leave_cash_in_lower_tiers_without_resizing(self):
        p = plan(fees=replace(FREE, spot_buy=F(1, 100), spot_buy_basis='quote_in_addition'))
        self.assertEqual(p.spot_order_base, F(97, 100))
        self.assertEqual(p.spot_order_quote, 97)
        self.assertEqual(p.face_usd, 90)
        rows = [evaluate_carry(p, cost_multiple=k) for k in (1, 2, 3)]
        self.assertEqual([unwire(r['leftover_quote']) for r in rows], [F(203, 100), F(106, 100), F(9, 100)])
        self.assertEqual({str(r['fixed_spot_order_base']) for r in rows}, {str(rows[0]['fixed_spot_order_base'])})

    def test_spot_buy_coin_fee_changes_coin_inventory_not_quote_cash(self):
        p = plan(fees=replace(FREE, spot_buy=F(1, 100)))
        self.assertEqual(p.spot_order_base, 1)
        self.assertEqual(p.face_usd, 90)
        self.assertEqual(unwire(evaluate_carry(p, cost_multiple=3)['residual_coin']), F(7, 100))

    def test_spot_sell_fee_assets_use_distinct_cash_formulas(self):
        quote_fee = plan(fees=replace(FREE, spot_sell=F(1, 100)))
        coin_fee = plan(fees=replace(FREE, spot_sell=F(1, 100), spot_sell_basis='base_in_addition'))
        q = evaluate_carry(quote_fee, delivery_price=100, exit_ratio=1)
        b = evaluate_carry(coin_fee, delivery_price=100, exit_ratio=1)
        self.assertEqual(unwire(q['terminal_proceeds_quote']), 99)
        self.assertEqual(unwire(b['continuous_terminal_reference_quote']), F(10000, 101))
        self.assertEqual(unwire(b['terminal_proceeds_quote']), 99)
        self.assertEqual(unwire(b['unsold_dust_coin']), F(1, 10000))

    def test_exit_conversion_is_not_inferred_from_entry_or_delivery(self):
        p = plan()
        r = evaluate_carry(p, delivery_price=100)
        self.assertIsNone(r['terminal_proceeds_quote'])
        self.assertIsNone(r['conditional_lower_proceeds_quote'])
        breach = evaluate_carry(p, delivery_price=100, exit_ratio=F(9, 10), exit_ratio_floor=F(99, 100),
                                delivery_price_ceiling=100)
        self.assertFalse(breach['observed_exit_ratio_satisfies_floor'])
        self.assertLess(unwire(breach['terminal_proceeds_quote']), unwire(breach['conditional_lower_proceeds_quote']))
        self.assertFalse(breach['actual_order_allowed'])

    def test_terminal_minimum_and_dust_prevent_continuous_cash_guarantee(self):
        p = plan()
        r = evaluate_carry(p, delivery_price=20000, exit_ratio=1, exit_ratio_floor=1)
        self.assertEqual(unwire(r['continuous_terminal_reference_quote']), 100)
        self.assertEqual(unwire(r['terminal_proceeds_quote']), 0)
        self.assertEqual(unwire(r['unsold_dust_coin']), F(1, 200))
        self.assertIsNone(r['terminal_return'])
        self.assertFalse(r['exit_order_meets_declared_minima'])
        self.assertIsNone(r['conditional_lower_proceeds_quote'])
        r = evaluate_carry(p, exit_ratio_floor=1, delivery_price_ceiling=20000)
        self.assertIn('exit_base_minimum_not_proven_over_price_range', r['lower_bound_missing'])
        minimum_quote = plan(spot=replace(SPOT, minimum_quote=99))
        r = evaluate_carry(minimum_quote, exit_ratio_floor=1, delivery_price_ceiling=1000)
        self.assertIn('exit_quote_minimum_not_proven_over_price_range', r['lower_bound_missing'])

    def test_spot_and_inverse_lots_and_optional_face_cap(self):
        p = plan(spot=replace(SPOT, step_base=1, minimum_base=1),
                 spot_asks=[('3', '100')], future_bids=[('4', '1000')],
                 future=replace(FUTURE, face_step_usd=1, minimum_face_usd=1), budget_quote=10)
        self.assertEqual((p.spot_order_base, p.spot_order_quote, p.face_usd), (3, 9, 12))
        self.assertEqual(unwire(evaluate_carry(p)['leftover_quote']), 1)
        self.assertEqual(plan(maximum_face_usd=35).face_usd, 30)

    def test_unknown_fees_wrong_units_thin_depth_and_invalid_tiers_fail_closed(self):
        with self.assertRaises(ValueError): replace(FREE, future_entry=None)
        with self.assertRaises(ValueError): replace(FREE, spot_buy_basis='unknown_asset')
        for changes in ({'spot_asks': [('100', '.01')]}, {'future_bids': [('100', '5')]},
                        {'future': replace(FUTURE, coin='OTHER')},
                        {'future_bids': [('100', 50), ('101', 1000)]},
                        {'spot_asks': [()]}, {'fees': replace(FREE, spot_sell=F(1, 2))}):
            with self.assertRaises(ValueError): plan(**changes)
        p = plan(sizing_cost_multiple=1)
        with self.assertRaises(ValueError): evaluate_carry(p, cost_multiple=2)
        with self.assertRaises(ValueError): evaluate_carry(p, cost_multiple=True)


if __name__ == '__main__': unittest.main()
