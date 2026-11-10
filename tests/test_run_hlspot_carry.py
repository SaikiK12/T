"""scripts/run_hlspot_carry.py (R444): the Hyperliquid spot-against-perp book on a synthetic layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_hlspot_carry", ROOT / "scripts" / "run_hlspot_carry.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)
D = rs.DAY
T0 = rs.rx.ms("2025-03-01")
CANDLE_COLS = ["coin", "ts", "o", "h", "l", "c", "vol_base"]


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, rate=0.00002, days=30, drop_day=None, spot_move_day=None, spot_vol=1e4):
    """BTC perp (hourly prints `rate`, 0.00002 = 17.5%/yr) against spot pair @142; ETH perp at 0.000001 (0.9%/yr)."""
    h = root / "hl_spot"
    h.mkdir(parents=True)
    (h / "pairs.json").write_text(json.dumps({"pairs": {"@142": {"token": "UBTC", "perp": "BTC"},
                                                        "@151": {"token": "UETH", "perp": "ETH"}}}))
    fr = []
    for k in range(-10 * 24, days * 24):
        t = T0 + k * 3600_000
        r = rate if drop_day is None or t <= T0 + drop_day * D else 0.0
        fr += [{"coin": "BTC", "time": t, "rate": r}, {"coin": "ETH", "time": t, "rate": 0.000001}]
    write_csv(h / "funding" / "all.csv", ["coin", "time", "rate"], fr)
    pc, sc = [], []
    for k in range(-12, days + 1):
        for perp, pair in (("BTC", "@142"), ("ETH", "@151")):
            pc.append({"coin": perp, "ts": T0 + k * D, "o": 100, "h": 100, "l": 100, "c": 100, "vol_base": 1e4})
            c = 101.0 if (pair == "@142" and spot_move_day is not None and k >= spot_move_day) else 100.0
            sc.append({"coin": pair, "ts": T0 + k * D, "o": c, "h": c, "l": c, "c": c, "vol_base": spot_vol})
    write_csv(h / "perp_1d" / "all.csv", CANDLE_COLS, pc)
    write_csv(h / "spot_1d" / "all.csv", CANDLE_COLS, sc)


class HLSpotCarry(unittest.TestCase):
    def test_entry_funding_and_costs(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rs.run(d, "2025-03-01", "2025-03-03")
            self.assertEqual(list(trades.perp), ["BTC"])               # ETH pays ~0.9%/yr: below 10%
            w = 1 / (rs.SLOTS * 1.5)
            self.assertAlmostEqual(daily.funding.iloc[1], w * 24 * 0.00002)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_1x.iloc[0], w * (4.5 + 7 + 5 + 10) / 1e4)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_3x.iloc[0], 3 * w * 26.5 / 1e4)

    def test_price_sign_long_spot(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), spot_move_day=3)        # the spot candle opened on day 3 closes on day 4 at 101
            daily, _ = rs.run(d, "2025-03-01", "2025-03-06")
            w = 1 / (rs.SLOTS * 1.5)
            self.assertAlmostEqual(daily[daily.day == "2025-03-05"].price.iloc[0], w * 0.01)

    def test_exit_when_funding_falls(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), drop_day=2)
            _, trades = rs.run(d, "2025-03-01", "2025-03-20")
            ex = trades[trades.action == "exit"]
            self.assertEqual(len(ex), 1)
            self.assertGreater(ex.day.iloc[0], "2025-03-03")

    def test_spot_volume_filter(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), spot_vol=900)            # 900 x $100 = $90k < $100k
            _, trades = rs.run(d, "2025-03-01", "2025-03-05")
            self.assertEqual(len(trades), 0)

    def test_a_window_before_its_first_day_still_summarizes(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rs.run(d, "2025-03-05", "2025-03-04")
            s = rs.rx.summary(daily)
            self.assertEqual((s["days"], len(trades)), (0, 0))
            self.assertEqual(rs.decide_gate0(s), "NULL (stop)")

    def test_gate0_stops_only_below_zero(self):
        self.assertEqual(rs.decide_gate0({"1x": {"excess_ann": 0.001}}), "CONTINUE to gate 1")
        self.assertEqual(rs.decide_gate0({"1x": {"excess_ann": -0.001}}), "NULL (stop)")


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "hlspot_carry_v1" / "PREREG.md").read_text()
        self.assertIn("(D − 7 days, D]", text)
        self.assertIn("at least 10%/yr", text)
        self.assertIn("below 5%/yr", text)
        self.assertIn("There are 10 slots", text)
        self.assertIn("at least $100k", text)
        self.assertEqual(rs.FEE_BP, {"perp": 4.5, "spot": 7.0})
        self.assertIn("4.5 bp on the perp and 7.0 bp on spot", text)
        self.assertEqual(rs.IMPACT_BP, {"perp": 5.0, "spot": 10.0})
        self.assertIn("5 bp on the perp and 10 bp on spot", text)
        self.assertEqual(rs.LEVER, 2.0)
        self.assertIn("margined at 2x", text)
        self.assertIn("4.0%/yr on capital", text)
        self.assertEqual(rs.WINDOWS["gate0"], ("2025-01-01", "2026-11-10"))
        self.assertIn("2025-01-01..2026-11-10", text)
        self.assertEqual(rs.LOOKS, rs.rx.LOOKS)
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)
        self.assertIn("lag 10", text)


if __name__ == "__main__":
    unittest.main()
