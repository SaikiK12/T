"""scripts/record_hlp_positions.py: parsing and file layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_hlp_positions", ROOT / "scripts" / "record_hlp_positions.py")
hp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hp)

T = 1_794_360_000_000                                    # 2026-11-11 01:20 UTC
DETAILS = {"relationship": {"type": "parent", "data": {"childAddresses": ["0xa", "0xb"]}}}
STATE = {"time": T, "marginSummary": {"accountValue": "100.0", "totalNtlPos": "50.0", "totalMarginUsed": "5.0"},
         "assetPositions": [{"type": "oneWay", "position": {"coin": "BTC", "szi": "-0.5", "entryPx": "100000",
                                                            "positionValue": "50000", "unrealizedPnl": "12.5",
                                                            "marginUsed": "2500"}}]}
EMPTY = {"time": T, "marginSummary": {"accountValue": "0.0"}, "assetPositions": []}
META = ({"universe": [{"name": "BTC"}, {"name": "OLD", "isDelisted": True}]},
        [{"markPx": "100100", "oraclePx": "100050", "midPx": "100099", "funding": "0.0000125", "premium": "0.0001",
          "openInterest": "25000", "dayNtlVlm": "3e9"}, {}])


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class RecordHLP(unittest.TestCase):
    def test_children_and_rows(self):
        self.assertEqual(hp.children(DETAILS), ["0xa", "0xb"])
        self.assertEqual(hp.children({"relationship": {"type": "normal"}}), [])
        pos, acc = hp.vault_rows("0xa", STATE)
        self.assertEqual((pos[0]["coin"], pos[0]["szi"], pos[0]["ts"]), ("BTC", "-0.5", T))
        self.assertEqual(acc["account_value"], "100.0")
        self.assertEqual([r["coin"] for r in hp.ctx_rows(*META, T)], ["BTC"])

    def test_record_writes_day_files(self):
        def fake_post(body, tries=4):
            if body["type"] == "vaultDetails":
                return DETAILS
            if body["type"] == "clearinghouseState":
                return STATE if body["user"] == "0xa" else EMPTY
            return list(META)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(hp.xb, "post", fake_post):
            self.assertEqual(hp.record(d, now_ms=T), (1, 2))
            root = Path(d) / "hlp"
            self.assertEqual(len(read(root / "positions" / "2026-11-11.csv")), 1)
            self.assertEqual(len(read(root / "accounts" / "2026-11-11.csv")), 2)
            self.assertEqual(read(root / "ctx" / "2026-11-11.csv")[0]["open_interest"], "25000")
            self.assertEqual(json.loads((root / "children.json").read_text()), ["0xa", "0xb"])
            hp.record(d, now_ms=T)                                          # idempotent
            self.assertEqual(len(read(root / "positions" / "2026-11-11.csv")), 1)


if __name__ == "__main__":
    unittest.main()
