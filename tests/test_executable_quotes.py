from dataclasses import replace
from decimal import Decimal
import math
import unittest

from lab.executable_quotes import (Receipt, RestBook, common_quantity, lighter_book,
                                   mexc_book, pair_costs, receipt_quality, walk)
from lab.microstructure import DepthLevel as L


def metadata():
    return {"symbol": "BTC_USDT", "contractSize": "0.01", "volUnit": "3", "minVol": 1,
            "maxVol": 1000000, "type": 1, "settleCoin": "USDT", "marketOrderMaxLevel": 20}


def receipt():
    return Receipt(10_000_000_000, 10_100_000_000, 1_000_000_000, 1_100_000_000)


def book(venue="mexc"):
    return RestBook(venue, "BTC" + ("_USDT" if venue == "mexc" else ""), receipt(),
                    (L(99., 1.), L(98., 2.)), (L(101., 1.), L(102., 2.)), None, "unknown", None)


class QuoteContractTests(unittest.TestCase):
    def test_individual_receipt_clocks_reject_monotonic_reversal_detect_utc_steps(self):
        with self.assertRaises(ValueError):
            Receipt(1, 2, 10, 9)
        with self.assertRaises(ValueError):
            Receipt(True, 2, 10, 11)
        r = replace(receipt(), received_utc_ns=9_000_000_000)
        self.assertGreater(r.clock_step_ns, 50_000_000)
        quality = receipt_quality((replace(book(), receipt=r), book("lighter")), 1_100_000_000)
        self.assertFalse(quality["first_seen_pair_ok"])

    def test_local_synchronization_is_not_fabricated_source_or_execution_readiness(self):
        q = receipt_quality((book(), book("lighter")), 1_200_000_000)
        self.assertTrue(q["first_seen_pair_ok"])
        self.assertFalse(q["execution_ready"])
        self.assertIn("REST_book_event_age_unverified", q["execution_blockers"])
        for now in (1_000_000_000, 7_000_000_000):
            self.assertFalse(receipt_quality((book(), book("lighter")), now)["first_seen_pair_ok"])
        delayed = replace(book("lighter"), receipt=Receipt(12_000_000_000, 12_100_000_000, 3_000_000_000, 3_100_000_000))
        self.assertIn("cross_venue_receipt_skew", receipt_quality((book(), delayed), 3_100_000_000)["first_seen_flags"])

    def test_mexc_contracts_not_order_counts_and_market_order_depth_limit(self):
        meta = metadata()
        meta["marketOrderMaxLevel"] = 1
        raw = {"success": True, "data": {"timestamp": 100, "version": 7,
               "bids": [[99, 100, 3], [98, 10000, 1]], "asks": [[101, 100, 5], [102, 10000, 2]]}}
        b = mexc_book("BTC_USDT", raw, meta, receipt())
        self.assertEqual(b.bids, (L(99., 1.),))
        self.assertIsNone(walk(b.asks, "1.1"))
        self.assertEqual(b.version, 7)
        self.assertIn("not_verified", b.timestamp_role)
        with self.assertRaises(ValueError):
            mexc_book("OTHER_USDT", raw, meta, receipt())

    def test_lighter_aggregates_duplicate_order_prices_without_inventing_clock(self):
        r = {"code": 200, "timestamp": 123, "bids": [{"price": "99", "remaining_base_amount": ".2"},
             {"price": "99", "remaining_base_amount": ".3"}, {"price": "98", "remaining_base_amount": "1"}],
             "asks": [{"price": "101", "remaining_base_amount": "2"}]}
        b = lighter_book("BTC", r, receipt())
        self.assertEqual(b.bids, (L(99., .5), L(98., 1.)))
        self.assertIsNone(b.reported_timestamp_ms)
        for bad in ("NaN", "Infinity", "0", "-1", True):
            r["bids"][0]["remaining_base_amount"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                lighter_book("BTC", r, receipt())

    def test_locked_crossed_and_empty_books_are_not_zero_cost(self):
        for kwargs in ({"bids": ()}, {"bids": (L(101, 1),)}, {"bids": (L(102, 1),)},
                       {"bids": (L(98, 1), L(99, 1))}):
            with self.assertRaises(ValueError):
                replace(book(), **kwargs)

    def test_exact_common_lot_lattice_rounds_down_on_both_venues(self):
        # 0.03 MEXC base lot and 0.1 Lighter lot => 0.3 common base lot.
        lm = {"supported_size_decimals": 1, "min_base_amount": ".1", "min_quote_amount": "10"}
        q, step = common_quantity(metadata(), lm, 100)
        self.assertEqual((q, step), (Decimal("2.4"), Decimal("0.3")))
        self.assertEqual(q % Decimal(".03"), 0)
        self.assertEqual(q % Decimal(".1"), 0)
        for change in ({"minVol": 1000}, {"maxVol": 10}, {"type": True}):
            with self.assertRaises(ValueError):
                common_quantity({**metadata(), **change}, lm, 100)
        with self.assertRaises(ValueError):
            common_quantity(metadata(), {**lm, "supported_size_decimals": True}, 100)

    def test_same_quantity_cash_costs_and_capital_denominators_match_hand_example(self):
        # Each venue buys 2 base for 203 and sells 2 for 197. Crossing = 12.
        # Fees: 400*10bp + 400*4bp = .56. Total = 12.56 per 200 leg.
        result = pair_costs(book(), book("lighter"), Decimal("2"))
        self.assertTrue(result["displayed_fillable"])
        self.assertAlmostEqual(result["crossing_usd"], 12.)
        self.assertAlmostEqual(result["fee_usd"], .56)
        self.assertAlmostEqual(result["long_mexc_entry_cost_usd"] + result["long_lighter_entry_cost_usd"], 12.56)
        self.assertEqual(result["venue_margin_mid_notionals_usd"], [200., 200.])
        for row, k in zip(result["scenarios"], (1, 2, 3)):
            self.assertAlmostEqual(row["round_trip_cost_usd"], 12.56*k)
            self.assertAlmostEqual(row["break_even_leg_bp"], 628*k)
            self.assertAlmostEqual(row["capital_cost_bp"], 12.56*k)
        for fees in ((math.nan, 4), (-1, 4), (0,), (None, 4)):
            with self.assertRaises((ValueError, TypeError)):
                pair_costs(book(), book("lighter"), 2, fees)

    def test_thin_leg_blocks_both_hedges_preserves_capacity_without_partial_fill_profit(self):
        result = pair_costs(book(), book("lighter"), "3.01")
        self.assertFalse(result["displayed_fillable"])
        self.assertEqual(result["shown_two_way_capacity_base"], 3.)
        self.assertNotIn("scenarios", result)
        with self.assertRaises(ValueError):
            pair_costs(book(), book("lighter"), 2, capital=300)


if __name__ == "__main__":
    unittest.main()
