"""Independent simulated cash/collateral cases around the frozen risk engine."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest

from lab.paper_account import PaperAccount,PaperEvent,CloseMark
from lab.paper_controls import PaperRisk,RiskPolicy
from lab.paper_solvency import PaperSolvencyGuard,capital_status
from lab.stream_quotes import FrameClock,NS
from scripts.check_paper_solvency import main

ANCHOR=FrameClock(1790000000*NS,10*NS)
INITIAL={('mexc','USDT'):1000}


def clock(n): return FrameClock(ANCHOR.utc_ns+n*NS,ANCHOR.mono_ns+n*NS)


def post(account,id,kind='fill',second=1,**values):
    if kind=='fill': values={**dict(quantity=1,price=100,fee=0),**values}
    e=PaperEvent(id,kind,'mexc','USDT','BTC',clock(second).utc_ns,clock(second),'invented fixture',**values)
    account.post(e,clock(second).mono_ns)


def snapshot(account,second=2):
    mark=CloseMark('mexc','USDT','BTC',1,100,0,clock(second),clock(second).utc_ns,'invented liquidation')
    return account.snapshot(clock(second).mono_ns,[mark])


class SolvencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'risk.jsonl'

    def risk(self):
        return PaperRisk(self.path,RiskPolicy('fixture'),ANCHOR,contract_version='one',initial_balances=INITIAL)

    def observe(self,guard,s,**extra):
        return guard.observe(s,asof=s['asof_mono_ns'],clock=clock(2),complete=True,session_open=True,
                             fee_inputs_known=True,contract_version='one',expected_contract_version='one',
                             mode='fixture',**extra)

    def test_withdrawal_counterexample_is_vetoed_after_risk_reopen(self):
        a=PaperAccount(INITIAL,ANCHOR);post(a,'open');post(a,'withdraw','capital_change',2,amount=-950)
        s=snapshot(a);row=s['accounts'][0]
        self.assertEqual((row['cash'],row['nav'],row['available_capital']),('50','50','-50'))
        legacy=self.observe(self.risk(),s)
        self.assertTrue(legacy['model_new_entries_allowed'])
        before=self.path.read_bytes();r=self.observe(PaperSolvencyGuard(self.risk()),s)
        self.assertFalse(r['model_new_entries_allowed']);self.assertEqual(r['state'],'CAPITAL_BLOCKED')
        self.assertTrue(self.path.read_bytes().startswith(before))
        self.assertFalse(r['actual_order_allowed']);self.assertTrue(r['positions_retained'])
        self.assertFalse(r['automatic_flatten_performed'])

    def test_positive_capacity_still_requires_legacy_admission_and_reserve(self):
        a=PaperAccount(INITIAL,ANCHOR);post(a,'open');s=snapshot(a)
        g=PaperSolvencyGuard(self.risk())
        self.assertTrue(self.observe(g,s,required_reserves={('mexc','USDT'):900})['model_new_entries_allowed'])
        self.assertFalse(self.observe(g,s,required_reserves={('mexc','USDT'):901})['model_new_entries_allowed'])
        component=capital_status(s)
        self.assertTrue(component['capacity_available']);self.assertFalse(component['model_new_entries_allowed'])

    def test_persistent_risk_stop_is_not_cleared_by_positive_capacity(self):
        a=PaperAccount(INITIAL,ANCHOR);post(a,'open')
        post(a,'close',second=2,quantity=-1,price=50)
        s=a.snapshot(clock(2).mono_ns)
        r=self.observe(PaperSolvencyGuard(self.risk()),s)
        self.assertEqual(r['state'],'HALTED');self.assertFalse(r['model_new_entries_allowed'])
        post(a,'deposit','capital_change',2,amount=1000)
        fresh=a.snapshot(clock(2).mono_ns)
        self.assertGreater(int(fresh['accounts'][0]['available_capital']),0)
        self.assertFalse(self.observe(PaperSolvencyGuard(self.risk()),fresh)['model_new_entries_allowed'])

    def test_unknown_balances_unresolved_events_and_inconsistent_capacity_block(self):
        a=PaperAccount(INITIAL,ANCHOR);s=snapshot(a)
        cases=[{'nav':None},{'available_capital':None},{'reasons':['unqualified']},
               {'unresolved_events':['fee']},{'reconciliation_required':['revision']},
               {'available_capital':'1001'},{'capital_basis':'exchange_margin'},{'available_capital':'0','locked_capital':'1000'}]
        for change in cases:
            x=deepcopy(s);x['accounts'][0].update(change)
            self.assertIsNot(capital_status(x)['capacity_available'],True,change)

    def test_no_cross_venue_netting_or_absent_account_reserves(self):
        a=PaperAccount({('mexc','USDT'):1000,('lighter','USDC'):10000},ANCHOR)
        post(a,'open');post(a,'withdraw','capital_change',2,amount=-950);s=snapshot(a)
        self.assertFalse(capital_status(s)['capacity_available'])
        with self.assertRaises(ValueError): capital_status(s,{('missing','USDT'):1})
        x=capital_status(s,expected_accounts={('mexc','USDT')})
        self.assertIn('registered_account_set_incomplete_or_changed',x['reasons'])

    def test_malformed_identity_and_nonfinite_amounts_do_not_pass(self):
        a=PaperAccount(INITIAL,ANCHOR);s=snapshot(a)
        for value in (True,'NaN','Infinity'):
            x=deepcopy(s);x['accounts'][0]['available_capital']=value
            with self.assertRaises(ValueError): capital_status(x)
        x=deepcopy(s);x['accounts']*=2
        with self.assertRaises(ValueError): capital_status(x)
        with self.assertRaises(ValueError): capital_status(s,{('mexc','USDT'):-1})
        x=deepcopy(s);x['schema_version']=True
        with self.assertRaises(ValueError): capital_status(x)

    def test_cli_is_read_only_and_never_permits_entries_alone(self):
        a=PaperAccount(INITIAL,ANCHOR);path=Path(self.tmp.name)/'snapshot.json'
        path.write_text(json.dumps(snapshot(a)));before=path.read_bytes();out=io.StringIO()
        with redirect_stdout(out): code=main([str(path)])
        self.assertEqual(code,0);self.assertFalse(json.loads(out.getvalue())['model_new_entries_allowed'])
        self.assertEqual(path.read_bytes(),before)
        path.write_text('{"schema_version":1,"schema_version":2}')
        with redirect_stdout(io.StringIO()): self.assertEqual(main([str(path)]),2)


if __name__=='__main__': unittest.main()
