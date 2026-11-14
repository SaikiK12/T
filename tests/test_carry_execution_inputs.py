"""Synthetic parent-format fixtures; never opens a real market-data folder."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_carry_execution as runner


class CapturedInputTests(unittest.TestCase):
    def fixture(self, root):
        bodies = {
            "BTC_mexc_meta": dict(success=True, code=0, data=dict(symbol="BTC_USDT", baseCoin="BTC", quoteCoin="USDT",
                 settleCoin="USDT", type=1, contractSize=".01", volUnit="1", minVol="2", marketOrderMaxLevel=1)),
            "BTC_lighter_meta": dict(code=200, order_book_details=[dict(symbol="BTC", market_id=1, status="active",
                 supported_size_decimals=3, min_base_amount=".001", min_quote_amount="10")]),
            "BTC_mexc_book_0": dict(success=True, code=0, data=dict(bids=[[99, 10, 1], [98, 10, 2]], asks=[[101, 20, 1], [102, 30, 2]])),
            "BTC_lighter_book_0": dict(code=200, bids=[dict(price="99", remaining_base_amount=".2")],
                 asks=[dict(price="101", remaining_base_amount=".3"), dict(price="101", remaining_base_amount=".2")])}
        receipts = {}
        for name, body in bodies.items():
            raw = json.dumps(body).encode()
            (root / (name + ".json.gz")).write_bytes(gzip.compress(raw))
            receipts[name] = dict(body=name + ".json.gz", error=None, http_status=200,
                sha256=hashlib.sha256(raw).hexdigest(), receipt=dict(received_utc_ns=1000000, received_mono_ns=500000))
        return receipts

    def test_contract_multiplier_aggregation_and_order_depth_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = self.fixture(root)
            with patch.object(runner, "PARENT", root):
                books, lots, minima, quote_min, clock = runner.normalize_btc(records, 0)
            self.assertEqual(books[0].bids[0][1], runner.number(".1"))
            self.assertEqual(len(books[0].bids), 1)
            self.assertEqual(books[1].asks[0][1], runner.number(".5"))
            self.assertEqual(lots, (runner.number(".01"), runner.number(".001")))
            self.assertEqual(minima[0], runner.number(".02"))
            self.assertEqual(quote_min, 10)
            self.assertFalse(clock["actual_arrival_or_fills_observed"])

    def test_hash_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            records = self.fixture(root)
            records["BTC_mexc_meta"]["sha256"] = "0" * 64
            with patch.object(runner, "PARENT", root):
                with self.assertRaises(ValueError): runner.normalize_btc(records, 0)


if __name__ == "__main__":
    unittest.main()
