"""Invented decision/receipt boundaries; no market evidence or real orders."""
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from lab.paper_account import PaperEvent
from lab.paper_controls import RiskPolicy
from lab.paper_session import EntryIntent, PaperSession
from lab.stream_quotes import FrameClock, NS


ANCHOR = FrameClock(1_790_000_000 * NS, 10 * NS)
DECISION = ANCHOR.mono_ns + 2 * NS
DECISION_UTC = ANCHOR.utc_ns + DECISION - ANCHOR.mono_ns
BALANCES = {('mexc', 'USDT'): 1000}


def clock(mono_ns):
    return FrameClock(ANCHOR.utc_ns + mono_ns - ANCHOR.mono_ns, mono_ns)


class PaperSessionTimingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def session(self, name):
        session = PaperSession(Path(self.tmp.name) / name, BALANCES, ANCHOR,
            RiskPolicy('invented-timing-policy'), contract_version='fixture-v1')
        self.addCleanup(session.close)
        return session

    def admit(self, session, side):
        # A valid, recent source observation can precede the actual decision.
        # Its timestamp must not become the execution eligibility boundary.
        proposal = EntryIntent(intent_id='one', venue='mexc', asset='USDT',
            symbol='FIXTURE', quantity_base=side, reference_price=100,
            expected_gross_quote=10, round_trip_cost_quote=1,
            error_bound_quote=1, error_calibrated=True)
        result = session.propose_entry(proposal, asof=DECISION,
            clock=clock(DECISION - 500_000_000), complete=True,
            session_open=True, fee_inputs_known=True,
            expected_contract_version='fixture-v1', mode='fixture')
        self.assertTrue(result['intent_admitted'])

    def receipt(self, side, execution_offset_ns):
        return PaperEvent(event_id='explicit-fill', kind='fill', venue='mexc',
            asset='USDT', symbol='FIXTURE', quantity=side, price=100, fee=0,
            occurred_ns=DECISION_UTC + execution_offset_ns,
            clock=clock(DECISION + 250_000_000),
            source_identity='invented explicit receipt, not market evidence')

    def test_execution_before_actual_decision_cannot_discharge_either_side(self):
        for side in (1, -1):
            with self.subTest(side=side):
                session = self.session(str(side))
                self.admit(session, side)
                receipt = self.receipt(side, -250_000_000)
                result = session.record_receipt(receipt, receipt.clock.mono_ns,
                                                intent_id='one')
                # Accounting the observed exposure remains mandatory even
                # when it cannot count as execution of the later proposal.
                self.assertEqual(result['financial_receipt']['status'], 'applied')
                self.assertEqual(session.account.positions[
                    ('mexc', 'USDT', 'FIXTURE')][0], Decimal(side))
                self.assertFalse(result['joined_to_intent'])
                self.assertEqual(result['pending_intents'], ['one'])
                self.assertTrue(result['issues'])

    def test_restart_and_duplicate_delivery_preserve_actual_decision_boundary(self):
        for side in (1, -1):
            with self.subTest(side=side):
                name = 'restart-' + str(side)
                session = self.session(name)
                self.admit(session, side)
                session.close()
                session = self.session(name)
                receipt = self.receipt(side, -250_000_000)
                first = session.record_receipt(receipt, receipt.clock.mono_ns,
                                               intent_id='one')
                self.assertFalse(first['joined_to_intent'])
                session.close()
                session = self.session(name)
                duplicate = session.record_receipt(receipt, DECISION + NS,
                                                   intent_id='one')
                self.assertEqual(duplicate['financial_receipt']['status'], 'duplicate')
                self.assertFalse(duplicate['joined_to_intent'])
                self.assertEqual(duplicate['pending_intents'], ['one'])
                self.assertEqual(session.account.cash[('mexc', 'USDT')], 1000)

    def test_execution_at_or_after_actual_decision_can_join_and_survive_restart(self):
        for side in (1, -1):
            for offset in (0, 100_000_000):
                with self.subTest(side=side, execution_offset_ns=offset):
                    name = 'valid-' + str(side) + '-' + str(offset)
                    session = self.session(name)
                    self.admit(session, side)
                    receipt = self.receipt(side, offset)
                    result = session.record_receipt(receipt, receipt.clock.mono_ns,
                                                    intent_id='one')
                    self.assertTrue(result['joined_to_intent'])
                    self.assertEqual(result['pending_intents'], [])
                    self.assertEqual(result['issues'], [])
                    session.close()
                    session = self.session(name)
                    duplicate = session.record_receipt(receipt, DECISION + NS,
                                                       intent_id='one')
                    self.assertTrue(duplicate['joined_to_intent'])
                    self.assertEqual(duplicate['pending_intents'], [])
                    self.assertEqual(session.account.cash[('mexc', 'USDT')], 1000)


if __name__ == '__main__':
    unittest.main()
