"""scripts/record_llp_positions.py: parsing and file layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_llp_positions", ROOT / "scripts" / "record_llp_positions.py")
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)

T = 1_794_360_000_000                                    # 2026-11-11 01:20 UTC
ACCOUNT = {"code": 200, "total": 1, "accounts": [{
    "index": lp.LLP_INDEX, "total_asset_value": "1000.0", "collateral": "900.0", "available_balance": "100.0",
    "pool_info": {"total_shares": 123},
    "positions": [{"market_id": 1, "symbol": "BTC", "sign": -1, "position": "0.50", "position_value": "50000",
                   "avg_entry_price": "100000", "unrealized_pnl": "12.5", "realized_pnl": "1", "total_funding_paid_out":
                   "0.2", "allocated_margin": "0"},
                  {"market_id": 2, "symbol": "ETH", "sign": 1, "position": "0.00", "position_value": "0"}]}]}
DETAILS = {"code": 200, "order_book_details": [
    {"market_id": 1, "symbol": "BTC", "status": "active", "mark_price": "100100", "index_price": "100050",
     "last_trade_price": "100099", "open_interest": "25", "open_interest_usd": "2502500",
     "daily_quote_token_volume": 3e9, "taker_fee": "0.0000", "maker_fee": "0.0000"}],
    "spot_order_book_details": [{"market_id": 2048, "symbol": "ETH/USDC"}]}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class RecordLLP(unittest.TestCase):
    def test_rows(self):
        pos, acc = lp.pool_rows(ACCOUNT["accounts"][0], T)
        self.assertEqual([(p["symbol"], p["sign"], p["position"]) for p in pos], [("BTC", -1, "0.50")])  # zero dropped
        self.assertEqual((acc["total_shares"], acc["positions"]), (123, 1))
        self.assertEqual([m["symbol"] for m in lp.market_rows(DETAILS, T)], ["BTC"])                   # perps only

    def test_record_writes_day_files(self):
        def fake_get(path, tries=4):
            return ACCOUNT if path.startswith("account") else DETAILS
        with tempfile.TemporaryDirectory() as d, mock.patch.object(lp, "get", fake_get):
            self.assertEqual(lp.record(d, now_ms=T), (1, 1))
            root = Path(d) / "llp"
            self.assertEqual(read(root / "positions" / "2026-11-11.csv")[0]["sign"], "-1")
            self.assertEqual(read(root / "accounts" / "2026-11-11.csv")[0]["total_asset_value"], "1000.0")
            self.assertEqual(read(root / "markets" / "2026-11-11.csv")[0]["open_interest"], "25")
            lp.record(d, now_ms=T)                                          # idempotent
            self.assertEqual(len(read(root / "positions" / "2026-11-11.csv")), 1)

    def test_missing_account_raises(self):
        with mock.patch.object(lp, "get", lambda path, tries=4: {"accounts": []}), \
                tempfile.TemporaryDirectory() as d, self.assertRaises(RuntimeError):
            lp.record(d, now_ms=T)


if __name__ == "__main__":
    unittest.main()
