"""Offline extraction/version guards; the C++ synthetic replay is a separate CLI."""

import hashlib
import html
import unittest
from unittest.mock import patch

from research import audit_fh_hft as audit


class SourceGuardTests(unittest.TestCase):
    def test_changed_source_never_invokes_compiler_or_subprocess(self):
        with patch.object(audit.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                audit.audit(b"int tradeHFT() { return 1; }")
            run.assert_not_called()

    def test_html_decodes_code_entities_without_selecting_other_blocks(self):
        # A stand-in checks extraction only, not the publisher's algorithm.
        source = b"int named() { return 1 < 2; }\n"
        raw = ("<pre>other</pre><pre><code>" + html.escape(source.decode())
               + "</code></pre>").encode()
        with patch.object(audit, "SIGNAL_SHA256", hashlib.sha256(source).hexdigest()):
            self.assertEqual(audit.checked_signal(raw), source)

    def test_ambiguous_matching_blocks_are_rejected(self):
        source = b"exact block"
        raw = b"<pre>exact block</pre><pre>exact block</pre>"
        with patch.object(audit, "SIGNAL_SHA256", hashlib.sha256(source).hexdigest()):
            with self.assertRaises(ValueError):
                audit.checked_signal(raw)

    def test_exact_raw_block_is_accepted_without_html_rewriting(self):
        source = b"raw code with tabs\tand newline\n"
        with patch.object(audit, "SIGNAL_SHA256", hashlib.sha256(source).hexdigest()):
            self.assertEqual(audit.checked_signal(source), source)


if __name__ == "__main__":
    unittest.main()
