from contextlib import redirect_stdout
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.check_method_intake import audit, main


class MethodIntakeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('docs/SOURCE.md', '# Received source\n')
        digest = hashlib.sha256((self.root/'docs/SOURCE.md').read_bytes()).hexdigest()
        self.payload = {
            'methods': [dict(id='SRC1', title='Weak rule retained', status='blocked',
                             exact_tested_scope='No exact registered test', unrun_scope='Needs mechanics',
                             next_action='Define missing inputs and controls', required_inputs=['input'],
                             blockers=['input not held'], source_refs=[dict(path='docs/SOURCE.md')])],
            'sources': [dict(path='docs/SOURCE.md', sha256=digest, current_sha256=digest,
                             current_source_review_required=False, method_ids=['SRC1'])],
        }
        self.queue = [dict(id='M001', method='Weak rule', status='BLOCKED', data_held='N', rid='-')]
        self.aliases = [dict(rec_id='SRC1', title='Source rule', intake_status='blocked', queue_id='M001', also='')]
        self.save()

    def write(self, path, text):
        file = self.root/path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding='utf-8')

    def csv(self, path, fields, rows):
        self.write(path, '')
        with (self.root/path).open('w', newline='', encoding='utf-8') as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def save(self):
        self.write('research/intake/source_methods_20261020.json', json.dumps(self.payload))
        self.csv('registry/methods.csv', ['id', 'method', 'status', 'data_held', 'rid'], self.queue)
        self.csv('registry/methods_aliases.csv', ['rec_id', 'title', 'intake_status', 'queue_id', 'also'], self.aliases)

    def codes(self):
        return {i['code'] for i in audit(self.root)['issues']}

    def test_clean_audit_preserves_every_byte_and_historical_status(self):
        # A later queue result must not rewrite the intake snapshot.
        self.queue[0]['status'] = 'TESTED'
        self.queue[0]['rid'] = 'R999 NULL'
        self.save()
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report = audit(self.root)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(report['summary']['errors'], 0)
        self.assertEqual(report['summary']['warnings'], 0)
        self.assertEqual(before, after)
        self.assertEqual(self.payload['methods'][0]['status'], 'blocked')

    def test_reserved_gaps_multi_targets_and_context_are_valid(self):
        self.queue.append(dict(id='M260', method='Reserved writer block', status='UNTESTED', data_held='Y', rid='-'))
        self.aliases[0]['queue_id'] = 'M001;M260'
        self.aliases[0]['also'] = 'CONTEXT'
        self.aliases[0]['intake_status'] = 'context'
        self.save()
        self.assertEqual(audit(self.root)['summary']['errors'], 0)

    def test_queued_is_pending_without_promoting_source_snapshot(self):
        self.queue[0]['status'] = 'QUEUED'
        self.queue[0]['rid'] = 'R276 draft; not frozen'
        self.save()
        self.assertEqual(audit(self.root)['summary']['errors'], 0)
        self.assertEqual(self.payload['methods'][0]['status'], 'blocked')

    def test_duplicate_and_dangling_ids_fail(self):
        self.queue.append(copy.deepcopy(self.queue[0]))
        self.aliases[0]['queue_id'] = 'M999'
        self.aliases.append(dict(rec_id='ORPHAN', title='missing', intake_status='blocked', queue_id='M001', also='M998'))
        self.payload['methods'].append(dict(self.payload['methods'][0], id='UNMAPPED'))
        self.save()
        self.assertTrue({'DUPLICATE_ID', 'QUEUE_TARGET_MISSING', 'SOURCE_METHOD_MISSING', 'ALIAS_MISSING'} <= self.codes())

    def test_missing_scope_and_source_are_explicit_errors(self):
        self.payload['methods'][0]['unrun_scope'] = ''
        self.payload['methods'][0]['source_refs'] = []
        self.save()
        self.assertTrue({'SCOPE_MISSING', 'SOURCE_REFERENCE_MISSING'} <= self.codes())

    def test_source_drift_and_pending_review_remain_separate(self):
        self.payload['sources'][0]['current_source_review_required'] = True
        self.save()
        self.assertEqual(self.codes(), {'SOURCE_REVIEW_PENDING'})
        self.write('docs/SOURCE.md', '# Added unreviewed text\n')
        self.assertEqual(self.codes(), {'SOURCE_REVIEW_PENDING', 'SOURCE_CHANGED_SINCE_REVIEW'})
        report = audit(self.root)
        self.assertEqual(report['summary']['errors'], 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--root', str(self.root)]), 0)
            self.assertEqual(main(['--root', str(self.root), '--strict']), 1)

    def test_explicit_reviewed_history_retains_snapshot_and_detects_later_drift(self):
        source = self.payload['sources'][0]
        snapshot = source['sha256']
        self.write('docs/SOURCE.md', '# Reviewed revision\n')
        reviewed = hashlib.sha256((self.root/'docs/SOURCE.md').read_bytes()).hexdigest()
        source['current_sha256'] = reviewed
        self.payload['supplemental_intakes'] = [dict(intake_id='REVISION', records_added=[], media_sources=[])]
        source['reviewed_version_history'] = [
            dict(sha256=snapshot, reviewed_utc_date='2026-10-20', superseded_by_intake='REVISION'),
            dict(sha256=reviewed, reviewed_utc_date='2026-10-20', intake_id='REVISION'),
        ]
        self.save()
        self.assertEqual(self.codes(), set())
        self.assertEqual(source['sha256'], snapshot)
        self.write('docs/SOURCE.md', '# Unreviewed later revision\n')
        self.assertEqual(self.codes(), {'SOURCE_CHANGED_SINCE_REVIEW'})
        # Merely changing current_sha256 without a new review must stay ambiguous.
        source['current_sha256'] = hashlib.sha256((self.root/'docs/SOURCE.md').read_bytes()).hexdigest()
        self.save()
        self.assertEqual(self.codes(), {'SOURCE_VERSION_AMBIGUOUS'})

    def test_history_requires_a_valid_date_and_known_intake(self):
        self.payload['sources'][0]['reviewed_version_history'] = [
            dict(sha256=self.payload['sources'][0]['sha256'], reviewed_utc_date='not-a-date', intake_id='UNKNOWN')]
        self.save()
        self.assertIn('SOURCE_HISTORY_INVALID', self.codes())

    def test_supplement_counts_duplicate_records_and_actual_basis(self):
        self.payload['supplemental_intakes'] = [dict(
            intake_id='BATCH', records_added=['SRC1', 'SRC1', 'ABSENT'], media_source_count=2,
            media_sources=[dict(url='https://example.org', title='Title only')])]
        self.save()
        self.assertTrue({'SUPPLEMENT_METHOD_MISSING', 'SUPPLEMENT_RECORD_DUPLICATE',
                         'SOURCE_COUNT_MISMATCH', 'SOURCE_BASIS_MISSING'} <= self.codes())

    def test_provider_scope_urls_and_targets(self):
        self.write('research/intake/source_catalog_test.csv',
                   'id,provider,url,received_scope,access_boundary,existing_queue\n'
                   'P1,Provider,https://example.org,,paid catalog only,M999\n'
                   'P2,Provider,https://example.org,docs only,unverified,M001\n'
                   'P3,Provider,https://[,docs only,unverified,M001\n')
        self.assertTrue({'PROVIDER_SCOPE_MISSING', 'PROVIDER_URL_DUPLICATE',
                         'QUEUE_TARGET_MISSING', 'PROVIDER_URL_INVALID'} <= self.codes())

    def test_unsafe_paths_and_symlinks_do_not_read_sources(self):
        self.payload['sources'][0]['path'] = '../outside.txt'
        self.payload['methods'][0]['source_refs'] = [dict(path='../outside.txt')]
        self.save()
        self.assertTrue({'SOURCE_FILE_UNREADABLE', 'SOURCE_REFERENCE_INVALID'} <= self.codes())
        self.payload['sources'][0]['path'] = 'docs/LINK.md'
        (self.root/'docs/LINK.md').symlink_to(self.root/'docs/SOURCE.md')
        self.save()
        self.assertIn('SOURCE_FILE_UNREADABLE', self.codes())

    def test_malformed_payloads_report_instead_of_crashing(self):
        for replacement in [None, [], {'methods': [1]}]:
            with self.subTest(payload=replacement):
                self.write('research/intake/source_methods_20261020.json', json.dumps(replacement))
                self.assertIn('INTAKE_INVALID', self.codes())
        self.payload['sources'][0]['method_ids'] = None
        self.payload['methods'][0]['source_refs'] = [17]
        self.save()
        self.assertTrue({'SOURCE_SCHEMA_INVALID', 'SOURCE_REFERENCE_INVALID'} <= self.codes())

    def test_malformed_csv_and_unknown_states_fail(self):
        self.queue[0]['status'] = 'APPROVED_LIVE'
        self.payload['methods'][0]['status'] = 'proven_profitable'
        self.save()
        self.assertTrue({'QUEUE_STATUS_INVALID', 'INTAKE_STATUS_INVALID'} <= self.codes())
        self.write('registry/methods.csv', 'id,method\nM001,incomplete\n')
        self.assertIn('TABLE_INVALID', self.codes())

    def test_conflict_markers_fail_without_a_cascade_of_false_alias_errors(self):
        self.write('registry/methods.csv', '<<<<<<< HEAD\ninvalid\n=======\nother\n>>>>>>> branch\n')
        self.assertEqual(self.codes(), {'TABLE_INVALID'})

    def test_documented_collision_preserves_original_rule_and_checks_new_target(self):
        row = self.queue[0]
        annotation = dict(declared_id='M247', canonical_id='M001', reason='Collision on import',
                          source_commit='abc1234', round='R269',
                          original_header=list(row), original_row=['M247']+list(row.values())[1:])
        self.write('registry/method_id_reassignment_R269.json', json.dumps(annotation))
        self.assertEqual(audit(self.root)['summary']['id_reassignments'], 1)
        self.assertEqual(audit(self.root)['summary']['errors'], 0)
        annotation['canonical_id'] = 'M999'
        self.write('registry/method_id_reassignment_R269.json', json.dumps(annotation))
        self.assertIn('ID_REASSIGNMENT_INVALID', self.codes())

    def test_source_collision_checks_current_alias_targets(self):
        row = self.queue[0]
        annotation = dict(declared_id='M234', canonical_id='M001', reason='Source ID reused an earlier claim',
                          source_commit='abc1234', round='UNREGISTERED_SOURCE',
                          original_header=list(row), original_row=['M234']+list(row.values())[1:],
                          target_reassignments=[dict(path='registry/methods_aliases.csv', id_field='rec_id',
                             record_id='SRC1', field='queue_id', original_value='M234', canonical_value='M001')])
        self.write('registry/method_id_reassignment_source.json', json.dumps(annotation))
        self.assertEqual(audit(self.root)['summary']['errors'], 0)
        self.aliases[0]['queue_id'] = 'M234'
        self.save()
        self.assertIn('ID_REASSIGNMENT_INVALID', self.codes())


if __name__ == '__main__':
    unittest.main()
