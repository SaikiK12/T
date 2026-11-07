import json
from pathlib import Path
import unittest
from research.audit_blueshift_pairs import audit, SOURCE_SHA256


class PairsAuditGuards(unittest.TestCase):
    def test_changed_source_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            audit(b'raise RuntimeError("must not execute")')

    def test_receipt_matches_finite_protocol(self):
        folder = Path(__file__).resolve().parents[1] / 'research' / 'fixtures'
        protocol = json.loads((folder / 'blueshift_pairs_protocol.json').read_text())
        receipt = json.loads((folder / 'blueshift_pairs_audit.json').read_text())
        self.assertEqual(receipt['source_sha256'], SOURCE_SHA256)
        self.assertEqual(protocol['source_sha256'], SOURCE_SHA256)
        self.assertEqual([c['z'] for c in receipt['signal_cases']], protocol['signal_z_cases'])
        self.assertEqual([c['hedge_ratio'] for c in receipt['weight_cases']], protocol['weight_hedge_ratios'])
        self.assertEqual(receipt['execution_scope'], protocol['functions'])


if __name__ == '__main__':
    unittest.main()
