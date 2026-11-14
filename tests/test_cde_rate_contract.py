from datetime import datetime, timezone
import unittest

from lab.cde_rate_contract import evaluate, hour, rate


def fixtures(a="0.0001", b="0.0002"):
    times = ["2026-11-07T04:00:00Z", "2026-11-07T05:00:00Z"]
    obs = [dict(source_hour=f"synthetic{i}", funding_time=t, funding_rate=v,
                received_utc_ns=(hour(t) + 10) * 10**9) for i, (t, v) in enumerate(zip(times, (a, b)))]
    history = [dict(symbol="BIPZ30", event_time=t, funding_rate=v) for t, v in zip(times, (a, b))]
    return obs, history


class CdeRateContract(unittest.TestCase):
    def test_exact_numeric_identity_accepts_equivalent_decimal_formats(self):
        o, h = fixtures();h[0]["funding_rate"] = "1e-4"
        r = evaluate(o, h, symbol="BIPZ30", required=2)
        self.assertEqual(r["verdict"], "SAMPLED_FIELD_CONSISTENT")
        self.assertEqual(r["exact_matches"], 2)
        self.assertIsNone(r["pnl"])

    def test_factor100_mismatch_is_not_auto_corrected(self):
        o, h = fixtures();h[0]["funding_rate"] = "0.01"
        r = evaluate(o, h, symbol="BIPZ30", required=2)
        self.assertEqual(r["verdict"], "EXACT_FIELD_MISMATCH")
        self.assertIsNone(r["fitted_scale"])

    def test_small_decimal_difference_is_not_given_a_fitted_tolerance(self):
        o, h = fixtures();h[0]["funding_rate"] = "0.0001000000000000000001"
        self.assertEqual(evaluate(o, h, symbol="BIPZ30", required=2)["mismatches"], 1)

    def test_missing_timestamp_is_not_shifted_or_zero_filled(self):
        o, h = fixtures();h[0]["event_time"] = "2026-11-07T03:00:00Z"
        r = evaluate(o, h, symbol="BIPZ30", required=2)
        self.assertEqual(r["verdict"], "INCONCLUSIVE_COVERAGE")
        self.assertIsNone(r["rows"][0]["mda_raw"])
        self.assertIsNone(r["fitted_time_shift"])

    def test_future_field_does_not_become_known_at_original_receipt(self):
        o, h = fixtures();o[0]["received_utc_ns"] = (hour(o[0]["funding_time"]) - 1) * 10**9
        r = evaluate(o, h, symbol="BIPZ30", required=2)
        self.assertEqual(r["verdict"], "UNQUALIFIED_FUTURE_TIMESTAMP")

    def test_zero_or_constant_rate_cannot_identify_scale_and_time(self):
        for v in ["0", "0.0001"]:
            o, h = fixtures(v, v)
            self.assertEqual(evaluate(o, h, symbol="BIPZ30", required=2)["verdict"], "INCONCLUSIVE_VARIATION")

    def test_duplicates_and_wrong_identity_are_rejected(self):
        o, h = fixtures()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate(o, [*h, h[0]], symbol="BIPZ30", required=2)
        h[0]["symbol"] = "ETPZ30"
        with self.assertRaisesRegex(ValueError, "identity"):
            evaluate(o, h, symbol="BIPZ30", required=2)

    def test_missing_nonfinite_and_naive_time_are_rejected(self):
        for v in [None, "", "NaN", "Infinity", 0]:
            with self.subTest(v=v), self.assertRaises(ValueError):
                rate(v)
        with self.assertRaises(ValueError):
            hour("2026-11-07T04:00:00")
        with self.assertRaises(ValueError):
            hour("2026-11-07T04:00:01Z")

    def test_equivalent_timezone_preserves_the_exact_hour(self):
        self.assertEqual(hour("2026-11-07T04:00:00Z"), hour("2026-11-07T05:00:00+01:00"))


if __name__ == "__main__":
    unittest.main()
