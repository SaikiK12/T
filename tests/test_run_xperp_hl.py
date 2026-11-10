"""scripts/run_xperp_hl.py (R443): the OKX X-Perp / Hyperliquid book on a synthetic layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_xperp_hl", ROOT / "scripts" / "run_xperp_hl.py")
rh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rh)
D = rh.DAY
T0 = rh.rx.ms("2026-09-01")
CANDLE_COLS = ["instId", "ts", "o", "h", "l", "c", "vol_quote"]


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, hl_rate=0.00002, days=30, hl_drop_day=None, okx_move_day=None):
    """A-X (OKX, 8 h prints 0.00001 = ~1%/yr) vs HL coin A (hourly prints hl_rate = ~17.5%/yr at 0.00002);
    B-X pays more on OKX (8 h 0.0002 = ~22%/yr) than HL kB (hourly 0.000001)."""
    ins = [{"instId": "A-X", "instCategory": "1", "ctValCcy": "A"},
           {"instId": "B-X", "instCategory": "1", "ctValCcy": "B"}]
    (root / "instruments").mkdir(parents=True)
    (root / "instruments" / "2026-09-01.json").write_text(json.dumps({"instruments": ins}))
    fr = []
    for k in range(-10 * 3, days * 3):
        t = T0 + k * 8 * 3600_000
        fr += [{"instId": "A-X", "fundingTime": t, "fundingRate": 0.00001, "realizedRate": 0.00001},
               {"instId": "B-X", "fundingTime": t, "fundingRate": 0.0002, "realizedRate": 0.0002}]
    write_csv(root / "funding" / "all.csv", ["instId", "fundingTime", "fundingRate", "realizedRate"], fr)
    for kind in ("mark_1d", "trade_1d"):
        rows = []
        for k in range(-12, days + 1):
            for n in ("A-X", "B-X"):
                c = 101.0 if (n == "A-X" and okx_move_day is not None and k >= okx_move_day) else 100.0
                rows.append({"instId": n, "ts": T0 + k * D, "o": c, "h": c, "l": c, "c": c,
                             "vol_quote": 1e6 if kind == "trade_1d" else ""})
        write_csv(root / kind / "all.csv", CANDLE_COLS, rows)
    hf = []
    for k in range(-10 * 24, days * 24):
        t = T0 + k * 3600_000
        ra = hl_rate if hl_drop_day is None or t <= T0 + hl_drop_day * D else 0.0
        hf += [{"coin": "A", "time": t, "rate": ra}, {"coin": "kB", "time": t, "rate": 0.000001}]
    write_csv(root / "hl" / "funding" / "all.csv", ["coin", "time", "rate"], hf)
    hc = [{"coin": c, "ts": T0 + k * D, "o": 50, "h": 50, "l": 50, "c": 50, "vol_base": 1e5}
          for k in range(-12, days + 1) for c in ("A", "kB")]
    write_csv(root / "hl" / "candles_1d" / "all.csv", ["coin", "ts", "o", "h", "l", "c", "vol_base"], hc)
    (root / "hl" / "coins.json").write_text(json.dumps({"coins": {"A": "A", "kB": "B"}}))


class XperpHL(unittest.TestCase):
    def test_directions_funding_and_costs(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rh.run(d, "2026-09-01", "2026-09-03", books_ok=False)
            dirs = dict(zip(trades.instId, trades.direction))
            self.assertEqual(dirs, {"A-X": "hl_short", "B-X": "okx_short"})
            w = 1 / (rh.SLOTS * 1.0)
            # day 2: A: HL 24 x 0.00002 received, OKX 3 x 0.00001 paid; B: OKX 3 x 0.0002 received, HL 24 x 1e-6 paid
            want = w * ((24 * 0.00002 - 3 * 0.00001) + (3 * 0.0002 - 24 * 0.000001))
            self.assertAlmostEqual(daily.funding.iloc[1], want)
            # two entries on day 1: (5 + 5) + (4.5 + 5) bp each at 1x
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_1x.iloc[0], 2 * w * 19.5 / 1e4)

    def test_price_sign_long_okx_leg(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), okx_move_day=3)      # A-X mark candle opened on day 3 closes on day 4 at 101
            daily, _ = rh.run(d, "2026-09-01", "2026-09-06", books_ok=False)
            w = 1 / rh.SLOTS
            self.assertAlmostEqual(daily[daily.day == "2026-09-05"].price.iloc[0], w * 0.01)   # A: long OKX

    def test_exit_when_the_spread_collapses(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), hl_drop_day=2)
            _, trades = rh.run(d, "2026-09-01", "2026-09-20", books_ok=False)
            ex = trades[(trades.action == "exit") & (trades.instId == "A-X")]
            self.assertEqual(len(ex), 1)
            self.assertGreater(ex.day.iloc[0], "2026-09-03")

    def test_no_print_after_the_decision_counts(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), hl_rate=0.0)
            write_csv(Path(d) / "hl" / "funding" / "late.csv", ["coin", "time", "rate"],
                      [{"coin": "A", "time": T0 + 1, "rate": 0.5}])
            _, trades = rh.run(d, "2026-09-01", "2026-09-01", books_ok=False)
            self.assertNotIn("A-X", set(trades.instId))

    def test_a_window_before_its_first_day_still_summarizes(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rh.run(d, "2026-09-05", "2026-09-04", books_ok=False)
            self.assertEqual((len(daily), len(trades)), (0, 0))
            s = rh.rx.summary(daily)
            self.assertEqual(s["days"], 0)
            self.assertIsNone(s["1x"]["excess_ann"])


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "xperp_hl_v1" / "PREREG.md").read_text()
        self.assertIn("(D − 7 days, D]", text)
        self.assertIn("at least 10%/yr", text)
        self.assertIn("below 5%/yr", text)
        self.assertIn("There are 10 slots", text)
        self.assertIn("at least $100k", text)
        self.assertIn("5 bp on OKX and 4.5 bp on Hyperliquid", text)
        self.assertEqual(rh.FEE_BP, {"okx": 5.0, "hl": 4.5})
        self.assertIn("5 bp per leg", text)
        self.assertEqual(rh.DEFAULT_IMPACT_BP, 5.0)
        self.assertIn("margined at 2x", text)
        self.assertEqual(rh.LEVER, 2.0)
        self.assertIn("4.0%/yr on capital", text)
        self.assertIn("2026-08-20..2026-11-10", text)
        self.assertEqual(rh.WINDOWS, rh.rx.WINDOWS)
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)
        self.assertEqual(rh.LOOKS, rh.rx.LOOKS)
        self.assertIn("lag 10", text)


if __name__ == "__main__":
    unittest.main()
