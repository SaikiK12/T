from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.opportunity_execution_v1.fixture_support import Fixture, clock, A
from lab.opportunity_execution import OpportunityExecution
from lab.opportunity_value import Outcome
from lab.paper_account import PaperEvent


class OpportunityExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.f = Fixture(self.temp.name); self.addCleanup(lambda: self.f.execution.close())

    def test_budget_survives_batches_restart_and_single_writer(self):
        f = self.f
        self.assertTrue(f.admit('one', q='6')['rows'][0]['reserved'])
        with self.assertRaises(BlockingIOError):
            OpportunityExecution(f.account, f.risk, account_id='R338-invented')
        f.reopen()
        second = f.admit('two', q='6', t=10)['rows'][0]
        self.assertFalse(second['reserved'])
        self.assertIn('durable_segregated_capital_exceeded', second['reasons'])
        self.assertEqual(f.account.snapshot(clock(10).mono_ns)['accounts'][0]['cash'], '1000')
        self.assertEqual(len(f.execution.allocations), 1)

    def test_batch_replay_preserves_clock_risk_and_capital(self):
        f = self.f; request = f.request()
        first = f.execution.admit('same', **request)
        risk = (f.root/'risk.jsonl').read_bytes(); journal = f.account.journal_path.read_bytes()
        again = f.execution.admit('same', **request)
        self.assertTrue(again['duplicate']); self.assertEqual(first['rows'], again['rows'])
        self.assertEqual(risk, (f.root/'risk.jsonl').read_bytes())
        self.assertEqual(journal, f.account.journal_path.read_bytes())
        changed = dict(request); changed['asof'] += 1
        with self.assertRaises(ValueError):f.execution.admit('same', **changed)
        self.assertIn('batch_identity_conflict', f.view()['reasons'])

    def test_same_sign_pooled_margin_is_not_counted_twice(self):
        f = self.f
        self.assertTrue(f.admit('a', bid=99, ask=101, reserve='.8')['rows'][0]['reserved'])
        f.post('a', 'oa', 'submit', q='1')
        f.post('a', 'oa', 'fill', q='1', price='100', fee='.1', trade='ta')
        f.post('a', 'oa', 'complete', total='1')
        request = f.request('b', t=100, bid=198, ask=202, reserve='1.6')
        request['marks'] = f.marks(100, {'ETH': '200'})
        self.assertTrue(f.execution.admit('batch-b', **request)['rows'][0]['reserved'])
        f.post('b', 'ob', 'submit', q='1', t=110)
        f.post('b', 'ob', 'fill', q='1', price='200', fee='.2', trade='tb', t=120)
        f.post('b', 'ob', 'complete', total='1', t=130)
        view = f.view(prices={'ETH': '150'})
        holdings = {h['allocation_id']: h for h in view['holdings']}
        self.assertEqual(F(holdings['a']['attributed_actual_locked_quote']), 150)
        self.assertEqual(F(holdings['b']['attributed_actual_locked_quote']), 150)
        self.assertEqual(F(view['accounts'][0]['extra_capital_floor_quote']), 70)
        self.assertEqual(F(view['account']['accounts'][0]['locked_capital'])+70, 370)
        self.assertEqual(F(view['accounts'][0]['available_after_floors_quote']), F('999.7')-370)
        f.reopen(); self.assertEqual(f.view(prices={'ETH': '150'})['holdings'], view['holdings'])

    def test_crash_exposes_missing_join_blocks_writes_and_recovers_original_clock(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        fill, at = f.receipt('one', 'o', 'fill', q='1', price='100', fee='.1', trade='t')
        with patch.object(f.account, 'post', side_effect=RuntimeError('injected process loss')):
            with self.assertRaises(RuntimeError):f.execution.post(fill, at)
        self.assertIn('receipt_to_cash_join_incomplete', f.execution.snapshot(at)['reasons'])
        ack, later = f.receipt('one', 'o', 'ack')
        with self.assertRaises(ValueError):f.execution.post(ack, later)
        f.reopen(); f.execution.recover(later)
        self.assertEqual(f.account.accepted_events[0].clock, fill.clock)
        self.assertEqual(f.account.accepted_events[0].quantity, D(1))
        duplicate = replace(fill, receipt_id='alternate-envelope', clock=clock(100))
        f.execution.post(duplicate, clock(100).mono_ns)
        self.assertEqual(len(f.account.accepted_events), 1)

    def test_fill_is_not_terminal_and_only_reconciled_flat_releases(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        f.post('one', 'o', 'fill', q='1', price='100', trade='t')
        self.assertEqual(f.view()['pending_orders'], 1)
        self.assertFalse(f.release('one')['released'])
        f.post('one', 'o', 'complete', total='1', t=1010)
        f.post('one', 'exit', 'submit', q='1', purpose='close', t=1020)
        f.post('one', 'exit', 'fill', q='1', price='100', trade='x', purpose='close', t=1030)
        self.assertFalse(f.release('one', t=1040)['released'])
        f.post('one', 'exit', 'complete', total='1', purpose='close', t=1050)
        self.assertTrue(f.release('one', t=1060)['released'])
        self.assertEqual(f.view(t=1070)['accounts'][0]['extra_capital_floor_quote'], '0')

    def test_cancel_request_unknown_terminal_and_partial_fills_keep_reserve(self):
        f = self.f; f.admit(q='2'); f.post('one', 'o', 'submit', q='2')
        f.post('one', 'o', 'fill', q='1', price='100', trade='t')
        f.post('one', 'o', 'cancel_request')
        self.assertFalse(f.release('one')['released'])
        f.post('one', 'o', 'cancelled', total=None, t=1010)
        view = f.view(t=1020)
        self.assertIn('terminal_fill_totals_missing_or_unreconciled', view['reasons'])
        f.post('one', 'o', 'cancelled', total='1', t=1030)
        f.post('one', 'x', 'submit', q='1', purpose='close', t=1040)
        f.post('one', 'x', 'fill', q='1', price='100', trade='x', purpose='close', t=1050)
        f.post('one', 'x', 'complete', total='1', purpose='close', t=1060)
        self.assertTrue(f.release('one', t=1070)['released'])

    def test_trade_identity_cannot_move_between_models_or_orders(self):
        f = self.f; f.admit('a'); f.admit('b', t=1)
        f.post('a', 'a', 'submit', q='1', t=10)
        f.post('a', 'a', 'fill', q='1', price='100', trade='same', t=20)
        f.post('b', 'b', 'submit', q='1', t=30)
        f.post('b', 'b', 'fill', q='1', price='100', trade='same', t=40)
        self.assertEqual(len(f.account.accepted_events), 1)
        self.assertIn('trade_identity_or_owner_conflict', f.view()['reasons'])
        self.assertFalse(f.release('b')['released'])

    def test_observed_overfill_is_retained_as_exposure(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        f.post('one', 'o', 'fill', q='2', price='100', fee='.2', trade='over')
        view = f.view()
        self.assertIn('observed_overfill_or_unknown_requested_total', view['reasons'])
        self.assertEqual(view['account']['accounts'][0]['positions'][0]['quantity_base'], '2')
        self.assertFalse(f.release('one')['released'])

    def test_risk_path_and_history_cannot_reset(self):
        f = self.f; f.admit(); f.execution.close()
        with self.assertRaises(ValueError):
            OpportunityExecution(f.account, f.new_risk('different-risk.jsonl'), account_id='R338-invented')
        # Deliberately corrupt a test-owned file only; no repository data touched.
        (f.root/'risk.jsonl').write_bytes(b'')
        with self.assertRaises(ValueError):
            OpportunityExecution(f.account, f.new_risk(), account_id='R338-invented')

    def test_incomplete_assessment_resumes_identical_source_inputs(self):
        f = self.f; original = f.execution._commit
        def fail_after_risk(payload, head):
            if payload['action'] == 'admission':raise RuntimeError('injected between journals')
            return original(payload, head)
        with patch.object(f.execution, '_commit', side_effect=fail_after_risk):
            with self.assertRaises(RuntimeError):f.admit()
        self.assertIn('assessment_incomplete', f.execution.snapshot(clock().mono_ns)['reasons'])
        f.reopen()
        result = f.execution.resume_assessment()
        self.assertTrue(result['rows'][0]['reserved'])
        self.assertEqual(len(f.execution.allocations), 1)

    def test_malformed_scope_does_not_poison_future_batches(self):
        f = self.f; request = f.request(); request['fees_bp'] = {}
        journal = f.account.journal_path.read_bytes(); risk = (f.root/'risk.jsonl').read_bytes()
        with self.assertRaises(ValueError):f.execution.admit('bad', **request)
        self.assertEqual(journal, f.account.journal_path.read_bytes())
        self.assertEqual(risk, (f.root/'risk.jsonl').read_bytes())
        self.assertTrue(f.admit()['rows'][0]['reserved'])

    def test_unknown_and_negative_forecasts_never_credit_cash(self):
        f = self.f
        row = f.admit('weak', outcomes=(Outcome('.7', '1', '0'), Outcome('.3', '-1', '0')))['rows'][0]
        self.assertFalse(row['reserved'])
        row = f.admit('unknown', t=1, outcomes=(Outcome('1', '100', None),))['rows'][0]
        self.assertFalse(row['reserved']); self.assertIsNone(row['forecast']['expected_gross_quote'])
        self.assertEqual(f.account.snapshot(clock(1).mono_ns)['accounts'][0]['cash'], '1000')

    def test_opposite_models_in_same_batch_do_not_net_capital_or_risk(self):
        f = self.f; a = f.request('a'); b = f.request('b', q='-1')
        a['opportunities'] += b['opportunities']
        for key in ('books', 'fees_bp', 'market_reports'):a[key].update(b[key])
        result = f.execution.admit('both', **a)
        self.assertTrue(result['rows'][0]['reserved']); self.assertFalse(result['rows'][1]['reserved'])
        self.assertIn('opposite_model_inventory_requires_separate_contract', result['rows'][1]['reasons'])

    def test_unknown_fee_and_funding_keep_known_components_without_fake_zero(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        result = f.post('one', 'o', 'fill', q='1', price='100', fee=None, trade='t')
        event_id = result['recovered'][0]['event_id']
        self.assertIsNone(f.view()['account']['accounts'][0]['cash'])
        event = PaperEvent('fee-resolution', 'fee_resolution', 'mexc', 'USDT', 'ETH',
            clock(1010).utc_ns, clock(1010), 'invented-fee', amount='.1', resolves=event_id)
        f.execution.post_cash(event, clock(1010).mono_ns)
        self.assertEqual(f.view(t=1020)['account']['accounts'][0]['cash'], '999.9')
        funding = PaperEvent('unknown-funding', 'funding', 'mexc', 'USDT', 'ETH',
            clock(1030).utc_ns, clock(1030), 'invented-funding', amount=None)
        f.execution.post_cash(funding, clock(1030).mono_ns)
        account = f.view(t=1040)['account']['accounts'][0]
        self.assertIsNone(account['cash']); self.assertEqual(account['known_cash_component'], '999.9')

    def test_precision_of_partial_fill_is_independent_of_ambient_decimal_context(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        quantity = '0.123456789012345678901234567890123456789'
        with localcontext() as context:
            context.prec = 12
            f.post('one', 'o', 'fill', q=quantity, price='100', trade='precise')
        self.assertEqual(f.account.accepted_events[0].quantity, D(quantity))
        view = f.view()
        self.assertNotIn('financial_join_payload_or_first_clock_mismatch', view['reasons'])
        self.assertNotIn('model_inventory_not_equal_to_same_sign_account', view['reasons'])

    def test_fraction_attribution_conserves_reported_locked_collateral(self):
        f = self.f; f.admit('a'); f.admit('b', q='2', t=1)
        f.post('a', 'a', 'submit', q='1', t=10)
        f.post('a', 'a', 'fill', q='1', price='100', trade='a', t=20)
        f.post('b', 'b', 'submit', q='2', t=30)
        f.post('b', 'b', 'fill', q='2', price='150', trade='b', t=40)
        view = f.view()
        attributed = sum((F(h['attributed_actual_locked_quote']) for h in view['holdings']), F(0))
        self.assertEqual(attributed, F(view['account']['accounts'][0]['locked_capital']))
        self.assertEqual(len(f.execution.allocations), 2)

    def test_observed_drawdown_stop_survives_price_recovery(self):
        f = self.f; f.admit(); f.post('one', 'o', 'submit', q='1')
        f.post('one', 'o', 'fill', q='1', price='100', trade='t')
        request = f.request('watch', t=100)
        result = f.execution.observe_risk('watch', asof=clock(100).mono_ns,
            risk_inputs=request['risk_inputs'], marks=f.marks(100, {'ETH': '50'}))
        self.assertIn('risk:loss_limit', result['risk_stops'])
        self.assertEqual(result['rows'], [])
        f.reopen(); request = f.request('next', t=200)
        request['marks'] = f.marks(200, {'ETH': '100'})
        later = f.execution.admit('next', **request)
        self.assertFalse(later['rows'][0]['reserved'])
        self.assertIn('risk:loss_limit', later['risk_stops'])

    def test_rejected_forecast_identity_cannot_refresh_later(self):
        f = self.f
        f.admit('weak', outcomes=(Outcome('.7', '1', '0'), Outcome('.3', '-1', '0')))
        result = f.execution.admit('changed', **f.request('weak', t=10))
        self.assertFalse(result['rows'][0]['reserved'])
        self.assertIn('opportunity_identity_conflict', f.view()['reasons'])


if __name__ == '__main__':
    unittest.main()
