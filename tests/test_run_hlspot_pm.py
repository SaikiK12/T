"""scripts/run_hlspot_pm.py (R445): R444's carry on HYPE and BTC, fully deployed, on a synthetic layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_hlspot_pm", ROOT / "scripts" / "run_hlspot_pm.py")
pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pm)
D = pm.DAY
T0 = pm.rx.ms("2025-03-01")
CANDLE_COLS = ["coin", "ts", "o", "h", "l", "c", "vol_base"]
BP = (4.5 + 7.0 + 5.0 + 10.0) / 1e4          # both legs, one side each, per unit of notional


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, rates=None, start_hour=None, drop=None, days=30, spot_move=None):
    """Perps BTC (@142), HYPE (@107) and ETH (@151), hourly prints rates[coin] from start_hour[coin] (hours from T0);
    drop = (coin, day): that coin pays 0 after the day; spot_move = (pair, day): that spot closes at 101 from the
    candle opened on that day."""
    rates = rates or {"BTC": 0.00002, "HYPE": 0.00002, "ETH": 0.00005}     # 0.00002/h = 17.5%/yr
    start_hour = start_hour or {}
    h = root / "hl_spot"
    h.mkdir(parents=True)
    (h / "pairs.json").write_text(json.dumps({"pairs": {"@142": {"token": "UBTC", "perp": "BTC"},
                                                        "@107": {"token": "HYPE", "perp": "HYPE"},
                                                        "@151": {"token": "UETH", "perp": "ETH"}}}))
    fr = []
    for coin, r in rates.items():
        for k in range(start_hour.get(coin, -10 * 24), days * 24):
            t = T0 + k * 3600_000
            rr = 0.0 if drop and drop[0] == coin and t > T0 + drop[1] * D else r
            fr.append({"coin": coin, "time": t, "rate": rr})
    write_csv(h / "funding" / "all.csv", ["coin", "time", "rate"], fr)
    pc, sc = [], []
    for k in range(-12, days + 1):
        for perp, pair in (("BTC", "@142"), ("HYPE", "@107"), ("ETH", "@151")):
            pc.append({"coin": perp, "ts": T0 + k * D, "o": 100, "h": 100, "l": 100, "c": 100, "vol_base": 1e4})
            c = 101.0 if spot_move and spot_move[0] == pair and k >= spot_move[1] else 100.0
            sc.append({"coin": pair, "ts": T0 + k * D, "o": c, "h": c, "l": c, "c": c, "vol_base": 1e4})
    write_csv(h / "perp_1d" / "all.csv", CANDLE_COLS, pc)
    write_csv(h / "spot_1d" / "all.csv", CANDLE_COLS, sc)


class HLSpotPM(unittest.TestCase):
    def test_only_hype_and_btc_and_full_deployment(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = pm.run(d, "2025-03-01", "2025-03-03")
            self.assertEqual(sorted(trades.perp), ["BTC", "HYPE"])       # ETH pays more but is not in the universe
            w = 1 / (2 * 1.1)                                              # two pairs held, capital 1.1 per notional
            self.assertAlmostEqual(daily.turnover.iloc[0], 2 * w)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_1x.iloc[0], 2 * w * BP)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_3x.iloc[0], 3 * 2 * w * BP)
            self.assertAlmostEqual(daily.funding.iloc[1], 2 * w * 24 * 0.00002)
            self.assertEqual(daily.turnover.iloc[1], 0.0)

    def test_no_pm_capital_is_one_and_a_half(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, _ = pm.run(d, "2025-03-01", "2025-03-03", capital="no_pm")
            self.assertAlmostEqual(daily.funding.iloc[1], 2 * (1 / (2 * 1.5)) * 24 * 0.00002)

    def test_a_second_entry_reweights_and_is_costed(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), start_hour={"HYPE": 0})          # HYPE's 7-day lookback is complete on 2025-03-08
            daily, trades = pm.run(d, "2025-03-01", "2025-03-10")
            ent = trades[trades.action == "enter"].set_index("perp").day
            self.assertEqual(ent["BTC"], "2025-03-01")
            self.assertEqual(ent["HYPE"], "2025-03-08")
            row = daily[daily.day == "2025-03-08"].iloc[0]
            one, two = 1 / 1.1, 1 / 2.2
            self.assertAlmostEqual(row.turnover, (one - two) + two)       # trim BTC, add HYPE
            self.assertAlmostEqual(row.funding, one * 24 * 0.00002)        # booked at yesterday's weight
            nxt = daily[daily.day == "2025-03-09"].iloc[0]
            self.assertAlmostEqual(nxt.funding, 2 * two * 24 * 0.00002)

    def test_exit_returns_the_capital_to_the_pair_left(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), drop=("HYPE", 2))
            daily, trades = pm.run(d, "2025-03-01", "2025-03-20")
            ex = trades[trades.action == "exit"]
            self.assertEqual(list(ex.perp), ["HYPE"])
            row = daily[daily.day == ex.day.iloc[0]].iloc[0]
            self.assertAlmostEqual(row.turnover, 1 / 2.2 + (1 / 1.1 - 1 / 2.2))
            self.assertEqual(int(daily.held.iloc[-1]), 1)

    def test_price_sign_long_spot(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), spot_move=("@107", 3))        # the HYPE spot candle opened on day 3 closes on day 4 at 101
            daily, _ = pm.run(d, "2025-03-01", "2025-03-06")
            self.assertAlmostEqual(daily[daily.day == "2025-03-05"].price.iloc[0], (1 / 2.2) * 0.01)

    def test_a_window_before_its_first_day_still_summarizes(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = pm.run(d, "2025-03-05", "2025-03-04")
            s = pm.rx.summary(daily)
            self.assertEqual((s["days"], len(trades)), (0, 0))
            self.assertEqual(pm.decide_gate0(s), "NULL (stop)")

    def test_gate0_stops_only_below_zero(self):
        self.assertEqual(pm.decide_gate0({"1x": {"excess_ann": 0.001}}), "CONTINUE to gate 1")
        self.assertEqual(pm.decide_gate0({"1x": {"excess_ann": -0.001}}), "NULL (stop)")


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "hlspot_pm_v1" / "PREREG.md").read_text()
        self.assertEqual(pm.PERPS, ("HYPE", "BTC"))
        self.assertIn("HYPE (spot pair @107) and BTC (spot pair @142, UBTC)", text)
        self.assertEqual((pm.LOOKBACK_D, pm.ENTER_ANN, pm.EXIT_ANN, pm.MIN_VOL_USD), (7, 0.10, 0.05, 100_000))
        self.assertIn("(D − 7 days, D]", text)
        self.assertIn("at least 10%/yr", text)
        self.assertIn("below 5%/yr", text)
        self.assertIn("at least $100k", text)
        self.assertEqual(pm.BUFFER, 0.10)
        self.assertIn("capital is N × 1.1", text)
        self.assertEqual(pm.CAPITAL_PER_NOTIONAL["no_pm"], 1.5)
        self.assertIn("N × 1.5", text)
        self.assertEqual(pm.FEE_BP, {"perp": 4.5, "spot": 7.0})
        self.assertIn("4.5 bp on the perp and 7.0 bp on spot", text)
        self.assertEqual(pm.IMPACT_BP, {"perp": 5.0, "spot": 10.0})
        self.assertIn("5 bp on the perp and 10 bp on spot", text)
        self.assertEqual(pm.HURDLE_ANN, 0.04)
        self.assertIn("4.0%/yr on capital", text)
        self.assertEqual(pm.WINDOWS["gate0"], ("2025-01-01", "2026-11-10"))
        self.assertIn("2025-01-01..2026-11-10", text)
        self.assertEqual(pm.LOOKS, pm.rx.LOOKS)
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)
        self.assertIn("lag 10", text)


if __name__ == "__main__":
    unittest.main()
