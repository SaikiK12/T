"""scripts/record_hl_daily.py: coin matching and closed candles, offline."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_hl_daily", ROOT / "scripts" / "record_hl_daily.py")
hl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hl)


class RecordHL(unittest.TestCase):
    def test_match_plain_and_k_coins(self):
        m = hl.match({"BTC", "kPEPE", "kBONK", "ETH", "HYPE", "kaito"}, {"BTC", "PEPE", "ETH", "kaito"})
        self.assertEqual(m, {"BTC": "BTC", "ETH": "ETH", "kPEPE": "PEPE", "kaito": "kaito"})

    def test_okx_bases_from_newest_listing_crypto_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "instruments"
            p.mkdir()
            (p / "2026-11-09.json").write_text(json.dumps({"instruments": [
                {"instCategory": "1", "ctValCcy": "OLD"}]}))
            (p / "2026-11-10.json").write_text(json.dumps({"instruments": [
                {"instCategory": "1", "ctValCcy": "BTC"}, {"instCategory": "3", "ctValCcy": "AAPL"}]}))
            self.assertEqual(hl.okx_bases(d), {"BTC"})

    def test_only_closed_daily_candles(self):
        day = hl.DAY
        raw = [{"t": 0, "o": "1", "h": "2", "l": "0.5", "c": "1.5", "v": "10"},
               {"t": day, "o": "1.5", "h": "2", "l": "1", "c": "1.8", "v": "12"}]
        rows = hl.closed_candles(raw, "BTC", now_ms=2 * day - 1)
        self.assertEqual([r["ts"] for r in rows], [0])
        self.assertEqual(rows[0]["vol_base"], "10")


if __name__ == "__main__":
    unittest.main()
