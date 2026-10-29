import csv
import io
import os
import re
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import handover as h  # noqa: E402

ROWS = [
    {"path": "data/tape", "class": "RECORDED", "restore": "none", "provenance": "", "note": ""},
    {"path": "data/unlocks", "class": "RECORDED", "restore": "none", "provenance": "", "note": ""},
    {"path": "data/unlocks/2026-10-20", "class": "REFETCH", "restore": "x", "provenance": "", "note": ""},
    {"path": "data/klines_1h", "class": "REFETCH", "restore": "x", "provenance": "", "note": ""},
    {"path": "data/databento", "class": "LICENSED", "restore": "x", "provenance": "", "note": ""},
]
OLD = 10_000.0


def put(root, rel, data=b"x", age_s=3600.0):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    t = time.time() - age_s
    os.utime(p, (t, t))
    return p


class ManifestFile(unittest.TestCase):
    def test_every_row_is_valid_and_its_references_exist(self):
        rows = h.load_manifest()
        self.assertGreater(len(rows), 50)
        paths = [r["path"] for r in rows]
        self.assertEqual(len(paths), len(set(paths)), "duplicate manifest path")
        for r in rows:
            self.assertTrue(r["path"].startswith("data/"), r["path"])
            self.assertTrue(r["restore"].strip(), r["path"])
            for script in re.findall(r"scripts/[A-Za-z0-9_]+\.py", r["restore"]):
                self.assertTrue((ROOT / script).exists(), f"{r['path']}: {script} is missing")
            if r["provenance"]:
                self.assertTrue((ROOT / r["provenance"]).exists(), f"{r['path']}: {r['provenance']} is missing")

    def test_licensed_data_is_never_a_recorded_class(self):
        by = {r["path"]: r["class"] for r in h.load_manifest()}
        self.assertEqual(by["data/databento"], "LICENSED")
        self.assertEqual(by["data/tape"], "RECORDED")


class Classify(unittest.TestCase):
    def test_longest_prefix_wins_and_unlisted_is_none(self):
        self.assertEqual(h.classify("data/unlocks/2026-10-21/a.json", ROWS), "RECORDED")
        self.assertEqual(h.classify("data/unlocks/2026-10-20/a.json", ROWS), "REFETCH")
        self.assertIsNone(h.classify("data/new_thing/a.parquet", ROWS))
        self.assertIsNone(h.classify("data/tape_extra/a.parquet", ROWS))   # a prefix of the name is not a parent folder


