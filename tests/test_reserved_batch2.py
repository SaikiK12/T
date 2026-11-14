"""R391 reserved batch 2: the symbol table builder (contract lists and file names only) and the decision rule."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import decide_reserved_batch2 as dec  # noqa: E402
import reserved_venue_table as tab  # noqa: E402


def touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def contracts(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, ["symbol", "base", "route"])
        w.writeheader()
        w.writerows(rows)


class TableTests(unittest.TestCase):
    def test_rows_need_two_venues_one_reserved_and_skip_mexc_only(self):
        with tempfile.TemporaryDirectory() as t:
            data, root = Path(t) / "data", Path(t) / "root"
            contracts(data / "kucoin_hist/contracts.csv", [
                {"symbol": "AAAUSDTM", "base": "AAA", "route": "reserved"},
                {"symbol": "BBBUSDTM", "base": "BBB", "route": "reserved"},
                {"symbol": "ZZZUSDTM", "base": "ZZZ", "route": "reserved"},      # no files: dropped
                {"symbol": "XBTUSDTM", "base": "BTC", "route": "open"}])         # open: never in the table
            for s in ("AAAUSDTM", "BBBUSDTM"):
                touch(data / f"kucoin_hist/reserved/candles_1d/{s}.parquet")
                touch(data / f"kucoin_hist/reserved/funding/{s}.parquet")
            for v in ("dydx", "lighter"):
                contracts(data / f"{v}_hist/contracts.csv", [{"symbol": "CCC", "base": "CCC", "route": "reserved"}])
                touch(data / f"{v}_hist/reserved/candles_1h/CCC.parquet")
                touch(data / f"{v}_hist/reserved/funding/CCC.parquet")
            for s in ("AAA_USDT", "BBB_USDT", "BTC_USDT", "ZZZ_USDT"):
                touch(data / f"mexc_hist/klines_1h/{s}.parquet")
                touch(data / f"mexc_hist/funding/{s}.parquet")
            (root / "experiments/unlocks_v1").mkdir(parents=True)
            with open(root / "experiments/unlocks_v1/events.csv", "w", newline="") as f:
                w = csv.DictWriter(f, ["perp", "window"])
                w.writeheader()
                w.writerow({"perp": "BBB_USDT", "window": "reserved_mexc"})
            rows = tab.build(data, root)
        self.assertEqual([r["key"] for r in rows], ["AAA", "CCC"])      # BBB: its MEXC contract is MEXC-only
        self.assertEqual(rows[0], {"key": "AAA", "kucoin": "AAAUSDTM", "dydx": "", "lighter": "", "mexc": "AAA_USDT"})
        self.assertEqual(rows[1]["dydx"], "CCC")
        self.assertEqual(rows[1]["lighter"], "CCC")


class DecideTests(unittest.TestCase):
    base = {"n": 400, "p_one_sided": 0.01, "mean_2x_bp": 0.5, "trimmed_mean_bp": 0.3, "l2co_mean_bp": 0.2}

    def test_pass_needs_every_check(self):
        self.assertEqual(dec.decide(self.base)[0], "PASS")
        for k, bad in (("p_one_sided", 0.06), ("mean_2x_bp", -0.1), ("trimmed_mean_bp", 0.0), ("l2co_mean_bp", -1)):
            v, checks = dec.decide({**self.base, k: bad})
            self.assertEqual(v, "FAIL", k)
            self.assertEqual(sum(not x for x in checks.values()), 1)

    def test_unreadable_below_sixty_days(self):
        self.assertEqual(dec.decide({**self.base, "n": 59})[0], "UNREADABLE")


if __name__ == "__main__":
    unittest.main()
