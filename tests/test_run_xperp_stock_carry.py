"""scripts/run_xperp_stock_carry.py (R442): the stock X-Perp book on a synthetic recorder layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_xperp_stock_carry", ROOT / "scripts" / "run_xperp_stock_carry.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)
D = rs.DAY
T0 = rs.rx.ms("2026-09-01")            # a Tuesday
CANDLE_COLS = ["instId", "ts", "o", "h", "l", "c", "vol_quote"]


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, rate_a=0.0001, days=30, a_drop_day=None, index_weekends=True, index_move_day=None):
    """Stock X-Perps A (AAPL, hourly funding), X (DRAM, not on the allowlist, pays more) and M (MSFT, pays little)."""
    ins = [{"instId": "AAPL-X", "instCategory": "3", "ctValCcy": "AAPL", "uly": "AAPL-USD", "ruleType": "xperp"},
           {"instId": "DRAM-X", "instCategory": "3", "ctValCcy": "DRAM", "uly": "DRAM-USD", "ruleType": "xperp"},
           {"instId": "MSFT-X", "instCategory": "3", "ctValCcy": "MSFT", "uly": "MSFT-USD", "ruleType": "xperp"},
           {"instId": "BTC-X", "instCategory": "1", "ctValCcy": "BTC", "uly": "BTC-USD", "ruleType": "xperp"}]
    (root / "instruments").mkdir(parents=True)
    (root / "instruments" / "2026-09-01.json").write_text(json.dumps({"instruments": ins}))
    fr = []
    for k in range(-10 * 24, days * 24):
        t = T0 + k * 3600_000
        ra = rate_a if a_drop_day is None or t <= T0 + a_drop_day * D else -0.00001
        fr += [{"instId": "AAPL-X", "fundingTime": t, "fundingRate": ra, "realizedRate": ra},
               {"instId": "DRAM-X", "fundingTime": t, "fundingRate": 0.0005, "realizedRate": 0.0005},
               {"instId": "MSFT-X", "fundingTime": t, "fundingRate": 0.000001, "realizedRate": 0.000001}]
    write_csv(root / "funding" / "all.csv", ["instId", "fundingTime", "fundingRate", "realizedRate"], fr)
    for kind, names in (("mark_1d", ["AAPL-X", "DRAM-X", "MSFT-X"]), ("trade_1d", ["AAPL-X", "DRAM-X", "MSFT-X"]),
                        ("index_1d", ["AAPL-USD", "DRAM-USD", "MSFT-USD"])):
        rows = []
        for k in range(-12, days + 1):
            ts = T0 + k * D
            if kind == "index_1d" and not index_weekends and pd.Timestamp(ts, unit="ms").weekday() >= 5:
                continue                     # the stock index prints no candle opened on Saturday or Sunday
            c = 100.0
            if kind == "index_1d" and index_move_day is not None and k >= index_move_day:
                c = 102.0
            rows += [{"instId": n, "ts": ts, "o": c, "h": c, "l": c, "c": c,
                      "vol_quote": 1e6 if kind == "trade_1d" else ""} for n in names]
        write_csv(root / kind / "all.csv", CANDLE_COLS, rows)


class StockCarry(unittest.TestCase):
    def test_allowlist_entry_costs_and_funding(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rs.run(d, "2026-09-01", "2026-09-03", books_ok=False)
            self.assertEqual(list(trades.instId), ["AAPL-X"])     # DRAM pays more but is off the allowlist
            w = 1 / (rs.SLOTS * 1.5)
            self.assertAlmostEqual(daily.funding.iloc[1], w * 24 * 0.0001)
            # entry: X-Perp 5 fee + 5 impact, stock 10 fee + 5 impact = 25 bp at 1x
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_1x.iloc[0], w * 25 / 1e4)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_2x.iloc[0], w * 50 / 1e4)

    def test_no_entry_on_sunday_or_monday(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            _, trades = rs.run(d, "2026-09-06", "2026-09-08", books_ok=False)    # Sun, Mon, Tue
            self.assertEqual(list(trades.day), ["2026-09-08"])

    def test_weekend_without_index_candles_keeps_the_position(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), index_weekends=False)
            daily, trades = rs.run(d, "2026-09-01", "2026-09-10", books_ok=False)
            self.assertEqual(len(trades), 1)
            self.assertEqual(int(daily.forced.sum()), 0)
            self.assertTrue((daily.held == 1).all())

    def test_hedge_gain_books_on_the_long_stock(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), index_move_day=3)        # the index candle opened on day 3 closes on day 4 at 102
            daily, _ = rs.run(d, "2026-09-01", "2026-09-06", books_ok=False)
            w = 1 / (rs.SLOTS * 1.5)
            self.assertAlmostEqual(daily[daily.day == "2026-09-05"].price.iloc[0], w * 0.02)

    def test_ordinary_exit_waits_for_an_action_day(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), a_drop_day=0)
            _, trades = rs.run(d, "2026-09-01", "2026-09-20", books_ok=False)
            ex = trades[trades.action == "exit"]
            self.assertEqual(len(ex), 1)
            self.assertIn(pd.Timestamp(ex.day.iloc[0]).weekday(), rs.ACTION_WEEKDAYS)

    def test_gate0_decides_only_a_stop(self):
        self.assertEqual(rs.decide_gate0({"1x": {"excess_ann": -0.001}}), "NULL (stop)")
        self.assertEqual(rs.decide_gate0({"1x": {"excess_ann": 0.0}}), "CONTINUE to gate 1")

    def test_allowlist_size(self):
        self.assertEqual(len(rs.STOCKS), len(set(rs.STOCKS)))
        self.assertEqual(len(rs.STOCKS), 62)


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "xperp_stock_v1" / "PREREG.md").read_text()
        for name in rs.STOCKS:
            self.assertIn(f"`{name}`", text)
        self.assertIn("(D − 7 days, D]", text)
        self.assertIn("signal at least 10%/yr", text)
        self.assertIn("below 5%/yr", text)
        self.assertIn("There are 10 slots", text)
        self.assertIn("at least $100k", text)
        self.assertIn("5 bp on the X-Perp and 10 bp on the stock", text)
        self.assertEqual(rs.FEE_BP, {"xperp": 5.0, "stock": 10.0})
        self.assertIn("5 bp per leg", text)
        self.assertEqual(rs.DEFAULT_IMPACT_BP, 5.0)
        self.assertIn("within 4 days", text)
        self.assertEqual(rs.STALE_DAYS, 4)
        self.assertIn("Tuesday to Saturday", text)
        self.assertEqual(rs.ACTION_WEEKDAYS, (1, 2, 3, 4, 5))
        self.assertIn("4.0%/yr on capital", text)
        self.assertIn("margined at 2x", text)
        self.assertIn("2026-08-20..2026-11-10", text)
        self.assertEqual(rs.WINDOWS, rs.rx.WINDOWS)
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)
        self.assertEqual(rs.LOOKS, rs.rx.LOOKS)
        self.assertIn("lag 10", text)


if __name__ == "__main__":
    unittest.main()
