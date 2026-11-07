"""Audit source-binding failures and independent invented cash-ledger checks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab import prereg
from lab.inverse_cash import InverseContract
from lab.locked_carry import SpotContract, CarryFees, plan_carry
from scripts import audit_locked_carry_mechanics as audit


class AuditTests(unittest.TestCase):
    def test_missing_freeze_and_source_drift_stop_before_measurement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            lane = root / 'lane'
            lane.mkdir()
            code = root / 'toy.py'
            code.write_text('invented source\n')
            manifest = lane / 'code_inputs.json'
            manifest.write_text(json.dumps({'toy.py': hashlib.sha256(code.read_bytes()).hexdigest()}))
            protocol = lane / 'PREREG.md'
            protocol.write_text('code_inputs.json SHA256: ' + hashlib.sha256(manifest.read_bytes()).hexdigest())
            with patch.object(audit, 'ROOT', root), patch.object(audit, 'LANE', lane):
                with self.assertRaises(prereg.PreregError): audit.verify()
                prereg.freeze(protocol)
                self.assertEqual(audit.verify(), prereg.verify(protocol))
                code.write_text('changed invented source\n')
                with self.assertRaisesRegex(ValueError, 'frozen input changed'): audit.verify()

    def test_separate_daily_delivery_ledger_preserves_dust_and_cash(self):
        spot = SpotContract('TOY_QUOTE', 'TOY', 'QUOTE', '.01', '.01', 0, 'invented')
        future = InverseContract('TOY-DATED', 'TOY', 10, 10, audit.ANCHOR.utc_ns + 100 * audit.NS, 'invented')
        fees = CarryFees(0, 'base_received', 0, 0, 0, 'quote_received', 'invented')
        bids = [('100', '10000')]
        plan = plan_carry(spot, future, fees, [('100', '100')], bids, 100)
        self.assertEqual(audit.ledger_oracle(plan, bids, 1, 100, 1)['cash'], 100)
        bad_exit = audit.ledger_oracle(plan, bids, 1, 20000, 1)
        self.assertEqual(bad_exit['cash'], 0)
        self.assertGreater(bad_exit['dust'], 0)


if __name__ == '__main__': unittest.main()
