"""Declared provenance only; targets, results and journals are never opened."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.repository_index import trace


class RepositoryTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = []
        (self.root/'registry').mkdir()
        self.table('methods.csv', [dict(id='M1', method='Invented method', rid='R2')])
        self.table('rounds.csv', [dict(id='R2', lane='example', status='REGISTERED',
                                     verdict='PENDING', trials='1', prereg_sha='b'*64)])

    def table(self, name, rows):
        with (self.root/'registry'/name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def write(self, path, value):
        p = self.root/path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)
        if path not in self.files:
            self.files.append(path)
        return p

    def metadata(self, value, name='code_inputs.json'):
        return self.write('experiments/example/'+name, json.dumps(value))

    def read(self):
        return trace(self.root, 'M1', self.files)['rounds'][0]

    def test_native_shaped_inline_inputs_bind_each_source_without_opening_it(self):
        sources = ['scripts/score_example.py', 'scripts/record_example.py', 'scripts/parent.py']
        self.write('experiments/example/PREREG.md', '# Invented R389-shaped protocol\n\n```inputs\n'+
                   '\n'.join(digest*64+'  '+path for digest, path in zip('acd', sources))+'\n```\n')
        # These target paths are declared tracked but absent: opening/hashing them would fail.
        self.files.extend(sources[:2])
        self.write('experiments/example/FINDINGS.md', 'DO NOT READ OUTCOME')
        row = self.read()
        self.assertEqual([entry['path'] for entry in row['identities']], sources)
        self.assertEqual([entry['local_tracked'] for entry in row['identities']], [True, True, False])
        self.assertTrue(all(not entry['identity_reverified'] for entry in row['identities']))
        self.assertEqual(row['provenance_issues'], [])
        self.assertEqual(row['identities'][0]['manifest'], 'experiments/example/PREREG.md')

    def test_training_manifest_records_are_found_and_target_payloads_stay_unopened(self):
        self.metadata([dict(path='data/not-opened.parquet', bytes=123, sha256='a'*64)],
                      'training_manifest.json')
        target = self.root/'data/not-opened.parquet'
        target.parent.mkdir()
        target.write_bytes(b'\xff invented payload')
        self.files.append('data/not-opened.parquet')
        for p in ('experiments/example/results/development_inputs.json',
                  'experiments/example/journal/inputs.json'):
            self.write(p, 'INVALID OUTCOME JSON MUST NOT BE READ')
        original = Path.open

        def guarded(path, *args, **kwargs):
            if path == target or 'results' in path.parts or 'journal' in path.parts:
                raise AssertionError('target/result/journal opened')
            return original(path, *args, **kwargs)

        with patch.object(Path, 'open', guarded):
            row = self.read()
        self.assertEqual(len(row['identities']), 1)
        self.assertEqual(row['identities'][0]['path'], 'data/not-opened.parquet')
        self.assertTrue(row['identities'][0]['local_tracked'])
        self.assertFalse(row['identities'][0]['identity_reverified'])

    def test_legacy_path_first_fences_preserve_paths_with_spaces(self):
        self.write('experiments/example/PREREG.md', '```inputs\n'+
                   'scripts/legacy.py  '+'a'*64+'\n'+
                   'data/invented source.csv  '+'c'*64+'\n```\n')
        entries = self.read()['identities']
        self.assertEqual([e['path'] for e in entries],
                         ['scripts/legacy.py', 'data/invented source.csv'])
        self.assertEqual([e['reported_sha256'] for e in entries], ['a'*64, 'c'*64])
        self.assertTrue(all(e['identity_reverified'] is False for e in entries))

    def test_legacy_mappings_and_companion_record_paths_keep_their_binding(self):
        self.metadata({'sha256': {'scripts/map.py': 'a'*64},
                       'files': [dict(path='scripts/record.py', sha256='c'*64)]})
        self.files.extend(['scripts/map.py', 'scripts/record.py'])
        entries = {e['path']: e for e in self.read()['identities']}
        self.assertEqual(set(entries), {'scripts/map.py', 'scripts/record.py'})
        self.assertTrue(all(e['local_tracked'] for e in entries.values()))
        self.assertEqual(entries['scripts/map.py']['field'], '/sha256/scripts/map.py')
        self.assertEqual(entries['scripts/record.py']['field'], '/files/0/sha256')

    def test_no_supported_metadata_is_explicit_and_other_code_fences_are_ignored(self):
        self.write('experiments/example/PREREG.md', '# Invented\n'+ 'a'*64+'  scripts/plain.py\n'+
                   '````python\n```inputs\n'+'a'*64+'  scripts/literal.py\n```\n````\n')
        row = self.read()
        self.assertEqual(row['identities'], [])
        self.assertEqual(row['provenance_issues'], [dict(kind='no_supported_identity_declarations')])

    def test_legacy_rebuild_recipe_is_metadata_and_never_executed(self):
        self.write('experiments/example/PREREG.md', '```inputs\n'+
                   'scripts/legacy.py  '+'a'*64+'\n'+
                   'rebuild: python -c "raise RuntimeError(\'must never execute\')"\n```\n')
        with patch('subprocess.run', side_effect=AssertionError('recipe executed')):
            row = self.read()
        self.assertEqual(len(row['identities']), 1)
        self.assertEqual(row['identities'][0]['path'], 'scripts/legacy.py')
        self.assertEqual(row['provenance_issues'][0]['kind'], 'rebuild_recipe_not_executed')

    def test_hash_without_path_remains_an_unresolved_pointer(self):
        self.metadata({'parent_digest': 'a'*64})
        row = self.read()
        self.assertEqual(row['identities'][0]['path'], None)
        self.assertFalse(row['identities'][0]['local_tracked'])
        self.assertEqual(row['provenance_issues'][0]['kind'], 'hash_path_unknown')

    def test_duplicate_json_keys_and_duplicate_paths_fail_closed(self):
        p = self.write('experiments/example/code_inputs.json',
                       '{"sha256":{"scripts/a.py":"'+'a'*64+'","scripts/a.py":"'+'c'*64+'"}}')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.read()
        p.write_text(json.dumps([dict(path='scripts/a.py', sha256='a'*64)]*2))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.read()
        p.unlink()
        self.files.remove('experiments/example/code_inputs.json')
        self.write('experiments/example/PREREG.md', '```inputs\n'+
                   ('a'*64+'  scripts/a.py\n')*2+'```\n')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.read()

    def test_conflicting_sources_are_explicit_not_verified(self):
        self.metadata({'sha256': {'scripts/a.py': 'a'*64}})
        self.write('experiments/example/PREREG.md', '```inputs\n'+'c'*64+'  scripts/a.py\n```\n')
        row = self.read()
        self.assertEqual(row['provenance_issues'][0]['kind'], 'conflicting_declared_hashes')
        self.assertTrue(all(e['declaration_conflict'] for e in row['identities']))
        self.assertTrue(all(e['identity_reverified'] is False for e in row['identities']))

    def test_malformed_metadata_and_unsupported_training_payload_fail_closed(self):
        malformed = [[dict(path='scripts/a.py', sha256='not-a-hash')],
                     [dict(path='scripts/a.py', sha256='a'*64, bytes=True)],
                     [dict(path='scripts/a.py', sha256='a'*64, outcome=[1, 2])],
                     {'path': 'scripts/a.py', 'sha256': 'a'*64}]
        for value in malformed:
            self.metadata(value, 'training_manifest.json')
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.read()
        self.files.remove('experiments/example/training_manifest.json')
        for text in ('```inputs\nnot a declaration\n```\n',
                     '```inputs\n'+'a'*64+'  scripts/a.py\n'):
            self.write('experiments/example/PREREG.md', text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read()

    def test_unsafe_declared_paths_and_lane_names_never_reach_a_target(self):
        for path in ('../outside', '/outside', 'scripts/../../outside', 'C:/outside',
                     'https://example.org/code.py', 'scripts\\outside.py'):
            self.metadata({'files': [dict(path=path, sha256='a'*64)]})
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.read()
        self.table('rounds.csv', [dict(id='R2', lane='../outside', status='REGISTERED',
                                     verdict='PENDING', trials='1', prereg_sha='b'*64)])
        with self.assertRaisesRegex(ValueError, 'lane'):
            self.read()

    def test_metadata_and_spec_symlinks_and_oversized_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as other:
            target = Path(other)/'fixture'
            target.write_text('[]')
            for name in ('training_manifest.json', 'PREREG.md'):
                p = self.root/'experiments/example'/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.symlink_to(target)
                self.files = ['experiments/example/'+name]
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Symlink'):
                    self.read()
                p.unlink()
        p = self.write('experiments/example/code_inputs.json', ' '*129)
        self.files = ['experiments/example/code_inputs.json']
        with patch('scripts.repository_index.PROVENANCE_LIMIT', 128), self.assertRaisesRegex(ValueError, 'oversized'):
            self.read()


if __name__ == '__main__':
    unittest.main()
