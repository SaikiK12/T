import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import project_status


class Status(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        (self.root / 'registry').mkdir(parents=True)
        (self.root / 'registry/methods.csv').write_text('id,status\nM1,BLOCKED\n')

    def env(self):
        return patch.object(project_status, 'environment', return_value={'qx_source_binding': 'MATCHES_BUILD_RECEIPT'})

    def test_missing_receipts_cannot_be_success_and_read_does_not_write(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        with self.env():
            report = project_status.build_status(self.root, now=100)
        self.assertTrue(report['operational_attention_required'])
        self.assertTrue(all(t['state'] == 'UNKNOWN' for t in report['tasks']))
        self.assertEqual(report['queue']['by_status'], {'BLOCKED': 1})
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))

    def test_successful_process_with_partial_or_stale_data_stays_attention(self):
        state = Path(self.tmp.name) / 'external'
        run = state / 'toy'
        run.mkdir(parents=True)
        (run / 'status.json').write_text(json.dumps({'schema_version': 1, 'root': str(self.root),
            'run_id': 'toy', 'started_at': '1970-01-01T00:00:01Z', 'tasks': [
                {'name': 'R200', 'status': 'SUCCESS', 'returncode': 0,
                 'data_state': 'INCOMPLETE', 'finished_at': '1970-01-01T00:00:02Z'}]}))
        with self.env():
            report = project_status.build_status(self.root, state_dir=state, now=10000)
        item = next(t for t in report['attention'] if t['task_id'] == 'R200')
        self.assertEqual(item['reasons'], ['stale_receipt', 'data_incomplete'])
        self.assertEqual(report['gate_eligibility'], 'UNASSESSED')

    def test_malformed_external_state_is_explicit(self):
        with self.env():
            report = project_status.build_status(self.root, state_dir=Path(self.tmp.name)/'absent', now=100)
        self.assertIn('REPORT_INPUT', [t['task_id'] for t in report['attention']])


if __name__ == '__main__':
    unittest.main()
