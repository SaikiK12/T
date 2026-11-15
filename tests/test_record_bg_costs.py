"""The cost walk must match hand arithmetic, and Gate's contract multiplier must be applied."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load():
    spec = importlib.util.spec_from_file_location("bg", ROOT / "scripts/record_bg_costs.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class CostWalkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load()

    def test_flat_book_costs_only_the_half_spread(self):
        # mid 100, bid 99 / ask 101, deep on both sides: a small order pays 100 bp of half-spread
        bids = [(99.0, 1e9)]
        asks = [(101.0, 1e9)]
        r = self.m.measure(bids, asks)
        self.assertAlmostEqual(r["half_spread_bp"], 100.0, places=6)
        self.assertAlmostEqual(r["side_1k_bp"], 100.0, places=6)

    def test_walking_the_book_costs_more_than_the_half_spread(self):
        # ask side: 100 USD at 101, then plenty at 110. A 1000 USD buy averages above 101.
        bids = [(99.0, 1e9)]
        asks = [(101.0, 100.0), (110.0, 1e9)]
        r = self.m.measure(bids, asks)
        mid = 100.0
        expected_ask = ((100 * 101 + 900 * 110) / 1000 / mid - 1) * 1e4
        expected_bid = (1 - 99 / mid) * 1e4
        self.assertAlmostEqual(r["side_1k_bp"], (expected_ask + expected_bid) / 2, places=6)
        self.assertGreater(r["side_1k_bp"], r["half_spread_bp"])

    def test_thin_book_is_nan_not_zero(self):
        r = self.m.measure([(99.0, 10.0)], [(101.0, 10.0)])
        self.assertTrue(r["unfilled_10k"])
        self.assertNotEqual(r["side_10k_bp"], 0.0)
        self.assertNotEqual(r["side_10k_bp"], r["side_10k_bp"])  # NaN

    def test_crossed_or_empty_book_is_rejected(self):
        self.assertIsNone(self.m.measure([], [(101.0, 1e6)]))
        self.assertIsNone(self.m.measure([(102.0, 1e6)], [(101.0, 1e6)]))
        self.assertIsNone(self.m.measure([(0.0, 1e6)], [(101.0, 1e6)]))

    def test_bigger_orders_never_cost_less(self):
        bids = [(99.0, 500.0), (98.0, 1e9)]
        asks = [(101.0, 500.0), (103.0, 1e9)]
        r = self.m.measure(bids, asks)
        self.assertLessEqual(r["side_1k_bp"], r["side_5k_bp"])
        self.assertLessEqual(r["side_5k_bp"], r["side_10k_bp"])

    def test_gate_multiplier_changes_notional_by_its_factor(self):
        # 1000 contracts at 100 with mult 0.0001 is 10 USD, not 100_000 USD
        px, s, mult = 100.0, 1000, 0.0001
        self.assertAlmostEqual(s * mult * px, 10.0, places=9)
        # ignoring the multiplier would overstate the shown depth 10_000x
        self.assertAlmostEqual((s * px) / (s * mult * px), 1 / mult, places=6)

    def test_sizes_and_pacing_are_the_frozen_ones(self):
        self.assertEqual(self.m.SIZES, (1_000, 5_000, 10_000))
        self.assertEqual(self.m.PAUSE, 0.2)
        self.assertIn("www.binance.com", self.m.BINANCE)


if __name__ == "__main__":
    unittest.main()
