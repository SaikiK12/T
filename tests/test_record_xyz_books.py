"""scripts/record_xyz_books.py: book costs and file layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


spec = importlib.util.spec_from_file_location("record_xyz_books", ROOT / "scripts" / "record_xyz_books.py")
xb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xb)

BOOK = {"coin": "xyz:NVDA", "time": 1_794_360_000_000,
        "levels": [[{"px": "99.9", "sz": "20", "n": 1}, {"px": "99.0", "sz": "1000", "n": 3}],
                   [{"px": "100.1", "sz": "20", "n": 1}, {"px": "101.0", "sz": "1000", "n": 2}]]}
CTX = {"markPx": "100.0", "oraclePx": "100.02", "funding": "0.0000062", "premium": "0.0001",
       "openInterest": "5000", "dayNtlVlm": "12345678.9"}


class RecordXyzBooks(unittest.TestCase):
    def test_costs_walk_the_book(self):
        r = xb.book_row("xyz", BOOK, CTX, (1_000, 5_000, 200_000))
        self.assertAlmostEqual(r["spread_bp"], (100.1 / 99.9 - 1) * 1e4, places=3)
        # $1k fits in the first level: half the spread, 10 bp from a mid of 100.0
        self.assertAlmostEqual(r["buy_1000_bp"], 10.0, places=2)
        self.assertAlmostEqual(r["sell_1000_bp"], 10.0, places=2)
        # $5k: $2,002 at 100.1 and $2,998 at 101.0 -> (2002 * 10 + 2998 * 100) / 5000 bp
        self.assertAlmostEqual(r["buy_5000_bp"], (2002 * 10 + 2998 * 100) / 5000, places=1)
        self.assertIsNone(r["buy_200000_bp"])             # deeper than the 20 levels returned
        self.assertEqual(r["day_ntl_vlm"], "12345678.9")

    def test_empty_side_gives_no_row(self):
        b = dict(BOOK, levels=[[], BOOK["levels"][1]])
        self.assertIsNone(xb.book_row("xyz", b, CTX, (1_000,)))

    def test_record_writes_day_files_and_skips_delisted(self):
        meta = [{"universe": [{"name": "xyz:NVDA", "growthMode": "enabled", "deployerFeeScale": "1.0",
                               "maxLeverage": 10},
                              {"name": "xyz:OLD", "isDelisted": True}]}, [CTX, CTX]]

        def fake_post(body, tries=4):
            return meta if body["type"] == "metaAndAssetCtxs" else BOOK
        with tempfile.TemporaryDirectory() as d, mock.patch.object(xb, "post", fake_post):
            n, failed = xb.record(d, ("xyz",), (1_000,), now_ms=BOOK["time"])
            self.assertEqual((n, failed), (1, 0))
            rows = read(Path(d) / "books" / "2026-11-11.csv")
            self.assertEqual([r["coin"] for r in rows], ["xyz:NVDA"])
            self.assertEqual(list(rows[0]), xb.book_cols((1_000,)))
            m = read(Path(d) / "markets" / "2026-11-11.csv")
            self.assertEqual([(r["coin"], r["growthMode"]) for r in m], [("xyz:NVDA", "enabled")])
            xb.record(d, ("xyz",), (1_000,), now_ms=BOOK["time"])           # idempotent re-run
            self.assertEqual(len(read(Path(d) / "books" / "2026-11-11.csv")), 1)


if __name__ == "__main__":
    unittest.main()
