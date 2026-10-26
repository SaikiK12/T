from dataclasses import replace
from decimal import Decimal as D
import unittest

from lab.funding_prefix import (PrefixPosition, PrefixObservation, assess,
    before_resize, margin_component, paper_event)
from lab.paper_account import PaperAccount
from lab.stream_quotes import FrameClock, NS


ANCHOR = FrameClock(1_800_000_000 * NS, 100 * NS)


def clock(seconds=0):
    return FrameClock(ANCHOR.utc_ns + seconds * NS, ANCHOR.mono_ns + seconds * NS)


def position(**kwargs):
    data = dict(account_id='fixture-account', market_id=7, strategy_index=0,
                margin_mode='cross', size_units=1_000_000, last_prefix=0,
                quote_multiplier=100, parameter_epoch='fixture-epoch', initialized=True,
                last_update_ns=ANCHOR.utc_ns, clock=ANCHOR)
    return PrefixPosition(**{**data, **kwargs})


def observation(**kwargs):
    data = dict(event_id='fixture-event', market_id=7, strategy_index=0,
                prefix=1000, quote_multiplier=100, parameter_epoch='fixture-epoch',
                occurred_ns=clock(1).utc_ns, clock=clock(1), source_identity='invented-input',
                input_scope='invented_encoded_fixture')
    return PrefixObservation(**{**data, **kwargs})


def result(p=None, o=None):
    return assess(p or position(), o or observation(), clock(3).mono_ns, ANCHOR)


