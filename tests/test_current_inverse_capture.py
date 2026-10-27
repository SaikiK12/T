import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import probe_current_inverse as probe


class CurrentInverseCaptureTests(unittest.TestCase):
    def fixture(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        root = Path(temporary.name); lane = root/'lane'; lane.mkdir()
        a = patch.object(probe, 'ROOT', root); b = patch.object(probe, 'LANE', lane)
        a.start(); b.start(); self.addCleanup(a.stop); self.addCleanup(b.stop)
        return probe.Acquisition()

    def test_reservations_survive_restart_without_dispatch_or_budget_reset(self):
        a = self.fixture(); a.reserve('one', 'https://example.invalid/no-network')
        b = probe.Acquisition()
        self.assertEqual(b.budget.status()['requests_charged'], 1)
        with self.assertRaises(ValueError): b.reserve('one', 'https://example.invalid/no-network')
        self.assertEqual(b.budget.status()['requests_charged'], 1)

    def test_all_three_accumulated_limits_close_at_registered_sixteen(self):
        a = self.fixture()
        for i in range(16): a.reserve(str(i), 'https://example.invalid/no-network')
        with self.assertRaises(ValueError): a.reserve('extra', 'https://example.invalid/no-network')
        status = a.budget.status()
        self.assertEqual(status['requests_charged'], 16)
        self.assertEqual(status['body_bytes_charged_upper_bound'], 8*1024**2)
        self.assertEqual(status['duration_ns_charged_upper_bound'], 128*probe.NS)

    def test_source_scope_has_no_account_order_or_historical_endpoint(self):
        urls = [url for _, url in probe.DOCS+probe.META]
        self.assertEqual(len(urls), 6)
        self.assertTrue(all(url.startswith('https://') for url in urls))
        self.assertFalse(any(x in url.lower() for url in urls for x in ('/order?', '/account', '/klines', 'token=', 'api_key')))
