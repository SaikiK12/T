from pathlib import Path
import tempfile
import unittest
from unittest import mock

from lab.acquisition_budget import BudgetError
from lab.stream_quotes import FrameClock
from lab.stream_recovery import StreamRecovery,RecoveryError
from tests.test_lighter_depth_state import snapshot,message
from tests.test_stream_quotes import ANCHOR,NS,UTC


def clock(second):return FrameClock(UTC+int(second*NS),ANCHOR.mono_ns+int(second*NS))


class StreamRecoveryTests(unittest.TestCase):
    def make(self,**kw):
        r=StreamRecovery(1,'BTC',max_restarts=2,**kw);self.addCleanup(r.close);return r

    def test_disconnect_requires_finite_restart_and_new_snapshot(self):
        r=self.make();old=r.token
        self.assertEqual(r.consume(snapshot(),clock(0),epoch=old)['status'],'snapshot')
        r.disconnect('fixture socket ended',clock(.1));self.assertEqual(r.status()['state'],'invalid')
        with self.assertRaises(ValueError):r.state.as_stream_book()
        new=r.restart('replacement allowed',clock(.2));self.assertEqual(new,old+1)
        self.assertEqual(r.status()['state'],'snapshot_required')
        self.assertEqual(r.consume(snapshot(),clock(.3),epoch=old)['status'],'stale_epoch')
        self.assertEqual(r.status()['state'],'snapshot_required')
        self.assertEqual(r.consume(snapshot(),clock(.4),epoch=new)['status'],'snapshot')
        self.assertFalse(r.status()['execution_ready'])

    def test_gap_is_sticky_until_restart_and_update_cannot_replace_snapshot(self):
        r=self.make();e=r.token;r.consume(snapshot(),clock(0),epoch=e)
        self.assertEqual(r.consume(message(begin=999),clock(.1),epoch=e)['status'],'invalid')
        self.assertEqual(r.consume(snapshot(),clock(.2),epoch=e)['status'],'invalid')
        e=r.restart('known gap',clock(.3))
        self.assertEqual(r.consume(message(),clock(.4),epoch=e)['status'],'invalid')
        e=r.restart('replacement snapshot required',clock(.5))
        r.consume(snapshot(),clock(.6),epoch=e);r.disconnect('next failure',clock(.7))
        with self.assertRaisesRegex(RecoveryError,'exhausted'):r.restart('no more epochs',clock(.8))
        self.assertEqual(r.status()['restarts_used'],2)

    def test_duplicate_pong_and_no_effect_do_not_refresh_liquidity(self):
        r=self.make();e=r.token;p=snapshot();r.consume(p,clock(0),epoch=e)
        stamp=r.state.liquidity_clock
        self.assertEqual(r.consume(p,clock(.1),epoch=e)['status'],'duplicate')
        self.assertEqual(r.consume({'type':'pong'},clock(.2),epoch=e)['status'],'ignored')
        self.assertEqual(r.consume(message(),clock(.3),epoch=e)['status'],'no_effect')
        self.assertEqual(r.state.liquidity_clock,stamp)
        self.assertTrue(any('receive_age' in f for f in r.state.freshness_flags(ANCHOR.mono_ns+2*NS,ANCHOR)))

    def test_reopen_preserves_control_budget_and_never_resumes_old_liquidity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'epochs.jsonl';r=self.make(journal_path=p);r.consume(snapshot(),clock(0),epoch=r.token)
            with self.assertRaises(BlockingIOError):self.make(journal_path=p)
            r.disconnect('failure',clock(.1));e=r.restart('allowed',clock(.2));r.consume(snapshot(),clock(.3),epoch=e)
            r.close();prefix=p.read_bytes();s=self.make(journal_path=p)
            self.assertTrue(p.read_bytes().startswith(prefix));self.assertEqual(s.status()['restarts_used'],1)
            self.assertEqual(s.status()['frames_used'],2);self.assertEqual(s.status()['state'],'invalid')
            self.assertEqual(s.consume(snapshot(),clock(.4),epoch=e)['status'],'invalid')
            e=s.restart('new process transport',clock(.5));self.assertEqual(e,2)
            self.assertEqual(s.consume(snapshot(),clock(.6),epoch=e)['status'],'snapshot')

    def test_frame_budget_includes_old_epoch_and_fresh_restart_does_not_reset_it(self):
        r=self.make(max_frames=2);r.consume(snapshot(),clock(0),epoch=r.token)
        r.disconnect('failure',clock(.1));r.restart('allowed',clock(.2))
        r.consume(snapshot(),clock(.3),epoch=0)
        with self.assertRaisesRegex(RecoveryError,'frame budget'):r.consume(snapshot(),clock(.4),epoch=r.token)
        self.assertEqual(r.status()['frames_used'],2);self.assertEqual(r.status()['state'],'invalid')

    def test_ready_reset_closed_scope_change_and_partial_journal_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'epochs.jsonl';r=self.make(journal_path=p);r.consume(snapshot(),clock(0),epoch=r.token)
            with self.assertRaisesRegex(RecoveryError,'failure required'):r.restart('adaptive refresh',clock(.1))
            r.close()
            with self.assertRaisesRegex(RecoveryError,'closed'):r.consume(snapshot(),clock(.2),epoch=r.token)
            with self.assertRaisesRegex(RecoveryError,'scope'):StreamRecovery(1,'BTC',max_restarts=3,journal_path=p)
            with p.open('a') as f:f.write('partial')
            with self.assertRaisesRegex(BudgetError,'incomplete'):self.make(journal_path=p)

    def test_restart_reservation_survives_interruption_before_reset(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'epochs.jsonl';r=self.make(journal_path=p);r.disconnect('failed source',clock(0))
            with mock.patch.object(r.state,'reset',side_effect=RuntimeError('invented interruption')):
                with self.assertRaises(RuntimeError):r.restart('replacement',clock(.1))
            r.close();s=self.make(journal_path=p)
            self.assertEqual(s.status()['restarts_used'],1);self.assertEqual(s.token,1);self.assertEqual(s.status()['state'],'invalid')

    def test_frame_reservation_survives_interruption_before_consume(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'epochs.jsonl';r=self.make(journal_path=p,max_frames=1)
            with mock.patch.object(r.state,'consume',side_effect=RuntimeError('invented interruption')):
                with self.assertRaises(RuntimeError):r.consume(snapshot(),clock(0),epoch=r.token)
            self.assertEqual(r.status()['state'],'invalid')
            r.close();s=self.make(journal_path=p,max_frames=1)
            self.assertEqual(s.status()['frames_used'],1)
            with self.assertRaisesRegex(RecoveryError,'frame budget'):s.consume(snapshot(),clock(.1),epoch=s.token)

    def test_result_journal_failure_poisoned_state_cannot_export(self):
        # Exercise the real write-failure guard rather than replacing _record.
        import lab.stream_recovery as module
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'epochs.jsonl';s=self.make(journal_path=p);write=module._append_record
            def fail(handle,records,event):
                if event['kind']=='frame_result':raise OSError('fixture journal failure')
                return write(handle,records,event)
            with mock.patch.object(module,'_append_record',side_effect=fail):
                with self.assertRaises(OSError):s.consume(snapshot(),clock(0),epoch=s.token)
            self.assertEqual(s.status()['state'],'invalid')
            with self.assertRaises(ValueError):s.state.as_stream_book()
