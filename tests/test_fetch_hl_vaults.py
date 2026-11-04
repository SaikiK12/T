"""fetch_hl_vaults: resumable append, slim records, disk stop, no network."""
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_hl_vaults as hv  # noqa: E402


def vault(a):
    return {"summary": {"vaultAddress": a, "isClosed": False}}


class FetchTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.out = Path(self.t.name)
        (self.out / "list_2026-11-04.json").write_text(json.dumps([vault("0xA"), vault("0xB"), vault("0xC")]))
        self.patch = mock.patch.object(hv, "OUT", self.out)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.t.cleanup()

    def read(self):
        with gzip.open(self.out / "details_2026-11-04.jsonl.gz", "rt") as f:
            return [json.loads(x) for x in f]

    def test_resumes_and_slims(self):
        calls = []
        fetch = lambda b: calls.append(b["vaultAddress"]) or {"vaultAddress": b["vaultAddress"], "followers": [1, 2]}
        hv.run("2026-11-04", pause=0, fetch=fetch, free_gb=lambda: 100, limit=2)
        hv.run("2026-11-04", pause=0, fetch=fetch, free_gb=lambda: 100)
        self.assertEqual(calls, ["0xa", "0xb", "0xc"])
        rows = self.read()
        self.assertEqual([r["vaultAddress"] for r in rows], ["0xa", "0xb", "0xc"])
        self.assertEqual(rows[0]["followers_n"], 2)
        self.assertNotIn("followers", rows[0])

    def test_stops_on_low_disk(self):
        n = hv.run("2026-11-04", pause=0, fetch=lambda b: {}, free_gb=lambda: 0.5)
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()


class RecoverTests(unittest.TestCase):
    def test_a_cut_file_is_rewritten_with_its_complete_lines(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "details.jsonl.gz"
            with gzip.open(path, "wt") as f:
                f.write(json.dumps({"vaultAddress": "0xA"}) + "\n" + json.dumps({"vaultAddress": "0xB"}) + "\n")
            blob = path.read_bytes()
            path.write_bytes(blob[:-12])                  # cut the gzip trailer, as a killed writer would
            seen = hv.done_addresses(path)
            self.assertLessEqual(seen, {"0xa", "0xb"})
            with gzip.open(path, "at") as f:              # appending after recovery keeps the file readable
                f.write(json.dumps({"vaultAddress": "0xC"}) + "\n")
            self.assertEqual(hv.done_addresses(path), seen | {"0xc"})
