"""scripts/snapshot_route_costs.py: book walk, crossed books, and one offline snapshot over all four routes."""
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import snapshot_route_costs as sr  # noqa: E402


class Parts(unittest.TestCase):
    def test_impact(self):
        asks = [(100.0, 5.0), (101.0, 100.0)]                 # $500 at 100, then plenty at 101
        self.assertAlmostEqual(sr.impact(asks, 400, 100.0), 0.0)
        cost = sr.impact(asks, 1_000, 100.0)                   # 5 at 100 and 500/101 at 101
        self.assertAlmostEqual(cost, (1000 / (5 + 500 / 101) / 100 - 1) * 1e4)
        self.assertTrue(math.isnan(sr.impact([(100.0, 1.0)], 1_000, 100.0)))

    def test_row_rejects_crossed_and_empty(self):
        self.assertIsNone(sr.row("x", "BTC", [(101.0, 1.0)], [(100.0, 1.0)]))
        self.assertIsNone(sr.row("x", "BTC", [], [(100.0, 1.0)]))
        r = sr.row("x", "BTC", [(99.0, 1000.0)], [(101.0, 1000.0)])
        self.assertAlmostEqual(r["half_spread_bp"], 100.0)
        self.assertAlmostEqual(r["side_1k_bp"], 100.0)


class Snapshot(unittest.TestCase):
    def test_offline(self):
        def get(url, body=None):
            if url.endswith("/markets"):
                return {"results": [{"asset_kind": "PERP", "symbol": "BTC-USD-PERP", "base_currency": "BTC"},
                                    {"asset_kind": "OPTION", "symbol": "X", "base_currency": "X"}]}
            if "/orderbook/BTC-USD-PERP/interactive" in url:
                return {"bids": [["99.99", "1000"]], "asks": [["100.01", "1000"]]}
            if "/orderbook/BTC-USD-PERP" in url:
                return {"bids": [["99", "1000"]], "asks": [["101", "1000"]]}
            if "orderBookDetails" in url:
                return {"order_book_details": [{"symbol": "BTC", "market_id": 1, "status": "active"}]}
            if "orderBookOrders" in url:
                return {"bids": [{"price": "99.995", "remaining_base_amount": "1000"}],
                        "asks": [{"price": "100.005", "remaining_base_amount": "1000"}]}
            if body == {"type": "meta"}:
                return {"universe": [{"name": "BTC"}]}
            if body and body.get("type") == "l2Book":
                return {"levels": [[{"px": "99.995", "sz": "1000"}], [{"px": "100.005", "sz": "1000"}]]}
            raise AssertionError(url)

        x = sr.snapshot(get=get, pause=lambda s: None).set_index("book")
        self.assertEqual(sorted(x.index), ["hyperliquid", "lighter", "paradex_api_public", "paradex_interactive"])
        self.assertAlmostEqual(x.loc["paradex_interactive", "allin_1k_bp"], 1.0)
        self.assertAlmostEqual(x.loc["paradex_api_public", "allin_1k_bp"], 100.0 + 2.0)
        self.assertAlmostEqual(x.loc["lighter", "allin_10k_bp"], 0.5)
        self.assertAlmostEqual(x.loc["hyperliquid", "allin_1k_bp"], 0.5 + 4.5)


if __name__ == "__main__":
    unittest.main()
