import asyncio
from decimal import Decimal as D
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from lab.live_pair_control import LivePairControl
from lab.stream_quotes import FrameClock, NS, SYMBOLS
from scripts import capture_live_pair_controls as capture
from scripts import check_live_pair_controls as checker
from tests.test_depth_quotes import depth_frame
from tests.test_stream_quotes import ANCHOR, UTC, frame, metadata
from tests.test_lighter_depth_state import message


def clock(s):
    return FrameClock(UTC + int(s * NS), ANCHOR.mono_ns + int(s * NS))


def config():
    return {'symbols': list(SYMBOLS), 'directions': [1, -1], 'cost_multiples': [1, 2, 3],
            'capital_per_venue': '5000', 'leg_budget': '250', 'fees_bp': {'mexc': '10', 'lighter': '4'},
            'entry_second': 20, 'exit_second': 50, 'deadline_lateness_ns': 250_000_000,
            'decision_to_execution_ns': 300_000_000, 'fx_scenario': {'USDT': '1', 'USDC': '1'}}


def connections():
    return {v: {'opened_mono_ns': ANCHOR.mono_ns, 'closed_mono_ns': None} for v in ('mexc', 'lighter')}


def initial():
    return [frame('mexc', 20), depth_frame(20)]


def final_frames(thin=False):
    change = message(begin=100, nonce=101, offset=11, stamp=UTC // 1000 + 50_000_000,
        bids=[{'price': '99', 'size': '.2'}, *([{'price': '98.5', 'size': '0'}] if thin else [])],
        asks=[{'price': '101.5', 'size': '0'}] if thin else [])
    return initial() + [frame('mexc', 20.3, version=2, ask=103),
        frame('mexc', 50, version=3), depth_frame(50, initial=False, data=change)]


