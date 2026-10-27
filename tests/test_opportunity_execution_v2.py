from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from experiments.opportunity_execution_v1.fixture_support import Fixture, clock
from experiments.opportunity_execution_v2.fixture_support import FixtureV2
from lab.opportunity_execution_v2 import canonical_marks, OpportunityExecutionV2
from lab.paper_account import CloseMark


class OpportunityExecutionV2Tests(unittest.TestCase):
    def fixture(self, cls):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        f = cls(Path(temporary.name)); self.addCleanup(lambda: f.execution.close())
        f.admit('one'); f.post('one', 'o', 'submit', q='1', t=10)
        f.post('one', 'o', 'fill', q='1', price='101', fee='.202', trade='t', t=20)
        return f

    def mark(self):
        return CloseMark('mexc', 'USDT', 'ETH', D('1.0'), D('99.0'), D('.1980'),
            clock(100), clock(100).utc_ns, 'invented-unmodified-source')

    def test_original_failure_retained_and_adapter_accepts_same_values(self):
        mark = self.mark(); old = self.fixture(Fixture); new = self.fixture(FixtureV2)
        for f, failure in ((old, True), (new, False)):
            inputs = f.request('unused', t=100)['risk_inputs']
            call = lambda: f.execution.observe_risk('mark', asof=clock(100).mono_ns,
                risk_inputs=inputs, marks=(mark,))
            if failure:
                with self.assertRaisesRegex(ValueError, 'financial state changed'):call()
            else:
                self.assertEqual(call()['rows'], [])
                self.assertEqual(f.account.snapshot(clock(100).mono_ns, [mark])['accounts'][0]['cash'], '999.798')
                self.assertEqual(f.account.accepted_events[0].fee, D('.202'))
                f.reopen()
                self.assertEqual(f.execution.snapshot(clock(100).mono_ns, [mark])['unapplied_fill_ids'], [])

    def test_normalization_is_idempotent_exact_and_preserves_source_clocks(self):
        mark = self.mark(); normalized = canonical_marks((mark,))
        self.assertEqual(canonical_marks(normalized), normalized)
        self.assertEqual(normalized[0], mark)
        self.assertEqual(normalized[0].clock, mark.clock)
        self.assertEqual(normalized[0].source_identity, mark.source_identity)
        precise = replace(mark, position_quantity=D('.123456789012345678901234567890123456789'))
        self.assertEqual(canonical_marks((precise,))[0].position_quantity, precise.position_quantity)
        with self.assertRaises(ValueError):canonical_marks([{'exit_notional': '99'}])

    def test_changed_financial_state_still_blocks_pending_assessment(self):
        f = self.fixture(FixtureV2)
        from unittest.mock import patch
        from lab.paper_account import PaperEvent
        original = f.execution._commit
        def stop(payload, head):
            if payload['action'] == 'admission':raise RuntimeError('injected loss')
            return original(payload, head)
        with patch.object(f.execution, '_commit', side_effect=stop):
            with self.assertRaises(RuntimeError):
                f.execution.observe_risk('mark', asof=clock(100).mono_ns,
                    risk_inputs=f.request('unused', t=100)['risk_inputs'], marks=(self.mark(),))
        f.account.post(PaperEvent('foreign-cash', 'capital_change', 'mexc', 'USDT', 'ETH',
            clock(100).utc_ns, clock(100), 'foreign-input', amount=D(1)), clock(100).mono_ns)
        with self.assertRaisesRegex(ValueError, 'financial state changed'):
            f.execution.resume_assessment()

    def test_original_journal_is_not_silently_adopted(self):
        f = self.fixture(Fixture); f.execution.close()
        with self.assertRaises(ValueError):
            OpportunityExecutionV2(f.account, f.risk, account_id='R338-invented')
