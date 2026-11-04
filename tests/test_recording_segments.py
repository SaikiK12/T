"""Opaque invented byte recovery, corruption, identity and publication contracts."""
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from lab import recording_segments as seg
from scripts.recording_segments import main


ROWS = [('data/tape', 'RECORDED'), ('data/news', 'RECORDED'),
        ('data/vendor', 'LICENSED'), ('data/tape/refetch', 'REFETCH')]


def repository(path, rows=ROWS):
    (path / 'registry').mkdir(parents=True)
    with (path / 'registry/data_manifest.csv').open('w', newline='') as stream:
        csv.writer(stream).writerows([('path', 'class'), *rows])
    return path


class SegmentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = repository(self.base / 'repo')
        self.restore_root = repository(self.base / 'restored')
        self.relative = 'data/tape/2026-11-04.bin'
        self.source = self.root / self.relative
        self.source.parent.mkdir(parents=True)
        self.payload = b'opaque invented bytes\x00\xff' * 13
        self.source.write_bytes(self.payload)
        self.archive = self.base / 'segments'

    def tearDown(self):
        self.tmp.cleanup()

    def pack(self, **kw):
        return seg.pack_recording(self.root, self.relative, self.archive,
                                  **dict(dict(chunk_bytes=31, budget_bytes=20_000,
                                              min_age_seconds=0), **kw))

    def verify(self, receipt):
        return seg.verify_recording(self.archive, expected_manifest_sha256=receipt['manifest_sha256'],
                                    budget_bytes=20_000)

    def restore(self, receipt):
        return seg.restore_recording(self.archive, self.restore_root,
                                     expected_manifest_sha256=receipt['manifest_sha256'], budget_bytes=20_000)

    def rewrite_manifest(self, change):
        path = self.archive / 'manifest.json'
        value = json.loads(path.read_bytes()); change(value)
        raw = (json.dumps(value) + '\n').encode(); path.write_bytes(raw)
        return dict(manifest_sha256=hashlib.sha256(raw).hexdigest())

    def test_segmented_round_trip_hashes_read_only_verify_and_source_unchanged(self):
        before = self.source.stat()
        receipt = self.pack()
        self.assertGreater(receipt['segments'], 3)
        self.assertEqual(receipt['source_sha256'], hashlib.sha256(self.payload).hexdigest())
        snapshots = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.archive.iterdir()}
        self.assertEqual(self.verify(receipt)['state'], 'VERIFIED')
        self.assertEqual(snapshots, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.archive.iterdir()})
        restored = self.restore(receipt)
        self.assertEqual(restored['state'], 'RESTORED')
        target = self.restore_root / self.relative
        self.assertEqual(target.read_bytes(), self.payload)
        self.assertEqual(target.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.source.read_bytes(), self.payload)
        self.assertEqual(self.source.stat().st_mtime_ns, before.st_mtime_ns)

    def test_restore_persists_new_ancestors_and_timestamp_before_publication(self):
        receipt = self.pack()
        events = []
        real_mkdir, real_sync, real_utime, real_link = os.mkdir, os.fsync, os.utime, os.link
        def mkdir(name, *args, **kw):
            result = real_mkdir(name, *args, **kw)
            events.append(('mkdir', os.fstat(kw['dir_fd']).st_ino))
            return result
        def sync(fd):
            s = os.fstat(fd)
            events.append(('sync_file' if stat.S_ISREG(s.st_mode) else 'sync_dir', s.st_ino))
            return real_sync(fd)
        def utime(fd, *args, **kw):
            result = real_utime(fd, *args, **kw)
            events.append(('utime', os.fstat(fd).st_ino))
            return result
        def link(*args, **kw):
            events.append(('publish', None))
            return real_link(*args, **kw)
        with patch.object(seg.os, 'mkdir', side_effect=mkdir), patch.object(seg.os, 'fsync', side_effect=sync), \
                patch.object(seg.os, 'utime', side_effect=utime), patch.object(seg.os, 'link', side_effect=link):
            self.restore(receipt)
        made = [(i, inode) for i, (kind, inode) in enumerate(events) if kind == 'mkdir']
        self.assertEqual(len(made), 2)
        for i, inode in made:
            self.assertEqual(events[i+1], ('sync_dir', inode))
        stamp = next(i for i, event in enumerate(events) if event[0] == 'utime')
        self.assertEqual(events[stamp+1], ('sync_file', events[stamp][1]))
        self.assertLess(stamp+1, next(i for i, event in enumerate(events) if event[0] == 'publish'))

    def test_file_above_ordinary_archive_limit_is_restored_in_bounded_segments(self):
        # A sparse invented file exercises the actual >95 MB handover exclusion.
        with self.source.open('wb') as stream:
            stream.truncate(96_000_000)
        receipt = seg.pack_recording(self.root, self.relative, self.archive, chunk_bytes=9_000_000,
                                     budget_bytes=97_000_000, min_age_seconds=0)
        self.assertEqual(receipt['segments'], 11)
        self.assertTrue(all(p.stat().st_size <= 9_000_000 for p in self.archive.glob('segment-*.bin')))
        seg.restore_recording(self.archive, self.restore_root,
                              expected_manifest_sha256=receipt['manifest_sha256'], budget_bytes=97_000_000)
        with self.source.open('rb') as original, (self.restore_root / self.relative).open('rb') as restored:
            self.assertEqual(hashlib.file_digest(original, 'sha256').hexdigest(),
                             hashlib.file_digest(restored, 'sha256').hexdigest())

    def test_licensed_unclassified_public_text_and_state_are_refused(self):
        for relative in ('data/vendor/a.bin', 'data/unknown/a.bin', 'data/news/a.json',
                         'data/tape/status.json', 'data/tape/a.lock', 'data/tape/refetch/a.bin'):
            p = self.root / relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b'x')
            with self.subTest(relative=relative), self.assertRaises(seg.SegmentError):
                seg.pack_recording(self.root, relative, self.archive, budget_bytes=10000, min_age_seconds=0)
            self.assertFalse(self.archive.exists())

    def test_source_and_ancestor_symlinks_are_refused(self):
        link = self.root / 'data/tape/link.bin'; link.symlink_to(self.source)
        with self.assertRaises(OSError):
            seg.pack_recording(self.root, 'data/tape/link.bin', self.archive,
                               budget_bytes=10000, min_age_seconds=0)
        parent = self.root / 'data/tape/alias'; parent.symlink_to(self.source.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            seg.pack_recording(self.root, 'data/tape/alias/2026-11-04.bin', self.archive,
                               budget_bytes=10000, min_age_seconds=0)
        self.assertFalse(self.archive.exists())
        alias = self.base / 'root-link'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            seg.pack_recording(alias, self.relative, self.archive, budget_bytes=10000, min_age_seconds=0)

    def test_fifo_is_rejected_without_blocking(self):
        fifo = self.root / 'data/tape/pipe'; os.mkfifo(fifo)
        with self.assertRaises(seg.SegmentError):
            seg.pack_recording(self.root, 'data/tape/pipe', self.archive,
                               budget_bytes=10000, min_age_seconds=0)
        self.assertFalse(self.archive.exists())

    def test_destinations_and_overlapping_paths_never_replace_existing_content(self):
        self.archive.mkdir()
        with self.assertRaises(FileExistsError): self.pack()
        self.assertEqual(list(self.archive.iterdir()), [])
        self.archive.rmdir()
        with self.assertRaises(seg.SegmentError):
            seg.pack_recording(self.root, self.relative, self.root / 'archive', budget_bytes=10000)
        receipt = self.pack()
        target = self.restore_root / self.relative
        target.parent.mkdir(parents=True); target.write_bytes(b'keep this newer recording')
        with self.assertRaises(FileExistsError): self.restore(receipt)
        self.assertEqual(target.read_bytes(), b'keep this newer recording')
        with self.assertRaises(seg.SegmentError):
            seg.restore_recording(self.archive, self.archive.parent,
                                  expected_manifest_sha256=receipt['manifest_sha256'], budget_bytes=20000)

    def test_budget_accounts_for_manifest_and_cleans_unpublished_files(self):
        for budget in (1, len(self.payload), len(self.payload) + 1):
            with self.subTest(budget=budget), self.assertRaises(seg.SegmentError):
                seg.pack_recording(self.root, self.relative, self.archive,
                                   chunk_bytes=31, budget_bytes=budget, min_age_seconds=0)
            self.assertFalse(self.archive.exists())
            self.assertFalse(list(self.base.glob('.segments-*')))

    def test_numeric_limits_age_and_relative_paths(self):
        for kwargs in ({'chunk_bytes': 0}, {'chunk_bytes': True}, {'chunk_bytes': seg.MAX_SEGMENT_BYTES + 1},
                       {'budget_bytes': True}, {'min_age_seconds': -1}, {'now_ns': 0}):
            settings = dict(chunk_bytes=31, budget_bytes=20000, min_age_seconds=0); settings.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(seg.SegmentError):
                seg.pack_recording(self.root, self.relative, self.archive, **settings)
        with self.assertRaises(seg.SegmentError):
            seg.pack_recording(self.root, self.relative, self.archive, budget_bytes=20000)
        for relative in ('../outside', '/data/tape/a', 'data/tape/../x', 'data//tape/a', 'data/tape\\a'):
            with self.subTest(path=relative), self.assertRaises(seg.SegmentError):
                seg.pack_recording(self.root, relative, self.archive, budget_bytes=20000)
        self.assertFalse(self.archive.exists())

    def test_tampering_truncation_and_missing_parts_never_publish_restore(self):
        receipt = self.pack()
        part = self.archive / 'segment-000000.bin'; original = part.read_bytes()
        for changed in (b'Z' + original[1:], original[:-1], original + b'x'):
            part.write_bytes(changed)
            with self.assertRaises(seg.SegmentError): self.verify(receipt)
            with self.assertRaises(seg.SegmentError): self.restore(receipt)
            self.assertFalse((self.restore_root / self.relative).exists())
            self.assertFalse(list(self.restore_root.rglob('.restore-*')))
        part.unlink()
        with self.assertRaises(seg.SegmentError): self.verify(receipt)

    def test_pinned_manifest_whole_file_hash_and_unlisted_entries_are_checked(self):
        receipt = self.pack()
        with self.assertRaises(seg.SegmentError):
            seg.verify_recording(self.archive, expected_manifest_sha256='0' * 64, budget_bytes=20000)
        bad = self.rewrite_manifest(lambda m: m['source'].update(sha256='0' * 64))
        with self.assertRaises(seg.SegmentError): self.verify(bad)
        (self.archive / 'unlisted.bin').write_bytes(b'unknown')
        with self.assertRaises(seg.SegmentError): self.verify(bad)

    def test_manifest_schema_paths_versions_offsets_and_duplicate_keys(self):
        self.pack()
        manifest = self.archive / 'manifest.json'; original = manifest.read_bytes()
        mutations = [lambda m: m.update(version=True), lambda m: m.update(version=99),
                     lambda m: m['source'].update(path='data/tape/../../outside'),
                     lambda m: m['source'].update(path='data/news/text.json'),
                     lambda m: m['source'].update(**{'class': 'LICENSED'}),
                     lambda m: m['segments'][0].update(name='../outside'),
                     lambda m: m['segments'][1].update(offset=0),
                     lambda m: m['segments'][1].update(name=m['segments'][0]['name']),
                     lambda m: m['source'].update(bytes=True)]
        for mutate in mutations:
            manifest.write_bytes(original); bad = self.rewrite_manifest(mutate)
            with self.subTest(mutate=mutate), self.assertRaises(seg.SegmentError): self.verify(bad)
        raw = b'{"format":"a","format":"b"}'; manifest.write_bytes(raw)
        with self.assertRaises(seg.SegmentError):
            self.verify(dict(manifest_sha256=hashlib.sha256(raw).hexdigest()))

    def test_symlink_archive_segment_manifest_and_restore_ancestor_are_refused(self):
        receipt = self.pack(); part = self.archive / 'segment-000000.bin'
        elsewhere = self.base / 'elsewhere'; elsewhere.write_bytes(part.read_bytes())
        part.unlink(); part.symlink_to(elsewhere)
        with self.assertRaises(OSError): self.verify(receipt)
        part.unlink(); part.write_bytes(elsewhere.read_bytes())
        link = self.base / 'archive-link'; link.symlink_to(self.archive, target_is_directory=True)
        with self.assertRaises(OSError):
            seg.verify_recording(link, expected_manifest_sha256=receipt['manifest_sha256'], budget_bytes=20000)
        outside = self.base / 'outside'; outside.mkdir()
        (self.restore_root / 'data').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError): self.restore(receipt)
        self.assertEqual(list(outside.iterdir()), [])
        manifest = self.archive / 'manifest.json'; backup = self.base / 'manifest-copy'
        backup.write_bytes(manifest.read_bytes()); manifest.unlink(); manifest.symlink_to(backup)
        with self.assertRaises(OSError): self.verify(receipt)

    def test_source_change_or_replacement_during_read_refuses_publication(self):
        fsync = os.fsync; mutated = False
        def change(fd):
            nonlocal mutated
            fsync(fd)
            if not mutated:
                mutated = True
                replacement = self.source.with_suffix('.replacement')
                replacement.write_bytes(self.payload)
                os.replace(replacement, self.source)
        with patch.object(seg.os, 'fsync', side_effect=change), self.assertRaises(seg.SegmentError):
            self.pack()
        self.assertFalse(self.archive.exists())
        self.assertFalse(list(self.base.glob('.segments-*')))
        self.assertEqual(self.source.read_bytes(), self.payload)

    def test_classification_changes_and_destination_class_are_not_ignored(self):
        fsync = os.fsync; mutated = False
        def change(fd):
            nonlocal mutated
            fsync(fd)
            if not mutated:
                mutated = True
                path = self.root / 'registry/data_manifest.csv'
                path.write_text(path.read_text().replace('data/tape,RECORDED', 'data/tape,LICENSED'))
        with patch.object(seg.os, 'fsync', side_effect=change), self.assertRaises(seg.SegmentError): self.pack()
        self.assertFalse(self.archive.exists())
        path = self.root / 'registry/data_manifest.csv'
        path.write_text(path.read_text().replace('data/tape,LICENSED', 'data/tape,RECORDED'))
        receipt = self.pack()
        target = self.restore_root / 'registry/data_manifest.csv'
        target.write_text(target.read_text().replace('data/tape,RECORDED', 'data/tape,LICENSED'))
        with self.assertRaises(seg.SegmentError): self.restore(receipt)
        self.assertFalse((self.restore_root / self.relative).exists())

    def test_publication_failure_and_existing_directory_race_leave_no_bundle(self):
        with patch.object(seg, '_publish_directory', side_effect=seg.SegmentError('unsupported host')):
            with self.assertRaises(seg.SegmentError): self.pack()
        self.assertFalse(self.archive.exists())
        self.assertFalse(list(self.base.glob('.segments-*')))
        publish = seg._publish_directory
        def race(fd, temporary, destination):
            self.archive.mkdir()
            publish(fd, temporary, destination)
        with patch.object(seg, '_publish_directory', side_effect=race), self.assertRaises(FileExistsError): self.pack()
        self.assertEqual(list(self.archive.iterdir()), [])

    def test_cli_executes_explicit_commands_and_refuses_unknown_manifest(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(['pack', '--root', str(self.root), '--source', self.relative,
                         '--out', str(self.archive), '--budget-mb', '1', '--min-age-min', '0'])
        self.assertEqual(code, 0); receipt = json.loads(buffer.getvalue())
        for command in (['verify'], ['restore', '--root', str(self.restore_root)]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([*command, '--archive', str(self.archive), '--budget-mb', '1',
                                       '--expected-manifest-sha256', receipt['manifest_sha256']]), 0)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            self.assertEqual(main(['verify', '--archive', str(self.archive), '--budget-mb', '1',
                                   '--expected-manifest-sha256', '0' * 64]), 2)
        self.assertEqual(json.loads(buffer.getvalue())['state'], 'REFUSED')


if __name__ == '__main__':
    unittest.main()
