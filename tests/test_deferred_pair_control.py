from pathlib import Path
import json
import tempfile
from unittest import mock

from lab.deferred_pair_control import DeferredDepthReplay, DeferredPairControl
from lab.live_pair_control import LivePairControl
from lab.stream_quotes import SYMBOLS
from tests import test_incremental_pair_control as prior
from tests.test_depth_quotes import depth_frame
from tests.test_live_pair_control import clock, config, connections, final_frames, initial
from tests.test_stream_quotes import ANCHOR, frame, metadata
from scripts.check_deferred_pair_control import check_money, helper


class DeferredDepthTests(prior.IncrementalDepthTests):
    def engine(self, cs=None):
        return DeferredDepthReplay(metadata(), {1:'BTC'}, ANCHOR, cs or connections())

    def test_receive_exports_zero_books_and_same_asof_profile_reuses_one_materialization(self):
        r = self.engine(); state = r.states['BTC']
        with mock.patch.object(state, 'as_stream_book', wraps=state.as_stream_book) as export:
            for f in prior.ordered(initial()): r.receive(f)
            self.assertEqual(export.call_count, 0)
            for s in SYMBOLS: r.observe(s, clock(20).mono_ns)
            self.assertEqual(export.call_count, 2)
            self.assertEqual(r.materializations, 1)
            for s in SYMBOLS: r.observe(s, clock(20).mono_ns, profile='top_only')
            self.assertEqual(export.call_count, 4)
            r.observe('BTC', clock(20.1).mono_ns, profile='top_only')
            self.assertEqual(export.call_count, 6)
            r.receive(frame('mexc', 20.2, version=2))
            self.assertEqual(export.call_count, 6)
            r.observe('BTC', clock(20.2).mono_ns, profile='top_only')
            self.assertEqual(export.call_count, 8)

    def test_new_same_asof_unusable_boundary_invalidates_export_cache(self):
        r = self.engine()
        for f in prior.ordered(initial()): r.receive(f)
        row, _ = r.observe('BTC', clock(20).mono_ns)
        self.assertEqual(row['book_flags'], [])
        cs = connections(); cs['lighter']['unusable_mono_ns'] = clock(20).mono_ns
        r.update_connections(cs)
        row, _ = r.observe('BTC', clock(20).mono_ns)
        self.assertIn('lighter:disconnected', row['book_flags'])
        self.assertEqual(row['lighter_assembly']['reason'], 'transport disconnected')

    def test_idle_cache_never_reuses_a_fresh_book_at_a_later_stale_asof(self):
        r = self.engine()
        for f in prior.ordered(initial()): r.receive(f)
        a, _ = r.observe('BTC', clock(20).mono_ns)
        b, _ = r.observe('BTC', clock(22).mono_ns)
        self.assertIsNotNone(a['quantity_base'])
        self.assertIsNone(b['quantity_base'])
        self.assertIn('lighter:receive_age_outside_0_1s', b['book_flags'])


class DeferredControllerTests(prior.IncrementalControllerTests):
    def issue(self, directory, adaptive, frames=None, cs=None, late=False):
        cs = cs or connections(); frames = prior.ordered(frames or final_frames())
        args = (Path(directory), metadata(), {1:'BTC'}, ANCHOR, config())
        c = DeferredPairControl(*args, cs) if adaptive else LivePairControl(*args)
        index = 0
        for stage, kind, second in (('entry','plan',20), ('entry','tick',20.7 if late else 20.3),
                                    ('exit','plan',50), ('exit','tick',50.3)):
            now = clock(second)
            while index < len(frames) and frames[index]['mono_ns'] <= now.mono_ns:
                if adaptive: c.receive(frames[index])
                index += 1
            issued = clock(second+.4) if late and stage == 'entry' and kind == 'plan' else now
            args = (stage, now, cs) if adaptive else (stage, now, frames[:index], cs)
            getattr(c, kind)(*args, completed_clock=lambda c=issued: c)
        return c.report(clock(60))

    def test_future_owned_state_cannot_be_backdated_and_new_adapter_has_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = DeferredPairControl(Path(tmp)/'a', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            c.receive(frame('mexc', 21))
            with self.assertRaises(ValueError): c.plan('entry', clock(20), connections())
            self.assertFalse(c.control.receipts)

    def test_instance_dependency_binding_never_patches_other_or_original_controllers(self):
        from lab import live_pair_control as original
        with tempfile.TemporaryDirectory() as tmp:
            before = original.DepthReplay
            a = DeferredPairControl(Path(tmp)/'a', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            b = DeferredPairControl(Path(tmp)/'b', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            for f in prior.ordered(initial()): a.receive(f)
            self.assertIsNotNone(a.plan('entry', clock(20), connections())['views']['BTC']['quantity'])
            self.assertIsNone(b.plan('entry', clock(20), connections())['views']['BTC']['quantity'])
            self.assertIs(original.DepthReplay, before)

    def test_independent_arithmetic_preserves_supplied_float_midpoint_and_rejects_bad_cash(self):
        frames=final_frames()
        for f in frames:
            if f['venue']=='mexc':
                payload=json.loads(f['raw']);payload['data']['bids'][0][0]=99.01
                payload['data']['asks'][0][0]=101.03;f['raw']=json.dumps(payload)
        with tempfile.TemporaryDirectory() as tmp:
            result=self.issue(Path(tmp)/'a',True,frames)
            checks,outcomes=check_money(result,config())
            self.assertGreater(checks.n,300);self.assertEqual(len(outcomes),6)
            with self.assertRaises(AssertionError):helper().check_money(result,config())
            cell=next(c for c in result['cells'] if c['closed_price_fee_subtotal'] is not None)
            cell['price_fee_only_native_snapshot']['accounts'][0]['known_cash_component']='999999'
            with self.assertRaises(AssertionError):check_money(result,config())
