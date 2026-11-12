"""rollcarry_v1 (M532): marks, candle choice, accounting, roll-ups, liquidation, cycles and verdicts on synthetic
data (no market data)."""
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import run_rollcarry as rc  # noqa: E402

H = rc.HOUR


def book(lo, hi, fund=20.0, perp=3.0, rate=0.0, irx=4.0, hourly=True):
    """Fund closes lo..hi; perp candles (1 h, or 4 h only) and hourly funding (50 ms after the hour)."""
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(lo, hi)]
    e = pd.DataFrame({"date": days, "close": fund, "adjclose": fund})
    a = rc.mark_ms(days[0]) - 48 * H
    a -= a % (4 * H)
    b = rc.mark_ms(days[-1]) + 48 * H
    h1 = np.arange(a, b, H, dtype=np.int64)
    h4 = np.arange(a, b, 4 * H, dtype=np.int64)
    c1 = pd.DataFrame({"open_ms": h1, "open": perp, "high": perp, "low": perp, "close": perp}) if hourly else \
        pd.DataFrame(columns=["open_ms", "open", "high", "low", "close"])
    c4 = pd.DataFrame({"open_ms": h4, "open": perp, "high": perp, "low": perp, "close": perp})
    f = pd.DataFrame({"time": h1 + 50, "fundingRate": rate, "premium": 0.0})
    i = pd.DataFrame({"date": days, "close": irx, "adjclose": irx})
    return e, c1, c4, f, i


def set_from(frame, col, start, value, cols=("open", "high", "low", "close")):
    frame.loc[frame[col] >= start, [k for k in cols if k in frame]] = value


class MarkTest(unittest.TestCase):
    def test_new_york_close_follows_dst(self):
        summer = datetime.fromtimestamp(rc.mark_ms("2026-07-01") / 1000, timezone.utc)
        winter = datetime.fromtimestamp(rc.mark_ms("2026-01-15") / 1000, timezone.utc)
        self.assertEqual((summer.hour, summer.minute), (20, 0))
        self.assertEqual((winter.hour, winter.minute), (21, 0))

    def test_price_prefers_the_hour_ending_at_the_mark(self):
        c1 = pd.DataFrame({"open_ms": [0, H, 2 * H], "close": [1.0, 2.0, 3.0]})
        c4 = pd.DataFrame({"open_ms": [-4 * H, 0], "close": [7.0, 9.0]})
        self.assertEqual(rc.price_at(c1, c4, 2 * H), (2.0, "1h"))       # the 1 h candle H..2H
        self.assertEqual(rc.price_at(c1, c4, 5 * H), (9.0, "4h"))       # no 1 h candle ends at 5H; 4 h 0..4H did
        self.assertTrue(np.isnan(rc.price_at(c1, c4, 9 * H)[0]))        # the last 4 h candle ended 5 h earlier
        self.assertTrue(np.isnan(rc.price_at(c1, c4, -1)[0]))


class AccountingTest(unittest.TestCase):
    def test_flat_prices_earn_funding_less_costs(self):
        r = 1e-5
        e, c1, c4, f, i = book("2026-08-03", "2026-08-28", rate=r)
        d = rc.simulate("NATGAS", e, c1, c4, f, i, "2026-08-03", "2026-08-28")
        v0, usdc0 = 1 / (1 + rc.M), 1 - 1 / (1 + rc.M)
        entry = (rc.FUND_BP * v0 + rc.LEG_BP * v0 + rc.XFER_BP * usdc0) / 1e4
        hours = (rc.mark_ms("2026-08-28") - rc.mark_ms("2026-08-03")) // H
        fund = r * v0 * hours
        usdc = usdc0 - entry + fund
        exit_ = (rc.FUND_BP * v0 + rc.LEG_BP * v0 + rc.XFER_BP * usdc) / 1e4
        self.assertAlmostEqual(d["fund"].sum(), fund, places=12)
        self.assertAlmostEqual(d["equity"].iloc[-1], 1 - entry + fund - exit_, places=12)
        self.assertEqual(int(d["resplit"].sum()), 1)
        self.assertEqual(int(d["liq"].sum()), 0)

    def test_roll_up_costs_the_short_and_not_the_fund(self):
        e, c1, c4, f, i = book("2026-08-03", "2026-08-21")
        set_from(c1, "open_ms", rc.mark_ms("2026-08-12") - H, 3.15)  # the oracle passes a 5% spread to the perp
        d = rc.simulate("NATGAS", e, c1, c4, f, i, "2026-08-03", "2026-08-21")
        u = 1 / (1 + rc.M) / 3.0
        self.assertAlmostEqual(d["perp_pnl"].sum(), -u * 0.15, places=12)
        self.assertAlmostEqual(d["etf_pnl"].sum(), 0.0, places=12)
        self.assertEqual(int(d["liq"].sum()), 0)

    def test_spike_liquidates_the_isolated_margin(self):
        e, c1, c4, f, i = book("2026-08-03", "2026-08-21", rate=1e-5)
        k = int(np.searchsorted(c1["open_ms"].to_numpy(), rc.mark_ms("2026-08-12") - 5 * H))
        c1.loc[k, "high"] = 3.0 * 1.35                                   # one hourly high 35% up, then back
        d = rc.simulate("NATGAS", e, c1, c4, f, i, "2026-08-03", "2026-08-21")
        row = d[d["date"] == "2026-08-12"].iloc[0]
        self.assertEqual(int(row["liq"]), 1)
        self.assertEqual(int(row["resplit"]), 1)
        usdc_before = d[d["date"] == "2026-08-11"]["equity"].iloc[0] - 1 / (1 + rc.M)
        self.assertAlmostEqual(row["perp_pnl"], -usdc_before, places=9)
        self.assertGreater(row["fund"], 0)                               # funding up to the breach is kept
        self.assertEqual(int(d["liq"].sum()), 1)

    def test_four_hour_fallback_marks_before_hourly_history(self):
        e, c1, c4, f, i = book("2026-02-02", "2026-02-13", hourly=False)
        d = rc.simulate("CL", e, c1, c4, f, i, "2026-02-02", "2026-02-13")
        self.assertEqual(set(d["src"]), {"4h"})
        self.assertEqual(d.attrs["missing_marks"], 0)


