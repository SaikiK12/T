"""Offline scope guards; the original-source audit runs separately with its pinned input."""

import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from research import audit_qc_term_structure as audit


class SourceScopeTests(unittest.TestCase):
    def test_source_drift_is_rejected_before_compile(self):
        with patch("builtins.compile") as compile_source:
            with self.assertRaisesRegex(ValueError, "Source version mismatch"):
                audit.definition(b"raise RuntimeError('must not execute')")
            compile_source.assert_not_called()

    def test_only_selected_block_is_compiled(self):
        # Invented stand-in checks the extraction boundary, not the native strategy.
        first = "executed = 1"
        raw = ("raise RuntimeError('HTML outside block must not run')"
               '<pre class="python">' + first + '</pre>'
               '<pre class="python">raise RuntimeError("History must not run")</pre>'
               '<pre class="python">raise RuntimeError("orders must not run")</pre>').encode()
        with patch.object(audit, "SHA256", hashlib.sha256(raw).hexdigest()), \
                patch.object(audit, "BLOCK_SHA256", hashlib.sha256(first.encode()).hexdigest()):
            code = audit.definition(raw)
        self.assertEqual(audit.execute(code, {})["executed"], 1)

    def test_block_drift_or_missing_blocks_refuses_compile(self):
        for raw in (b'<pre class="python">changed</pre>',
                    b'<pre class="python">changed</pre>' * 3):
            with self.subTest(raw=raw), patch.object(audit, "SHA256", hashlib.sha256(raw).hexdigest()), \
                    patch("builtins.compile") as compile_source:
                with self.assertRaises(ValueError):
                    audit.definition(raw)
                compile_source.assert_not_called()

    def test_committed_receipt_retains_rank_reversal_and_scope(self):
        path = Path(__file__).resolve().parents[1] / "research/fixtures/qc_term_structure_audit.json"
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt["source_sha256"], audit.SHA256)
        self.assertEqual(receipt["selected_block_sha256"], audit.BLOCK_SHA256)
        self.assertEqual(receipt["market_trials"], 0)
        self.assertEqual(receipt["checks_passed"], len(receipt["checks"]))
        check = receipt["checks"][0]
        self.assertEqual(check["original"]["rank"], ["B1", "A1"])
        self.assertEqual(check["scaled"]["rank"], ["A1", "B1"])
        self.assertIn("Not the embedded algorithm", receipt["limits"][0])


if __name__ == "__main__":
    unittest.main()
