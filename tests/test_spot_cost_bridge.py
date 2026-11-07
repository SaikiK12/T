from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from scripts.probe_spot_costs import Acquisition,fatal
from scripts.run_spot_costs import cost_account
from lab.spot_quote_costs import spot_rules,conditional_costs
from tests.test_spot_quote_costs import books,info,metadata


class SpotCostBridgeTests(unittest.TestCase):
    def test_realized_price_fee_component_matches_cost_without_zero_funding(self):
        s,p=books();cell=conditional_costs(s,p,spot_rules('BTCUSDT',info()),metadata(),1,fee_control='advertised_quote_fee')
        with tempfile.TemporaryDirectory() as tmp:
            result=cost_account(cell,'BTC','invented-control',Path(tmp))
            self.assertEqual(D(result['known_four_fill_price_fee_component']),D('-4.608'))
            self.assertIsNone(result['snapshot']['combined_nav']);self.assertIsNone(result['funding_cash'])
            self.assertTrue(result['snapshot']['perp']['unresolved_events'])
            self.assertTrue(result['reopened_identical'])
            self.assertEqual(len(result['journal_sha256']),2)

    def test_one_attempt_budget_and_explicit_network_stop_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Acquisition(Path(tmp));a.reserve('fixed','https://example.invalid/public')
            with self.assertRaises(ValueError):a.reserve('fixed','https://example.invalid/public')
            self.assertEqual(a.budget.status()['requests_charged'],1)
            self.assertEqual(a.budget.status()['pending'],['fixed'])
        for status in (403,429,451,500,302,None):self.assertTrue(fatal({'http_status':status,'complete':True}))
        self.assertTrue(fatal({'http_status':200,'complete':False}))
        self.assertFalse(fatal({'http_status':400,'complete':True}))


if __name__=='__main__':unittest.main()
