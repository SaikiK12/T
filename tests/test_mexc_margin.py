"""Synthetic checks for the MEXC USDT-M margin arithmetic kernel; no account/API data."""
import math
import unittest

from lab.mexc_margin import MexcLinearPosition, cross_path, cross_state, isolated_liquidation_price, isolated_state


class MexcLinearPositionTest(unittest.TestCase):
    def setUp(self):
        # MEXC guide example: 100 contracts × 0.0001 BTC at 50,000 USDT = 500 USDT.
        self.long = MexcLinearPosition("BTC_USDT", +1, 50_000, 100, 0.0001, 0.005)
        self.short = MexcLinearPosition("BTC_USDT", -1, 50_000, 100, 0.0001, 0.005)

    def test_contract_size_and_maintenance_match_published_arithmetic(self):
        self.assertAlmostEqual(self.long.base_quantity, 0.01)
        self.assertAlmostEqual(self.long.entry_notional_usdt, 500.0)
        self.assertAlmostEqual(self.long.maintenance_usdt, 2.5)

    def test_isolated_long_and_short_thresholds_match_published_10x_example(self):
        self.assertAlmostEqual(isolated_liquidation_price(self.long, 50.0), 45_250.0)
        self.assertAlmostEqual(isolated_liquidation_price(self.short, 50.0), 54_750.0)

    def test_isolated_threshold_matches_mexc_25x_example(self):
        position = MexcLinearPosition("BTC_USDT", +1, 8_000, 10_000, 0.0001, 0.005)
        # 8,000 USDT notional, 0.5% maintenance = 40 USDT; 25x margin = 320.
        self.assertAlmostEqual(position.entry_notional_usdt, 8_000)
        self.assertAlmostEqual(position.maintenance_usdt, 40)
        self.assertAlmostEqual(isolated_liquidation_price(position, 320), 7_720)

    def test_isolated_boundary_is_liquidated_and_one_tick_inside_is_not(self):
        boundary = isolated_state(self.long, 45_250, 50)
        safe = isolated_state(self.long, 45_251, 50)
        self.assertTrue(boundary.liquidated)
        self.assertAlmostEqual(boundary.equity_usdt, boundary.requirement_usdt)
        self.assertFalse(safe.liquidated)

    def test_liquidation_fee_moves_the_threshold_toward_entry(self):
        position = MexcLinearPosition("BTC_USDT", +1, 50_000, 100, 0.0001, 0.005, 0.5)
        self.assertAlmostEqual(isolated_liquidation_price(position, 50), 45_300.0)
        self.assertTrue(isolated_state(position, 45_300, 50).liquidated)

    def test_added_margin_and_settled_funding_credit_or_debit_shift_risk(self):
        base = isolated_liquidation_price(self.long, 50)
        added = isolated_liquidation_price(self.long, 50, added_margin_usdt=5)
        credited = isolated_liquidation_price(self.long, 50, cashflow_usdt=5)
        debited = isolated_liquidation_price(self.long, 50, cashflow_usdt=-5)
        self.assertLess(added, base)
        self.assertEqual(added, credited)
        self.assertGreater(debited, base)

    def test_insolvent_state_is_reported_as_breach_not_hidden(self):
        state = isolated_state(self.long, 1, 1)
        self.assertTrue(state.liquidated)
        self.assertEqual(state.margin_rate, math.inf)

    def test_invalid_position_identity_side_tier_and_amounts_fail(self):
        bad = [
            {"symbol": "BTCUSDT"}, {"symbol": "_USDT"}, {"side": 0}, {"side": True},
            {"entry_price": 0}, {"entry_price": math.nan}, {"contracts": -1},
            {"entry_price": 1e308, "contracts": 2},
            {"contract_size": 0}, {"mmr": -0.1}, {"mmr": 1},
            {"liquidation_fee_usdt": -1}, {"liquidation_fee_usdt": math.inf},
        ]
        base = dict(symbol="BTC_USDT", side=1, entry_price=100.0, contracts=1.0,
                    contract_size=1.0, mmr=0.01, liquidation_fee_usdt=0.0)
        for change in bad:
            with self.subTest(change=change), self.assertRaises(ValueError):
                MexcLinearPosition(**(base | change))


