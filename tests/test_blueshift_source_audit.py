"""Version and execution-scope guards; the pinned-source audit is a separate CLI."""

import hashlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research import audit_blueshift_no_regret as audit


class SourceScopeTests(unittest.TestCase):
    def test_mismatched_source_is_rejected_before_compile(self):
        with patch("builtins.compile") as compile_source:
            with self.assertRaisesRegex(ValueError, "version mismatch"):
                audit.definitions(b"raise RuntimeError('must not run')")
            compile_source.assert_not_called()

    def test_only_named_methods_are_executed(self):
        # This stand-in tests extraction boundaries, not the publisher's algorithm.
        source = b"""
raise RuntimeError('top level must not run')
class Advisor:
    raise RuntimeError('class body must not run')
    def update_performance(self):
        self.perf += 1
    def order(self):
        raise RuntimeError('unselected method must not run')
class Agent:
    def weighing_function(self):
        return {'unchanged': self.perf}
"""
        with patch.object(audit, "SHA256", hashlib.sha256(source).hexdigest()):
            update, weigh = audit.definitions(source)
        state = SimpleNamespace(perf=10)
        update(state)
        self.assertEqual(weigh(state), {"unchanged": 11})

    def test_missing_selected_method_fails(self):
        source = b"class Advisor: pass\nclass Agent: pass\n"
        with patch.object(audit, "SHA256", hashlib.sha256(source).hexdigest()):
            with self.assertRaises(ValueError):
                audit.definitions(source)


if __name__ == "__main__":
    unittest.main()
