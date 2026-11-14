"""Invented loss-at-size and restart cases, never market returns or fills."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from pathlib import Path
import tempfile
import unittest

from lab.paper_account import PaperEvent, CloseMark
from lab.paper_controls import RiskPolicy
from lab.paper_entry_risk import EntryLossPolicy, EntryScenario, assess_entry_loss
from lab.paper_session import EntryIntent, PaperSession
from lab.stream_quotes import FrameClock, NS


ANCHOR = FrameClock(1_790_000_000 * NS, 10 * NS)
BALANCES = {('fixture', 'USDT'): 1000}


def clock(n):
    return FrameClock(ANCHOR.utc_ns + n * NS, ANCHOR.mono_ns + n * NS)


def policy(**changes):
    values = dict(policy_id='invented-loss-policy',
        account_limits=(('fixture', 'USDT', 15),), required_scenarios=('gap',))
    return EntryLossPolicy(**{**values, **changes})


def intent(id='one', **changes):
    values = dict(intent_id=id, venue='fixture', asset='USDT', symbol='INVENTED',
        quantity_base=1, reference_price=100, expected_gross_quote=10,
        round_trip_cost_quote=1, error_bound_quote=1, error_calibrated=True)
    return EntryIntent(**{**values, **changes})


def scenario(**changes):
    values = dict(scenario_id='gap', venue='fixture', asset='USDT', symbol='INVENTED',
        quantity_base=1, entry_price=100, exit_price=90, entry_fee_quote='.1',
        exit_fee_quote='.1', funding_quote=0, extra_loss_quote=0)
    return EntryScenario(**{**values, **changes})


def receipt(id, n=1, kind='fill', **changes):
    values = dict(event_id=id, kind=kind, venue='fixture', asset='USDT', symbol='INVENTED',
        occurred_ns=clock(n).utc_ns, clock=clock(n), source_identity='invented supplied receipt')
    if kind == 'fill':
        values.update(quantity=1, price=100, fee=0)
    return PaperEvent(**{**values, **changes})


class EntryLossArithmeticTests(unittest.TestCase):
    def assess(self, s=None, i=None, p=None, **changes):
        return assess_entry_loss(i or intent(), [s or scenario()], p or policy(),
            dict(loss_stop_room_quote='30', drawdown_stop_room_quote='20',
                 current_solvency_room_quote='1000'), **changes)

    def test_long_short_and_full_wipeout_include_signed_funding_and_both_fees(self):
        long = self.assess(scenario(funding_quote=-2, extra_loss_quote=1))
        short = self.assess(scenario(quantity_base=-1, exit_price=110, funding_quote=-2,
                                    extra_loss_quote=1), intent(quantity_base=-1))
        self.assertEqual(D(long['worst_declared_loss_quote']), D('13.2'))
        self.assertEqual(long['worst_declared_loss_quote'], short['worst_declared_loss_quote'])
        self.assertTrue(long['model_size_within_loss_limits'])
        wipeout = self.assess(scenario(exit_price=0))
        self.assertEqual(D(wipeout['worst_declared_loss_quote']), D('100.2'))
        self.assertFalse(wipeout['model_size_within_loss_limits'])

    def test_fee_sensitivity_can_remove_size_admission(self):
        s = scenario(exit_price=88, entry_fee_quote='.75', exit_fee_quote='.75')
        cases = [self.assess(s, cost_multiple=k) for k in (1, 2, 3)]
        self.assertEqual([D(x['worst_declared_loss_quote']) for x in cases], [D('13.5'), D(15), D('16.5')])
        self.assertEqual([x['model_size_within_loss_limits'] for x in cases], [True, True, False])
        self.assertTrue(all(not x['actual_order_allowed'] and not x['activation_allowed'] for x in cases))

    def test_future_profit_does_not_finance_unknown_timing_of_cash_debits(self):
        r = self.assess(scenario(exit_price=200, funding_quote=-12, entry_fee_quote=4))
        self.assertGreater(D(r['scenarios'][0]['net_pnl_quote']), 0)
        self.assertEqual(D(r['worst_declared_loss_quote']), D('16.1'))
        self.assertFalse(r['model_size_within_loss_limits'])
        funding_offset = self.assess(scenario(exit_price=50, funding_quote=50))
        self.assertEqual(D(funding_offset['scenarios'][0]['net_pnl_quote']), D('-.2'))
        self.assertEqual(D(funding_offset['worst_declared_loss_quote']), D('50.2'))
        self.assertFalse(funding_offset['model_size_within_loss_limits'])

    def test_missing_scenario_or_any_unknown_money_never_becomes_zero(self):
        for field in ('entry_price', 'exit_price', 'entry_fee_quote', 'exit_fee_quote',
                      'funding_quote', 'extra_loss_quote'):
            r = self.assess(scenario(**{field: None}))
            self.assertFalse(r['model_size_within_loss_limits'], field)
            self.assertIsNone(r['worst_declared_loss_quote'])
        p = replace(policy(), required_scenarios=('gap', 'hedge_failure'))
        self.assertIn('required_loss_scenarios_incomplete_or_changed', self.assess(p=p)['reasons'])

    def test_wrong_currency_instrument_side_or_size_cannot_borrow_other_scenario(self):
        for changes in ({'asset': 'USDC'}, {'venue': 'other'}, {'symbol': 'OTHER'},
                        {'quantity_base': -1}, {'quantity_base': '.1'}):
            r = self.assess(scenario(**changes))
            self.assertIn('scenario_instrument_asset_side_or_size_mismatch', r['reasons'])
            self.assertFalse(r['model_size_within_loss_limits'])

    def test_duplicates_invalid_amounts_and_low_precision_do_not_weaken_limits(self):
        with self.assertRaises(ValueError):
            assess_entry_loss(intent(), [scenario(), scenario()], policy(), None)
        for field in ('entry_price', 'exit_fee_quote', 'funding_quote', 'quantity_base'):
            for value in (True, 'NaN', 'Infinity'):
                with self.assertRaises(ValueError): scenario(**{field: value})
        for value in (-1, 0):
            with self.assertRaises(ValueError): EntryLossPolicy('bad', (('fixture', 'USDT', value),), ('gap',))
        with localcontext() as context:
            context.prec = 3
            r = self.assess(scenario(exit_price='85.19999999999999999999'))
        self.assertEqual(D(r['worst_declared_loss_quote']), D('15.00000000000000000001'))
        self.assertFalse(r['model_size_within_loss_limits'])


class SizedSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'session'

    def session(self, p=None, **kwargs):
        s = PaperSession(self.path, BALANCES, ANCHOR, RiskPolicy('invented-policy'),
                         contract_version='one', entry_loss_policy=p or policy(), **kwargs)
        self.addCleanup(s.close)
        return s

    def propose(self, s, i=None, scenarios=None, n=1, **changes):
        values = dict(asof=clock(n).mono_ns, clock=clock(n), complete=True, session_open=True,
            fee_inputs_known=True, expected_contract_version='one', mode='fixture',
            loss_scenarios=[scenario()] if scenarios is None else scenarios)
        return s.propose_entry(i or intent(), **{**values, **changes})

    def test_capital_and_gross_pass_but_loss_at_size_blocks_large_bet(self):
        s = self.session()
        r = self.propose(s, intent(quantity_base='2.5'),
                         [scenario(quantity_base='2.5', exit_price=50)])
        self.assertTrue(r['risk']['model_new_entries_allowed'])
        self.assertNotIn('proposed_symbol_gross_limit', r['reasons'])
        self.assertFalse(r['intent_admitted'])
        self.assertEqual(D(r['loss_assessment']['worst_declared_loss_quote']), D('125.2'))
        self.assertEqual(s.account.accepted_events, [])
        self.assertTrue(self.propose(s, intent('smaller'), [scenario()])['intent_admitted'])

    def test_missing_scenarios_block_and_restart_cannot_remove_or_relax_policy(self):
        s = self.session()
        self.assertFalse(self.propose(s, scenarios=[])['intent_admitted'])
        s.close()
        for p in (None, replace(policy(), account_limits=(('fixture', 'USDT', 100),)),
                  replace(policy(), required_scenarios=('easier',))):
            with self.assertRaises(ValueError):
                PaperSession(self.path, BALANCES, ANCHOR, RiskPolicy('invented-policy'),
                             contract_version='one', entry_loss_policy=p)
        s = self.session()
        self.assertTrue(self.propose(s, intent('valid'))['intent_admitted'])

    def test_loss_policy_cannot_be_attached_after_activity(self):
        s = PaperSession(self.path, BALANCES, ANCHOR, RiskPolicy('invented-policy'), contract_version='one')
        self.addCleanup(s.close)
        self.propose(s, scenarios=[])
        s.close()
        with self.assertRaises(ValueError): self.session()

    def test_remaining_drawdown_headroom_survives_restart_and_deposit(self):
        s = self.session()
        # Build a10 gain high-water then give back15. Neither native stop fires.
        s.record_receipt(receipt('open'), clock(1).mono_ns)
        s.record_receipt(receipt('profit', 2, quantity=-1, price=110), clock(2).mono_ns)
        self.assertTrue(self.propose(s, intent('observe-peak'), scenarios=[], n=2)['risk']['model_new_entries_allowed'])
        s.record_receipt(receipt('open-again', 3), clock(3).mono_ns)
        s.record_receipt(receipt('loss', 4, quantity=-1, price=85), clock(4).mono_ns)
        s.record_receipt(receipt('deposit', 4, kind='capital_change', amount=1000), clock(4).mono_ns)
        s.close(); s = self.session()
        r = self.propose(s, intent('after-loss'), n=4)
        self.assertTrue(r['risk']['model_new_entries_allowed'])
        h = r['loss_assessment']['native_headroom']
        self.assertEqual(D(h['drawdown_stop_room_quote']), D(5))
        self.assertEqual(D(h['loss_stop_room_quote']), D(25))
        self.assertIn('proposed_drawdown_stop_reached', r['loss_assessment']['reasons'])
        self.assertFalse(r['intent_admitted'])
        # Hitting the native stop exactly is also blocked; no fictitious buffer.
        r = self.propose(s, intent('at-limit'), [scenario(exit_price='95.2')], n=4)
        self.assertFalse(r['intent_admitted'])

    def test_scenario_entry_prices_also_bound_proposed_notional(self):
        s = self.session()
        r = self.propose(s, intent(quantity_base='2.5'),
                         [scenario(quantity_base='2.5', entry_price=101, exit_price=100)])
        self.assertIn('proposed_symbol_gross_limit', r['reasons'])
        self.assertFalse(r['intent_admitted'])

    def test_withdrawal_cannot_leave_scenario_losses_above_current_cash(self):
        s = self.session()
        s.record_receipt(receipt('withdraw', kind='capital_change', amount=-995), clock(1).mono_ns)
        r = self.propose(s, intent(quantity_base='-.02'), [scenario(quantity_base='-.02',
            exit_price=600, entry_fee_quote=0, exit_fee_quote=0)])
        self.assertTrue(r['risk']['model_new_entries_allowed'])
        self.assertEqual(D(r['loss_assessment']['worst_declared_loss_quote']), D(10))
        self.assertIn('proposed_current_capital_exhausted', r['loss_assessment']['reasons'])
        self.assertFalse(r['intent_admitted'])

    def test_declared_scenario_fees_are_reserved_without_future_profit_offsets(self):
        # Even a generous loss policy cannot fund the fee from an unrealized gain.
        s = PaperSession(self.path, BALANCES, ANCHOR,
            RiskPolicy('generous', max_loss_fraction='.5', max_drawdown_fraction='.5',
                       max_symbol_gross_fraction=1), contract_version='one',
            entry_loss_policy=policy(account_limits=(('fixture', 'USDT', 100),)))
        self.addCleanup(s.close)
        r = self.propose(s, intent(quantity_base='9.9'), [scenario(quantity_base='9.9',
            exit_price=102, entry_fee_quote=20, exit_fee_quote=0)])
        self.assertTrue(r['loss_assessment']['model_size_within_loss_limits'])
        self.assertFalse(r['intent_admitted'])
        self.assertEqual(D(r['risk']['capital']['accounts'][0]['required_reserve']), D(1010))

    def test_partial_fill_fees_and_later_fee_resolutions_keep_the_full_size_budget(self):
        for resolve in (False, True):
            with self.subTest(resolve=resolve):
                self.path = Path(self.tmp.name) / str(resolve)
                s = self.session()
                self.assertTrue(self.propose(s)['intent_admitted'])
                r = s.record_receipt(receipt('part-one', quantity='.5', fee='.08'),
                                     clock(1).mono_ns, intent_id='one')
                # A fixed fee need not be proportional to the partial quantity.
                self.assertFalse(r['issues'])  # full-size declared allowance is0.1
                self.assertEqual(s.account.positions[('fixture', 'USDT', 'INVENTED')][0], D('.5'))
                s.record_receipt(receipt('part-two', 2, quantity='.5', fee=None if resolve else '.1'),
                                 clock(2).mono_ns, intent_id='one')
                if resolve:
                    s.record_receipt(receipt('resolved', 3, kind='fee_resolution', amount='.1', resolves='part-two'),
                                     clock(3).mono_ns)
                s.close(); s = self.session()
                state = s.status(clock(3).mono_ns)
                self.assertIn('one:entry_fees_exceed_declared_budget', state['issues'])
                self.assertEqual(D(state['snapshot']['accounts'][0]['cash']), D('999.82'))

    def test_policy_cannot_be_omitted_by_mutating_session_configuration(self):
        s = self.session()
        s.entry_loss_policy = None
        with self.assertRaises(ValueError): self.propose(s, scenarios=[])

    def test_other_positions_need_portfolio_stress_and_unexpected_fills_are_retained(self):
        s = self.session()
        s.record_receipt(receipt('other', symbol='OTHER'), clock(1).mono_ns)
        quote = CloseMark('fixture', 'USDT', 'OTHER', 1, 100, 0, clock(2), clock(2).utc_ns, 'invented')
        r = self.propose(s, marks=[quote], n=2)
        self.assertIn('loss_at_size_requires_flat_account_without_portfolio_stress', r['reasons'])
        s.record_receipt(receipt('other-close', 2, symbol='OTHER', quantity=-1), clock(2).mono_ns)
        self.assertTrue(self.propose(s, intent('fresh'), n=3)['intent_admitted'])
        r = s.record_receipt(receipt('outside-price', 3, price=101), clock(3).mono_ns, intent_id='fresh')
        self.assertEqual(r['financial_receipt']['status'], 'applied')
        self.assertTrue(r['issues'])
        self.assertEqual(s.account.positions[('fixture', 'USDT', 'INVENTED')][0], D(1))
        s.close(); s = self.session()
        self.assertTrue(s.status(clock(3).mono_ns)['issues'])


if __name__ == '__main__': unittest.main()