class CrossMarginTest(unittest.TestCase):
    def test_same_timestamp_cross_snapshot_nets_position_pnl_inside_one_account(self):
        positions = (
            MexcLinearPosition("BTC_USDT", +1, 100, 1, 1, 0.01),
            MexcLinearPosition("ETH_USDT", -1, 100, 1, 1, 0.01),
        )
        state = cross_state(100, positions, (110, 110))
        self.assertAlmostEqual(state.unrealized_pnl_usdt, 0)
        self.assertAlmostEqual(state.equity_usdt, 100)
        self.assertAlmostEqual(state.maintenance_usdt, 2)
        self.assertAlmostEqual(state.margin_rate, 0.02)
        self.assertFalse(state.liquidated)

    def test_cross_boundary_matches_mexc_published_single_long_example(self):
        position = MexcLinearPosition("BTC_USDT", +1, 8_000, 10_000, 0.0001, 0.005)
        # MEXC's published example: 500 USDT cross wallet, no other positions/orders.
        boundary = cross_state(500, (position,), (7_540,))
        safe = cross_state(500, (position,), (7_541,))
        self.assertAlmostEqual(boundary.equity_usdt, boundary.requirement_usdt)
        self.assertTrue(boundary.liquidated)
        self.assertFalse(safe.liquidated)

    def test_cross_uses_common_fair_prices_and_signed_settlement_cashflows(self):
        positions = (
            MexcLinearPosition("BTC_USDT", +1, 100, 1, 1, 0.01),
            MexcLinearPosition("ETH_USDT", +1, 100, 1, 1, 0.01),
        )
        state = cross_state(10, positions, (90, 90), cashflows_usdt=(2, -1))
        self.assertAlmostEqual(state.unrealized_pnl_usdt, -20)
        self.assertAlmostEqual(state.cashflow_usdt, 1)
        self.assertAlmostEqual(state.equity_usdt, -9)
        self.assertTrue(state.liquidated)
        self.assertEqual(state.margin_rate, math.inf)

    def test_cross_empty_account_is_cash_with_no_maintenance(self):
        state = cross_state(25, (), ())
        self.assertEqual((state.equity_usdt, state.requirement_usdt, state.margin_rate), (25, 0, 0))
        self.assertFalse(state.liquidated)

    def test_cross_rejects_misaligned_positions_marks_and_cashflows(self):
        pos = (MexcLinearPosition("BTC_USDT", +1, 100, 1, 1, 0.01),)
        bad_inputs = [
            (pos, (), None), (pos, (100,), (0, 1)),
            (pos, (0,), None), (pos, (math.nan,), None),
        ]
        for positions, marks, flows in bad_inputs:
            with self.subTest(marks=marks, flows=flows), self.assertRaises(ValueError):
                cross_state(100, positions, marks, cashflows_usdt=flows)

    def test_wallet_balance_and_cashflows_must_be_finite_and_nonnegative_wallet(self):
        with self.assertRaises(ValueError):
            cross_state(-1, (), ())
        with self.assertRaises(ValueError):
            cross_state(math.inf, (), ())

    def test_synchronized_path_finds_first_breach_without_combining_separate_extremes(self):
        positions = (
            MexcLinearPosition("BTC_USDT", +1, 100, 1, 1, 0.01),
            MexcLinearPosition("ETH_USDT", -1, 100, 1, 1, 0.01),
        )
        path = cross_path(positions, (1_000, 2_000, 3_000, 4_000), (100, 100, 100, 100),
                          ((100, 100), (20, 100), (100, 180), (20, 180)))
        self.assertEqual(path.timestamps_ms, (1_000, 2_000, 3_000, 4_000))
        self.assertFalse(path.states[1].liquidated)  # long's 80 USDT loss; short unchanged
        self.assertFalse(path.states[2].liquidated)  # short's 80 USDT loss; long unchanged
        self.assertTrue(path.states[3].liquidated)   # both adverse moves align only at this timestamp
        self.assertEqual((path.first_breach_index, path.first_breach_ms), (3, 4_000))

    def test_synchronized_path_rejects_order_time_and_row_mismatches(self):
        positions = (MexcLinearPosition("BTC_USDT", +1, 100, 1, 1, 0.01),)
        cases = [
            ((1_000,), (100, 100), ((100,),)),
            ((2_000, 1_000), (100, 100), ((100,), (100,))),
            ((1_000,), (100,), ((100, 100),)),
            ((True,), (100,), ((100,),)),
        ]
        for times, balances, marks in cases:
            with self.subTest(times=times, balances=balances, marks=marks), self.assertRaises(ValueError):
                cross_path(positions, times, balances, marks)


if __name__ == "__main__":
    unittest.main()
