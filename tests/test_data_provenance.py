import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from scripts import data_provenance as dp

H = dp.H


def write_hourly(path, hours):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"t": [1_700_000_000_000 + h * H for h in hours], "c": [1.0] * len(hours)}).to_parquet(path)


class DataProvenanceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.folder = self.root / "data" / "demo"
        write_hourly(self.folder / "candles_1h" / "AAA.parquet", [0, 1, 2, 3])
        write_hourly(self.folder / "candles_1h" / "BBB.parquet", [3, 0, 5])      # unsorted, hours 1, 2, 4 missing
        (self.folder / "notes").mkdir()
        (self.folder / "notes" / "readme.txt").write_text("hello\n")
        (self.folder / "skip").mkdir()
        (self.folder / "skip" / "big.bin").write_bytes(b"x" * 10)
        (self.folder / "top.txt").write_text("top\n")

    def run_main(self, *args):
        argv = ["data_provenance.py", str(self.folder), "--source", "fixture", "--script", "none", *args]
        with mock.patch.object(dp, "ROOT", self.root), mock.patch.object(sys, "argv", argv), \
                mock.patch("builtins.print"):
            dp.main()
        return json.loads((self.root / "docs" / "provenance" / "demo.json").read_text())

    def test_sha256_matches_hashlib(self):
        path = self.folder / "top.txt"
        self.assertEqual(dp.sha256(path), hashlib.sha256(b"top\n").hexdigest())

    def test_coverage_counts_bars_and_interior_holes(self):
        self.assertEqual(dp.coverage(self.folder / "candles_1h" / "AAA.parquet")["holes"], 0)
        c = dp.coverage(self.folder / "candles_1h" / "BBB.parquet")
        self.assertEqual((c["bars"], c["holes"]), (3, 3))
        self.assertEqual(c["last"] - c["first"], 5 * H)

    def test_coverage_is_none_without_open_time_column(self):
        path = self.root / "no_t.parquet"
        pd.DataFrame({"x": [1]}).to_parquet(path)
        self.assertIsNone(dp.coverage(path))
        self.assertIsNone(dp.coverage(self.folder / "top.txt"))

    def test_record_hashes_every_file_and_combined_digest(self):
        out = self.run_main()
        self.assertEqual(out["folder"], "data/demo")
        self.assertEqual(out["files"], 5)
        paths = [r["path"] for r in out["file_hashes"]]
        self.assertEqual(paths, sorted(paths))
        combined = hashlib.sha256()
        for r in out["file_hashes"]:
            self.assertEqual(r["sha256"], dp.sha256(self.folder / r["path"]))
            combined.update(f"{r['path']}\t{r['sha256']}\n".encode())
        self.assertEqual(out["combined_sha256"], combined.hexdigest())
        self.assertEqual(out["subfolders"]["."]["files"], 1)
        self.assertEqual(out["subfolders"]["candles_1h"]["files"], 2)

    def test_default_hourly_folders_end_in_1h(self):
        summary = self.run_main()["hourly_coverage"]
        self.assertEqual(list(summary), ["candles_1h"])
        self.assertEqual(summary["candles_1h"]["bars"], 7)
        self.assertEqual(summary["candles_1h"]["files_with_holes"], 1)
        self.assertEqual(summary["candles_1h"]["holes"], 3)

    def test_exclude_drops_subfolder_and_is_recorded(self):
        out = self.run_main("--exclude", "skip/")
        self.assertNotIn("skip", out["subfolders"])
        self.assertEqual(out["files"], 4)
        self.assertEqual(out["excluded"], ["skip/"])

    def test_named_hourly_folder_replaces_default(self):
        write_hourly(self.folder / "open" / "bars" / "CCC.parquet", [0, 2])
        summary = self.run_main("--hourly", "open/bars")["hourly_coverage"]
        self.assertEqual(list(summary), ["open/bars"])
        self.assertEqual(summary["open/bars"]["holes"], 1)


if __name__ == "__main__":
    unittest.main()
