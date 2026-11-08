from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import Message
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib import request

from lab.fred_quote_scope import FRED, admitted_rows, csv_view, fence, scoped_url
from lab.paper_transport import InheritedBudget
from lab.runtime_transport import TransportStop

NOW = datetime(2026, 11, 8, 14, 0, tzinfo=timezone.utc)
CSV = b'observation_date,DTB3\n2025-10-06,3.625\n2026-11-05,3.500\n'


class Reply(io.BytesIO):
    def __init__(self, body, *, encoding='', content_type='application/csv'):
        super().__init__(body)
        self.code = 200
        self.url = scoped_url(NOW)
        self.headers = Message()
        self.headers['Content-Type'] = content_type
        self.headers['Content-Length'] = str(len(body))
        if encoding:
            self.headers['Content-Encoding'] = encoding


class FredQuoteScope(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.folder = self.root / 'network'
        self.baseline = self.root / 'baseline.jsonl'
        self.frozen = self.root / 'frozen.jsonl'
        raw = b'{"event":"START","id":"0","reserved_bytes":16777216}\n{"event":"END","id":"0","charged_bytes":16384014}\n'
        self.baseline.write_bytes(raw);self.frozen.write_bytes(raw)
        self.policy = dict(prefixes=[FRED], wire_caps={FRED: 16384}, max_requests=4096,
                           max_body_bytes=16777216, max_decoded_bytes=4194304)

    @contextmanager
    def intercepted(self, opener):
        with patch.object(request.OpenerDirector, 'open', opener):
            with fence(self.folder, self.policy, baseline=self.baseline, frozen_baseline=self.frozen,
                       clock=lambda: NOW):
                yield

    def budget(self):
        return InheritedBudget(self.folder, dict(self.policy, response_cap=16384), self.baseline, self.frozen)

    def test_native_400_day_window_uses_utc_without_changing_series(self):
        self.assertEqual(scoped_url(NOW), FRED + '&cosd=2025-10-04&coed=2026-11-08')
        with self.assertRaises(ValueError):
            scoped_url(datetime(2026, 11, 8))

    def test_real_budget_boundary_is_reproduced_and_smaller_view_preserves_all_spend(self):
        calls = []
        self.policy['wire_caps'][FRED] = 393216
        with self.intercepted(lambda *a, **k: calls.append(1)), self.assertRaises(TransportStop):
            request.urlopen(FRED)
        self.assertEqual(calls, [])
        self.assertEqual(self.budget().usage(), (1, 16384014))
        self.policy['wire_caps'][FRED] = 16384
        def opened(_self, req, *args, **kwargs):
            calls.append(req.full_url)
            return Reply(CSV)
        with self.intercepted(opened):
            with request.urlopen(FRED) as response:
                self.assertEqual(response.read(), CSV)
        self.assertEqual(calls, [scoped_url(NOW)])
        self.assertEqual(self.budget().usage(), (2, 16384014 + len(CSV)))
        alias = json.loads((self.folder / 'quote_views.jsonl').read_text())
        self.assertEqual(alias['original_url'], FRED)
        self.assertEqual(alias['physical_url'], scoped_url(NOW))
        self.assertTrue(alias['source_body_unchanged'])

    def test_gzip_bytes_and_unchanged_decoded_csv_reach_original_caller(self):
        wire = gzip.compress(CSV, mtime=0)
        with self.intercepted(lambda *a, **k: Reply(wire, encoding='gzip')):
            with request.urlopen(FRED) as response:
                self.assertEqual(response.read(), CSV)
        self.assertEqual(self.budget().usage(), (2, 16384014 + len(wire)))

    def test_old_denial_cannot_be_avoided_by_date_parameters(self):
        with self.baseline.open('ab') as f:
            f.write(b'{"event":"BLOCK","key":"fred.stlouisfed.org/graph/fredgraph.csv","reason":"old denial"}\n')
        calls = []
        with self.intercepted(lambda *a, **k: calls.append(1)), self.assertRaises(TransportStop):
            request.urlopen(FRED)
        self.assertFalse(calls)

    def test_future_or_unbounded_csv_is_charged_then_persistently_blocked(self):
        bad = b'DATE,DTB3\n2020-01-01,3.25\n'
        with self.intercepted(lambda *a, **k: Reply(bad)), self.assertRaises(TransportStop):
            request.urlopen(FRED)
        self.assertEqual(self.budget().usage(), (2, 16384014 + len(bad)))
        calls = []
        with self.intercepted(lambda *a, **k: calls.append(1)), self.assertRaises(TransportStop):
            request.urlopen(FRED)
        self.assertFalse(calls)

    def test_bad_or_missing_rates_are_not_replaced_by_a_default(self):
        for value in [b'NaN', b'Infinity', b'bad', b'.']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                csv_view(b'DATE,DTB3\n2026-11-05,' + value + b'\n', NOW)

    def test_missing_dates_and_raw_rate_precision_survive(self):
        raw = b'DATE,DTB3\n2026-11-04,.\n2026-11-05,3.500000000000000001\n'
        rows = admitted_rows(raw, NOW)
        self.assertIsNone(rows[0][1])
        self.assertEqual(str(rows[1][1]), '3.500000000000000001')

    def test_authenticated_and_spoofed_requests_remain_forbidden(self):
        for header in [{'Cookie': 'synthetic'}, {'Authorization': 'synthetic'}, {'User-Agent': 'Mozilla/5.0'}]:
            calls = []
            with self.subTest(header=header), self.intercepted(lambda *a, **k: calls.append(1)), self.assertRaises(TransportStop):
                request.urlopen(request.Request(FRED, headers=header))
            self.assertFalse(calls)

    def test_unknown_old_reservations_are_not_discounted_to_the_new_cap(self):
        with self.baseline.open('ab') as f:
            f.write(b'{"event":"START","id":"1","reserved_bytes":300000}\n')
        with self.intercepted(lambda *a, **k: Reply(CSV)):
            self.assertEqual(request.urlopen(FRED).read(), CSV)
        self.assertEqual(self.budget().usage(), (3, 16384014 + 300000 + len(CSV)))

    def test_view_receipt_failure_cannot_be_swallowed_as_a_legacy_network_error(self):
        with self.intercepted(lambda *a, **k: Reply(CSV)), \
                patch('lab.fred_quote_scope.append', side_effect=OSError('synthetic disk failure')):
            with self.assertRaises(TransportStop):
                try:
                    request.urlopen(FRED)
                except OSError:
                    self.fail('audit failure reached the legacy fallback')

    def test_native_tbill_append_preserves_existing_history_and_only_adds_new_dates(self):
        from scripts import forward_lockcarry as native
        journal = self.root / 'journal';journal.mkdir()
        original = b't_ms,pct\n1793750400000,3.25\n'
        path = journal / 'tbill.csv';path.write_bytes(original)
        import os
        os.utime(path, ns=(0, 0))
        with self.intercepted(lambda *a, **k: Reply(CSV)):
            series = native.tbill_series(int(NOW.timestamp() * 1000), j=journal)
        self.assertTrue(path.read_bytes().startswith(original))
        self.assertGreater(len(series), 1)


if __name__ == '__main__':
    unittest.main()
