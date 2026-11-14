"""Recorder for xyz:COPPER and xyz:HO: contract lists by date and one offline run (network replaced)."""
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_cuho as cu  # noqa: E402

UTC = timezone.utc
H = 3_600_000


class Contracts(unittest.TestCase):
    def test_copper_follows_xyz_designated_months(self):
        self.assertEqual(cu.copper(datetime(2026, 11, 12, tzinfo=UTC)), ["HGZ26.CMX", "HGH27.CMX", "HGK27.CMX"])
        self.assertEqual(cu.copper(datetime(2026, 12, 1, tzinfo=UTC)), ["HGH27.CMX", "HGK27.CMX", "HGN27.CMX"])
        self.assertEqual(cu.copper(datetime(2027, 2, 8, tzinfo=UTC)), ["HGH27.CMX", "HGK27.CMX", "HGN27.CMX"])
        self.assertEqual(cu.copper(datetime(2027, 8, 9, tzinfo=UTC)), ["HGU27.CMX", "HGZ27.CMX", "HGH28.CMX"])
        self.assertEqual(cu.copper(datetime(2027, 9, 1, tzinfo=UTC)), ["HGZ27.CMX", "HGH28.CMX", "HGK28.CMX"])

    def test_heating_oil_next_four_months(self):
        self.assertEqual(cu.heating_oil(datetime(2026, 11, 12, tzinfo=UTC)),
                         ["HOZ26.NYM", "HOF27.NYM", "HOG27.NYM", "HOH27.NYM"])
        self.assertEqual(cu.heating_oil(datetime(2026, 12, 31, tzinfo=UTC))[0], "HOF27.NYM")


class OfflineRun(unittest.TestCase):
    def test_record_writes_every_file_and_merges(self):
        now = datetime(2026, 11, 12, 20, tzinfo=UTC)
        now_ms = int(now.timestamp() * 1000)
        bar = {"open_ms": now_ms - 2 * H, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}
        fund = {"time": now_ms - H, "fundingRate": "0.00001", "premium": "0"}
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(cu.rec, "yahoo_bars", return_value=[bar]), \
                mock.patch.object(cu.rec, "venue_candles", return_value=[bar]), \
                mock.patch.object(cu.rec, "venue_funding", return_value=[fund]), \
                mock.patch.object(cu.time, "sleep"):
            self.assertEqual(cu.record(d, now), 0)
            names = sorted(p.relative_to(d).as_posix() for p in Path(d).rglob("*.csv"))
            self.assertEqual(len(names), 3 + 4 + 4)
            self.assertIn("yahoo/HGH27.CMX.csv", names)
            self.assertIn("xyz/HO_funding.csv", names)
            self.assertEqual(cu.record(d, now), 0)        # a second run adds nothing
            self.assertEqual((Path(d) / "xyz" / "COPPER_1h.csv").read_text().count("\n"), 2)


if __name__ == "__main__":
    unittest.main()