class LivePairTests(unittest.TestCase):
    def observer(self, path):
        return LivePairControl(Path(path) / 'online', metadata(), {1: 'BTC'}, ANCHOR, config())

    def entered(self, path):
        o = self.observer(path)
        o.plan('entry', clock(20), initial(), connections())
        o.tick('entry', clock(20.3), final_frames()[:3], connections())
        return o

    def test_future_early_or_stepped_clock_cannot_make_a_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.observer(tmp)
            for when, frames in ((clock(19), initial()), (clock(20), initial() + [frame('mexc', 21)]),
                                  (FrameClock(clock(20).utc_ns + 100_000_000, clock(20).mono_ns), initial())):
                with self.assertRaises(ValueError):
                    o.plan('entry', when, frames, connections())
            self.assertFalse(o.receipts)

    def test_persisted_decision_precedes_execution_and_quantity_cannot_follow_later_price(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.observer(tmp)
            p = o.plan('entry', clock(20), initial(), connections())
            self.assertEqual(D(p['views']['BTC']['quantity']), D('2.5'))
            self.assertEqual(p['execution_not_before_ns'], clock(20.3).mono_ns)
            with self.assertRaises(ValueError):
                o.tick('entry', clock(20.2), initial(), connections())
            o.tick('entry', clock(20.3), final_frames()[:3], connections())
            for cell in o.cells.values():
                if cell['symbol'] == 'BTC':
                    self.assertEqual(D(cell['quantity']), D('2.5'))
                    for e in cell['account'].accepted_events:
                        self.assertEqual(abs(e.quantity), D('2.5'))
                        self.assertEqual(e.occurred_ns, clock(20.3).utc_ns)
            with self.assertRaises(ValueError):
                o.plan('entry', clock(21), initial(), connections())

    def test_exit_closes_original_q_with_action_time_separate_from_old_quote_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.entered(tmp)
            o.plan('exit', clock(50), final_frames(), connections())
            o.tick('exit', clock(50.3), final_frames(), connections())
            r = o.report(clock(60))
            self.assertEqual(len(r['cells']), 36)
            for cell in r['cells']:
                self.assertIsNone(cell['full_net_pnl'])
                self.assertIsNone(cell['funding_cash'])
                if cell['symbol'] == 'BTC':
                    self.assertIsNotNone(cell['closed_price_fee_subtotal'])
                    for close in cell['exit'].values():
                        self.assertEqual(D(close['quantity']).copy_abs(), D('2.5'))
                        self.assertEqual(close['model_action_clock'], vars(clock(50.3)))
                        self.assertEqual(close['source_first_seen_clock'], vars(clock(50)))
                    for account in cell['price_fee_only_native_snapshot']['accounts']:
                        self.assertFalse(account['positions'])
            self.assertEqual([x['stage'] for x in r['online_receipts']],
                             ['entry_decision', 'entry_execution', 'exit_decision', 'exit_execution'])
            self.assertEqual(r['prospective_strategy_days'], 0)

    def test_thin_exit_or_missed_exit_never_flattens_inventory(self):
        for thin in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                o = self.entered(tmp)
                if thin:
                    frames = final_frames(thin=True)
                    o.plan('exit', clock(50), frames, connections())
                    o.tick('exit', clock(50.3), frames, connections())
                r = o.report(clock(60))
                for cell in r['cells']:
                    if cell['symbol'] == 'BTC':
                        self.assertIsNone(cell['closed_price_fee_subtotal'])
                        self.assertTrue(all(a['positions'] for a in cell['price_fee_only_native_snapshot']['accounts']))
                if not thin:
                    self.assertEqual(r['missed_stages'], ['exit'])

    def test_late_persisted_entry_decision_cannot_create_position(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.observer(tmp)
            p = o.plan('entry', clock(20), initial(), connections(), completed_clock=lambda: clock(20.4))
            self.assertFalse(p['on_time'])
            o.tick('entry', clock(20.7), final_frames()[:3], connections())
            for cell in o.cells.values():
                self.assertFalse(cell['account'].accepted_events)

    def test_no_market_contract_or_negative_session_control_is_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.observer(tmp)
            r = o.plan('entry', clock(20), initial(), connections())
            self.assertIn('predeclared_metal_session_negative_control', r['views']['XPD']['reasons'])
            o.tick('entry', clock(20.3), initial(), connections())
            report = o.report(clock(30))
            self.assertEqual(len(report['cells']), 36)
            self.assertTrue(all(x['entry']['state'] == 'blocked' for x in report['cells'] if x['symbol'] != 'BTC'))

    def test_missing_fx_never_adds_separate_settlement_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = self.entered(tmp)
            del o.config['fx_scenario']
            report = o.report(clock(30))
            for cell in report['cells']:
                self.assertIsNone(cell['known_realized_price_fee_component'])
                self.assertIsNone(cell['closed_price_fee_subtotal'])
                self.assertIsNone(cell['full_net_pnl'])


class BoundedCaptureTests(unittest.TestCase):
    def test_source_denial_closes_unused_allowance_and_existing_directory_prevents_retry(self):
        class Network:
            def __init__(self, out):
                self.records = []; self.total = 0; self.read_upper_bound = 0

            def get(self, name, url):
                self.records.append({'name': name, 'url': url, 'http_status': 403})
                return None

        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp) / 'lane'; lane.mkdir()
            (lane / 'code_inputs.json').write_text('{}\n')
            with mock.patch.object(capture, 'verify', return_value=config()), \
                 mock.patch.object(capture.transport, 'Metadata', Network), \
                 mock.patch.object(capture.transport.old, 'LT_LOCK', Path(tmp) / 'lock'), \
                 mock.patch.object(capture.asyncio, 'run') as run:
                result = capture.capture(lane)
                self.assertEqual(len(result['cells']), 36)
                self.assertEqual(result['capture_state'], 'NOT_STARTED_OR_METADATA_BLOCKED')
                run.assert_not_called()
                with self.assertRaises(FileExistsError):
                    capture.capture(lane)
            receipt = json.loads((lane / 'evidence/receipts.json').read_text())
            self.assertEqual(receipt['requests'], 1)
            self.assertEqual(receipt['unused_metadata_slots_closed'], 6)
            self.assertEqual(receipt['scope_state'], 'CLOSED')
            self.assertIsNone(result['full_net_pnl'])

    def test_mirror_records_own_first_seen_before_parent_without_network_side_effect(self):
        class Socket:
            async def recv(self):
                return '{"type":"pong"}'

        frames = []; status = {'messages': 0, 'payload_bytes': 0}
        ws = capture.MirroredSocket(Socket(), 'lighter', status, frames, ANCHOR)
        with mock.patch.object(capture, 'clock', return_value=clock(20)), \
             mock.patch.object(capture.time, 'monotonic_ns', return_value=clock(19.9).mono_ns):
            self.assertEqual(asyncio.run(ws.recv()), '{"type":"pong"}')
        self.assertEqual(frames[0]['mono_ns'], clock(20).mono_ns)
        self.assertEqual(frames[0]['number'], 1)
        self.assertEqual(status['messages'], 0)
        self.assertLess(frames[0]['read_started_mono_ns'], frames[0]['mono_ns'])

    def test_independent_checker_accepts_known_fixture_and_rejects_corrupted_money(self):
        # Invented input only. This test performs no public/private request and
        # cannot count as a prospective ticket or a live market observation.
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp) / 'fixture'; lane.mkdir()
            evidence = lane / 'evidence'; evidence.mkdir()
            frames = final_frames()
            for f in frames:
                f['read_started_mono_ns'] = f['mono_ns'] - 1
            con = connections()
            for state in con.values():
                state['handshake_attempts'] = 1
            o = LivePairControl(evidence / 'online', metadata(), {1: 'BTC'}, ANCHOR, config())
            for stage, when in [('entry', 20), ('exit', 50)]:
                o.plan(stage, clock(when), [f for f in frames if f['mono_ns'] <= clock(when).mono_ns], con)
                o.tick(stage, clock(when + .3), [f for f in frames if f['mono_ns'] <= clock(when + .3).mono_ns], con)
            result = o.report(clock(65)); result['capture_state'] = 'FINISHED_OR_PARTIAL'
            result['errors'] = []
            (lane / 'results.json').write_bytes(checker.encoded(result))
            (evidence / 'first_seen.jsonl.gz').write_bytes(gzip.compress(b''.join(checker.encoded(f) for f in frames), mtime=0))
            (evidence / 'anchor.json').write_bytes(checker.encoded(vars(ANCHOR)))
            (evidence / 'connections.json').write_bytes(checker.encoded(con))
            for v in ('mexc', 'lighter'):
                (evidence / (v + '.jsonl.gz')).write_bytes(gzip.compress(b''.join(checker.encoded(f) for f in frames if f['venue'] == v), mtime=0))
            scope = {'scope_state': 'CLOSED', 'requests': 0, 'unused_metadata_slots_closed': 7,
                     'records': [], 'response_bytes': 0, 'response_body_read_upper_bound': 0,
                     'duration_seconds': 65, 'metadata_window_started_clock': vars(ANCHOR),
                     'mirrored_first_seen_frames': len(frames)}
            (evidence / 'receipts.json').write_bytes(checker.encoded(scope))
            (lane / 'code_inputs.json').write_bytes(checker.encoded({'sha256': {}}))
            (lane / 'config.json').write_bytes(checker.encoded(config()))
            (lane / 'sources.json').write_bytes(checker.encoded({'scope': 'invented unittest only'}))
            spec = '\n'.join(hashlib.sha256((lane / p).read_bytes()).hexdigest()
                             for p in ['code_inputs.json', 'config.json', 'sources.json']).encode()
            (lane / 'PREREG.md').write_bytes(spec)
            (lane / 'PREREG.sha256').write_text(hashlib.sha256(spec).hexdigest() + '\n')

            def seal():
                identity = {'sha256': {str(p.relative_to(lane)): hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in evidence.rglob('*') if p.is_file()},
                            'result_sha256': hashlib.sha256((lane / 'results.json').read_bytes()).hexdigest()}
                (lane / 'evidence_inputs.json').write_bytes(checker.encoded(identity))

            seal()
            with mock.patch.object(checker, 'LANE', lane), mock.patch('sys.argv', ['check', '--out', str(Path(tmp) / 'pass')]), redirect_stdout(io.StringIO()):
                checker.main()
            self.assertEqual(json.loads((Path(tmp) / 'pass/audit.json').read_text())['closed_price_fee_cells'], 6)
            target = next(c for c in result['cells'] if c['symbol'] == 'BTC')
            target['price_fee_only_native_snapshot']['accounts'][0]['known_cash_component'] = '999999'
            (lane / 'results.json').write_bytes(checker.encoded(result)); seal()
            with mock.patch.object(checker, 'LANE', lane), mock.patch('sys.argv', ['check', '--out', str(Path(tmp) / 'fail')]), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(AssertionError, 'native known price/fee cash'):
                    checker.main()


if __name__ == '__main__':
    unittest.main()
