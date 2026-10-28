from copy import deepcopy
from dataclasses import FrozenInstanceError
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from lab.depth_replay import DepthReplay
from lab.incremental_pair_control import IncrementalDepthReplay, IncrementalPairControl
from lab import live_pair_control as original
from lab.stream_quotes import NS, SYMBOLS
from tests.test_depth_quotes import depth_frame
from tests.test_lighter_depth_state import message
from tests.test_live_pair_control import clock, config, connections, final_frames, initial
from tests.test_stream_quotes import ANCHOR, UTC, frame, metadata
from scripts.check_incremental_pair_control import check_money


def ordered(frames):
    return sorted(frames, key=lambda f: (f['mono_ns'], f['venue'], f['number']))


class IncrementalDepthTests(unittest.TestCase):
    def engine(self, cs=None):
        return IncrementalDepthReplay(metadata(), {1: 'BTC'}, ANCHOR, cs or connections())

    def compare(self, stream, points, cs=None):
        cs = cs or connections()
        incremental = self.engine(cs)
        frames, index = ordered(stream), 0
        for when in points:
            while index < len(frames) and frames[index]['mono_ns'] <= when:
                incremental.receive(frames[index]); index += 1
            baseline = DepthReplay(frames[:index], metadata(), {1: 'BTC'}, ANCHOR, cs)
            for profile in ('full', 'top_only', 'full'):
                for symbol in SYMBOLS:
                    a = baseline.observe(symbol, when, D('2.5'), allow_new_quantity=False, profile=profile)
                    b = incremental.observe(symbol, when, D('2.5'), allow_new_quantity=False, profile=profile)
                    self.assertEqual(a, b)
            self.assertEqual(baseline.errors, incremental.errors)
            self.assertEqual(baseline.assembly_events, incremental.assembly_events)
        return incremental

    def test_every_prefix_idle_noop_and_profile_keep_exact_first_seen_clocks(self):
        stream = initial() + [frame('mexc', 20.3, version=2), depth_frame(20.3, initial=False),
                              depth_frame(20.4, data={'type': 'pong'})]
        self.compare(stream, [clock(s).mono_ns for s in (19, 20, 20.3, 20.4, 21.4)])

    def test_corrupt_conflicting_duplicate_regression_and_nonce_gap_poison_identically(self):
        variants = [
            [frame('mexc', 20.1, version=1, ask=999)],
            [frame('mexc', 20.1, version=0)],
            [depth_frame(20.1, data=message(begin=999, stamp=UTC//1000+20_100_000))],
            [depth_frame(20.1, data=[])],
            [depth_frame(20.1, data={'type': 'shutdown'})],
        ]
        corrupt = frame('mexc', 20.1, version=2); corrupt['raw'] = 'bad-json'
        variants.append([corrupt])
        for suffix in variants:
            with self.subTest(suffix=suffix):
                self.compare(initial() + suffix + [depth_frame(20.2, data={'type': 'pong'})],
                             [clock(s).mono_ns for s in (20, 20.1, 20.2, 21.2)])

    def test_retransmission_content_with_new_number_never_refreshes_liquidity(self):
        duplicate = deepcopy(depth_frame(20)); duplicate['mono_ns'] = clock(20.2).mono_ns
        duplicate['utc_ns'] = clock(20.2).utc_ns; duplicate['number'] += 1
        self.compare(initial() + [duplicate], [clock(s).mono_ns for s in (20, 20.2, 21.2)])

    def test_source_or_local_clock_step_and_future_availability_remain_vetoes(self):
        stepped = depth_frame(20.1, initial=False); stepped['utc_ns'] += 100_000_000
        self.compare(initial() + [stepped, frame('mexc', 21, version=2)],
                     [clock(s).mono_ns for s in (19.9, 20, 20.1, 20.2, 21)])

    def test_unusable_boundary_precedes_close_and_epoch_cannot_be_reset(self):
        cs = connections(); cs['lighter']['closed_mono_ns'] = clock(22).mono_ns
        cs['lighter']['unusable_mono_ns'] = clock(20.1).mono_ns
        r = self.compare(initial(), [clock(s).mono_ns for s in (20, 20.1, 21)], cs)
        with self.assertRaises(ValueError):
            r.update_connections(connections())
        changed = deepcopy(cs); changed['lighter']['opened_mono_ns'] += NS
        with self.assertRaises(ValueError):
            r.update_connections(changed)
        fresh = self.engine()
        for f in ordered(initial()): fresh.receive(f)
        fresh.update_connections(cs)
        row, _ = fresh.observe('BTC', clock(20.1).mono_ns)
        self.assertIn('lighter:disconnected', row['book_flags'])
        self.assertEqual(row['lighter_assembly']['reason'], 'transport disconnected')

    def test_frames_metadata_and_encoding_are_owned_without_mutable_cache_reuse(self):
        md, f = metadata(), depth_frame(20)
        r = IncrementalDepthReplay(md, {1: 'BTC'}, ANCHOR, connections())
        copied = r.receive(f); saved = copied.canonical
        f['raw'] = 'corrupted after receive'; md['BTC']['mexc']['apiAllowed'] = False
        self.assertNotEqual(copied['raw'], f['raw'])
        self.assertEqual(copied.canonical, saved)
        self.assertTrue(r.metadata['BTC']['mexc']['apiAllowed'])
        with self.assertRaises(FrozenInstanceError): copied.canonical = b'new'
        with self.assertRaises(TypeError): copied['mono_ns'] = clock(21).mono_ns
        self.assertEqual(saved, original.encoded(dict(copied)))

    def test_regressive_receipt_backfill_or_capacity_failure_cannot_mutate_prefix(self):
        r = self.engine(); f = depth_frame(20); r.receive(f)
        for bad in (f, depth_frame(19), frame('mexc', 19), {**frame('mexc', 21), 'utc_ns': True},
                    {**frame('mexc', 21), 'raw': 'x' * (256*1024+1)}):
            with self.assertRaises(ValueError): r.receive(bad)
            self.assertEqual(len(r.received), 1)
        r.observe('BTC', clock(21).mono_ns)
        with self.assertRaises(ValueError): r.receive(frame('mexc', 20.9))
        r.frame_counts['mexc'] = 20000
        with self.assertRaises(ValueError): r.receive(frame('mexc', 21.1))
        self.assertEqual(len(r.received), 1)


class IncrementalControllerTests(unittest.TestCase):
    def issue(self, directory, adaptive, frames=None, cs=None, late=False):
        cs = cs or connections(); frames = ordered(frames or final_frames())
        ctor = IncrementalPairControl if adaptive else original.LivePairControl
        args = (Path(directory), metadata(), {1: 'BTC'}, ANCHOR, config())
        c = ctor(*args, cs) if adaptive else ctor(*args)
        index = 0
        for stage, kind, second in (('entry','plan',20), ('entry','tick',20.7 if late else 20.3),
                                    ('exit','plan',50), ('exit','tick',50.3)):
            now = clock(second)
            while index < len(frames) and frames[index]['mono_ns'] <= now.mono_ns:
                if adaptive: c.receive(frames[index])
                index += 1
            issued = clock(second + .4) if late and stage == 'entry' and kind == 'plan' else now
            args = (stage, now, cs) if adaptive else (stage, now, frames[:index], cs)
            getattr(c, kind)(*args, completed_clock=lambda c=issued: c)
        return c.report(clock(60))

    def test_exact_journals_receipts_original_lot_costs_and_unknown_funding(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'baseline', Path(tmp)/'incremental'
            self.assertEqual(self.issue(a, False), self.issue(b, True))
            self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()},
                             {p.name:p.read_bytes() for p in b.iterdir()})

    def test_thin_missing_closed_session_and_late_entry_keep_all_refusals(self):
        bad = final_frames(thin=True)
        for frames, cs, late in ((bad, None, False), (initial(), None, False),
                                (None, {**connections(), 'lighter': {'opened_mono_ns': 0,
                                     'closed_mono_ns': clock(49).mono_ns}}, False), (None, None, True)):
            with tempfile.TemporaryDirectory() as tmp:
                a = self.issue(Path(tmp)/'a', False, frames, cs, late)
                b = self.issue(Path(tmp)/'b', True, frames, cs, late)
                self.assertEqual(a, b)
                self.assertTrue(all(c['full_net_pnl'] is None for c in b['cells']))

    def test_instance_dependency_binding_never_patches_other_or_original_controllers(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = original.DepthReplay
            a = IncrementalPairControl(Path(tmp)/'a', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            b = IncrementalPairControl(Path(tmp)/'b', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            for f in ordered(initial()): a.receive(f)
            pa = a.plan('entry', clock(20), connections())
            pb = b.plan('entry', clock(20), connections())
            self.assertIs(original.DepthReplay, before)
            self.assertIsNotNone(pa['views']['BTC']['quantity'])
            self.assertIsNone(pb['views']['BTC']['quantity'])
            with self.assertRaises(ValueError): a.plan('entry', clock(20), connections())

    def test_future_owned_state_cannot_be_backdated_and_new_adapter_has_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = IncrementalPairControl(Path(tmp)/'a', metadata(), {1:'BTC'}, ANCHOR, config(), connections())
            c.receive(frame('mexc', 21))
            with self.assertRaises(ValueError): c.plan('entry', clock(20), connections())
            self.assertFalse(c.control.receipts)
            self.assertFalse(c.control.cells['BTC_d1_k1']['account'].accepted_events)

    def test_independent_money_checker_rejects_corrupted_closed_cash(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.issue(Path(tmp)/'a', True)
            checks, outcomes = check_money(result, config())
            self.assertGreater(checks.n, 200)
            self.assertEqual(len(outcomes), 6)
            next(c for c in result['cells'] if c['closed_price_fee_subtotal'] is not None)['closed_price_fee_subtotal'] = '999999'
            with self.assertRaises(AssertionError): check_money(result, config())


if __name__ == '__main__':
    unittest.main()
