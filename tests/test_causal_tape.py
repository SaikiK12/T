from dataclasses import FrozenInstanceError, replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from lab.causal_tape import CausalTape, legacy_availability
from lab.paper_account import PaperAccount, PaperEvent
from lab.paper_controls import PaperRisk, RiskPolicy
from lab.stream_quotes import FrameClock, NS

UTC = 1790000000*NS
ANCHOR = FrameClock(UTC, 10*NS)


def clock(ms):
    return FrameClock(UTC+ms*1_000_000, ANCHOR.mono_ns+ms*1_000_000)


class CausalTapeTests(unittest.TestCase):
    def book(self, t, at=900, identity='a'):
        return t.ingest('book', 'BTC', UTC//1_000_000+800, (99., 2., 101., 3.), clock(at), identity)

    def test_finalized_row_has_own_clock_and_cannot_be_used_at_second_end(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t)
        self.assertEqual(t.finalize(clock(1000)), [])
        self.assertEqual(t.finalize(clock(2999)), [])
        row,=t.finalize(clock(3000))
        self.assertEqual(row.max_received_clock,clock(900))
        self.assertEqual(row.finalized_clock,clock(3000))
        self.assertTrue(row.complete)
        self.assertFalse(t.readiness(row,clock(1000).mono_ns)['finalized_feature_known'])
        self.assertTrue(t.readiness(row,clock(3000).mono_ns)['finalized_feature_known'])
        self.assertFalse(t.readiness(row,clock(3000).mono_ns)['actual_execution_ready'])

    def test_trade_receipt_and_grace_are_retained_too(self):
        t=CausalTape('lighter','one',ANCHOR)
        t.ingest('trade','ETH',UTC//1_000_000+999,(100.,2.,1),clock(1500),'trade')
        row,=t.finalize(clock(3000))
        self.assertEqual(row.kind,'trade');self.assertEqual(row.max_received_clock,clock(1500))
        self.assertEqual(row.mapping()['row']['buy_qty'],2)

    def test_terminal_drain_keeps_incomplete_bucket_and_prevents_more_input(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t)
        row,=t.finalize(clock(1500),terminal=True)
        self.assertFalse(row.complete)
        self.assertIn('terminal_bucket_before_settlement_grace',row.reasons)
        self.assertEqual(self.book(t,1600,identity='later')['status'],'after_connection_close')
        with self.assertRaises(ValueError):t.finalize(clock(4000),terminal=True)

    def test_duplicate_never_refreshes_first_receipt_and_revision_stops(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t)
        duplicate=self.book(t,1000)
        self.assertEqual(duplicate['status'],'duplicate')
        self.assertEqual(duplicate['first_seen_clock']['mono_ns'],clock(900).mono_ns)
        self.assertEqual(duplicate['observed_clock']['mono_ns'],clock(1000).mono_ns)
        row,=t.finalize(clock(3000));self.assertEqual(row.max_received_clock,clock(900))
        changed=t.ingest('book','BTC',UTC//1_000_000+800,(98.,2.,101.,3.),clock(3500),'a')
        self.assertEqual(changed['status'],'conflicting_source_revision')
        self.assertFalse(t.readiness(row,clock(3500).mono_ns)['finalized_feature_known'])
        self.assertTrue(t.readiness(row,clock(3000).mono_ns)['finalized_feature_known'])

    def test_late_observation_does_not_rewrite_previous_feature_or_earlier_knowledge(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t);row,=t.finalize(clock(3000))
        old=row.mapping();late=self.book(t,4000,'new')
        self.assertEqual(late['status'],'late_after_finalization');self.assertEqual(row.mapping(),old)
        self.assertTrue(t.readiness(row,clock(3000).mono_ns)['finalized_feature_known'])
        self.assertFalse(t.readiness(row,clock(4000).mono_ns)['finalized_feature_known'])
        with self.assertRaises(ValueError):t.finalize(clock(3500))
        with self.assertRaises(FrozenInstanceError):row.complete=False

    def test_connections_do_not_share_previous_ofi_or_readiness(self):
        a=CausalTape('mexc','old',ANCHOR);self.book(a);row,=a.finalize(clock(3000))
        b=CausalTape('mexc','new',clock(3000))
        b.ingest('book','BTC',UTC//1_000_000+3100,(101.,2.,102.,3.),clock(3200),'b')
        new,=b.finalize(clock(6000))
        self.assertEqual(new.mapping()['row']['ofi'],0)
        self.assertIn('wrong_connection',b.readiness(row,clock(6000).mono_ns)['reasons'])

    def test_bad_clocks_and_source_identity_are_not_silently_accepted(self):
        t=CausalTape('mexc','one',ANCHOR)
        with self.assertRaises(ValueError):
            t.ingest('book','BTC',UTC//1_000_000+2000,(99.,2.,101.,3.),clock(900),'future')
        with self.assertRaises(ValueError):
            t.ingest('book','BTC',UTC//1_000_000+800,(99.,2.,101.,3.),FrameClock(UTC+1000*1_000_000,clock(900).mono_ns),'step')
        with self.assertRaises(ValueError):t.finalize(clock(1))

    def test_legacy_exchange_second_and_max_lag_cannot_become_finalized_time(self):
        for lag in [0,50,500,10000]:
            row={'s':UTC//1_000_000,'sym':'BTC','lag_ms':lag}
            self.assertIsNone(legacy_availability(row)['finalized_feature_known'])

    def test_unissued_or_modified_row_and_bad_input_cannot_become_ready(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t);row,=t.finalize(clock(3000))
        self.assertFalse(t.readiness(replace(row),clock(3000).mono_ns)['finalized_feature_known'])
        with self.assertRaises(ValueError):
            t.ingest('book','BTC',UTC//1_000_000+3100,(101.,2.,99.,3.),clock(3200),'bad')
        self.assertEqual(t.evidence[-1]['status'],'invalid_input_requires_reconciliation')
        self.assertFalse(t.readiness(row,clock(3200).mono_ns)['finalized_feature_known'])

    def test_later_clock_error_does_not_backdate_its_quality_flag(self):
        t=CausalTape('mexc','one',ANCHOR);self.book(t);row,=t.finalize(clock(3000))
        bad=FrameClock(clock(4000).utc_ns+60_000_000,clock(4000).mono_ns)
        with self.assertRaises(ValueError):
            t.ingest('book','BTC',UTC//1_000_000+3800,(99.,2.,101.,3.),bad,'stepped')
        self.assertTrue(t.readiness(row,clock(3000).mono_ns)['finalized_feature_known'])
        self.assertFalse(t.readiness(row,clock(4000).mono_ns)['finalized_feature_known'])
        with self.assertRaises(ValueError):t.finalize(clock(3500))

    def test_native_account_keeps_unknown_exit_and_risk_stop_after_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);balances={('lighter-model','MODEL_QUOTE'):10000}
            a=PaperAccount(balances,ANCHOR,journal_path=path/'account.jsonl')
            at=clock(1000)
            event=PaperEvent('invented-entry','fill','lighter-model','MODEL_QUOTE','TOY',at.utc_ns,at,
                'invented-not-R348',quantity=D(10),price=D(100),fee=D(0))
            self.assertEqual(a.post(event,at.mono_ns)['status'],'applied')
            missing=a.snapshot(clock(2000).mono_ns)['accounts'][0]
            self.assertEqual(missing['cash'],'10000');self.assertEqual(missing['locked_capital'],'1000')
            self.assertIsNone(missing['nav']);self.assertTrue(missing['positions'])
            risk=PaperRisk(path/'risk.jsonl',RiskPolicy('invented'),ANCHOR,contract_version='R350',initial_balances=balances)
            snap=a.snapshot(clock(2000).mono_ns)
            kw=dict(asof=clock(2000).mono_ns,clock=clock(2000),complete=False,session_open=True,
                    fee_inputs_known=True,contract_version='R350',expected_contract_version='R350',mode='fixture')
            stopped=risk.observe(snap,**kw)
            self.assertFalse(stopped['model_new_entries_allowed']);self.assertFalse(stopped['automatic_flatten_performed'])
            old=(path/'account.jsonl').read_bytes()
            again=PaperAccount(balances,ANCHOR,journal_path=path/'account.jsonl')
            self.assertEqual((path/'account.jsonl').read_bytes(),old)
            self.assertEqual(again.snapshot(clock(2000).mono_ns)['accounts'][0],missing)


if __name__=='__main__':unittest.main()