class FundingPrefixTests(unittest.TestCase):
    def test_signed_encoded_money_and_no_second_index_or_rate(self):
        self.assertEqual(result()['collateral_delta'], -100_000_000_000)
        self.assertEqual(D(result()['conditional_collateral_usdc']), D('-.1'))
        self.assertEqual(D(result(position(size_units=-1_000_000))['conditional_collateral_usdc']), D('.1'))
        self.assertEqual(D(result(o=observation(prefix=-1000))['conditional_collateral_usdc']), D('.1'))
        self.assertIsNone(result()['cash_delta'])
        self.assertFalse(result()['settled_cash_verified'])

    def test_old_inventory_accrues_before_increase_flip_or_close(self):
        p = position()
        for delta, expected_new in ((1_000_000, 2_000_000), (-2_000_000, -1_000_000), (-1_000_000, 0)):
            transition = before_resize(p, observation(), delta, clock(3).mono_ns, ANCHOR)
            self.assertEqual(transition['assessment']['collateral_delta'], -100_000_000_000)
            next_p = transition['next_position']
            self.assertEqual(next_p.size_units, expected_new)
            self.assertEqual(next_p.last_prefix, 1000)
            later = observation(event_id='second', prefix=2000, occurred_ns=clock(2).utc_ns, clock=clock(2))
            self.assertEqual(result(next_p, later)['collateral_delta'], -expected_new * 100_000)
            self.assertFalse(transition['trade_cashflows_modeled'])

    def test_flat_disabled_and_nonadvancing_transition_are_distinct(self):
        self.assertEqual(result(position(size_units=0))['collateral_delta'], 0)
        x = before_resize(position(), observation(), 1, clock(3).mono_ns, ANCHOR, enabled=False)
        self.assertEqual(x['next_position'], position())
        self.assertIsNone(x['assessment'])
        x = before_resize(position(last_update_ns=clock(1).utc_ns, clock=clock(1)),
                          observation(), 1, clock(3).mono_ns, ANCHOR)
        self.assertEqual(x['state'], 'UNKNOWN')
        self.assertIsNone(x['next_position'])

    def test_missing_epochs_mismatches_and_causal_clocks_withhold_values(self):
        for o in (None, observation(prefix=None), observation(market_id=8), observation(strategy_index=1),
                  observation(quote_multiplier=10), observation(parameter_epoch='changed'),
                  observation(clock=clock(4)), observation(clock=FrameClock(clock(1).utc_ns + NS, clock(1).mono_ns))):
            x = assess(position(), o, clock(3).mono_ns, ANCHOR)
            self.assertIsNone(x['collateral_delta'])
        for p in (position(initialized=False), position(clock=clock(4)),
                  position(last_update_ns=clock(2).utc_ns, clock=clock(2))):
            self.assertIsNone(result(p)['collateral_delta'])

    def test_integer_domain_and_product_overflow_fail_closed(self):
        for kwargs in ({'size_units':True}, {'size_units':2**56}, {'last_prefix':2**62},
                       {'quote_multiplier':10001}, {'strategy_index':8}, {'market_id':255},
                       {'market_id':2**40}, {'source_tree':'unreviewed'}):
            with self.assertRaises(ValueError):
                position(**kwargs)
        p = position(size_units=2**56-1, last_prefix=2**62-1, quote_multiplier=10000)
        self.assertIsNone(result(p, observation(prefix=-(2**62-1), quote_multiplier=10000))['collateral_delta'])

    def test_provider_alias_cannot_post_same_start_twice(self):
        p, o = position(), observation()
        account = PaperAccount({p.bucket():5000}, ANCHOR)
        a = paper_event(p, o, result(p, o), clock(3).mono_ns, ANCHOR)
        alias = replace(o, event_id='different-provider-label', source_identity='second-receipt')
        b = paper_event(p, alias, result(p, alias), clock(3).mono_ns, ANCHOR)
        self.assertEqual(a.event_id, b.event_id)
        self.assertEqual(account.post(a, clock(3).mono_ns)['status'], 'applied')
        self.assertEqual(account.post(b, clock(3).mono_ns)['status'], 'duplicate')
        self.assertEqual(account.funding[p.bucket()], D('-.1'))

    def test_overlapping_interval_or_revised_size_requires_reconciliation(self):
        for revised_p, revised_o in ((position(), observation(prefix=2000)),
                                     (position(size_units=2_000_000), observation()),
                                     (position(margin_mode='isolated'), observation())):
            p, o = position(), observation()
            account = PaperAccount({p.bucket():2500, position(margin_mode='isolated').bucket():2500}, ANCHOR)
            a = paper_event(p, o, result(p, o), clock(3).mono_ns, ANCHOR)
            b = paper_event(revised_p, revised_o, result(revised_p, revised_o), clock(3).mono_ns, ANCHOR)
            self.assertEqual(a.event_id, b.event_id)
            account.post(a, clock(3).mono_ns)
            self.assertEqual(account.post(b, clock(3).mono_ns)['status'], 'conflicting_revision')
            self.assertEqual(account.funding[p.bucket()], D('-.1'))

    def test_distinct_initialized_start_and_margin_buckets_keep_separate_cash(self):
        p, o = position(), observation()
        next_p = before_resize(p, o, 0, clock(3).mono_ns, ANCHOR)['next_position']
        later = observation(event_id='later', prefix=2000, occurred_ns=clock(2).utc_ns, clock=clock(2))
        a = paper_event(p, o, result(p, o), clock(3).mono_ns, ANCHOR)
        b = paper_event(next_p, later, result(next_p, later), clock(3).mono_ns, ANCHOR)
        self.assertNotEqual(a.event_id, b.event_id)
        self.assertNotEqual(p.bucket(), position(margin_mode='isolated').bucket())
        self.assertNotEqual(p.bucket(), position(strategy_index=1).bucket())

    def test_unverified_encoded_observation_remains_pending_in_existing_account(self):
        p, o = position(), observation(input_scope='unverified_encoded_observation')
        assessment = result(p, o)
        self.assertEqual(D(assessment['conditional_collateral_usdc']), D('-.1'))
        event = paper_event(p, o, assessment, clock(3).mono_ns, ANCHOR)
        self.assertIsNone(event.amount)
        account = PaperAccount({p.bucket():5000}, ANCHOR)
        account.post(event, clock(3).mono_ns)
        self.assertIn(event.event_id, account.pending)
        self.assertEqual(account.funding[p.bucket()], 0)  # Known component only; total remains unknown.
        with self.assertRaises(ValueError):
            paper_event(p, o, {**assessment, 'conditional_collateral_usdc':'1'}, clock(3).mono_ns, ANCHOR)

    def test_rounded_component_depends_on_old_remainder_and_is_not_second_cash(self):
        self.assertEqual(margin_component(1_000_000, -1)['component_delta_micro_usdc'], -1)
        self.assertEqual(margin_component(1_000_001, -1)['component_delta_micro_usdc'], 0)
        self.assertEqual(D(margin_component(1_000_001, -1)['conditional_collateral_usdc']), D('-1e-12'))
        self.assertFalse(margin_component(1_000_001, -1)['wallet_credit_verified'])


if __name__ == '__main__':
    unittest.main()
