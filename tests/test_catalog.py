"""Registry/navigation fixtures only: no market data, outcome reads or journal changes."""
import csv
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import catalog


class ExperimentCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / "registry").mkdir()
        (self.root / "experiments").mkdir()
        (self.root / 'scripts').mkdir()
        (self.root / 'lab').mkdir()

    def registry(self, rows):
        with (self.root / "registry/rounds.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "path", "status", "verdict", "trials", "title"])
            w.writeheader()
            for rid, lane, status in rows:
                w.writerow(dict(id=rid, path="experiments/" + lane, status=status, verdict="PENDING",
                                trials="1", title="Fixture " + rid))

    def folder(self, lane):
        p = self.root / "experiments" / lane
        p.mkdir()
        (p / 'README.md').write_text('# Invented folder scope\n')
        return p

    def stage(self):
        subprocess.run(['git', '-C', str(self.root), 'add', '--all'], check=True)

    def render(self):
        self.stage()
        return catalog.experiment_catalog(self.root)

    def command(self, *args):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return catalog.main(['--root', str(self.root), *args])

    def simple_sources(self):
        self.registry([])
        (self.root / 'scripts/good.py').write_text('"""Published command description."""\n')
        (self.root / 'lab/good.py').write_text('"""Published library description."""\n')
        self.stage()

    def outputs(self):
        return {p: (self.root / p).read_bytes() for p in
                ('experiments/README.md', 'scripts/README.md', 'lab/README.md')}

    def test_absent_import_remains_visible_without_a_dangling_link(self):
        self.registry([("R143", "imported", "DONE"), ("R308", "local", "DONE")])
        p = self.folder("local")
        (p / "PREREG.md").write_text("fixture only")
        text, counts = self.render()
        self.assertEqual(counts, (1, 0))
        self.assertIn("Registered rounds with no local folder (1)", text)
        self.assertIn("**R143** `experiments/imported`: DONE PENDING", text)
        self.assertNotIn("](imported", text)
        self.assertIn("[PREREG](local/PREREG.md)", text)
        self.assertFalse((self.root / "experiments/README.md").exists())

    def test_unregistered_study_is_not_presented_as_collected_data(self):
        self.registry([])
        self.folder("recorders")
        self.folder("unregistered_study")
        text, counts = self.render()
        self.assertEqual(counts, (0, 2))
        collection = text.split("## Collection and loop folders (1)", 1)[1].split("## Unregistered folders", 1)[0]
        self.assertIn("[recorders]", collection)
        self.assertNotIn("unregistered_study", collection)
        self.assertIn("[unregistered_study](unregistered_study/)", text.split("## Unregistered folders (1)", 1)[1])

    def test_running_batch_and_planned_round_do_not_acquire_paper_or_done_labels(self):
        self.registry([("R286", "reserved", "RUNNING"), ("R184", "draft", "PLANNED")])
        self.folder("reserved")
        self.folder("draft")
        text, _ = self.render()
        active, rest = text.split("## Other registered rounds", 1)
        self.assertIn("**[reserved]", active)
        self.assertNotIn("**[draft]", active)
        self.assertIn("**[draft]", rest)
        self.assertNotIn("Forward paper lanes (running)", text)
        self.assertNotIn("Finished and registered rounds", text)

    def test_multiple_registry_rows_are_preserved_and_results_are_never_read(self):
        self.registry([("R200", "shared", "REGISTERED"), ("R199", "shared", "DONE")])
        p = self.folder("shared")
        # Evidence links need existence only. Deliberately invalid text must never be parsed.
        (p / "FINDINGS.md").write_bytes(b"\xff\x00")
        (p / "journal").mkdir()
        (p / "journal/days.csv").write_bytes(b"\xff\x00")
        before = {q: q.read_bytes() for q in p.rglob("*") if q.is_file()}
        first = self.render()
        self.assertEqual(first, catalog.experiment_catalog(self.root))
        text, counts = first
        self.assertEqual(counts, (1, 0))
        self.assertEqual(text.count("Fixture R200"), 1)
        self.assertEqual(text.count("Fixture R199"), 1)
        self.assertLess(text.index("Fixture R200"), text.index("Fixture R199"))
        self.assertIn("[journal](shared/journal/)", text)
        self.assertEqual(before, {q: q.read_bytes() for q in p.rglob("*") if q.is_file()})

    def test_one_snapshot_pins_registry_paths_and_source_text(self):
        self.simple_sources()
        source = catalog.IndexSnapshot(self.root)
        (self.root / 'scripts/good.py').write_text('"""Unstaged private working text."""\n')
        (self.root / 'scripts/wip.py').write_text('"""Untracked working text."""\n')
        self.registry([('R999', 'wip', 'PLANNED')])
        self.folder('wip')
        text, count = catalog.script_catalog(self.root, source)
        self.assertEqual(count, 1)
        self.assertIn('Published command description', text)
        self.assertNotIn('working text', text)
        self.assertNotIn('wip.py', text)
        self.assertNotIn('R999', catalog.experiment_catalog(self.root, source)[0])
        self.stage()
        # Staging a later revision cannot change an already pinned generation.
        self.assertEqual((text, count), catalog.script_catalog(self.root, source))
        self.assertIn('Unstaged private working text', catalog.script_catalog(self.root)[0])
        self.assertIn('R999', catalog.experiment_catalog(self.root)[0])

    def test_staged_symlinks_and_worktree_replacements_do_not_leak_external_text(self):
        self.simple_sources()
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / 'outside.py'
            outside.write_text('"""External fixture sentinel."""\n')
            (self.root / 'scripts/leak.py').symlink_to(outside)
            (self.root / 'lab/leak.py').symlink_to(outside)
            self.stage()
            # A regular indexed source can also become a symlink only in the worktree.
            (self.root / 'scripts/good.py').unlink()
            (self.root / 'scripts/good.py').symlink_to(outside)
            commands, n = catalog.script_catalog(self.root)
            library, m = catalog.library_catalog(self.root)
            self.assertEqual((n, m), (1, 1))
            self.assertIn('Published command description', commands)
            self.assertNotIn('leak.py', commands + library)
            self.assertNotIn('External fixture sentinel', commands + library)

    def test_intent_to_add_is_not_confused_with_a_staged_empty_file(self):
        self.simple_sources()
        (self.root / 'scripts/pending.py').write_text('"""Still a working draft."""\n')
        (self.root / 'scripts/empty.py').touch()
        subprocess.run(['git', '-C', str(self.root), 'add', 'scripts/empty.py'], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '-N', 'scripts/pending.py'], check=True)
        original_index = (self.root / '.git/index').read_bytes()
        original_objects = sorted(p.relative_to(self.root / '.git') for p in (self.root / '.git/objects').rglob('*'))
        text, count = catalog.script_catalog(self.root)
        self.assertEqual(count, 2)
        self.assertIn('empty.py', text)
        self.assertNotIn('pending.py', text)
        self.assertEqual((self.root / '.git/index').read_bytes(), original_index)
        self.assertEqual(original_objects, sorted(p.relative_to(self.root / '.git')
                                                 for p in (self.root / '.git/objects').rglob('*')))

    def test_check_mode_reports_missing_stale_and_current_without_writing(self):
        self.simple_sources()
        index = (self.root / '.git/index').read_bytes()
        self.assertEqual(self.command('--check'), 1)
        self.assertFalse((self.root / 'experiments/README.md').exists())
        self.assertEqual((self.root / '.git/index').read_bytes(), index)
        self.assertEqual(self.command(), 0)
        before = self.outputs()
        mtimes = {p: (self.root / p).stat().st_mtime_ns for p in before}
        self.assertEqual(self.command('--check'), 0)
        self.assertEqual(self.command(), 0)
        self.assertEqual(self.outputs(), before)
        self.assertEqual(mtimes, {p: (self.root / p).stat().st_mtime_ns for p in before})
        (self.root / 'scripts/good.py').write_text('"""New staged description."""\n')
        self.stage()
        self.assertEqual(self.command('--check'), 1)
        self.assertEqual(self.outputs(), before)
        self.assertEqual(self.command(), 0)
        self.assertIn('New staged description', (self.root / 'scripts/README.md').read_text())
        self.assertFalse(list(self.root.rglob('.catalog-*.tmp')))

    def test_output_symlink_or_parent_symlink_blocks_the_whole_publication(self):
        self.simple_sources()
        self.assertEqual(self.command(), 0)
        before = self.outputs()
        with tempfile.TemporaryDirectory() as external:
            outside = Path(external) / 'README.md'
            outside.write_text('External output fixture\n')
            target = self.root / 'scripts/README.md'
            target.unlink()
            target.symlink_to(outside)
            for args in ((), ('--check',)):
                self.assertEqual(self.command(*args), 2)
                self.assertEqual(outside.read_text(), 'External output fixture\n')
                self.assertEqual((self.root / 'experiments/README.md').read_bytes(), before['experiments/README.md'])
            target.unlink()
            target.write_bytes(before['scripts/README.md'])
            (self.root / 'scripts').rename(self.root / 'saved-scripts')
            (self.root / 'scripts').symlink_to(external, target_is_directory=True)
            self.assertEqual(self.command(), 2)
            self.assertEqual(outside.read_text(), 'External output fixture\n')

    def test_all_inputs_are_rendered_before_any_output_is_replaced(self):
        self.simple_sources()
        self.assertEqual(self.command(), 0)
        before = self.outputs()
        (self.root / 'scripts/good.py').write_text('"""A valid changed command."""\n')
        (self.root / 'lab/good.py').write_bytes(b'\xff')
        self.stage()
        self.assertEqual(self.command(), 2)
        self.assertEqual(self.outputs(), before)

    def test_unmerged_index_is_not_published(self):
        self.simple_sources()
        self.assertEqual(self.command(), 0)
        before = self.outputs()
        sha = catalog.IndexSnapshot(self.root).blobs['scripts/good.py']
        records = ('0 ' + '0' * 40 + '\tscripts/good.py\n' +
                   '100644 ' + sha + ' 2\tscripts/good.py\n')
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--index-info'],
                       input=records.encode(), check=True)
        self.assertEqual(self.command(), 2)
        self.assertEqual(self.outputs(), before)


if __name__ == "__main__":
    unittest.main()
