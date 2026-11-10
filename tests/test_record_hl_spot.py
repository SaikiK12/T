"""scripts/record_hl_spot.py: the pair rule and an offline run against a fake API."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_hl_spot", ROOT / "scripts" / "record_hl_spot.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)
DAY = rs.DAY

SPOT_META = {
    "tokens": [{"index": 0, "name": "USDC"}, {"index": 1, "name": "UBTC", "fullName": "Unit Bitcoin"},
               {"index": 2, "name": "HYPE", "fullName": "Hyperliquid"}, {"index": 3, "name": "SOL"},
               {"index": 4, "name": "UFART", "fullName": "Unit Fartcoin"}, {"index": 5, "name": "USDT0"},
               {"index": 6, "name": "UETH", "fullName": "Unit Ethereum"}],
    "universe": [{"name": "@1", "index": 1, "tokens": [1, 0]}, {"name": "@2", "index": 2, "tokens": [2, 0]},
                 {"name": "@3", "index": 3, "tokens": [3, 0]}, {"name": "@4", "index": 4, "tokens": [4, 0]},
                 {"name": "@5", "index": 5, "tokens": [2, 5]}, {"name": "@6", "index": 6, "tokens": [6, 5]}]}


class RecordHLSpot(unittest.TestCase):
    def test_pairs_take_hype_and_unit_coins_with_a_same_name_perp(self):
        p = rs.pairs(SPOT_META, {"BTC", "HYPE", "SOL", "FARTCOIN", "ETH"})
        # SOL is a plain name (could be another asset), UFART has no FART perp, UETH is quoted in USDT0
        self.assertEqual(p, {"@1": {"token": "UBTC", "perp": "BTC"}, "@2": {"token": "HYPE", "perp": "HYPE"}})

    def test_offline_run_writes_closed_days_and_is_idempotent(self):
        now = rs.ms_of("2024-11-04") + 3600_000
        calls = []

        def fake(body):
            calls.append(body["type"])
            if body["type"] == "meta":
                return {"universe": [{"name": "BTC"}, {"name": "HYPE"}]}
            if body["type"] == "spotMeta":
                return SPOT_META
            if body["type"] == "fundingHistory":
                s = body["startTime"]
                return [{"time": t, "fundingRate": "0.0000125"}
                        for t in range(s - s % 3600_000 + 3600_000, now, 3600_000)][:500]
            c = body["req"]["coin"]
            return [{"t": rs.ms_of("2024-11-01") + k * DAY, "o": "1", "h": "1", "l": "1", "c": "1", "v": "5"}
                    for k in range(4) if c in ("BTC", "HYPE", "@1", "@2")]
        old, rs.hl.post = rs.hl.post, fake
        try:
            with tempfile.TemporaryDirectory() as d:
                s = rs.record(Path(d), since="2024-11-01", now_ms=now)
                self.assertEqual((s["pairs"], s["failed"]), (2, []))
                self.assertEqual(s["perp_rows"], 6)                  # 3 closed days x 2 perps; 11-04 is open
                self.assertEqual(s["spot_rows"], 6)
                with open(Path(d) / "spot_1d" / "2024-11-01.csv") as f:
                    self.assertEqual(sorted(r["coin"] for r in csv.DictReader(f)), ["@1", "@2"])
                n_f = s["funding_rows"]
                self.assertEqual(n_f, 2 * 3 * 24)                     # hourly prints 11-01 01:00 .. 11-04 00:00
                again = rs.record(Path(d), since="2024-11-01", now_ms=now)
                self.assertEqual((again["funding_rows"], again["perp_rows"], again["spot_rows"]), (0, 0, 0))
                self.assertEqual(json.loads((Path(d) / "pairs.json").read_text())["pairs"]["@1"]["perp"], "BTC")
        finally:
            rs.hl.post = old


if __name__ == "__main__":
    unittest.main()
