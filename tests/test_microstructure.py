"""Synthetic identities and stream failures; no strategy, market data or fills."""

from dataclasses import FrozenInstanceError, replace
import math
import unittest

from lab.microstructure import (BestQuote, DepthLevel, DepthSnapshot, RollingOFI,
                                bbo_ofi, depth_imbalance, weighted_mid)


def quote(sequence=0, receive=0, exchange=None, bid=99, bid_size=10, ask=101, ask_size=20, symbol="X_USDT"):
    return BestQuote(symbol, receive if exchange is None else exchange, receive, sequence,
                     bid, bid_size, ask, ask_size)


def snapshot(bids=((99, 10), (98, 30)), asks=((101, 20), (102, 10))):
    return DepthSnapshot("X_USDT", 1_000_000, 7, tuple(DepthLevel(*x) for x in bids),
                         tuple(DepthLevel(*x) for x in asks))


def window():
    return RollingOFI("X_USDT", window_ns=10, max_exchange_gap_ns=10, max_receive_gap_ns=10)


def update(stream, observation):
    return stream.update(observation, now_receive_time_ns=observation.receive_time_ns)


class ObservationTests(unittest.TestCase):
    def test_both_quotes_and_depth_are_immutable(self):
        q, depth = quote(), snapshot()
        with self.assertRaises(FrozenInstanceError):
            q.bid_price = 90
        with self.assertRaises(FrozenInstanceError):
            depth.bids[0].size = 1
        supplied = [DepthLevel(99, 3)]
        copied = DepthSnapshot("X_USDT", 1, 2, supplied, [DepthLevel(101, 4)])
        supplied.clear()
        self.assertEqual(len(copied.bids), 1)

    def test_positive_finite_numbers_only(self):
        for field in ("bid_price", "ask_price", "bid_size", "ask_size"):
            for value in (0, -1, math.inf, -math.inf, math.nan, True, "10", 10**400):
                with self.subTest(field=field, value=repr(value)):
                    with self.assertRaises(ValueError):
                        replace(quote(), **{field: value})
        for value in (0, -1, math.inf, math.nan, True, "10"):
            with self.subTest(depth_size=value):
                with self.assertRaises(ValueError):
                    DepthLevel(1, value)

    def test_locked_crossed_and_invalid_identity(self):
        for bid, ask in ((101, 101), (102, 101)):
            with self.assertRaises(ValueError):
                quote(bid=bid, ask=ask)
        for symbol in ("", "X USDT", None, 1):
            with self.assertRaises(ValueError):
                quote(symbol=symbol)
        for field in ("sequence", "exchange_time_ns", "receive_time_ns"):
            for value in (-1, 1.5, True, "1"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        replace(quote(), **{field: value})

    def test_snapshot_requires_ordered_unique_uncrossed_validated_levels(self):
        cases = [(((99, 1), (100, 2)), ((101, 1),)),
                 (((99, 1), (99, 2)), ((101, 1),)),
                 (((99, 1),), ((102, 1), (101, 1))),
                 (((99, 1),), ((101, 1), (101, 2))),
                 (((101, 1),), ((101, 1),)),
                 ((), ((101, 1),)), (((99, 1),), ())]
        for bids, asks in cases:
            with self.subTest(bids=bids, asks=asks):
                with self.assertRaises(ValueError):
                    snapshot(bids, asks)
        with self.assertRaises(ValueError):
            DepthSnapshot("X_USDT", 0, 0, ((99, 10),), (DepthLevel(101, 10),))


class OFIIdentityTests(unittest.TestCase):
    def test_price_moves_use_new_or_old_depth_not_size_change(self):
        # Expected bid effects: worsening removes old 10, same adds 3, improving adds new 13.
        # Expected ask effects: improving removes new 17, same cancels 3, worsening removes old 20.
        for bid, bid_effect in ((98, -10), (99, 3), (100, 13)):
            for ask, ask_effect in ((100.5, -17), (101, 3), (102, 20)):
                with self.subTest(bid=bid, ask=ask):
                    got = bbo_ofi(quote(), quote(1, 1, bid=bid, bid_size=13, ask=ask, ask_size=17))
                    self.assertEqual(got, bid_effect + ask_effect)

    def test_bid_add_cancel_and_ask_add_cancel_have_opposite_signs(self):
        changes = [("bid_size", 17, 7), ("bid_size", 3, -7),
                   ("ask_size", 27, -7), ("ask_size", 13, 7)]
        for field, size, expected in changes:
            with self.subTest(field=field, size=size):
                self.assertEqual(bbo_ofi(quote(), replace(quote(1, 1), **{field: size})), expected)

    def test_unchanged_price_path_telescopes_even_when_orders_cancel(self):
        observations = [quote(i, i, bid_size=b, ask_size=a) for i, (b, a) in
                        enumerate(((10, 20), (17, 20), (17, 24), (12, 24), (12, 11)))]
        contributions = [bbo_ofi(a, b) for a, b in zip(observations, observations[1:])]
        self.assertEqual(contributions, [7, -4, -5, 13])
        self.assertEqual(sum(contributions), (12 - 10) - (11 - 20))

    def test_side_reflection_negates_ofi_and_depth_imbalance(self):
        def reflect(q):
            return replace(q, bid_price=200 - q.ask_price, bid_size=q.ask_size,
                           ask_price=200 - q.bid_price, ask_size=q.bid_size)
        for current in (quote(1, 1, bid=100, bid_size=7, ask=102, ask_size=3),
                        quote(1, 1, bid=98, bid_size=2, ask=100, ask_size=35),
                        quote(1, 1, bid_size=17, ask_size=4)):
            self.assertEqual(bbo_ofi(reflect(quote()), reflect(current)), -bbo_ofi(quote(), current))
        original = snapshot()
        reflected = snapshot(tuple((200 - x.price, x.size) for x in original.asks),
                             tuple((200 - x.price, x.size) for x in original.bids))
        self.assertEqual(depth_imbalance(reflected, 2), -depth_imbalance(original, 2))

    def test_scale_invariance_of_normalized_features_and_ofi_units(self):
        old, new = quote(), quote(1, 1, bid=100, bid_size=13, ask_size=17)
        for scale in (0.001, 7, 1e100):
            scaled = [replace(q, bid_size=q.bid_size * scale, ask_size=q.ask_size * scale) for q in (old, new)]
            self.assertAlmostEqual(bbo_ofi(*scaled) / scale, bbo_ofi(old, new))
            self.assertAlmostEqual(weighted_mid(scaled[1]), weighted_mid(new))
            scaled_depth = snapshot(((99, 10 * scale), (98, 30 * scale)),
                                    ((101, 20 * scale), (102, 10 * scale)))
            self.assertAlmostEqual(depth_imbalance(scaled_depth, 2), depth_imbalance(snapshot(), 2))
        self.assertEqual(bbo_ofi(replace(old, bid_price=990, ask_price=1010),
                                 replace(new, bid_price=1000, ask_price=1010)), bbo_ofi(old, new))

    def test_contribution_rejects_unproven_continuity_or_clock_regression(self):
        old = quote(10, 20, exchange=1000)
        for new in (quote(12, 21, exchange=1001), quote(None, 21, exchange=1001),
                    quote(11, 19, exchange=1001), quote(11, 21, exchange=999),
                    quote(11, 21, exchange=1001, symbol="Y_USDT")):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    bbo_ofi(old, new)

    def test_weighted_mid_opposite_price_weighting_and_bounds(self):
        self.assertEqual(weighted_mid(quote(bid_size=10, ask_size=10)), 100)
        self.assertEqual(weighted_mid(quote(bid_size=30, ask_size=10)), 100.5)
        self.assertEqual(weighted_mid(quote(bid_size=10, ask_size=30)), 99.5)
        for bid_size, ask_size in ((1e308, 1e308), (1e-300, 1e308), (1e308, 1e-300)):
            q = quote(bid=1e308, ask=1.7e308, bid_size=bid_size, ask_size=ask_size)
            self.assertTrue(q.bid_price <= weighted_mid(q) <= q.ask_price)
            self.assertTrue(math.isfinite(weighted_mid(q)))

    def test_depth_uses_exact_l_quantity_levels_and_handles_huge_sizes(self):
        self.assertAlmostEqual(depth_imbalance(snapshot(), 1), -1 / 3)
        self.assertAlmostEqual(depth_imbalance(snapshot(), 2), 1 / 7)
        huge = snapshot(((99, 1e308), (98, 1e308)), ((101, 1e308), (102, 1e308)))
        self.assertEqual(depth_imbalance(huge, 2), 0)
        for levels in (0, -1, True, 1.5, 3):
            with self.assertRaises(ValueError):
                depth_imbalance(snapshot(), levels)


class RollingOFITests(unittest.TestCase):
    def test_open_left_closed_right_window_and_full_observed_warmup(self):
        stream = window()
        self.assertFalse(update(stream, quote()).ready)
        # Contributions +1, +4, -3; a full ten ns of observed coverage is required.
        self.assertFalse(update(stream, quote(1, 5, bid_size=11)).ready)
        self.assertFalse(update(stream, quote(2, 9, bid_size=15)).ready)
        result = update(stream, quote(3, 10, bid_size=12))
        self.assertEqual((result.value, result.contribution, result.event_count), (2, -3, 3))
        self.assertEqual(result.status, "ready")
        result = stream.at(now_receive_time_ns=15)
        self.assertEqual((result.value, result.window_start_receive_time_ns, result.event_count), (1, 5, 2))
        self.assertEqual(stream.at(now_receive_time_ns=19).value, -3)
        self.assertEqual(stream.at(now_receive_time_ns=20).value, 0)

    def test_clock_alone_does_not_manufacture_observed_warmup(self):
        stream = RollingOFI("X_USDT", window_ns=10, max_receive_gap_ns=20, max_exchange_gap_ns=20)
        update(stream, quote())
        self.assertFalse(stream.at(now_receive_time_ns=10).ready)
        self.assertTrue(update(stream, quote(1, 11)).ready)

    def test_exchange_clock_epoch_and_equal_timestamps_do_not_change_receive_window(self):
        stream = window()
        update(stream, quote(0, 0, exchange=1_700_000_000_000_000_000))
        update(stream, quote(1, 0, exchange=1_700_000_000_000_000_000, bid_size=13))
        result = update(stream, quote(2, 10, exchange=1_700_000_000_000_000_005, ask_size=18))
        self.assertEqual(result.value, -1)  # t=0 contribution excluded; latest (-3 bid +2 ask) remains.
        self.assertEqual(result.event_count, 1)

    def test_duplicates_do_not_add_flow_or_refresh_freshness(self):
        stream = window()
        update(stream, quote())
        update(stream, quote(1, 10, bid_size=15))
        duplicate = quote(1, 11, exchange=10, bid_size=15)
        result = update(stream, duplicate)
        self.assertEqual((result.status, result.value, result.contribution, result.event_count),
                         ("duplicate", 5, None, 1))
        # Repeated re-receipts cannot keep an old book alive.
        result = update(stream, replace(duplicate, receive_time_ns=21))
        self.assertEqual((result.status, result.value), ("stale", None))
        self.assertFalse(update(stream, quote(2, 22)).ready)

    def test_conflicting_latest_event_invalidates_and_requires_new_warmup(self):
        stream = window()
        update(stream, quote())
        update(stream, quote(1, 10, bid_size=15))
        conflict = update(stream, quote(1, 11, exchange=10, bid_size=16))
        self.assertEqual((conflict.status, conflict.value, conflict.event_count), ("conflict", None, 0))
        self.assertFalse(update(stream, quote(2, 12)).ready)
        self.assertTrue(update(stream, quote(3, 22, bid_size=13)).ready)

    def test_sequence_and_each_clock_gap_restart_from_new_baseline(self):
        for new in (quote(4, 11, exchange=11), quote(2, 11, exchange=21), quote(2, 21, exchange=11)):
            with self.subTest(new=new):
                stream = window()
                update(stream, quote())
                self.assertTrue(update(stream, quote(1, 10)).ready)
                result = update(stream, new)
                self.assertEqual((result.status, result.value, result.contribution), ("gap", None, None))
                following = replace(new, sequence=new.sequence + 1, receive_time_ns=new.receive_time_ns + 10,
                                    exchange_time_ns=new.exchange_time_ns + 10, bid_size=13)
                self.assertEqual(update(stream, following).value, 3)

    def test_unknown_sequence_cannot_be_a_baseline(self):
        stream = window()
        update(stream, quote())
        update(stream, quote(1, 10))
        unknown = update(stream, quote(None, 11))
        self.assertEqual((unknown.status, unknown.value), ("unknown_sequence", None))
        self.assertFalse(update(stream, quote(100, 20)).ready)
        self.assertEqual(update(stream, quote(101, 30, ask_size=17)).value, 3)

    def test_regressions_and_older_duplicates_invalidate_without_rebasing(self):
        for bad in (quote(0, 11), quote(2, 11, exchange=9), quote(2, 9, exchange=11)):
            with self.subTest(bad=bad):
                stream = window()
                update(stream, quote())
                update(stream, quote(1, 10))
                result = stream.update(bad, now_receive_time_ns=11)
                self.assertEqual((result.status, result.value), ("out_of_order", None))
                self.assertFalse(update(stream, quote(3, 12)).ready)

    def test_polling_cannot_be_retroactively_backfilled(self):
        stream = window()
        update(stream, quote())
        stream.at(now_receive_time_ns=5)
        result = stream.update(quote(1, 4), now_receive_time_ns=5)
        self.assertEqual((result.status, result.value), ("out_of_order", None))
        self.assertFalse(update(stream, quote(2, 10)).ready)

    def test_future_symbol_and_backward_query_rejections_do_not_mutate(self):
        stream = window()
        update(stream, quote())
        for q, now in ((quote(1, 11), 10), (quote(1, 10, symbol="Y_USDT"), 10)):
            with self.assertRaises(ValueError):
                stream.update(q, now_receive_time_ns=now)
        self.assertEqual(update(stream, quote(1, 10, bid_size=15)).value, 5)
        for method in (stream.at, stream.reset):
            with self.assertRaises(ValueError):
                method(now_receive_time_ns=9)
        self.assertEqual(stream.at(now_receive_time_ns=10).value, 5)

    def test_staleness_and_explicit_reset_never_carry_old_ofi(self):
        stream = window()
        update(stream, quote())
        update(stream, quote(1, 10, bid_size=15))
        result = stream.at(now_receive_time_ns=21)
        self.assertEqual((result.status, result.value, result.event_count), ("stale", None, 0))
        self.assertFalse(update(stream, quote(50, 22)).ready)
        self.assertEqual(update(stream, quote(51, 32, bid_size=14)).value, 4)
        result = stream.reset(now_receive_time_ns=32)
        self.assertEqual((result.status, result.value, result.event_count), ("reset", None, 0))
        self.assertFalse(update(stream, quote(0, 32)).ready)
        self.assertEqual(update(stream, quote(1, 42, bid_size=12)).value, 2)

    def test_ofi_overflow_invalidates_instead_of_carrying_a_previous_feature(self):
        stream = window()
        update(stream, quote(bid_size=1e308, ask_size=1e308))
        with self.assertRaises(ValueError):
            update(stream, quote(1, 10, bid=100, ask=102, bid_size=1e308, ask_size=1e308))
        self.assertFalse(stream.at(now_receive_time_ns=10).ready)
        self.assertFalse(update(stream, quote(2, 11)).ready)

    def test_rolling_sum_overflow_also_invalidates_when_each_contribution_is_finite(self):
        stream = window()
        update(stream, quote(bid_size=1e308))
        self.assertEqual(update(stream, quote(1, 5, bid=100, bid_size=1e308)).contribution, 1e308)
        with self.assertRaises(ValueError):
            update(stream, quote(2, 10, bid=100.5, bid_size=1e308))
        self.assertFalse(stream.at(now_receive_time_ns=10).ready)

    def test_newly_supplied_but_already_stale_observation_is_not_a_baseline(self):
        stream = window()
        result = stream.update(quote(), now_receive_time_ns=11)
        self.assertEqual((result.status, result.value), ("stale", None))
        self.assertFalse(update(stream, quote(1, 12)).ready)
        self.assertEqual(update(stream, quote(2, 22, bid_size=13)).value, 3)

    def test_sequence_count_at_one_timestamp_does_not_complete_warmup(self):
        stream = window()
        for sequence in range(30):
            self.assertFalse(update(stream, quote(sequence, 0, bid_size=sequence + 1)).ready)

    def test_exchange_and_sequence_rewinds_require_reset_even_after_invalidation(self):
        for invalidation in ("unknown", "stale", "conflict"):
            with self.subTest(invalidation=invalidation):
                stream = window()
                update(stream, quote(10, 0, exchange=100))
                if invalidation == "unknown":
                    update(stream, quote(None, 1, exchange=101))
                elif invalidation == "stale":
                    stream.at(now_receive_time_ns=11)
                else:
                    update(stream, quote(10, 1, exchange=100, bid_size=13))
                # Both clocks/sequence must retain their trusted ordering across a cleared baseline.
                for bad in (quote(1, 12, exchange=102), quote(11, 13, exchange=10),
                            quote(2, 23, exchange=20)):
                    result = update(stream, bad)
                    self.assertEqual((result.status, result.value), ("out_of_order", None))
                stream.reset(now_receive_time_ns=23)
                self.assertFalse(update(stream, quote(0, 23, exchange=0)).ready)
                self.assertEqual(update(stream, quote(1, 33, exchange=10, bid_size=13)).value, 3)

    def test_old_duplicate_cannot_restart_warmup_after_staleness(self):
        stream = window()
        update(stream, quote())
        stream.at(now_receive_time_ns=11)
        result = update(stream, quote(0, 12, exchange=0))
        self.assertEqual((result.status, result.value), ("duplicate", None))
        self.assertFalse(update(stream, quote(1, 22, bid_size=13)).ready)
        self.assertEqual(update(stream, quote(2, 32, bid_size=15)).value, 2)

    def test_configuration_requires_explicit_positive_integer_bounds(self):
        for name in ("window_ns", "max_exchange_gap_ns", "max_receive_gap_ns"):
            for value in (0, -1, True, 1.5):
                config = {"window_ns": 10, "max_exchange_gap_ns": 10, "max_receive_gap_ns": 10}
                config[name] = value
                with self.assertRaises(ValueError):
                    RollingOFI("X_USDT", **config)


if __name__ == "__main__":
    unittest.main()
