import csv
import tempfile
from pathlib import Path
import unittest

from scripts import fetch_equation_history as f


class FakePages:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return next(self.payloads)


class EquationFetchTests(unittest.TestCase):
    def test_lighter_preserves_exact_settlement_clock_sign_and_inclusive_boundary(self):
        page = FakePages([{"fundings": [
            {"timestamp": 3600, "rate": ".01", "direction": "long", "value": "1"},
            {"timestamp": 7200, "rate": ".02", "direction": "short", "value": "2"},
            {"timestamp": 10800, "rate": ".03", "direction": "long", "value": "3"},
        ]}])
        df = f.lighter_rows(page, 1, "funding", 0, 7200000)
        self.assertEqual(df.t.tolist(), [3600000, 7200000])
        self.assertEqual(df.rate.tolist(), [.0001, -.0002])
        self.assertEqual(df.raw_value_uninterpreted.tolist(), ["1", "2"])

    def test_lighter_rejects_unknown_payer_and_negative_unsigned_rate(self):
        for direction, rate in [("unknown", ".01"), ("long", "-.01")]:
            p = FakePages([{"fundings": [{"timestamp": 3600, "rate": rate, "direction": direction}]}])
            with self.assertRaises(ValueError):
                f.lighter_rows(p, 1, "funding", 0, 7200000)

    def test_price_requests_stay_below_silent_server_cap_and_exclude_active_end(self):
        p = FakePages([{"c": [{"t": 0, "c": 1, "v": 2}, {"t": 480*f.H, "c": 3, "v": 4}]},
                       {"c": [{"t": 480*f.H, "c": 3, "v": 4}, {"t": 481*f.H, "c": 5, "v": 6}]}])
        df = f.lighter_rows(p, 1, "prices", 0, 481*f.H)
        self.assertEqual(df.t.tolist(), [0, 480*f.H])
        self.assertEqual(len(p.calls), 2)

    def test_mexc_funding_rejects_stalled_page(self):
        row = {"settleTime": 7200000, "fundingRate": .0001, "collectCycle": 8}
        p = FakePages([{"data": {"currentPage": 1, "totalPage": 2, "resultList": [row]}},
                       {"data": {"currentPage": 2, "totalPage": 2, "resultList": [row]}}])
        with self.assertRaisesRegex(ValueError, "stalled"):
            f.mexc_rows(p, "TOY", "funding", 0, 7200000)

    def test_non_binance_frozen_pair_is_rejected_without_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "symbols.csv"
            with p.open("w", newline="") as h:
                w = csv.DictWriter(h, ["key", "binance", "mexc", "lighter"])
                w.writeheader()
                w.writerow({"key": "TOYUSDT", "binance": "", "mexc": "TOY_USDT", "lighter": "TOY"})
            with self.assertRaisesRegex(ValueError, "reserved"):
                f.pairs(p)


if __name__ == "__main__":
    unittest.main()
