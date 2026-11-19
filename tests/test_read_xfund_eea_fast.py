import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import read_xfund_eea_fast as fast


def journal(lane, days):
    """R509-shaped journal: one ontime decision per day, one entry on the first day, flat funding, no price move."""
    j = lane / "journal"
    j.mkdir(parents=True)
    run = "r1"
    pd.DataFrame([{"run": run, "day": d, "book": "A", "kind": "ontime", "exits": 0, "entries": int(i == 0),
                   "held": 1, "ready": "{}"} for i, d in enumerate(days)]).to_csv(j / "decisions.csv", index=False)
    t = {"run": run, "day": days[0], "book": "A", "action": "enter", "coin": "X", "long": "kraken",
         "short": "hyperliquid", "spread_ann": "1", "forced": "false", "kind": "ontime", "close_long": "1",
         "close_short": "1", "fill_long": "1", "fill_short": "1"}
    pd.DataFrame([t]).to_csv(j / "tickets.csv", index=False)
    rows = []
    for i, d in enumerate(days[1:]):
        legs = 2.0 if i == 0 else 0.0
        rows.append({"day": d, "book": "A", "kind": "ontime", "run": run, "held": 1, "legs": legs,
                     "gross": 0.0005, "funding": 0.0005, "fill_adj": 0, "net": 0.0005 - 0.0007 * legs / 40,
                     "net_2x": 0, "net_3x": 0, "net_close": 0, "net_close_2x": 0, "net_close_3x": 0})
    pd.DataFrame(rows).to_csv(j / "days.csv", index=False)
    pd.DataFrame([{"run": run, "day": days[0], "book": "A", "action": "enter", "coin": "X", "venue": v,
                   "symbol": "S", "side": "buy", "utc": "", "mid": 1, "fill_1000": 1, "cost_bp_1000": 10.0,
                   "fill_2500": "", "cost_bp_2500": ""} for v in ("kraken", "hyperliquid")]).to_csv(
        j / "book_fills.csv", index=False)


class FastRead(unittest.TestCase):
    def test_funding_net_of_measured_costs(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp)
            days = [str(d.date()) for d in pd.date_range("2026-11-19", periods=32)]
            journal(lane, days)
            s = fast.series(lane)
            self.assertEqual(len(s), 31)
            c = ((10 + 5.0) + (10 + 4.5)) / 1e4 / 40                     # both legs' measured cost + fees, per capital
            self.assertAlmostEqual(s.fund_book.iloc[0], 0.0005 - c)
            self.assertAlmostEqual(s.fund_book.iloc[1], 0.0005)
            self.assertAlmostEqual(abs(s.price).max(), 0.0, places=12)   # no price move, no fill gap
            self.assertEqual(fast.read(s, 1)["verdict"], "PASS")       # constant funding: t is infinite or huge
            self.assertTrue(fast.read(s.iloc[:10], 1)["verdict"].startswith("NOT DUE"))

    def test_negative_funding_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp)
            days = [str(d.date()) for d in pd.date_range("2026-11-19", periods=32)]
            journal(lane, days)
            d = pd.read_csv(lane / "journal" / "days.csv")
            d["funding"] = -0.0002
            d["gross"] = -0.0002
            d.to_csv(lane / "journal" / "days.csv", index=False)
            self.assertEqual(fast.read(fast.series(lane), 1)["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
