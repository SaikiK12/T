"""Synthetic mark-price contracts only: no requests, files, or strategy outcomes."""
import dataclasses
from decimal import localcontext
import math
import unittest

from lab import markbars


HOUR = 3_600_000
DAY = 24 * HOUR
START = 2 * DAY
END = START + DAY
ERRORS = (TypeError, ValueError)


def mark(start, *, venue="binance_usdm", contract="BTCUSDT", close=112.0):
    return markbars.MarkBar(venue, contract, start, start + HOUR, 110.0, 120.0, 90.0, close)


def full_day():
    # The first open differs from the preceding close: it cannot substitute for the anchor.
    anchor = markbars.MarkBar("binance_usdm", "BTCUSDT", START - HOUR, START,
                             100.0, 101.0, 99.0, 100.0)
    return [anchor] + [mark(START + i * HOUR, close=113.0 if i == 23 else 112.0) for i in range(24)]


def summarize(bars, *, day_end_ms=END, interval_ms=HOUR, as_of_ms=END):
    return markbars.day_range(bars, day_end_ms=day_end_ms, interval_ms=interval_ms, as_of_ms=as_of_ms)


def binance_row(start=START):
    return [start, "110", "120", "90", "112", "0", start + HOUR - 1, "0", 0, "0", "0", "0"]


class MarkBarTest(unittest.TestCase):
    def test_mark_bar_is_immutable_and_accepts_all_normalized_venues(self):
        bar = mark(START)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            bar.close = 111.0
        self.assertEqual(mark(START, venue="gate_usdt", contract="mark_BTC_USDT").venue, "gate_usdt")
        self.assertEqual(mark(START, venue="mexc_usdt", contract="BTC_USDT").venue, "mexc_usdt")

    def test_invalid_clock_identity_and_price_types_fail(self):
        valid = dict(venue="binance_usdm", contract="BTCUSDT", start_ms=START, end_ms=START + HOUR,
                     open=110.0, high=120.0, low=90.0, close=112.0)
        changes = [
            {"venue": "unknown"}, {"venue": "mexc_usdt", "contract": "BTCUSDT"},
            {"contract": ""}, {"contract": None},
            {"start_ms": -1}, {"start_ms": START + 0.5}, {"start_ms": True},
            {"end_ms": START}, {"end_ms": START - 1}, {"end_ms": "later"},
            {"open": 0}, {"high": math.inf}, {"low": math.nan}, {"close": -1},
            {"open": 130.0}, {"close": 130.0}, {"low": 121.0}, {"high": 89.0},
            {"open": "not-a-price"}, {"low": True}, {"close": None},
        ]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ERRORS):
                markbars.MarkBar(**(valid | change))