class CycleVerdictTest(unittest.TestCase):
    def test_tenth_business_day_follows_the_documented_rolls(self):
        # trade.xyz roll windows end on business day 9 at 17:30 ET: 2026-07-14, 10-13, 11-12, 2027-01-14
        self.assertEqual(rc.bdays(2026, 7)[9], "2026-07-15")
        self.assertEqual(rc.bdays(2026, 10)[9], "2026-10-14")
        self.assertEqual(rc.bdays(2026, 11)[9], "2026-11-13")
        self.assertEqual(rc.bdays(2026, 4)[8], "2026-04-14")            # Good Friday is not a business day
        self.assertEqual(rc.bdays(2026, 9)[8], "2026-09-14")            # nor is Labor Day

    def test_cycles_sum_the_legs(self):
        e, c1, c4, f, i = book("2026-07-01", "2026-09-30", rate=1e-5)
        d = rc.simulate("NATGAS", e, c1, c4, f, i, "2026-07-01", "2026-09-30")
        cyc = rc.cycles(d)
        self.assertEqual(list(cyc["from"]), ["2026-07-15", "2026-08-14"])
        self.assertEqual(list(cyc["to"]), ["2026-08-14", "2026-09-15"])
        g = d[(d["date"] > "2026-07-15") & (d["date"] <= "2026-08-14")]
        self.assertAlmostEqual(cyc["fund"].iloc[0], g["fund"].sum(), places=12)

    def test_verdicts(self):
        base = {"weeks": 20, "ann_excess_2x_pct": 3.0, "ann_excess_3x_pct": 2.0, "funding_ann_pct": 9.0,
                "perp_price_ann_pct": -4.0, "fund_price_ann_pct": 1.0, "liquidations": 0}
        self.assertEqual(rc.verdict({**base, "ann_excess_pct": 4.0, "nw_t": 2.1}, 0, 100)[0], "PASS")
        self.assertEqual(rc.verdict({**base, "ann_excess_pct": 4.0, "nw_t": 1.9}, 0, 100)[0], "PARTIAL")
        self.assertEqual(rc.verdict({**base, "ann_excess_pct": 4.0, "nw_t": 2.5, "ann_excess_2x_pct": -0.1}, 0,
                                    100)[0], "PARTIAL")
        self.assertEqual(rc.verdict({**base, "ann_excess_pct": -1.0, "nw_t": -0.5}, 0, 100)[0], "NULL")
        self.assertIn("reverse", rc.verdict({**base, "ann_excess_pct": -9.0, "nw_t": -2.5}, 0, 100)[1])
        self.assertEqual(rc.verdict({**base, "weeks": 11, "ann_excess_pct": 9.0, "nw_t": 3.0}, 0, 100)[0],
                         "INCONCLUSIVE")
        self.assertEqual(rc.verdict({**base, "ann_excess_pct": 9.0, "nw_t": 3.0}, 12, 100)[0], "INCONCLUSIVE")


class RunTest(unittest.TestCase):
    def test_run_end_to_end_on_a_synthetic_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, lane = Path(tmp) / "data", Path(tmp) / "lane"
            (data / "xyz").mkdir(parents=True)
            (data / "yahoo").mkdir()
            for name, etf in rc.PAIRS.items():
                e, c1, c4, f, i = book("2026-01-05", "2026-11-11", rate=2e-5)
                f.to_csv(data / "xyz" / f"{name}_funding.csv", index=False)
                c1[c1["open_ms"] >= rc.mark_ms("2026-04-20")].to_csv(data / "xyz" / f"{name}_1h.csv", index=False)
                c4.to_csv(data / "xyz" / f"{name}_4h.csv", index=False)
                e.to_parquet(data / "yahoo" / f"{etf}.parquet", index=False)
            i.to_parquet(data / "yahoo" / "IRX.parquet", index=False)
            man = {"files": {str(p.relative_to(data)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                             for p in data.rglob("*") if p.is_file()}}
            (data / "manifest.json").write_text(json.dumps(man))
            state = rc.run(lane=lane, data=data, check=False)
            s = json.loads((lane / "results" / "summary.json").read_text())
            self.assertEqual(state, s["state"])
            nat = s["pairs"]["NATGAS"]
            self.assertGreater(nat["A"]["weeks"], 20)
            self.assertGreater(nat["marks_from_4h"], 0)
            self.assertAlmostEqual(nat["A"]["funding_rate_ann_pct_mean"], 2e-5 * 24 * 365 * 100, places=6)
            self.assertEqual(nat["A"]["liquidations"], 0)
            self.assertIn(state, ("PASS", "PARTIAL", "NULL"))


if __name__ == "__main__":
    unittest.main()
