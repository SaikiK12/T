import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lab import __main__ as lab_main, websearch

ROOT = Path(__file__).resolve().parents[1]
GOOD = dict(date="2026-11-03", agent="a", lens="l", query="q one", tool="t", fetch_status="NOT_FOUND",
            source_tier="primary", verification="UNVERIFIED")


def make_root(directory):
    root = Path(directory)
    (root / "registry").mkdir()
    (root / "research" / "intake").mkdir(parents=True)
    (root / websearch.LEDGER).write_text(",".join(websearch.COLUMNS) + "\n", encoding="utf-8")
    (root / "registry" / "methods.csv").write_text("id,method\nM001,x\n", encoding="utf-8")
    (root / "registry" / "methods_aliases.csv").write_text("rec_id,queue_id\nC1,M001\n", encoding="utf-8")
    (root / "research" / "intake" / "source_catalog_x.csv").write_text(
        "id,provider,url,research_gap\nS1,Prov,https://example.org/doc,gap\n", encoding="utf-8")
    return root


class WebSearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = make_root(self.tmp.name)

    def test_append_assigns_sequential_ids_and_keeps_old_bytes(self):
        self.assertEqual(websearch.append(self.root, **GOOD)["search_id"], "WS0001")
        before = (self.root / websearch.LEDGER).read_bytes()
        row = websearch.append(self.root, **{**GOOD, "query": "two", "queue_ids": "M001;C1"})
        self.assertEqual(row["search_id"], "WS0002")
        after = (self.root / websearch.LEDGER).read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(after[len(before):].count(b"\n"), 1)

    def test_invalid_rows_rejected_and_ledger_untouched(self):
        before = (self.root / websearch.LEDGER).read_bytes()
        for bad in ({"fetch_status": "MAYBE"}, {"source_tier": "x"}, {"verification": "y"}, {"date": "2026-13-40"},
                    {"urls_fetched": "not a url"}, {"queue_ids": "M999"}, {"routed_to": "docs/missing.md"},
                    {"query": ""}):
            with self.assertRaises(ValueError, msg=bad):
                websearch.append(self.root, **{**GOOD, **bad})
        self.assertEqual((self.root / websearch.LEDGER).read_bytes(), before)

    def test_duplicate_id_detected(self):
        row = {**GOOD, "search_id": "WS0001"}
        self.assertTrue(any("duplicate" in p for p in websearch.validate([row, dict(row)])))

    def test_seen_finds_catalog_url_and_ledger_query(self):
        websearch.append(self.root, **{**GOOD, "urls_fetched": "https://ledger.example/p"})
        self.assertEqual(websearch.seen(self.root, "EXAMPLE.org/doc")[0]["id"], "S1")
        self.assertEqual(websearch.seen(self.root, "ledger.example")[0]["id"], "WS0001")
        self.assertEqual(websearch.seen(self.root, "q one")[0]["id"], "WS0001")
        self.assertEqual(websearch.seen(self.root, "absent text"), [])

    def test_committed_ledger_passes_and_cli_agrees(self):
        self.assertEqual(websearch.validate(websearch.load(ROOT), ROOT), [])
        done = subprocess.run([sys.executable, "-m", "lab", "websearch", "check", "--json"], cwd=ROOT,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["summary"]["errors"], 0)

    def test_committed_catalog_url_is_seen(self):
        catalog = sorted((ROOT / "research" / "intake").glob("source_catalog_webdeep_*.csv"))[0]
        with catalog.open(newline="", encoding="utf-8") as handle:
            url = next(csv.DictReader(handle))["url"]
        self.assertTrue(websearch.seen(ROOT, url))

    def test_lab_routes_websearch_and_integrity_includes_it(self):
        self.assertEqual(lab_main.TOOLS["websearch"], "web_search_ledger.py")
        self.assertTrue((ROOT / "scripts" / "web_search_ledger.py").exists())
        calls = []
        real = lab_main.subprocess.run
        lab_main.subprocess.run = lambda cmd, **kw: calls.append(Path(cmd[1]).name) or subprocess.CompletedProcess(cmd, 0)
        try:
            self.assertEqual(lab_main.main(["integrity"]), 0)
        finally:
            lab_main.subprocess.run = real
        self.assertIn("web_search_ledger.py", calls)


if __name__ == "__main__":
    unittest.main()
