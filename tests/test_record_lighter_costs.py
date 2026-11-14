"""scripts/record_lighter_costs.py: book arithmetic and file layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_lighter_costs", ROOT / "scripts" / "record_lighter_costs.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)

T = 1_794_360_000_000                                    # 2026-11-11 01:20 UTC
DETAILS = {"order_book_details": [{"market_id": 1, "symbol": "BTC", "status": "active"},
                                  {"market_id": 2, "symbol": "OLD", "status": "inactive"},
                                  {"market_id": 3, "symbol": "THIN", "status": "active"},
                                  {"market_id": 4, "symbol": "DOWN", "status": "active"}]}
BOOK = {"asks": [{"price": "101", "remaining_base_amount": "5"}, {"price": "102", "remaining_base_amount": "100"}],
        "bids": [{"price": "99", "remaining_base_amount": "100"}]}
THIN = {"asks": [{"price": "10.1", "remaining_base_amount": "1"}],
        "bids": [{"price": "9.9", "remaining_base_amount": "1"}]}


def fake_get(path, tries=4):
    if path == "orderBookDetails":
        return DETAILS
    mid = int(path.split("market_id=")[1].split("&")[0])
    if mid == 4:
        raise RuntimeError("down")
    return BOOK if mid == 1 else THIN


class Costs(unittest.TestCase):
    def test_impact_walks_the_book(self):
        r = lc.book_row(T, {"market_id": 1, "symbol": "BTC"}, BOOK)
        self.assertAlmostEqual(r["half_spread_bp"], 100.0)
        self.assertAlmostEqual(r["sell_1k_bp"], 100.0)                       # all at 99, mid 100
        qty = 505 / 101 + 495 / 102                                          # $505 at 101, the rest at 102
        self.assertAlmostEqual(r["buy_1k_bp"], (1000 / qty / 100 - 1) * 1e4)
        self.assertIsNone(lc.book_row(T, {"market_id": 3, "symbol": "THIN"}, THIN)["buy_1k_bp"])  # $10 shown

    def test_record_paces_skips_and_writes(self):
        waits = []
        with tempfile.TemporaryDirectory() as d:
            n, failed = lc.record(d, now_ms=T, get=fake_get, sleep=waits.append, clock=lambda: 0.0)
            self.assertEqual((n, failed), (2, 1))                            # inactive left out, DOWN failed
            self.assertEqual(waits, [lc.PACE_S] * 3)
            with open(Path(d) / "lighter" / "books" / "2026-11-11.csv", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r["symbol"] for r in rows], ["BTC", "THIN"])
            self.assertEqual(rows[1]["buy_1k_bp"], "")
            lc.record(d, now_ms=T, get=fake_get, sleep=lambda s: None)       # idempotent
            with open(Path(d) / "lighter" / "books" / "2026-11-11.csv", newline="") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 2)


if __name__ == "__main__":
    unittest.main()