class DecodeMarkBarsTest(unittest.TestCase):
    def test_binance_preserves_ohlc_and_uses_exclusive_close_clock(self):
        bars = markbars.decode_binance([binance_row()], symbol="BTCUSDT", interval_ms=HOUR)
        self.assertIsInstance(bars, tuple)
        self.assertEqual(len(bars), 1)
        bar = bars[0]
        self.assertEqual((bar.venue, bar.contract, bar.start_ms, bar.end_ms),
                         ("binance_usdm", "BTCUSDT", START, START + HOUR))
        self.assertEqual((bar.open, bar.high, bar.low, bar.close), (110.0, 120.0, 90.0, 112.0))

    def test_binance_dummy_activity_columns_never_filter_or_validate_marks(self):
        zero_row = binance_row()
        dummy_row = zero_row.copy()
        for i, value in zip((5, 7, 8, 9, 10, 11), (None, "ignored", {}, [], False, object())):
            dummy_row[i] = value
        zero = markbars.decode_binance([zero_row], symbol="BTCUSDT", interval_ms=HOUR)
        dummy = markbars.decode_binance([dummy_row], symbol="BTCUSDT", interval_ms=HOUR)
        self.assertEqual(zero, dummy)
        self.assertEqual(len(zero), 1)

    def test_binance_rejects_wrong_width_duration_and_invalid_ohlc(self):
        rows = [binance_row()[:-1], binance_row() + [0]]
        for index, value in ((6, START + HOUR), (6, START - 1), (0, START + 0.5),
                             (1, "nan"), (2, "100"), (3, "0")):
            row = binance_row()
            row[index] = value
            rows.append(row)
        for row in rows:
            with self.subTest(row=row), self.assertRaises(ERRORS):
                markbars.decode_binance([row], symbol="BTCUSDT", interval_ms=HOUR)

    def test_gate_keeps_unresolved_timestamp_and_needs_no_volume(self):
        row = {"t": START // 1000, "o": "110", "h": "120", "l": "90", "c": "112"}
        candles = markbars.decode_gate([row], contract="mark_BTC_USDT", interval_ms=HOUR)
        self.assertIsInstance(candles, tuple)
        self.assertEqual(len(candles), 1)
        candle = candles[0]
        self.assertIsInstance(candle, markbars.GateMarkCandle)
        self.assertEqual((candle.venue, candle.contract), ("gate_usdt", "mark_BTC_USDT"))
        self.assertEqual((candle.timestamp_ms, candle.interval_ms, candle.timestamp_role),
                         (START, HOUR, "unresolved"))
        self.assertEqual((candle.open, candle.high, candle.low, candle.close), (110.0, 120.0, 90.0, 112.0))
        with self.assertRaises(ERRORS):
            summarize(candles)

    def test_gate_rejects_trade_contract_missing_fields_and_invalid_clocks(self):
        row = {"t": START // 1000, "o": "110", "h": "120", "l": "90", "c": "112"}
        for contract in ("BTC_USDT", "index_BTC_USDT", "mark_", "mark_BTC_USD", "mark__USDT", ""):
            with self.subTest(contract=contract), self.assertRaises(ERRORS):
                markbars.decode_gate([row], contract=contract, interval_ms=HOUR)
        bad_rows = [{k: v for k, v in row.items() if k != "h"}]
        bad_rows += [row | {"t": x} for x in (-1, True, 1.0001, "not-a-time")]
        bad_rows += [row | {"l": "121"}, row | {"c": "inf"}]
        for bad in bad_rows:
            with self.subTest(row=bad), self.assertRaises(ERRORS):
                markbars.decode_gate([bad], contract="mark_BTC_USDT", interval_ms=HOUR)

    def test_empty_decodes_return_empty_tuples(self):
        self.assertEqual(markbars.decode_binance([], symbol="BTCUSDT", interval_ms=HOUR), ())
        self.assertEqual(markbars.decode_gate([], contract="mark_BTC_USDT", interval_ms=HOUR), ())

    def test_gate_accepts_exact_millisecond_seconds_without_guessing_clock_role(self):
        row = {"t": 1.5, "o": "110", "h": "120", "l": "90", "c": "112"}
        for value in (1.5, "1.500"):
            candle, = markbars.decode_gate([row | {"t": value}], contract="mark_BTC_USDT", interval_ms=HOUR)
            self.assertEqual(candle.timestamp_ms, 1500)
            self.assertEqual(candle.timestamp_role, "unresolved")

    def test_decoders_reject_unsupported_intervals_and_inverse_symbol_identity(self):
        for symbol in ("BTCUSD_PERP", "BTC", "BTCUSDT_261225"):
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                markbars.decode_binance([], symbol=symbol, interval_ms=HOUR)
        for interval in (1000, 120000):
            with self.subTest(binance_interval=interval), self.assertRaises(ValueError):
                markbars.decode_binance([], symbol="BTCUSDT", interval_ms=interval)
        with self.assertRaises(ValueError):
            markbars.decode_gate([], contract="mark_BTC_USDT", interval_ms=2 * HOUR)

    def test_gate_seconds_conversion_is_independent_of_decimal_context(self):
        row = {"t": "1761000000.123", "o": "1", "h": "1", "l": "1", "c": "1"}
        with localcontext() as context:
            context.prec = 10
            candle, = markbars.decode_gate([row], contract="mark_BTC_USDT", interval_ms=HOUR)
        self.assertEqual(candle.timestamp_ms, 1761000000123)

    def test_gate_never_rounds_away_sub_millisecond_seconds(self):
        row = {"o": "1", "h": "1", "l": "1", "c": "1"}
        for value in ("1761000000.0000000000000000001", "1761000000.123000000000000001"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                markbars.decode_gate([row | {"t": value}], contract="mark_BTC_USDT", interval_ms=HOUR)

    def test_mexc_fair_arrays_decode_without_volume_or_real_price_fallback(self):
        payload = {"success": True, "code": 0, "data": {
            "time": [START // 1000, END // 1000],
            "open": ["110", "112"], "high": ["120", "125"],
            "low": ["90", "111"], "close": ["112", "120"],
            "vol": [0, 0], "amount": [0, 0],
            "realOpen": [1, 1], "realHigh": [1, 1],
            "realLow": [1, 1], "realClose": [1, 1],
        }}
        candles = markbars.decode_mexc_fair(payload, contract="BTC_USDT", interval="Min60")
        self.assertEqual(len(candles), 2)
        first = candles[0]
        self.assertEqual((first.venue, first.contract, first.timestamp_s, first.interval,
                          first.timestamp_role),
                         ("mexc_usdt", "BTC_USDT", START // 1000, "Min60", "bar_start"))
        self.assertEqual((first.open, first.high, first.low, first.close), (110, 120, 90, 112))
        normalized = first.to_mark_bar()
        self.assertEqual((normalized.venue, normalized.contract, normalized.start_ms, normalized.end_ms),
                         ("mexc_usdt", "BTC_USDT", START, START + HOUR))
        with self.assertRaises(ValueError):
            summarize(candles)

    def test_mexc_unprobed_interval_keeps_clock_unresolved_and_cannot_normalize(self):
        candle = markbars.MexcFairCandle("BTC_USDT", START // 1000, "Min5", 110, 120, 90, 112)
        self.assertEqual(candle.timestamp_role, "unresolved")
        with self.assertRaises(ValueError):
            candle.to_mark_bar()
        misaligned = markbars.MexcFairCandle("BTC_USDT", START // 1000 + 1, "Min60", 110, 120, 90, 112)
        with self.assertRaises(ValueError):
            misaligned.to_mark_bar()

    def test_mexc_decoder_rejects_untrusted_response_shape_and_unfixed_month(self):
        payload = {"success": True, "code": 0, "data": {
            "time": [START // 1000], "open": [110], "high": [120],
            "low": [90], "close": [112],
        }}
        failures = [
            {"success": False, "code": 0, "data": payload["data"]},
            {"success": True, "code": 1, "data": payload["data"]},
            {"success": True, "code": False, "data": payload["data"]},
            {"success": True, "code": 0, "data": payload["data"] | {"high": [120, 121]}},
            {"success": True, "code": 0, "data": payload["data"] | {"time": [True]}},
            {"success": True, "code": 0, "data": payload["data"] | {"low": [121]}},
            {"success": True, "code": 0, "data": {k: v for k, v in payload["data"].items() if k != "close"}},
        ]
        for bad in failures:
            with self.subTest(payload=bad), self.assertRaises(ValueError):
                markbars.decode_mexc_fair(bad, contract="BTC_USDT", interval="Min60")
        for contract in ("BTCUSDT", "_USDT", "BTC_USDC", ""):
            with self.subTest(contract=contract), self.assertRaises(ValueError):
                markbars.decode_mexc_fair(payload, contract=contract, interval="Min60")
        for interval in ("Month1", "min1", "2Min"):
            with self.subTest(interval=interval), self.assertRaises(ValueError):
                markbars.decode_mexc_fair(payload, contract="BTC_USDT", interval=interval)

    def test_mexc_empty_public_response_decodes_to_no_candles(self):
        payload = {"success": True, "code": 0,
                   "data": {key: [] for key in ("time", "open", "high", "low", "close")}}
        self.assertEqual(markbars.decode_mexc_fair(payload, contract="ETH_USDT", interval="Min1"), ())


class MarkDayRangeTest(unittest.TestCase):
    def assert_incomplete(self, result, observed):
        self.assertEqual((result.expected, result.observed), (24, observed))
        self.assertFalse(result.range_complete)
        self.assertFalse(result.ready)
        self.assertIsNone(result.high)
        self.assertIsNone(result.low)
        self.assertIsNone(result.closing_mark)
        self.assertIsNone(markbars.adverse(result, +1))
        self.assertIsNone(markbars.adverse(result, -1))

    def test_complete_day_uses_preceding_close_and_known_arithmetic(self):
        result = summarize(full_day())
        self.assertEqual((result.expected, result.observed), (24, 24))
        self.assertTrue(result.range_complete)
        self.assertTrue(result.ready)
        self.assertEqual((result.anchor_close, result.high, result.low, result.closing_mark),
                         (100.0, 120.0, 90.0, 113.0))
        self.assertAlmostEqual(markbars.adverse(result, +1), 0.1)
        self.assertAlmostEqual(markbars.adverse(result, -1), 0.2)

    def test_normalized_mexc_hourly_marks_can_enter_complete_day_ranges(self):
        anchor = markbars.MarkBar("mexc_usdt", "BTC_USDT", START - HOUR, START,
                                  100, 101, 99, 100)
        bars = [anchor] + [mark(START + i * HOUR, venue="mexc_usdt", contract="BTC_USDT",
                               close=113 if i == 23 else 112) for i in range(24)]
        result = summarize(bars)
        self.assertTrue(result.ready)
        self.assertEqual((result.low, result.high), (90.0, 120.0))

    def test_missing_middle_slot_has_no_daily_extremes_or_forward_fill(self):
        bars = full_day()
        del bars[13]
        result = summarize(bars)
        self.assert_incomplete(result, 23)
        self.assertEqual(result.anchor_close, 100.0)

    def test_duplicate_cannot_replace_a_missing_slot(self):
        bars = full_day()
        del bars[13]
        bars.append(bars[1])
        self.assert_incomplete(summarize(bars), 23)

    def test_identical_duplicates_dedupe_and_input_order_does_not_matter(self):
        bars = full_day()
        self.assertEqual(summarize(list(reversed(bars)) + [bars[0], bars[7]]), summarize(bars))

    def test_conflicting_duplicate_is_an_error_including_anchor(self):
        bars = full_day()
        for index in (0, 7):
            other = dataclasses.replace(bars[index], close=100.5 if index == 0 else 111.0)
            with self.subTest(index=index), self.assertRaises(ERRORS):
                summarize(bars + [other])

    def test_unfinished_final_slot_is_not_observed_even_if_payload_exists(self):
        self.assert_incomplete(summarize(full_day(), as_of_ms=END - 1), 23)

    def test_missing_anchor_leaves_complete_range_unready(self):
        result = summarize(full_day()[1:])
        self.assertEqual((result.expected, result.observed), (24, 24))
        self.assertTrue(result.range_complete)
        self.assertFalse(result.ready)
        self.assertIsNone(result.anchor_close)
        self.assertEqual((result.high, result.low, result.closing_mark), (120.0, 90.0, 113.0))
        self.assertIsNone(markbars.adverse(result, +1))

    def test_old_close_cannot_substitute_for_immediate_predecessor(self):
        bars = full_day()
        bars[0] = dataclasses.replace(bars[0], start_ms=START - 2 * HOUR, end_ms=START - HOUR)
        result = summarize(bars)
        self.assertTrue(result.range_complete)
        self.assertFalse(result.ready)
        self.assertIsNone(result.anchor_close)

    def test_next_days_first_bar_does_not_contaminate_range(self):
        bars = full_day()
        following = markbars.MarkBar("binance_usdm", "BTCUSDT", END, END + HOUR, 112.0, 999.0, 1.0, 112.0)
        self.assertEqual(summarize(bars + [following], as_of_ms=END + HOUR), summarize(bars))

    def test_empty_input_and_one_bar_do_not_certify_a_day(self):
        self.assert_incomplete(summarize([]), 0)
        self.assert_incomplete(summarize([mark(END - HOUR)]), 1)

    def test_daily_interval_has_one_expected_bar_and_requires_prior_close(self):
        bars = [markbars.MarkBar("binance_usdm", "BTCUSDT", START - DAY, START, 100, 101, 99, 100),
                markbars.MarkBar("binance_usdm", "BTCUSDT", START, END, 110, 120, 90, 113)]
        result = summarize(bars, interval_ms=DAY)
        self.assertEqual((result.expected, result.observed, result.ready), (1, 1, True))
        self.assertEqual(result.anchor_close, 100)

    def test_off_grid_interval_mismatch_and_mixed_identities_are_errors(self):
        bars = full_day()
        alternatives = [
            dataclasses.replace(bars[4], start_ms=bars[4].start_ms + 1, end_ms=bars[4].end_ms + 1),
            dataclasses.replace(bars[4], end_ms=bars[4].end_ms - 1),
            dataclasses.replace(bars[4], venue="gate_usdt", contract="mark_BTC_USDT"),
            dataclasses.replace(bars[4], contract="ETHUSDT"),
        ]
        for other in alternatives:
            with self.subTest(other=other), self.assertRaises(ERRORS):
                summarize(bars[:4] + [other] + bars[5:])
        with self.assertRaises(ERRORS):
            summarize([{"t": START, "high": 120, "low": 90}])

    def test_request_requires_utc_day_end_valid_interval_and_observation_clock(self):
        changes = [{"day_end_ms": END + HOUR}, {"day_end_ms": -DAY}, {"day_end_ms": True},
                   {"interval_ms": 0}, {"interval_ms": -HOUR}, {"interval_ms": HOUR + 1},
                   {"interval_ms": True}, {"as_of_ms": -1}, {"as_of_ms": 1.5}, {"as_of_ms": True}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ERRORS):
                summarize([], **change)

    def test_adverse_floors_favorable_move_at_zero_and_validates_side(self):
        bars = full_day()
        for anchor, side in ((80.0, +1), (130.0, -1)):
            bars[0] = markbars.MarkBar("binance_usdm", "BTCUSDT", START - HOUR, START,
                                      anchor, anchor, anchor, anchor)
            self.assertEqual(markbars.adverse(summarize(bars), side), 0.0)
        result = summarize(full_day())
        for side in (0, 2, -2, True, "+1", None):
            with self.subTest(side=side), self.assertRaises(ERRORS):
                markbars.adverse(result, side)

    def test_finite_extreme_prices_cannot_return_infinite_adverse_move(self):
        bars = [markbars.MarkBar("binance_usdm", "BTCUSDT", START - DAY, START,
                                1e-300, 1e-300, 1e-300, 1e-300),
                markbars.MarkBar("binance_usdm", "BTCUSDT", START, END, 1.0, 1e300, 0.5, 1.0)]
        result = summarize(bars, interval_ms=DAY)
        self.assertTrue(result.ready)
        with self.assertRaises(ValueError):
            markbars.adverse(result, -1)


if __name__ == "__main__":
    unittest.main()
