"""Faults in invented R266 observations; no market archive, writer or network."""
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from lab import operations, runtime
from scripts import forward_unlocks as frozen

DAY, H = 24 * runtime.HOUR, runtime.HOUR
D = 1793059200000  # 2026-10-27


class UnlockJournal(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.j = self.root / 'experiments/unlocks_fwd/journal'
        self.j.mkdir(parents=True)
        self.snap = self.root / 'data/recorders/unlocks/2026-10-20.json.gz'
        self.snap.parent.mkdir(parents=True)
        self.snap.write_bytes(b'invented snapshot bytes; no calendar eligibility assertion')
        self.ticket = dict(zip(frozen.TICKET_COLS, ['U20753-TOY_USDT', 'toy', 'TOY', 'TOY_USDT', 1,
            True, '2026-10-27', D - 6 * DAY, D + DAY, .02, 100,
            self.snap.name, hashlib.sha256(self.snap.read_bytes()).hexdigest(),
            '2026-10-20T16:29:56Z', 1, 1, 1, .0004]))
        self.now = D + DAY + H + 600000

    def write(self, name, fields, rows):
        with (self.j / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fields)
            writer.writeheader()
            writer.writerows(rows)

    def tickets(self, rows=None):
        self.write('tickets.csv', frozen.TICKET_COLS, [self.ticket] if rows is None else rows)

    def check(self, phase='after'):
        return runtime.check('unlock_journal', self.root, now_ms=self.now, phase=phase)

    def score(self, **changes):
        row = dict(ticket=self.ticket['ticket'], entry_price=100, exit_price=90, stopped_trading=False,
            gross=.1, funding=.001, settlements=21, taker=.0004, spread_entry=.0001,
            spread_exit=.0001, spread_flag=False, cost_measured=.001, net=.1,
            net_1x=.099, net_2x=.097, net_3x=.095, mae=.02, mfe=.12,
            liq_1x=False, liq_2x=False, liq_3x=False, scored_at='2026-10-28T01:10:00Z')
        row.update(changes)
        return row

    def test_unchanged_native_writer_passes_ticket_to_score_fixture(self):
        import gzip
        import pandas as pd
        from unittest.mock import patch
        from tests.test_forward_unlocks import SNAP, TABLE, LAST, bars
        self.snap.write_bytes(gzip.compress(json.dumps(SNAP).encode()))
        def tick(now):
            return frozen.tick(now, contracts=lambda: TABLE, last_price=lambda c: LAST[c],
                klines=lambda c, a, b: bars(a, b - 2 * H, (2., 1.8)),
                funding=lambda c, a, b: pd.DataFrame({'t': [a + 8 * H, a + 16 * H], 'rate': [-.001, .0005]}),
                binance_bases={'AAA'}, snaps=self.snap.parent, ticks=self.root / 'empty-tickers')
        with patch.object(frozen, 'J', self.j):
            entry = D - 6 * DAY
            tick(entry - 12 * H)
            received = runtime.check('unlock_journal', self.root, now_ms=entry - 12 * H)
            self.assertTrue(received['usable'], received)
            now = D + DAY + H + 1_200_000
            tick(now)
            received = runtime.check('unlock_journal', self.root, now_ms=now)
            self.assertTrue(received['usable'], received)
            self.assertEqual(received['scores'], 1)
            self.assertEqual(received['source_validation'], 'UNVERIFIED')
            self.assertEqual(received['gate_eligibility'], 'UNASSESSED')

    def test_graph_installs_guard_on_the_native_paper_lane(self):
        self.assertEqual(next(t for t in operations.forward_tasks() if t.name == 'R266').checks, ('unlock_journal',))

    def test_bootstrap_and_legitimate_skip_only_tick(self):
        self.assertTrue(self.check('before')['usable'])
        self.assertFalse(self.check()['usable'])
        self.write('skipped.csv', frozen.SKIP_COLS, [dict(gecko_id='other', ticker='OTHER', day='2026-10-27',
            reason='no_contract', detail='', snapshot=self.snap.name, noted_at='2026-10-20T16:29:56Z')])
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=0, scored=0, open=0, updated='2026-10-28T01:10:00Z')))
        self.write('book_days.csv', ['day', 'ret', 'equity', 'drawdown'], [])
        self.assertTrue(self.check('before')['usable'])
        self.assertTrue(self.check()['usable'])

    def test_complete_open_and_scored_ticket_are_read_only(self):
        self.tickets()
        self.assertEqual(self.check('before')['open'], 1)
        self.write('scores.csv', frozen.SCORE_COLS, [self.score()])
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=1, open=0, updated='2026-10-28T01:10:00Z')))
        self.write('book_days.csv', ['day', 'ret', 'equity', 'drawdown'],
                   [dict(day='2026-10-28', ret=.01, equity=1.01, drawdown=0.)])
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.check()
        self.assertTrue(result['usable'])
        self.assertEqual(result['scores'], 1)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_scored_book_cannot_be_empty_duplicated_or_unordered(self):
        self.tickets()
        self.write('scores.csv', frozen.SCORE_COLS, [self.score()])
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=1, open=0, updated='2026-10-28T01:10:00Z')))
        a = dict(day='2026-10-27', ret=0., equity=1., drawdown=0.)
        b = {**a, 'day': '2026-10-28'}
        for rows in ([], [a, a], [b, a]):
            self.write('book_days.csv', ['day', 'ret', 'equity', 'drawdown'], rows)
            self.assertFalse(self.check()['usable'])

    def test_postflight_requires_fresh_derived_outputs(self):
        self.tickets()
        self.assertTrue(self.check('before')['usable'])
        self.assertFalse(self.check()['usable'])
        self.write('book_days.csv', ['day', 'ret', 'equity', 'drawdown'], [])
        for updated in ('2026-10-27T00:00:00Z', '2026-10-29T00:00:00Z'):
            (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=0, open=1, updated=updated)))
            self.assertFalse(self.check()['usable'])
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=0, open=1, updated='2026-10-28T01:10:00Z')))
        self.assertTrue(self.check()['usable'])

    def test_duplicate_ticket_event_and_contract_keys_rejected(self):
        for field, value in [('ticket', self.ticket['ticket']), ('gecko_id', 'different')]:
            other = {**self.ticket, field: value}
            self.tickets([self.ticket, other])
            self.assertFalse(self.check('before')['usable'])

    def test_partial_csv_and_missing_ticket_cannot_restart_writer(self):
        self.tickets()
        p = self.j / 'tickets.csv'
        p.write_bytes(p.read_bytes().rstrip(b'\r\n'))
        self.assertFalse(self.check('before')['usable'])
        p.unlink()
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=0, open=1)))
        self.assertFalse(self.check('before')['usable'])

    def test_header_only_ticket_loss_and_prior_score_count_fail(self):
        self.tickets([])
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=0, open=1)))
        self.assertFalse(self.check('before')['usable'])
        self.tickets()
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=1, scored=1, open=0)))
        self.assertFalse(self.check('before')['usable'])
        # A complete journal append may precede the derived status update.
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=0, scored=0, open=0)))
        self.assertTrue(self.check('before')['usable'])

    def test_cutoffs_and_future_snapshots_fail(self):
        for changes in [dict(frozen_at='2026-10-21T01:00:00Z'),
                        dict(frozen_at='2026-10-19T23:59:59Z'),
                        dict(exit_ms=D), dict(last_at_freeze=100), dict(index_price=1e-300, mult=1e-300), dict(snapshot='../2026-10-20.json.gz'),
                        dict(snapshot='2026-10-22.json.gz')]:
            self.tickets([{**self.ticket, **changes}])
            self.assertFalse(self.check('before')['usable'], changes)

    def test_missing_mismatched_and_symlink_snapshot_fail(self):
        self.tickets()
        self.snap.write_bytes(b'changed')
        self.assertFalse(self.check('before')['usable'])
        self.snap.unlink()
        self.assertEqual(self.check('before')['state'], 'MISSING_SNAPSHOT')
        self.snap.symlink_to(self.j / 'tickets.csv')
        self.assertFalse(self.check()['usable'])

    def test_orphan_duplicate_early_and_inconsistent_scores_fail(self):
        self.tickets()
        for rows in [[self.score(ticket='unknown')], [self.score(), self.score()],
                     [self.score(scored_at='2026-10-28T01:09:59Z')], [self.score(net=.5)],
                     [self.score(net_2x=.2)], [self.score(taker=.0)], [self.score(mae=2.)], [self.score(funding=float('nan'))]]:
            self.write('scores.csv', frozen.SCORE_COLS, rows)
            self.assertFalse(self.check('before')['usable'], rows)

    def test_orchestrator_blocks_before_the_writer_is_started(self):
        from dataclasses import replace
        import sys
        from unittest.mock import patch
        from scripts import orchestrate_forward as orchestrator
        self.tickets([self.ticket, self.ticket])
        task = replace(next(t for t in operations.forward_tasks() if t.name == 'R266'),
                       argv=(sys.executable, '-c', 'raise RuntimeError("writer must not run")'), optional=())
        state = self.root.parent / (self.root.name + '-state')
        self.addCleanup(lambda: __import__('shutil').rmtree(state, ignore_errors=True))
        with patch.object(orchestrator, 'run_process') as process, \
                patch.object(orchestrator, 'code_version', return_value={'fixture': 'unchanged'}):
            report = orchestrator.run_tasks([task], self.root, state, 'blocked')
        process.assert_not_called()
        self.assertEqual(report['tasks'][0]['status'], 'BLOCKED')
        self.assertEqual(report['tasks'][0]['data_state'], 'INCOMPLETE')

    def test_zero_ticket_status_cannot_hide_a_score(self):
        (self.j / 'status.json').write_text(json.dumps(dict(tickets=0, scored=0, open=0)))
        self.write('scores.csv', frozen.SCORE_COLS, [self.score()])
        self.assertFalse(self.check()['usable'])
