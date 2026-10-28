from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from lab.settlement_account import EntryLeg, SettlementAccount, nominal_exit_inventory
from lab.paper_account import PaperAccount
from lab.funding_values import FundingContract, FundingEvent, ValuePacket
from lab.stream_quotes import FrameClock, NS, StreamBook
from lab.microstructure import DepthLevel, DepthSnapshot

UTC = 1_790_000_000 * NS
ANCHOR = FrameClock(UTC, 10 * NS)


def clock(s):
    return FrameClock(UTC + s * NS, ANCHOR.mono_ns + s * NS)


def book(venue, mid=100, size=100, second=30):
    c = clock(second)
    return StreamBook(venue, 'BTC', c, DepthSnapshot('BTC', c.utc_ns, c.mono_ns,
        (DepthLevel(mid - 1, size),), (DepthLevel(mid + 1, size),)), 1, 'invented full book')


def legs():
    return (EntryLeg('mexc', 'USDT', 'BTC', D(-10), D(99), D(100), D(3), clock(1), 'invented entry s'),
            EntryLeg('lighter', 'USDC', 'BTC', D(10), D(101), D(100), D(0), clock(1), 'invented entry h'))


class SettlementAccountTests(unittest.TestCase):
    def setup_account(self, capital=None, multiple=1, **kw):
        a = PaperAccount(capital or {('mexc', 'USDT'): 5000, ('lighter', 'USDC'): 5000}, ANCHOR, **kw)
        return a, SettlementAccount(a, multiple)

    def test_fixed_dollars_leave_inventory_or_reverse_it(self):
        self.assertEqual(D(nominal_exit_inventory(10, 200, 1000)['residual_quantity']), 5)
        x = nominal_exit_inventory(10, 50, 1000)
        self.assertEqual(D(x['residual_quantity']), -10)
        self.assertTrue(x['position_reversed'])
        self.assertTrue(nominal_exit_inventory(-10, 100, 1000)['flat'])

    def test_exact_quantity_exit_and_changed_exit_notional_fee(self):
        a, s = self.setup_account()
        self.assertEqual(s.enter_pair('a', legs(), clock(1).mono_ns)['state'], 'conditional_model')
        x = s.close_fixed('mexc', 'USDT', 'BTC', book('mexc', 200), 3, clock(30).mono_ns)
        self.assertEqual(D(x['quantity']), 10)
        self.assertEqual(D(x['fee']), D('.603'))
        self.assertEqual(a.positions[('mexc', 'USDT', 'BTC')][0], 0)
        s.close_fixed('lighter', 'USDC', 'BTC', book('lighter', 100), 0, clock(30).mono_ns)
        r = s.report(clock(30).mono_ns, fx={'USDT': 1, 'USDC': 1})
        self.assertEqual(D(r['combined_initial_capital']), 10000)
        self.assertEqual(D(r['combined_scenario_pnl']), D('-1040.9'))
        self.assertEqual(D(r['whole_capital_scenario_return']), D('-.10409'))
        self.assertIsNone(r['actual_expected_net'])

    def test_thin_missing_future_stale_and_mismatched_exits_retain_inventory(self):
        options = [None, book('mexc', size=1), book('mexc', second=31),
                   book('mexc', second=27), book('lighter')]
        for b in options:
            a, s = self.setup_account()
            s.enter_pair('a', legs(), clock(1).mono_ns)
            before = len(a.accepted_events)
            self.assertEqual(s.close_fixed('mexc', 'USDT', 'BTC', b, 3, clock(30).mono_ns)['state'], 'unknown')
            self.assertEqual(len(a.accepted_events), before)
            self.assertEqual(a.positions[('mexc', 'USDT', 'BTC')][0], -10)
            report = s.report(clock(30).mono_ns, fx={'USDT': 1, 'USDC': 1})
            self.assertIsNone(report['combined_scenario_pnl'])
            self.assertEqual(report['combined_initial_capital'], '10000')

    def test_separate_capital_preflight_is_atomic_and_cannot_borrow_other_venue(self):
        a, s = self.setup_account({('mexc', 'USDT'): 990, ('lighter', 'USDC'): 9010})
        x = s.enter_pair('a', legs(), clock(1).mono_ns)
        self.assertEqual(x['state'], 'blocked')
        self.assertFalse(a.accepted_events)
        self.assertEqual(a.cash[('lighter', 'USDC')], 9010)

    def test_duplicate_entry_does_not_spend_or_resize_and_other_hop_is_blocked(self):
        a, s = self.setup_account()
        s.enter_pair('a', legs(), clock(1).mono_ns)
        before = dict(a.cash)
        x = s.enter_pair('a', legs(), clock(2).mono_ns)
        self.assertTrue(all(e['status'] == 'duplicate' for e in x['events']))
        self.assertEqual(a.cash, before)
        self.assertEqual(s.enter_pair('b', legs(), clock(2).mono_ns)['state'], 'blocked')

    def test_entry_clock_before_baseline_or_future_cannot_apply_one_leg(self):
        for c in (FrameClock(UTC - NS, ANCHOR.mono_ns - NS), clock(3)):
            a, s = self.setup_account()
            bad = (replace(legs()[0], clock=c), legs()[1])
            self.assertEqual(s.enter_pair('a', bad, clock(2).mono_ns)['state'], 'blocked')
            self.assertFalse(a.accepted_events)

    def funding_inputs(self, venue='lighter'):
        asset = 'USDC' if venue == 'lighter' else 'USDT'
        c = FundingContract(venue, 'BTC', 'linear_base', asset, True, 'invented exact contract',
                            'BTC', asset, 15 * NS if venue == 'mexc' else 0)
        e = FundingEvent('evt', venue, 'BTC', UTC + 10 * NS, D('.01'), 'fraction', 'settled', clock(30))
        p = ValuePacket(venue, 'BTC', 'index' if venue == 'lighter' else 'fair', D(200),
            clock(30), UTC + 30 * NS, 'settlement_value', 'invented event value', UTC + 10 * NS, 'evt')
        return c, e, p

    def test_missing_index_is_pending_then_resolved_once_including_provider_alias(self):
        a, s = self.setup_account()
        s.enter_pair('a', legs(), clock(1).mono_ns)
        c, e, p = self.funding_inputs()
        first = s.funding(c, e, None, clock(30), index_basis='pre_update_event_index')
        self.assertIsNone(first['cash_delta'])
        self.assertEqual(len(a.pending), 1)
        known = s.funding(c, e, p, clock(30), index_basis='pre_update_event_index')
        self.assertEqual(D(known['cash_delta']), -20)
        self.assertFalse(a.pending)
        self.assertEqual(a.funding[('lighter', 'USDC')], -20)
        again = s.funding(c, replace(e, event_id='alias'), replace(p, settlement_event_id='alias'),
                         clock(30), index_basis='pre_update_event_index')
        self.assertEqual(again['posting']['status'], 'duplicate')
        self.assertEqual(a.funding[('lighter', 'USDC')], -20)

    def test_mexc_batch_exposure_change_at_nominal_plus_five_seconds_stays_unknown(self):
        a, s = self.setup_account()
        s.enter_pair('a', legs(), clock(1).mono_ns)
        s.close_fixed('mexc', 'USDT', 'BTC', book('mexc', second=15), 3, clock(15).mono_ns)
        c, e, p = self.funding_inputs('mexc')
        x = s.funding(c, e, p, clock(30))
        self.assertIsNone(x['cash_delta'])
        self.assertIn('position_inclusion_unverified_or_changed', x['reasons'])
        self.assertEqual(a.funding[('mexc', 'USDT')], 0)
        self.assertTrue(a.pending)

    def test_estimated_future_rate_never_posts_cash(self):
        a, s = self.setup_account()
        s.enter_pair('a', legs(), clock(1).mono_ns)
        c, e, _ = self.funding_inputs()
        x = s.funding(c, replace(e, stage='estimate', clock=clock(5)), None, clock(5))
        self.assertEqual(x['posting'], 'future_economic_event_not_posted')
        self.assertEqual(len(a.accepted_events), 2)

    def test_cost_tiers_keep_quantity_and_exit_fee_on_stressed_exit_notional(self):
        for k in (1, 2, 3):
            a, s = self.setup_account(multiple=k)
            s.enter_pair('a', legs(), clock(1).mono_ns)
            self.assertEqual(a.positions[('mexc', 'USDT', 'BTC')][0], -10)
            x = s.close_fixed('mexc', 'USDT', 'BTC', book('mexc', mid=200), 3, clock(30).mono_ns)
            self.assertEqual(D(x['price']), 200 + k)
            self.assertEqual(D(x['fee']), D(10) * (200 + k) * 3 * k / 10000)

    def test_restart_uses_native_inventory_and_no_fx_assumption_is_implicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'account.jsonl'
            a, s = self.setup_account(journal_path=path)
            s.enter_pair('a', legs(), clock(1).mono_ns)
            restored, replay = self.setup_account(journal_path=path)
            x = replay.close_fixed('mexc', 'USDT', 'BTC', book('mexc'), 3, clock(30).mono_ns)
            self.assertEqual(D(x['quantity']), 10)
            self.assertEqual(restored.positions[('mexc', 'USDT', 'BTC')][0], 0)
            self.assertIsNone(replay.report(clock(30).mono_ns)['combined_scenario_pnl'])

    def test_unknown_exit_fee_is_not_zero(self):
        a, s = self.setup_account()
        s.enter_pair('a', legs(), clock(1).mono_ns)
        x = s.close_fixed('mexc', 'USDT', 'BTC', book('mexc'), None, clock(30).mono_ns)
        self.assertEqual(x['reasons'], ['exit_fee_unknown'])
        self.assertEqual(a.positions[('mexc', 'USDT', 'BTC')][0], -10)


if __name__ == '__main__':
    unittest.main()