class PackRestore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        self.out = Path(self.tmp.name) / "archive"
        put(self.root, "data/tape/binance/2026-10-28.parquet", b"a" * 1000)
        put(self.root, "data/tape/status.json", b"{}")
        put(self.root, "data/tape/recorder.lock", b"1")
        put(self.root, "data/tape/recorder.log", b"log")
        put(self.root, "data/tape/fresh.parquet", b"f", age_s=5)
        put(self.root, "data/unlocks/2026-10-21/a.json", b"u" * 10)
        put(self.root, "data/unlocks/2026-10-20/a.json", b"old")
        put(self.root, "data/klines_1h/BTC.parquet", b"k" * 10)
        put(self.root, "data/databento/cme.csv.zst", b"licensed")

    def tearDown(self):
        self.tmp.cleanup()

    def names(self):
        with open(self.out / "files.csv", newline="") as f:
            return sorted(r["path"] for r in csv.DictReader(f))

    def test_only_old_recorded_files_are_packed(self):
        s = h.pack(self.root, self.out, ROWS, min_age_min=15)
        self.assertEqual(self.names(), ["data/tape/binance/2026-10-28.parquet", "data/unlocks/2026-10-21/a.json"])
        self.assertEqual(s["added"], 2)

    def test_packing_twice_adds_nothing_and_a_changed_file_goes_into_a_new_chunk(self):
        h.pack(self.root, self.out, ROWS)
        s2 = h.pack(self.root, self.out, ROWS)
        self.assertEqual((s2["added"], s2["chunks"]), (0, 0))
        put(self.root, "data/tape/binance/2026-10-28.parquet", b"b" * 2000)
        s3 = h.pack(self.root, self.out, ROWS)
        self.assertEqual((s3["added"], s3["chunks"]), (1, 1))

    def test_restore_reproduces_the_files_and_keeps_a_different_local_file(self):
        h.pack(self.root, self.out, ROWS)
        fresh = Path(self.tmp.name) / "fresh"
        written, skipped, problems = h.restore(self.out, fresh)
        self.assertEqual((written, problems), (2, []))
        self.assertEqual((fresh / "data/tape/binance/2026-10-28.parquet").read_bytes(), b"a" * 1000)
        again = h.restore(self.out, fresh)
        self.assertEqual((again[0], again[1], again[2]), (0, 2, []))
        (fresh / "data/unlocks/2026-10-21/a.json").write_bytes(b"local newer")
        _, _, problems = h.restore(self.out, fresh)
        self.assertEqual(len(problems), 1)
        self.assertEqual((fresh / "data/unlocks/2026-10-21/a.json").read_bytes(), b"local newer")

    def test_restore_applies_a_later_version_of_a_file(self):
        h.pack(self.root, self.out, ROWS)
        put(self.root, "data/tape/binance/2026-10-28.parquet", b"b" * 2000)
        h.pack(self.root, self.out, ROWS)
        fresh = Path(self.tmp.name) / "fresh"
        h.restore(self.out, fresh)
        self.assertEqual((fresh / "data/tape/binance/2026-10-28.parquet").read_bytes(), b"b" * 2000)

    def test_chunks_respect_the_size_limit_and_the_budget(self):
        for i in range(6):
            put(self.root, f"data/tape/binance/d{i}.parquet", os.urandom(400_000))
        s = h.pack(self.root, self.out, ROWS, max_chunk_mb=1.0)
        self.assertGreaterEqual(s["chunks"], 3)
        out2 = Path(self.tmp.name) / "small"
        s2 = h.pack(self.root, out2, ROWS, max_chunk_mb=1.0, budget_mb=0.9)
        self.assertTrue(s2["over_budget"])
        self.assertLessEqual(s2["archive_bytes"], 0.9e6)

    def test_oversize_files_are_reported_not_packed(self):
        p = put(self.root, "data/tape/binance/huge.parquet", b"h")
        os.truncate(p, (h.MAX_FILE_MB + 1) * 1_000_000)
        t = time.time() - 3600
        os.utime(p, (t, t))
        s = h.pack(self.root, self.out, ROWS)
        self.assertEqual(s["oversize"], ["data/tape/binance/huge.parquet"])
        self.assertNotIn("data/tape/binance/huge.parquet", self.names())

    def test_a_damaged_chunk_and_a_member_outside_data_are_refused(self):
        h.pack(self.root, self.out, ROWS)
        chunk = next(self.out.glob("chunk-*.tar.gz"))
        fresh = Path(self.tmp.name) / "fresh"
        chunk.write_bytes(chunk.read_bytes()[:-5])
        written, _, problems = h.restore(self.out, fresh)
        self.assertEqual(written, 0)
        self.assertTrue(any("sha256" in p for p in problems))
        evil = Path(self.tmp.name) / "evil"
        evil.mkdir()
        name = "chunk-00001.tar.gz"
        with tarfile.open(evil / name, "w:gz") as tar:
            for member in ("../outside.txt", "etc/passwd"):
                info = tarfile.TarInfo(member)
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        with open(evil / "chunks.csv", "w", newline="") as f:
            csv.writer(f, lineterminator="\n").writerows([h.CHUNK_COLS, [name, 1, h.sha256_file(evil / name), 2, "t"]])
        with open(evil / "files.csv", "w", newline="") as f:
            csv.writer(f, lineterminator="\n").writerow(h.FILE_COLS)
        written, _, problems = h.restore(evil, Path(self.tmp.name) / "target")
        self.assertEqual(written, 0)
        self.assertEqual(len(problems), 2)
        self.assertFalse((Path(self.tmp.name) / "outside.txt").exists())


class Status(unittest.TestCase):
    def test_status_reports_totals_unclassified_and_absent(self):
        with tempfile.TemporaryDirectory() as d:
            put(d, "data/tape/a.parquet", b"a" * 10)
            put(d, "data/klines_1h/b.parquet", b"b" * 5)
            put(d, "data/mystery/c.bin", b"c" * 7)
            totals, unclassified, absent = h.status(Path(d), ROWS)
            self.assertEqual(totals["RECORDED"], [1, 10])
            self.assertEqual(totals["REFETCH"], [1, 5])
            self.assertEqual(unclassified, {"data/mystery": 7})
            self.assertIn("data/databento", absent)


if __name__ == "__main__":
    unittest.main()
