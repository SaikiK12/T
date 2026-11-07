"""The independent checker must reject a corrupted trade or removed calendar day."""
from contextlib import redirect_stdout
from io import StringIO
import json
import unittest

from scripts.check_orb_pilot import audit
from scripts.run_orb_family import run
from tests import test_run_orb_family as fixtures


class OrbIndependentAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OrbRunnerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.lane = self.fixture.root, self.fixture.lane
        with redirect_stdout(StringIO()):
            run(self.root, self.lane, 'synthetic')
        self.result = self.lane/'runs/synthetic/result.json'

    def test_independent_rational_audit_and_trade_corruption(self):
        report = audit(self.root, self.lane, self.result)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['ticket_checks'], 1)
        d = json.loads(self.result.read_text())
        d['result']['days'][0]['accounts']['parent_1x']['pnl'] += .01
        self.result.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'rational pnl discrepancy'):
            audit(self.root, self.lane, self.result)

    def test_calendar_deletion_refused(self):
        d = json.loads(self.result.read_text())
        d['result']['days'] = []
        self.result.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, 'calendar deletion'):
            audit(self.root, self.lane, self.result)


if __name__ == '__main__':unittest.main()
