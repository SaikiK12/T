"""Cash and missing-data behavior on invented prices only; never read lab market data."""
from copy import deepcopy
from decimal import Decimal as D
import unittest

from lab.kraken_carry import fixed_quantity, funding_intervals, replay


class CarryTest(unittest.TestCase):
    def fixture(self):
        start, end = 1767225600, 1767312000
        hours = list(range(start, end, 3600))
        return dict(start=start, end=end, capital="10000", lot="1",
                    spot={start:"100",end:"100"}, trade={start:"100",end:"100"},
                    marks={t:dict(open="100",high="100",low="100") for t in hours},
                    funding=[(t,D(1),D(1),True) for t in hours],
                    spot_fee="0",perp_fee="0",slip="0",initial_margin="0.1",
                    maintenance_margin="0.05",tier_ceiling="30000000",multiple=1)

    def test_funded_capital_is_both_legs(self):
        r=replay(**self.fixture())
        self.assertEqual(r["quantity"],50)
        self.assertEqual(r["funding_lower"],1200)
        self.assertEqual(r["counterfactual_net_lower"],1200)
        self.assertEqual(r["annual_funding_on_initial_notional_lower"],D(".24")*365)
        self.assertEqual(r["annual_funding_on_total_capital_lower"],D(".12")*365)
        self.assertIsNone(r["executable_net"])

    def test_costs_are_paid_on_four_actual_trade_values(self):
        f=self.fixture();f.update(spot_fee=".008",perp_fee=".0005",slip=".0001")
        rows=[replay(**dict(f,multiple=m)) for m in [1,2,3]]
        self.assertEqual({r["quantity"] for r in rows},{D(48)})
        for r,m in zip(rows,[1,2,3]):
            self.assertEqual(r["fees"],D(48)*D(100)*D(2)*D(".0085")*m)
            self.assertEqual(r["slippage_assumption"],D(48)*D(400)*D(".0001")*m)
            self.assertEqual(r["counterfactual_net_lower"],r["funding_lower"]-r["total_execution_cost"])
        self.assertGreater(rows[0]["counterfactual_net_lower"],rows[2]["counterfactual_net_lower"])

    def test_quantity_does_not_change_with_mark_or_cost_stress(self):
        f=self.fixture();f["spot"][f["end"]]="150";f["trade"][f["end"]]="150"
        for mark in f["marks"].values():mark.update(open="150",high="150",low="150")
        r=replay(**f)
        self.assertEqual(r["quantity"],50)
        self.assertEqual(r["basis_pnl"],0)
        self.assertTrue(r["margin_screen_clear"])

    def test_basis_is_realized_by_two_price_differences(self):
        f=self.fixture();f["spot"][f["end"]]="120"
        f["trade"].update({f["start"]:"102",f["end"]:"121"})
        r=replay(**f)
        self.assertEqual(r["basis_pnl"],50)
        self.assertEqual(r["counterfactual_net_lower"],1250)

    def test_negative_funding_is_a_debit(self):
        f=self.fixture();f["funding"]=[(t,-lo,-hi,k) for t,lo,hi,k in f["funding"]]
        self.assertEqual(replay(**f)["counterfactual_net_lower"],-1200)

    def test_missing_funding_has_an_interval_and_not_zero(self):
        f=self.fixture();observed={t:D(0) for t,*_ in f["funding"]};del observed[f["start"]]
        f["funding"]=funding_intervals(f["start"],f["end"],observed,{f["start"]:"120"},".005")
        r=replay(**f)
        self.assertEqual(r["unknown_funding_hours"],1)
        self.assertEqual((r["counterfactual_net_lower"],r["counterfactual_net_upper"]),(-30,30))

    def test_unknown_without_price_envelope_refuses(self):
        f=self.fixture()
        with self.assertRaisesRegex(ValueError,"unbounded"):
            funding_intervals(f["start"],f["end"],{}, {}, ".005")

    def test_funding_period_is_half_open(self):
        f=self.fixture();rates={t:D(0) for t,*_ in f["funding"]};rates[f["end"]]=D("1e8")
        rows=funding_intervals(f["start"],f["end"],rates,{},".005")
        self.assertEqual(len(rows),24)
        self.assertTrue(all(row[1]==0 for row in rows))

    def test_possible_margin_breach_blocks_execution_score(self):
        f=self.fixture();first=f["start"]
        f["marks"][first].update(high="200")
        r=replay(**f)
        self.assertFalse(r["margin_screen_clear"])
        self.assertEqual(r["possible_maintenance_breach"]["t"],first)
        self.assertIsNone(r["executable_net"])
        self.assertIn("counterfactual",r["terminal_scope"])

    def test_adverse_pending_funding_is_in_margin_stress(self):
        f=self.fixture();f["funding"][0]=(f["start"],D(-100),D(-100),True)
        self.assertFalse(replay(**f)["margin_screen_clear"])

    def test_usd_cash_deficit_is_not_hidden_by_unrealized_short_profit(self):
        f=self.fixture()
        for mark in f["marks"].values():mark.update(open="1",high="1",low="1")
        f["funding"]=[(t,D(0),D(0),True) for t,*_ in f["funding"]]
        f["funding"][0]=(f["start"],D(-101),D(-101),True)
        r=replay(**f)
        self.assertIsNone(r["possible_maintenance_breach"])
        self.assertEqual(r["possible_usd_cash_deficit"]["t"],f["start"])
        self.assertFalse(r["margin_screen_clear"])

    def test_unqualified_tier_is_not_extrapolated(self):
        f=self.fixture();f["tier_ceiling"]="5000"
        with self.assertRaisesRegex(ValueError,"tier"):
            replay(**f)

    def test_missing_mark_is_not_forward_filled(self):
        f=self.fixture();del f["marks"][f["start"]]
        with self.assertRaisesRegex(ValueError,"mark"):
            replay(**f)

    def test_missing_execution_day_refuses(self):
        f=self.fixture();del f["spot"][f["end"]]
        with self.assertRaisesRegex(ValueError,"benchmark"):
            replay(**f)

    def test_clock_and_ohlc_are_validated(self):
        f=self.fixture();f["funding"]=f["funding"][:-1]
        with self.assertRaisesRegex(ValueError,"clock"):
            replay(**f)
        f=self.fixture();f["marks"][f["start"]]["low"]="101"
        with self.assertRaisesRegex(ValueError,"OHLC"):
            replay(**f)

    def test_invalid_funding_interval_refuses(self):
        f=self.fixture();f["funding"][0]=(f["start"],D(2),D(1),False)
        with self.assertRaisesRegex(ValueError,"interval"):
            replay(**f)

    def test_fee_reserve_covers_three_cost_levels(self):
        q=fixed_quantity(10000,100,".0001",".008",".0001")
        self.assertLessEqual(q*D(100)*D("1.0003")*D("1.024"),5000)
        self.assertGreater((q+D(".0001"))*D(100)*D("1.0003")*D("1.024"),5000)

    def test_month_boundaries_are_attribution_without_trades(self):
        f=self.fixture();r=replay(**f)
        self.assertEqual(len(r["monthly_funding_attribution"]),1)
        self.assertEqual(r["monthly_funding_attribution"][0]["funding_lower"],1200)

    def test_input_is_not_mutated(self):
        f=self.fixture();before=deepcopy(f);replay(**f)
        self.assertEqual(f,before)


if __name__=="__main__":
    unittest.main()
