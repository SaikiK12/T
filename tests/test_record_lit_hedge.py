"""scripts/record_lit_hedge.py (R447): LIT perp funding and LIT candles on fake Lighter answers, offline."""
import csv
import importlib.util
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("record_lit_hedge", ROOT / "scripts" / "record_lit_hedge.py")
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)
D, H = rl.DAY, rl.HOUR
NOW = rl.START_MS + 3 * D + 5 * H


def fake_get(url):
    path, q = url.split("?")
    q = dict(urllib.parse.parse_qsl(q))
    if path.endswith("/fundings"):
        assert q["market_id"] == str(rl.PERP) and q["resolution"] == "1h"
        a, b = int(q["start_timestamp"]), int(q["end_timestamp"])          # seconds
        return {"fundings": [{"timestamp": t, "rate": "0.0010", "value": "0.00003",
                              "direction": "long" if (t // 3600) % 2 else "short"}
                             for t in range(a - a % 3600, b, 3600) if t * 1000 >= rl.START_MS]}
    if path.endswith("/candles"):
        mid = int(q["market_id"])
        return {"c": [{"t": rl.START_MS + k * D, "o": 2, "h": 2.2, "l": 1.9, "c": 2.1 + mid / 10 ** 5, "v": 1, "V": 2}
                      for k in range(4)]}
    raise AssertionError(url)


def read(folder):
    return [r for p in sorted(folder.glob("*.csv")) for r in csv.DictReader(open(p, newline=""))]


class Record(unittest.TestCase):
    def test_writes_funding_with_sign_and_finished_bars_only(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            s = rl.record(out, now_ms=NOW, get=fake_get, pause=0)
            self.assertEqual(s["failed"], [])
            f = read(out / "perp_funding")
            self.assertEqual(len(f), (NOW - rl.START_MS) // H)
            for r in f:
                self.assertAlmostEqual(float(r["rate"]), 0.00001 if r["direction"] == "long" else -0.00001)
            self.assertEqual(len({r["ts"] for r in f}), len(f))
            perp, spot = read(out / "perp_candles_1d"), read(out / "spot_candles_1d")
            self.assertEqual(len(perp), 3)                                   # the fourth bar is not finished
            self.assertNotEqual(perp[0]["close"], spot[0]["close"])          # each market's own bars
            s2 = rl.record(out, now_ms=NOW, get=fake_get, pause=0)
            self.assertEqual((s2["funding"], s2["perp_candles"], s2["spot_candles"]), (0, 0, 0))   # idempotent

    def test_one_failure_does_not_stop_the_others(self):
        def half(url):
            if "/fundings" in url:
                raise OSError("down")
            return fake_get(url)
        with tempfile.TemporaryDirectory() as d:
            s = rl.record(Path(d), now_ms=NOW, get=half, pause=0)
            self.assertEqual(s["failed"], ["funding"])
            self.assertEqual(s["perp_candles"], 3)


if __name__ == "__main__":
    unittest.main()
