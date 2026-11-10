"""scripts/record_okx_xperp.py: offline checks of the pure helpers (no network)."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_okx_xperp", ROOT / "scripts" / "record_okx_xperp.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)
D = rec.DAY


class RecordOkxXperp(unittest.TestCase):
    def test_merge_rows_is_idempotent_and_new_rows_win(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f" / "2026-11-10.csv"
            rows = [{"instId": "B", "fundingTime": 2, "fundingRate": "0.1"},
                    {"instId": "A", "fundingTime": 1, "fundingRate": "0.2"}]
            self.assertEqual(rec.merge_rows(p, rows, rec.FUND_COLS, ["instId", "fundingTime"]), 2)
            self.assertEqual(rec.merge_rows(p, rows, rec.FUND_COLS, ["instId", "fundingTime"]), 0)
            self.assertEqual(rec.merge_rows(p, [{"instId": "A", "fundingTime": 1, "fundingRate": "0.3"}],
                                            rec.FUND_COLS, ["instId", "fundingTime"]), 1)
            got = list(csv.DictReader(open(p)))
            self.assertEqual([r["instId"] for r in got], ["A", "B"])
            self.assertEqual(got[0]["fundingRate"], "0.3")
            self.assertEqual(got[0]["realizedRate"], "")

    def test_by_day_uses_utc_day_of_the_key(self):
        t0 = 1794268800000          # 2026-11-10 00:00 UTC
        out = rec.by_day([{"t": t0}, {"t": t0 + D - 1}, {"t": t0 + D}], "t")
        self.assertEqual(sorted(out), ["2026-11-10", "2026-11-11"])
        self.assertEqual(len(out["2026-11-10"]), 2)

    def test_closed_candles_drops_the_open_day(self):
        t0 = 1794268800000
        raw = [[str(t0), "1", "2", "0.5", "1.5", "0"], [str(t0 - D), "1", "2", "0.5", "1.2", "1"]]
        got = rec.closed_candles(raw, "X", t0 + 3600_000)
        self.assertEqual([r["ts"] for r in got], [t0 - D])
        self.assertEqual(got[0]["c"], "1.2")
        self.assertEqual(got[0]["vol_quote"], "")
        trade = [[str(t0 - D), "1", "2", "0.5", "1.2", "10", "10", "12.5", "1"]]
        self.assertEqual(rec.closed_candles(trade, "X", t0)[0]["vol_quote"], "12.5")

    def test_walk_cost(self):
        asks = [["101", "5"], ["102", "100"]]          # sizes in base units
        usd = lambda px, sz: px * sz
        self.assertAlmostEqual(rec.walk_cost(asks, 505, 100, "buy", usd), 100.0)    # all at 101: 100 bp
        c = rec.walk_cost(asks, 1015, 100, "buy", usd)                                # 505 at 101, 510 at 102
        self.assertAlmostEqual(c, (505 * 0.01 + 510 * 0.02) / 1015 * 1e4, places=2)
        self.assertIsNone(rec.walk_cost(asks, 1e6, 100, "buy", usd))
        bids = [["99", "10"]]
        self.assertAlmostEqual(rec.walk_cost(bids, 500, 100, "sell", usd), 100.0)

    def test_spot_pair_prefers_usdc_then_eur(self):
        self.assertEqual(rec.spot_pair("BTC", {"BTC-EUR", "BTC-USDC"}), "BTC-USDC")
        self.assertEqual(rec.spot_pair("XYZ", {"XYZ-EUR"}), "XYZ-EUR")
        self.assertIsNone(rec.spot_pair("Q", {"Q-USDT"}))


if __name__ == "__main__":
    unittest.main()
