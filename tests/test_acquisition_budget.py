from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from lab.acquisition_budget import BudgetError,BudgetJournal,BudgetLimits,historical_baseline


class AcquisitionBudgetTests(unittest.TestCase):
    def make(self,path,**kw):
        return BudgetJournal(path,'fixture-public-data',BudgetLimits(3,120,30,10),**kw)

    def test_crashed_failed_or_completed_reservation_never_refunds_and_replay_never_dispatches(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'budget.jsonl';a=self.make(p)
            x=a.reserve('one',40,10,now_ns=100,deadline_ns=120);self.assertTrue(x['dispatch_allowed'])
            prefix=p.read_bytes();b=self.make(p)
            self.assertEqual(b.status()['pending'],['one'])
            self.assertFalse(b.reserve('one',40,10,now_ns=115,deadline_ns=120)['dispatch_allowed'])
            self.assertEqual(p.read_bytes(),prefix)
            b.complete('one',5,2,outcome='failure')
            state=b.status();self.assertEqual(state['body_bytes_charged_upper_bound'],40)
            self.assertEqual(state['duration_ns_charged_upper_bound'],10);self.assertEqual(state['pending'],[])
            settled=p.read_bytes();self.assertTrue(b.complete('one',5,2,outcome='failure')['replayed']);self.assertEqual(p.read_bytes(),settled)
            with self.assertRaisesRegex(BudgetError,'conflicting'):b.complete('one',5,2,outcome='success')
            with self.assertRaisesRegex(BudgetError,'conflicting'):b.reserve('one',41,10,now_ns=100,deadline_ns=120)
            self.assertTrue(p.read_bytes().startswith(prefix))

    def test_accumulated_concurrency_and_reopen_cannot_reset_allowance(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'budget.jsonl';a=self.make(p)
            def reserve(i):
                try:return a.reserve(str(i),40,10,now_ns=100,deadline_ns=120)['dispatch_allowed']
                except BudgetError:return False
            with ThreadPoolExecutor(max_workers=8) as pool:out=list(pool.map(reserve,range(8)))
            self.assertEqual(sum(out),3);self.assertEqual(a.status()['requests_charged'],3)
            self.assertTrue(a.status()['new_dispatch_blocked'])
            self.assertEqual(set(a.status()['dispatch_block_reasons']),{'request_allowance_exhausted','body_allowance_exhausted','duration_allowance_exhausted'})
            with self.assertRaisesRegex(BudgetError,'exhausted'):self.make(p).reserve('next',1,1,now_ns=100,deadline_ns=120)
            with self.assertRaisesRegex(BudgetError,'reset or changed'):BudgetJournal(p,'fixture-public-data',BudgetLimits(10,120,30,10))

    def test_same_operation_concurrency_authorizes_only_one_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(Path(d)/'budget.jsonl')
            with ThreadPoolExecutor(max_workers=8) as pool:
                out=list(pool.map(lambda _:a.reserve('same',40,10,now_ns=100,deadline_ns=120),range(8)))
            self.assertEqual(sum(r['dispatch_allowed'] for r in out),1)
            self.assertEqual(a.status()['requests_charged'],1)

    def test_unknown_exact_historical_bytes_remain_unknown_and_block_new_grant(self):
        with tempfile.TemporaryDirectory() as d:
            a=BudgetJournal(Path(d)/'historical.jsonl','R310-R311-shared',BudgetLimits(8000,250*1024**2,100,10),baseline=historical_baseline())
            s=a.status();self.assertEqual(s['requests_charged'],7757);self.assertEqual(s['baseline']['reported_response_mib'],'229.85')
            self.assertIsNone(s['remaining_body_bytes']);self.assertTrue(s['new_dispatch_blocked'])
            self.assertFalse(s['authorization_verified'])
            with self.assertRaisesRegex(BudgetError,'unknown byte baseline'):a.reserve('no-renewal',1,1,now_ns=1,deadline_ns=100)

    def test_overrun_is_appended_visible_and_blocks_all_further_attempts(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.make(Path(d)/'budget.jsonl');a.reserve('one',40,10,now_ns=100,deadline_ns=120)
            r=a.complete('one',45,12,outcome='timeout')
            self.assertEqual(len(r['violations']),2);s=a.status();self.assertEqual(s['body_bytes_charged_upper_bound'],45)
            self.assertEqual(s['duration_ns_charged_upper_bound'],12);self.assertTrue(s['new_dispatch_blocked'])
            with self.assertRaisesRegex(BudgetError,'overrun'):a.reserve('two',1,1,now_ns=101,deadline_ns=120)

    def test_deadline_type_limits_corrupt_tail_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'budget.jsonl';a=self.make(p)
            for args in [(True,1,100,120),(1,11,100,120),(1,10,115,120)]:
                with self.assertRaises(BudgetError):a.reserve('bad',args[0],args[1],now_ns=args[2],deadline_ns=args[3])
            self.assertEqual(a.status()['requests_charged'],0)
            a.reserve('valid',1,1,now_ns=100,deadline_ns=120)
            with self.assertRaises(BudgetError):a.reserve('clock-back',1,1,now_ns=99,deadline_ns=120)
            with p.open('a') as f:f.write('{"partial":')
            with self.assertRaisesRegex(BudgetError,'incomplete'):a.status()
            linked=Path(d)/'link';linked.symlink_to(p)
            with self.assertRaises(OSError):self.make(linked)

    def test_missing_or_untyped_baseline_never_becomes_zero_spend(self):
        with tempfile.TemporaryDirectory() as d:
            for i,base in enumerate(({}, {'requests_used':0,'body_bytes_upper_bound':None,'reserved_duration_ns':0,'exact_body_bytes_known':True},
                                     {'requests_used':0,'body_bytes_upper_bound':0,'reserved_duration_ns':0,'unrecognized':1})):
                with self.assertRaises(BudgetError):self.make(Path(d)/str(i),baseline=base)
