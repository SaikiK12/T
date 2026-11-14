from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.paired_execution import PairedAccount,PairPlan,PairReceipt
from lab.paper_account import PaperAccount
from lab.stream_quotes import FrameClock,NS

UTC=1790000000*NS
ANCHOR=FrameClock(UTC,10*NS)
def clock(s):return FrameClock(UTC+int(s*NS),ANCHOR.mono_ns+int(s*NS))
def plan(**kw):return PairPlan(**{**dict(pair_id='fixture',symbol='BTC',assets=('USDT','USDC'),quantity_base=1,
                                        mexc_side=1,entry_deadline_mono_ns=clock(10).mono_ns),**kw})
def receipt(i,kind,leg=0,second=1,**kw):
    d=dict(receipt_id=str(i),leg=leg,order_id=('m','l')[leg],kind=kind,occurred_ns=clock(second).utc_ns,
           clock=clock(second),source_identity='invented lifecycle')
    if kind in ('submit','fill'):d['quantity_base']=1
    if kind=='fill':d.update(trade_id=str(i),price=100,fee='.1')
    return PairReceipt(**{**d,**kw})


class PairExecutionTests(unittest.TestCase):
    def make(self,path=None,p=None):
        account=PaperAccount({('mexc','USDT'):1000,('lighter','USDC'):1000},ANCHOR,journal_path=path)
        pair=PairedAccount(account,p or plan());self.addCleanup(pair.close);return pair
    def post(self,p,r,at=None):return p.post(r,r.clock.mono_ns if at is None else clock(at).mono_ns)
    def state(self,p,at=5):return p.snapshot(clock(at).mono_ns)

    def test_opening_gap_is_not_futures_profit_and_completion_requires_both_closes(self):
        p=self.make()
        for i,(leg,kind,price) in enumerate(((0,'submit',None),(1,'submit',None),(0,'fill',100),(1,'fill',101)),1):
            kw={'price':price} if kind=='fill' else {}
            self.post(p,receipt(i,kind,leg,second=i*.1,**kw))
        x=self.state(p);self.assertEqual(x['pair']['state'],'hedged');self.assertTrue(x['pair']['paired_target_fully_filled'])
        self.assertTrue(all(a['realized_price_pnl']=='0' and a['cash']=='999.9' for a in x['accounts']))
        for leg,price in ((0,99),(1,102)):
            self.post(p,receipt('close'+str(leg),'submit',leg,second=6+leg,purpose='close',order_id='close'+str(leg)))
            self.post(p,receipt('fillclose'+str(leg),'fill',leg,second=6.1+leg,purpose='close',order_id='close'+str(leg),price=price))
        x=self.state(p,8);self.assertEqual(x['pair']['state'],'flat');self.assertTrue(x['pair']['terminal_cash_known'])
        self.assertTrue(all(D(a['cash'])==D('998.8') for a in x['accounts']))

    def test_cancel_request_does_not_remove_fill_risk_or_allow_another_full_order(self):
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1))
        self.post(p,receipt(3,'submit',1,second=1.2));self.post(p,receipt(4,'fill',1,second=1.3,quantity_base='.4'))
        self.post(p,receipt(5,'cancel_request',1,second=1.4));x=self.state(p,2)['pair']
        self.assertEqual(x['positions_base'],['1','-0.4']);self.assertEqual(list(map(D,x['possible_delta_base'])),[D(0),D('.6')])
        self.assertIsNone(x['recovery_quantities'][1]['remaining_entry_base']);self.assertFalse(x['recovery_quantities'][1]['new_entry_model_allowed'])
        self.post(p,receipt(6,'fill',1,second=2.1,quantity_base='.2'))
        self.post(p,receipt(7,'cancelled',1,second=2.2,cumulative_filled_base='.6'))
        self.assertEqual(D(self.state(p,2.3)['pair']['recovery_quantities'][1]['remaining_entry_base']),D('.4'))
        self.post(p,receipt(8,'submit',1,second=2.4,quantity_base='.4',order_id='l2'))
        self.post(p,receipt(9,'fill',1,second=2.5,quantity_base='.4',order_id='l2'))
        self.assertEqual(self.state(p,3)['pair']['state'],'hedged')

    def test_retry_larger_than_remaining_marks_source_state_unknown(self):
        p=self.make();self.post(p,receipt(1,'submit',1));self.post(p,receipt(2,'fill',1,second=1.1,quantity_base='.4'))
        self.post(p,receipt(3,'cancelled',1,second=1.2,cumulative_filled_base='.4'))
        x=self.post(p,receipt(4,'submit',1,second=1.3,order_id='l2',quantity_base=1))
        self.assertIn('order_exceeds_residual_quantity',x['reasons']);self.assertIsNone(self.state(p)['pair']['net_delta_base'])

    def test_same_trade_with_new_receipt_id_never_posts_twice(self):
        p=self.make();self.post(p,receipt(1,'submit'));e=receipt(2,'fill',second=1.1);self.post(p,e)
        x=self.post(p,replace(e,receipt_id='redelivery',clock=clock(2)))
        self.assertEqual(x['status'],'duplicate_trade');self.assertEqual(x['financial_post']['status'],'duplicate')
        self.assertEqual(self.state(p)['pair']['positions_base'],['1','0'])
        self.assertEqual(next(a for a in self.state(p)['accounts'] if a['venue']=='mexc')['cash'],'999.9')

    def test_conflicting_trade_and_unknown_order_do_not_create_zero_risk(self):
        for conflict in (False,True):
            p=self.make()
            if conflict:
                self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1))
            e=receipt(3,'fill',second=2,trade_id='2' if conflict else 'unmatched',price=80)
            self.post(p,e);x=self.state(p)
            self.assertEqual(x['pair']['state'],'unknown');self.assertIsNone(x['pair']['net_delta_base'])
            self.assertTrue(all(a['cash'] is None and a['nav'] is None for a in x['accounts']))

    def test_reject_after_partial_fill_does_not_erase_filled_position(self):
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1,quantity_base='.4'))
        self.post(p,receipt(3,'rejected',second=1.2,cumulative_filled_base='.4'));x=self.state(p)
        self.assertEqual(x['pair']['state'],'exposed');self.assertEqual(x['pair']['positions_base'],['0.4','0'])
        self.assertEqual(x['pair']['recovery_quantities'][0]['remaining_entry_base'],'0.6')

    def test_terminal_without_final_quantity_and_gap_withhold_completeness(self):
        for kind in ('cancelled','gap'):
            p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,kind,second=2))
            x=self.state(p);self.assertEqual(x['pair']['state'],'unknown');self.assertIsNone(x['accounts'][0]['cash'])
            self.assertFalse(x['pair']['terminal_cash_known'])

    def test_deadline_budget_overfill_and_post_terminal_fill_stay_visible(self):
        p=self.make();self.assertIn('entry_deadline_passed',self.post(p,receipt(1,'submit',second=11))['reasons'])
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1,quantity_base='1.2'))
        x=self.state(p)['pair'];self.assertIn('reported_fill_exceeds_order',x['reasons']);self.assertEqual(x['known_received_positions_base'][0],'1.2')
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'cancelled',second=1.1,cumulative_filled_base=0))
        self.post(p,receipt(3,'fill',second=1.2));self.assertEqual(self.state(p)['pair']['state'],'unknown')

    def test_receipt_clock_and_financial_unknowns_cannot_become_pnl(self):
        p=self.make();self.post(p,receipt(1,'submit'));x=self.post(p,receipt(2,'fill',second=3),at=2)
        self.assertEqual(x['status'],'rejected');self.assertIsNone(self.state(p,4)['accounts'][0]['cash'])
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1,fee=None))
        mx=next(a for a in self.state(p)['accounts'] if a['venue']=='mexc');self.assertIsNone(mx['cash']);self.assertEqual(mx['known_cash_component'],'1000')

    def test_crash_between_receipt_and_cash_is_unknown_and_exact_replay_joins_once(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'account.jsonl';p=self.make(path);self.post(p,receipt(1,'submit'))
            e=receipt(2,'fill',second=2)
            with patch.object(p.account,'post',side_effect=RuntimeError('invented process interruption')):
                with self.assertRaises(RuntimeError):self.post(p,e)
            self.assertTrue(self.state(p,3)['pair']['unapplied_fill_ids']);p.close();prefix=path.read_bytes()
            p=self.make(path);self.assertIsNone(self.state(p,3)['pair']['net_delta_base'])
            self.post(p,replace(e,receipt_id='replayed',clock=clock(4)))
            x=self.state(p,4);self.assertEqual(x['pair']['positions_base'],['1','0']);self.assertEqual(x['pair']['unapplied_fill_ids'],[])
            self.assertTrue(path.read_bytes().startswith(prefix));self.assertEqual(len(p.account.accepted_events),1)

    def test_writer_lease_and_persistent_scope_refuse_reset(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'account.jsonl';p=self.make(path)
            with self.assertRaises(BlockingIOError):self.make(path)
            self.post(p,receipt(1,'submit'));p.close()
            with self.assertRaises(ValueError):self.make(path,plan(quantity_base=2))
            p=self.make(path);self.assertEqual(self.state(p)['pair']['state'],'pending_orders')

    def test_order_attempt_limit_is_accumulated_and_partial_close_is_not_flat(self):
        p=self.make()
        for i in range(3):
            self.post(p,receipt('s'+str(i),'submit',second=1+2*i,order_id='m'+str(i)))
            self.post(p,receipt('r'+str(i),'rejected',second=1.5+2*i,order_id='m'+str(i),cumulative_filled_base=0))
        x=self.post(p,receipt('extra','submit',second=8,order_id='m-extra'))
        self.assertIn('order_attempt_budget_exhausted',x['reasons'])
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'fill',second=1.1))
        self.post(p,receipt(3,'submit',second=2,order_id='mc',quantity_base='.3',purpose='close'))
        self.post(p,receipt(4,'fill',second=2.1,order_id='mc',quantity_base='.3',purpose='close'))
        x=self.state(p)['pair'];self.assertEqual(x['positions_base'],['0.7','0']);self.assertFalse(x['terminal_cash_known'])

    def test_schema_never_accepts_credentials_nonfinite_or_ack_as_fill(self):
        p=self.make();self.post(p,receipt(1,'submit'));self.post(p,receipt(2,'ack',second=2))
        self.assertEqual(self.state(p)['pair']['positions_base'],['0','0']);self.assertFalse(self.state(p)['pair']['paired_target_fully_filled'])
        for kw in ({'quantity_base':True},{'price':'NaN'},{'fee':-1},{'leg':True}):
            with self.assertRaises(ValueError):receipt(1,'fill',**kw)

