"""Invented admission/receipt/restart cases; no market statistics or orders."""
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lab.paper_account import PaperEvent, CloseMark
from lab.paper_controls import RiskPolicy
from lab.paper_session import PaperSession, EntryIntent
from lab.stream_quotes import FrameClock, NS


ANCHOR = FrameClock(1_790_000_000 * NS, 10 * NS)
BALANCES = {('mexc', 'USDT'): 1000}


def clock(n): return FrameClock(ANCHOR.utc_ns + n * NS, ANCHOR.mono_ns + n * NS)


def intent(id='one', **changes):
    args = dict(intent_id=id, venue='mexc', asset='USDT', symbol='FIXTURE', quantity_base=1,
                reference_price=100, expected_gross_quote=10, round_trip_cost_quote=1,
                error_bound_quote=1, error_calibrated=True)
    return EntryIntent(**{**args, **changes})


def event(id, n=1, kind='fill', **changes):
    args = dict(event_id=id, kind=kind, venue='mexc', asset='USDT', symbol='FIXTURE',
                occurred_ns=clock(n).utc_ns, clock=clock(n), source_identity='invented explicit receipt')
    if kind == 'fill': args.update(quantity=1, price=100, fee='.1')
    return PaperEvent(**{**args, **changes})


def mark(n=2, q=1, price=100, fee=0):
    return CloseMark('mexc', 'USDT', 'FIXTURE', q, D(str(abs(q))) * D(str(price)), fee,
                     clock(n), clock(n).utc_ns, 'invented liquidation quote')


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'session'

    def session(self, directory=None, balances=None):
        s = PaperSession(directory or self.path, balances or BALANCES, ANCHOR,
                         RiskPolicy('invented-policy'), contract_version='fixture-v1')
        self.addCleanup(s.close)
        return s

    def propose(self, s, i=None, n=1, **changes):
        args = dict(asof=clock(n).mono_ns, clock=clock(n), complete=True, session_open=True,
                    fee_inputs_known=True, expected_contract_version='fixture-v1', mode='fixture')
        return s.propose_entry(i or intent(), **{**args, **changes})

    def test_admission_is_only_an_intent_and_reopen_never_synthesizes_a_fill(self):
        s = self.session(); r = self.propose(s)
        self.assertTrue(r['intent_admitted']); self.assertFalse(r['actual_order_allowed'])
        self.assertEqual(s.account.accepted_events, [])
        self.assertEqual(s.account.cash[('mexc', 'USDT')], 1000)
        s.close(); s = self.session()
        state = s.status(clock(2).mono_ns)
        self.assertEqual(state['pending_intents'], ['one'])
        self.assertEqual(s.account.accepted_events, [])
        old = self.propose(s, n=2)
        self.assertEqual(old['state'], 'EXISTING_INTENT')
        self.assertFalse(old['model_new_entries_allowed'])
        blocked = self.propose(s, intent('two', symbol='OTHER'), n=2)
        self.assertIn('earlier_intent_requires_explicit_receipts', blocked['reasons'])

    def test_partial_receipts_keep_pending_and_full_receipt_completes_only_once(self):
        s = self.session(); self.propose(s, intent(quantity_base=2))
        first = event('fill-a')
        r = s.record_receipt(first, clock(1).mono_ns, intent_id='one')
        self.assertEqual(r['pending_intents'], ['one'])
        s.close(); s = self.session()
        s.record_receipt(event('fill-b', 2), clock(2).mono_ns, intent_id='one')
        self.assertEqual(s.status(clock(2).mono_ns, [mark(q=2)])['pending_intents'], [])
        before = s.account.cash.copy()
        duplicate = s.record_receipt(event('fill-b', 2), clock(2).mono_ns, intent_id='one')
        self.assertEqual(duplicate['financial_receipt']['status'], 'duplicate')
        self.assertEqual(s.account.cash, before)
        self.assertEqual(s.account.positions[('mexc', 'USDT', 'FIXTURE')][0], 2)

    def test_crash_between_financial_post_and_join_needs_explicit_idempotent_retry(self):
        s = self.session(); self.propose(s)
        original = s.account.record_evidence
        def fail_join(namespace, payload):
            if payload.get('component') == 'paper_session_join': raise RuntimeError('invented interruption')
            return original(namespace, payload)
        with patch.object(s.account, 'record_evidence', side_effect=fail_join):
            with self.assertRaises(RuntimeError):
                s.record_receipt(event('received'), clock(1).mono_ns, intent_id='one')
        s.close(); s = self.session()
        self.assertEqual(s.status(clock(2).mono_ns, [mark()])['pending_intents'], ['one'])
        self.assertEqual(s.account.cash[('mexc', 'USDT')], D('999.9'))
        r = s.record_receipt(event('received'), clock(2).mono_ns, intent_id='one')
        self.assertEqual(r['financial_receipt']['status'], 'duplicate')
        self.assertEqual(r['pending_intents'], [])
        self.assertEqual(s.account.cash[('mexc', 'USDT')], D('999.9'))

    def test_old_fill_cannot_discharge_a_new_intent_even_with_a_fresh_duplicate_clock(self):
        from dataclasses import replace
        s = self.session()
        old = event('old-open', 1, fee=0)
        s.record_receipt(old, clock(1).mono_ns)
        s.record_receipt(event('old-close', 2, quantity=-1, fee=0), clock(2).mono_ns)
        self.assertTrue(self.propose(s, n=3)['intent_admitted'])
        retry = replace(old, clock=clock(4))
        r = s.record_receipt(retry, clock(4).mono_ns, intent_id='one')
        self.assertEqual(r['financial_receipt']['status'], 'duplicate')
        self.assertFalse(r['joined_to_intent'])
        self.assertEqual(r['pending_intents'], ['one'])
        self.assertEqual(s.account.cash[('mexc', 'USDT')], 1000)
        s.close(); s = self.session()
        self.assertEqual(s.status(clock(4).mono_ns)['pending_intents'], ['one'])

    def test_same_clock_receipt_posted_before_intent_cannot_be_reassigned(self):
        s = self.session()
        old = event('same-clock-open', 1, fee=0)
        s.record_receipt(old, clock(1).mono_ns)
        s.record_receipt(event('same-clock-close', 1, quantity=-1, fee=0), clock(1).mono_ns)
        self.assertTrue(self.propose(s, n=1)['intent_admitted'])
        r = s.record_receipt(old, clock(1).mono_ns, intent_id='one')
        self.assertFalse(r['joined_to_intent'])
        self.assertEqual(r['pending_intents'], ['one'])

    def test_late_receipt_for_predecision_execution_is_booked_but_not_joined(self):
        s = self.session()
        self.assertTrue(self.propose(s, n=2)['intent_admitted'])
        late = event('late-old-execution', 2, occurred_ns=clock(1).utc_ns, fee=0)
        r = s.record_receipt(late, clock(2).mono_ns, intent_id='one')
        self.assertEqual(r['financial_receipt']['status'], 'applied')
        self.assertFalse(r['joined_to_intent'])
        self.assertEqual(r['pending_intents'], ['one'])
        self.assertEqual(s.account.positions[('mexc', 'USDT', 'FIXTURE')][0], 1)

    def test_close_uses_held_quantity_and_exit_notional_fee_then_cash_replays(self):
        s = self.session(); self.propose(s, intent(quantity_base=2))
        s.record_receipt(event('open', quantity=2, fee='.2'), clock(1).mono_ns, intent_id='one')
        s.record_receipt(event('funding', 2, 'funding', amount='1.2'), clock(2).mono_ns)
        before = (self.path / 'account.jsonl').read_bytes()
        plan = s.plan_close('mexc', 'USDT', 'FIXTURE', exit_price=110, fee_rate_fraction='.001', asof=clock(3).mono_ns)
        self.assertEqual(plan['quantity_base'], '-2')
        self.assertEqual(D(plan['estimated_fee_quote']), D('.220'))
        self.assertEqual((self.path / 'account.jsonl').read_bytes(), before)
        s.record_receipt(event('close', 3, quantity=plan['quantity_base'], price=plan['exit_price'],
                               fee=plan['estimated_fee_quote']), clock(3).mono_ns)
        expected = s.status(clock(3).mono_ns)['snapshot']
        self.assertEqual(D(expected['accounts'][0]['cash']), D('1020.780'))
        s.close(); s = self.session()
        self.assertEqual(s.status(clock(3).mono_ns)['snapshot'], expected)
        s.record_receipt(event('funding', 2, 'funding', amount='1.2'), clock(3).mono_ns)
        self.assertEqual(s.account.cash[('mexc', 'USDT')], D('1020.780'))

    def test_persistent_loss_stop_blocks_entries_but_never_suppresses_observed_receipts(self):
        s = self.session(); self.propose(s)
        s.record_receipt(event('open', fee=0), clock(1).mono_ns, intent_id='one')
        s.record_receipt(event('close', 2, quantity=-1, price=50, fee=0), clock(2).mono_ns)
        blocked = self.propose(s, intent('after-loss'), n=2)
        self.assertIn('risk:loss_limit', blocked['risk']['legacy_risk']['stops'])
        s.record_receipt(event('deposit', 3, 'capital_change', amount=1000), clock(3).mono_ns)
        s.close(); s = self.session()
        again = self.propose(s, intent('after-reopen'), n=3)
        self.assertFalse(again['intent_admitted'])
        # Accounting an unexpected receipt is independent of admitting entries.
        r = s.record_receipt(event('unexpected', 4, fee=0), clock(4).mono_ns)
        self.assertEqual(r['financial_receipt']['status'], 'applied')
        self.assertEqual(s.account.positions[('mexc', 'USDT', 'FIXTURE')][0], 1)

    def test_capital_veto_does_not_net_other_venue_or_asset_balance(self):
        s = self.session(balances={('mexc', 'USDT'):1000, ('lighter', 'USDC'):10000})
        s.record_receipt(event('withdraw', 1, 'capital_change', amount=-950), clock(1).mono_ns)
        r = self.propose(s)
        self.assertFalse(r['intent_admitted'])
        cap = next(a for a in r['risk']['capital']['accounts'] if a['venue'] == 'mexc')
        self.assertIn('proposed_reserve_exceeds_available_capital', cap['reasons'])
        with self.assertRaises(ValueError): self.propose(s, intent('wrong-asset', asset='USDC'))

    def test_projected_concentration_veto_checks_the_proposed_position(self):
        s = self.session()
        r = self.propose(s, intent(quantity_base=3))
        self.assertTrue(r['risk']['legacy_risk']['model_new_entries_allowed'])
        self.assertIn('proposed_symbol_gross_limit', r['reasons'])
        self.assertEqual(s.account.accepted_events, [])
        self.assertTrue(self.propose(s, intent('smaller'))['intent_admitted'])

    def test_unknown_forecast_costs_and_fee_declarations_block_new_entries(self):
        for j, changes in enumerate(({'round_trip_cost_quote':None}, {'error_bound_quote':None},
                                    {'expected_gross_quote':None}, {'error_calibrated':False})):
            s = self.session(Path(self.tmp.name) / str(j))
            self.assertFalse(self.propose(s, intent(**changes))['intent_admitted'])
        s = self.session()
        r = self.propose(s, fee_inputs_known=False)
        self.assertFalse(r['intent_admitted'])
        self.assertIn('data:complete_session_fee_inputs_required', r['risk']['legacy_risk']['stops'])

    def test_unknown_marks_or_cash_stay_unknown_and_block(self):
        s = self.session()
        s.record_receipt(event('observed'), clock(1).mono_ns)
        r = self.propose(s, intent(symbol='OTHER'), n=2)
        self.assertFalse(r['intent_admitted'])
        self.assertIn('nav_unknown', r['risk']['capital']['accounts'][0]['unknown'])
        self.assertIsNone(s.status(clock(2).mono_ns)['snapshot']['accounts'][0]['nav'])
        # Unknown fee on an explicit close is booked as unknown cash.
        close = s.plan_close('mexc', 'USDT', 'FIXTURE', exit_price=110, fee_rate_fraction=None, asof=clock(2).mono_ns)
        self.assertIsNone(close['estimated_fee_quote'])
        s.record_receipt(event('close', 2, quantity=close['quantity_base'], price=110, fee=None), clock(2).mono_ns)
        self.assertIsNone(s.status(clock(2).mono_ns)['snapshot']['accounts'][0]['cash'])
        s.record_receipt(event('fee-resolution', 3, 'fee_resolution', amount='.11', resolves='close'), clock(3).mono_ns)
        self.assertEqual(s.account.cash[('mexc', 'USDT')], D('1009.79'))

    def test_mismatched_receipt_is_booked_but_session_remains_blocked(self):
        s = self.session(); self.propose(s)
        r = s.record_receipt(event('unexpected-size', quantity=2), clock(1).mono_ns, intent_id='one')
        self.assertEqual(r['financial_receipt']['status'], 'applied')
        self.assertFalse(r['joined_to_intent']); self.assertTrue(r['issues'])
        self.assertEqual(s.account.positions[('mexc', 'USDT', 'FIXTURE')][0], 2)
        s.close(); s = self.session()
        blocked = self.propose(s, intent('different', symbol='OTHER'), n=2)
        self.assertIn('session_receipt_join_requires_reconciliation', blocked['reasons'])

    def test_single_writer_and_changed_intent_or_policy_cannot_reset(self):
        s = self.session(); self.propose(s)
        with self.assertRaises(BlockingIOError): self.session()
        with self.assertRaises(ValueError): self.propose(s, intent(reference_price=101))
        s.close()
        with self.assertRaises(ValueError):
            PaperSession(self.path, BALANCES, ANCHOR, RiskPolicy('changed'), contract_version='fixture-v1')

    def test_torn_native_journal_is_retained_and_refused(self):
        s = self.session(); self.propose(s); s.close()
        path = self.path / 'account.jsonl'
        with path.open('ab') as f: f.write(b'{"torn":')
        before = path.read_bytes()
        with self.assertRaises(ValueError): self.session()
        self.assertEqual(path.read_bytes(), before)

    def test_historical_and_changed_contract_inputs_never_admit(self):
        for n, changes in enumerate(({'mode':'historical'}, {'expected_contract_version':'changed'})):
            s = self.session(Path(self.tmp.name) / str(n))
            self.assertFalse(self.propose(s, **changes)['intent_admitted'])

    def test_unsafe_directory_and_invalid_intents_are_rejected(self):
        link = Path(self.tmp.name) / 'link'; link.symlink_to(self.path, target_is_directory=True)
        self.path.mkdir()
        with self.assertRaises(ValueError): self.session(link)
        for changes in ({'quantity_base':0}, {'reference_price':'NaN'}, {'error_calibrated':1}, {'round_trip_cost_quote':-1}):
            with self.assertRaises(ValueError): intent(**changes)


if __name__ == '__main__': unittest.main()
