"""scripts/run_xperp_carry.py (R441): the book on a synthetic recorder layout, offline."""
import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_xperp_carry", ROOT / "scripts" / "run_xperp_carry.py")
rx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rx)
D = rx.DAY
T0 = rx.ms("2026-09-01")


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def layout(root, rate_a=0.0003, rate_b=0.00001, days=30, a_drop_day=None):
    """Two crypto X-Perps A and B (8 h funding), spot A-USDC and B-USDC, flat prices except one move."""
    ins = [{"instId": "A-X", "instCategory": "1", "ctValCcy": "A"},
           {"instId": "B-X", "instCategory": "1", "ctValCcy": "B"}]
    (root / "instruments").mkdir(parents=True)
    (root / "instruments" / "2026-09-01.json").write_text(json.dumps({"instruments": ins}))
    fr = []
    for k in range(-10 * 3, days * 3):
        t = T0 + k * 8 * 3600_000
        ra = rate_a if a_drop_day is None or t <= T0 + a_drop_day * D else -0.0001
        fr += [{"instId": "A-X", "fundingTime": t, "fundingRate": ra, "realizedRate": ra},
               {"instId": "B-X", "fundingTime": t, "fundingRate": rate_b, "realizedRate": rate_b}]
    write_csv(root / "funding" / "all.csv", ["instId", "fundingTime", "fundingRate", "realizedRate"], fr)
    for kind, names in (("mark_1d", ["A-X", "B-X"]), ("trade_1d", ["A-X", "B-X"]), ("spot_1d", ["A-USDC", "B-USDC"])):
        rows = []
        for k in range(-12, days + 1):
            for n in names:
                c = 100.0
                if n == "A-X" and k >= 5:
                    c = 101.0            # the X-Perp mark rises 1% from the close of day 5 + 1
                rows.append({"instId": n, "ts": T0 + k * D, "o": c, "h": c, "l": c, "c": c,
                             "vol_quote": 1e6 if kind == "trade_1d" else ""})
        write_csv(root / kind / "all.csv", rx.__dict__.get("CANDLE_COLS", ["instId", "ts", "o", "h", "l", "c",
                                                                          "vol_quote"]), rows)


class XperpCarry(unittest.TestCase):
    def test_enters_the_high_payer_only_and_books_short_funding(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, trades = rx.run(d, "2026-09-01", "2026-09-04", books_ok=False)
            self.assertEqual(list(trades.instId), ["A-X"])            # B pays ~1%/yr: below the 10% entry
            self.assertEqual(daily.held.tolist(), [1, 1, 1, 1])
            w = 1 / (rx.SLOTS * 1.5)
            # day 2 books the interval 09-01 -> 09-02: three prints of +0.0003, received by the short
            self.assertAlmostEqual(daily.funding.iloc[1], w * 3 * 0.0003)
            self.assertAlmostEqual(daily.price.iloc[1], 0.0)
            # day 1 pays entry costs: (5 + 5) + (10 + 5) bp at 1x, without books
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_1x.iloc[0], w * 25 / 1e4)
            self.assertAlmostEqual(daily.gross.iloc[0] - daily.net_3x.iloc[0], w * 75 / 1e4)

    def test_short_loses_when_the_mark_rises(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d))
            daily, _ = rx.run(d, "2026-09-01", "2026-09-08", books_ok=False)
            w = 1 / (rx.SLOTS * 1.5)
            # the candle opened on day 5 closes on day 6 at 101: the interval ending on 09-07 books -1%
            row = daily[daily.day == "2026-09-07"].iloc[0]
            self.assertAlmostEqual(row.price, -w * 0.01)

    def test_exit_when_trailing_funding_falls(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), a_drop_day=3)
            _, trades = rx.run(d, "2026-09-01", "2026-09-20", books_ok=False)
            ex = trades[trades.action == "exit"]
            self.assertEqual(len(ex), 1)
            # 7-day trailing sum turns below 5%/yr only once enough negative prints are in the window
            self.assertGreater(ex.day.iloc[0], "2026-09-05")

    def test_signal_uses_prints_up_to_the_decision_only(self):
        with tempfile.TemporaryDirectory() as d:
            layout(Path(d), rate_a=0.0, a_drop_day=None)
            p = Path(d) / "funding" / "late.csv"           # a huge print 1 ms after the decision must not count
            write_csv(p, ["instId", "fundingTime", "fundingRate", "realizedRate"],
                      [{"instId": "A-X", "fundingTime": T0 + 1, "fundingRate": 0.05, "realizedRate": 0.05}])
            _, trades = rx.run(d, "2026-09-01", "2026-09-01", books_ok=False)
            self.assertEqual(len(trades), 0)

    def test_summary_and_decision(self):
        import pandas as pd
        n = 90
        daily = pd.DataFrame({"day": [f"d{i}" for i in range(n)], "held": 10, "forced": 0,
                              "funding": 0.0006, "price": 0.0,
                              "net_1x": [0.0005 + (0.0001 if i % 2 else -0.0001) for i in range(n)],
                              "net_2x": 0.0004, "net_3x": 0.0003})
        s = rx.summary(daily)
        self.assertAlmostEqual(s["1x"]["net_ann"], 0.0005 * 365)
        self.assertEqual(rx.decide(s, 90), "EARNED (continue to the 180-day look)")
        daily["net_1x"] = -0.0001
        self.assertEqual(rx.decide(rx.summary(daily), 90), "NULL (stop)")

    def test_looks_are_the_90th_and_180th_forward_days(self):
        import pandas as pd
        start = pd.Timestamp(rx.WINDOWS["forward"][0])
        self.assertEqual(str((start + pd.Timedelta(days=89)).date()), rx.LOOKS[90])
        self.assertEqual(str((start + pd.Timedelta(days=179)).date()), rx.LOOKS[180])



class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "xperp_carry_v1" / "PREREG.md").read_text()
        self.assertIn("(D − 7 days, D]", text)
        self.assertEqual(rx.LOOKBACK_D, 7)
        self.assertIn("signal at least 10%/yr", text)
        self.assertEqual(rx.ENTER_ANN, 0.10)
        self.assertIn("below 5%/yr", text)
        self.assertEqual(rx.EXIT_ANN, 0.05)
        self.assertIn("There are 10 slots", text)
        self.assertEqual(rx.SLOTS, 10)
        self.assertIn("at least $100k", text)
        self.assertEqual(rx.MIN_VOL_USD, 100_000)
        self.assertIn("5 bp on the X-Perp and 10 bp on spot", text)
        self.assertEqual(rx.FEE_BP, {"xperp": 5.0, "spot": 10.0})
        self.assertIn("or 5 bp per leg when none is held", text)
        self.assertEqual(rx.DEFAULT_IMPACT_BP, 5.0)
        self.assertIn("4.0%/yr on capital", text)
        self.assertEqual(rx.HURDLE_ANN, 0.04)
        self.assertIn("margined at 2x", text)
        self.assertEqual(rx.LEVER, 2.0)
        self.assertIn("2026-08-20..2026-11-10", text)
        self.assertEqual(rx.WINDOWS["gate0"], ("2026-08-20", "2026-11-10"))
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)
        self.assertIn("lag 10", text)
        self.assertEqual(rx.NW_LAG, 10)


if __name__ == "__main__":
    unittest.main()
