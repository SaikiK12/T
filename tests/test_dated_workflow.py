from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest

from lab.dated_carry import rules,entry_plan,projected_result
from scripts.run_dated_carry import model_account
from scripts.probe_dated_carry import Acquisition
from tests.test_dated_carry import inputs,EXPIRY


class DatedWorkflowTests(unittest.TestCase):
    def test_constructed_ownership_is_not_double_capital_and_reopens(self):
        m,sm,s,d,r=inputs();rule=rules(m,'BTC-25DEC26','BTC',EXPIRY,'constructed-only')
        plan=entry_plan(s,sm,r,d,rule,r)
        for k in (1,2,3):
            with self.subTest(cost=k),tempfile.TemporaryDirectory() as tmp:
                result=projected_result(plan,cost_multiple=k,fee_control='public_standard',
                           delivery_rate='0.00025',delivery_price=10000,exit_ratio=1)
                model=model_account(plan,result,rule.contract,F(10000),'unit',Path(tmp))
                self.assertEqual(F(model['initial_spot_coin_earmarked_as_same_inverse_collateral']),plan['initial_coin'])
                self.assertEqual(model['remaining_unearmarked_spot_coin'],'0')
                self.assertEqual(F(model['idle_cash_usdt'])+result['initial_spend_usdt'],10000)
                self.assertIsNone(model['combined_market_nav']);self.assertTrue(model['reopened_identical'])

    def test_new_current_scope_cannot_reset_or_refund_reserved_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            acq=Acquisition(tmp)
            for n in range(7):acq.reserve('never-dispatched-'+str(n),'https://example.invalid/public')
            status=acq.budget.status()
            self.assertEqual(status['requests_charged'],7)
            self.assertEqual(status['remaining_requests'],0)
            reopened=Acquisition(tmp).budget.status()
            self.assertEqual(reopened['requests_charged'],7)
            self.assertTrue(reopened['new_dispatch_blocked'])
            self.assertEqual(status['body_bytes_charged_upper_bound'],7*65536)


if __name__=='__main__':unittest.main()
