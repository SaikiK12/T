"""R474 tltcarry_fwd: marks, accounting, re-splits, verdicts and the date guard on synthetic data (no market data)."""
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
import run_tltcarry as tc  # noqa: E402

H = tc.HOUR


def book(lo, hi, etf=100.0, perp=100.0, rate=0.0, irx=4.0):
    """London closes lo..hi, hourly perp candles and funding (stamped 50 ms after the hour) over the same span."""
    days = [d.strftime("%Y-%m-%d") for d in pd.bdate_range(lo, hi)]
    e = pd.DataFrame({"date": days, "close": etf, "adjclose": etf})
    a = tc.mark_ms(days[0]) - 48 * H
    a -= a % H
    b = tc.mark_ms(days[-1]) + 48 * H
    hours = np.arange(a, b, H, dtype=np.int64)
    c = pd.DataFrame({"open_ms": hours, "open": perp, "close": perp})
    f = pd.DataFrame({"time": hours + 50, "fundingRate": rate, "premium": 0.0})
    i = pd.DataFrame({"date": days, "close": irx, "adjclose": irx})
    return e, c, f, i


def set_from(frame, col, day_or_ms, value):
    frame.loc[frame[col] >= day_or_ms, [k for k in ("open", "close") if k in frame]] = value


class MarkTest(unittest.TestCase):
    def test_london_close_follows_dst(self):
        summer = datetime.fromtimestamp(tc.mark_ms("2026-07-01") / 1000, timezone.utc)
        winter = datetime.fromtimestamp(tc.mark_ms("2026-12-01") / 1000, timezone.utc)
        self.assertEqual((summer.hour, summer.minute), (15, 30))
        self.assertEqual((winter.hour, winter.minute), (16, 30))

    def test_perp_price_is_the_candle_containing_the_mark(self):
        c = pd.DataFrame({"open_ms": [0, H, 3 * H], "open": [1.0, 1.5, 3.0], "close": [1.0, 2.0, 4.0]})
        self.assertEqual(tc.perp_at(c, H + 30 * 60_000), 2.0)
        self.assertEqual(tc.perp_at(c, H + 30 * 60_000, mid=True), 1.75)
        self.assertTrue(np.isnan(tc.perp_at(c, 2 * H + 1)))
        self.assertTrue(np.isnan(tc.perp_at(c, -1)))


class AccountingTest(unittest.TestCase):
    def test_flat_prices_earn_funding_less_costs(self):
        r = 1e-5
        e, c, f, i = book("2026-11-16", "2026-12-18", rate=r)
        d = tc.simulate(e, c, f, i, "2026-11-16", "2026-12-18")
        etf0, usdc0 = 1 / (1 + tc.M), 1 - 1 / (1 + tc.M)
        entry = (tc.ETF_BP * etf0 + tc.LEG_BP * etf0 + tc.XFER_BP * usdc0) / 1e4
        hours = (tc.mark_ms("2026-12-18") - tc.mark_ms("2026-11-16")) // H
        fund = r * etf0 * hours
        usdc = usdc0 - entry + fund
        exit_ = (tc.ETF_BP * etf0 + tc.LEG_BP * etf0 + tc.XFER_BP * usdc) / 1e4
        self.assertAlmostEqual(d["fund"].sum(), fund, places=12)
        self.assertAlmostEqual(d["equity"].iloc[-1], 1 - entry + fund - exit_, places=12)
        self.assertEqual(int(d["resplit"].sum()), 1)

    def test_short_perp_collects_the_ex_dividend_drop(self):
        e, c, f, i = book("2026-11-16", "2026-12-04")
        set_from(c, "open_ms", tc.mark_ms("2026-11-25") - H, 99.0)  # TLT goes ex; the accumulating ETF does not drop
        d = tc.simulate(e, c, f, i, "2026-11-16", "2026-12-04")
        u = 1 / (1 + tc.M) / 100.0
        self.assertAlmostEqual(d["perp_pnl"].sum(), u * 1.0, places=12)
        self.assertEqual(int(d["resplit"].sum()), 1)

    def test_rally_drains_margin_and_resplits(self):
        e, c, f, i = book("2026-11-16", "2026-12-04")
        set_from(e, "date", "2026-11-25", 120.0)
        set_from(c, "open_ms", tc.mark_ms("2026-11-25") - H, 120.0)
        d = tc.simulate(e, c, f, i, "2026-11-16", "2026-12-04")
        day = d[d["date"] == "2026-11-25"].iloc[0]
        self.assertEqual(int(day["resplit"]), 1)
        self.assertLess(day["margin_pre"], tc.MARGIN_LO)
        nxt = d[d["date"] == "2026-11-26"].iloc[0]
        self.assertAlmostEqual(nxt["margin_pre"], tc.M, delta=0.002)
        self.assertGreater(day["cost"], 0)

    def test_weekly_excess_subtracts_the_bill(self):
        e, c, f, i = book("2026-11-16", "2027-01-29", rate=2e-5, irx=4.0)
        d = tc.simulate(e, c, f, i, "2026-11-16", "2027-01-29")
        wk = tc.weekly(d)
        self.assertEqual(len(wk), 11)
        self.assertAlmostEqual(wk["bill"].iloc[1], 0.04 * 7 / 365, places=12)
        self.assertTrue(np.allclose(wk["excess"], wk["ret"] - wk["bill"]))
        self.assertAlmostEqual((1 + wk["ret"]).prod(), d["equity"].iloc[-1], places=12)


class VerdictTest(unittest.TestCase):
    def st(self, weeks, ex, t, missing=0):
        return {"weeks": weeks, "days": 5 * weeks, "missing_marks": missing, "ann_excess_pct": ex, "nw_t": t,
                "ann_return_pct": ex + 4, "funding_pct": 1.0, "price_pct": 0.1, "cost_pct": 0.2, "min_margin": 0.3}

    def test_cases(self):
        self.assertEqual(tc.verdict("held", self.st(7, -3, -1))[0], "REPORTED")
        self.assertEqual(tc.verdict("futility", self.st(13, -0.1, -0.1))[0], "NULL")
        self.assertEqual(tc.verdict("futility", self.st(13, 0.5, 0.2))[0], "CONTINUE")
        self.assertEqual(tc.verdict("futility", self.st(9, 5, 3))[0], "INCONCLUSIVE")
        self.assertEqual(tc.verdict("final", self.st(26, 2.5, 2.1))[0], "PASS")
        self.assertEqual(tc.verdict("final", self.st(26, 2.5, 1.9))[0], "PARTIAL")
        self.assertEqual(tc.verdict("final", self.st(26, 1.0, 3.0))[0], "PARTIAL")
        self.assertEqual(tc.verdict("final", self.st(26, -0.2, -0.1))[0], "NULL")
        self.assertEqual(tc.verdict("final", self.st(26, 5, 4, missing=20))[0], "INCONCLUSIVE")


def fake_fetch(rate=3e-5):
    def fetch(start, end, out):
        out = Path(out)
        (out / "xyz").mkdir(parents=True, exist_ok=True)
        (out / "yahoo").mkdir(parents=True, exist_ok=True)
        e, c, f, i = book(start, end, rate=rate)
        f.to_csv(out / "xyz" / "funding.csv", index=False)
        c.to_csv(out / "xyz" / "candles_1h.csv", index=False)
        e.to_parquet(out / "yahoo" / "DTLA.parquet", index=False)
        i.to_parquet(out / "yahoo" / "IRX.parquet", index=False)
        (out / "yahoo" / "DTLA.json").write_text(json.dumps({"chart": {"result": [{"meta": {"currency": "USD"}}]}}))
        files = {str(p.relative_to(out)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(out.rglob("*")) if p.is_file()}
        (out / "manifest.json").write_text(json.dumps({"files": files}))
    return fetch


class RunTest(unittest.TestCase):
    def test_date_guard_and_single_read(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            early = datetime(2027, 2, 12, 23, 59, tzinfo=timezone.utc)
            self.assertIsNone(tc.run("futility", lane, data, check=False, now=early, fetcher=fake_fetch()))
            self.assertFalse((lane / "results").exists())
            on = datetime(2027, 2, 13, 6, 23, tzinfo=timezone.utc)
            self.assertEqual(tc.run("futility", lane, data, check=False, now=on, fetcher=fake_fetch()), "CONTINUE")
            s = json.loads((lane / "results" / "futility" / "summary.json").read_text())
            self.assertEqual((s["registry"], s["state"], s["stats"]["weeks"]), ("R474", "CONTINUE", 13))
            self.assertGreater(s["stats"]["ann_excess_pct"], s["stats"]["ann_excess_2x_pct"])
            cost_w = s["stats"]["ann_excess_pct"] - s["stats"]["ann_excess_2x_pct"]
            d2, d3 = s["stats"]["ann_excess_2x_pct"], s["stats"]["ann_excess_3x_pct"]
            self.assertAlmostEqual(d2 - d3, cost_w, places=9)
            self.assertIsNone(tc.run("futility", lane, data, check=False, now=on, fetcher=fake_fetch(-1e-4)))

    def test_negative_funding_stops_at_futility(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            on = datetime(2027, 2, 13, 6, 23, tzinfo=timezone.utc)
            self.assertEqual(tc.run("futility", lane, data, check=False, now=on, fetcher=fake_fetch(-2e-5)), "NULL")

    def test_held_read_runs_now(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            now = datetime(2026, 11, 12, 6, 0, tzinfo=timezone.utc)
            self.assertEqual(tc.run("held", lane, data, check=False, now=now, fetcher=fake_fetch()), "REPORTED")
            daily = pd.read_csv(lane / "results" / "held" / "daily.csv")
            self.assertEqual((daily["date"].iloc[0], daily["date"].iloc[-1]), ("2026-09-24", "2026-11-11"))

    def test_wrong_currency_is_refused(self):
        def gbp(start, end, out):
            fake_fetch()(start, end, out)
            p = Path(out) / "yahoo" / "DTLA.json"
            p.write_text(json.dumps({"chart": {"result": [{"meta": {"currency": "GBp"}}]}}))
            m = json.loads((Path(out) / "manifest.json").read_text())
            m["files"]["yahoo/DTLA.json"]["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            (Path(out) / "manifest.json").write_text(json.dumps(m))
        with tempfile.TemporaryDirectory() as d:
            now = datetime(2026, 11, 12, tzinfo=timezone.utc)
            with self.assertRaises(SystemExit):
                tc.run("held", Path(d) / "lane", Path(d) / "data", check=False, now=now, fetcher=gbp)


if __name__ == "__main__":
    unittest.main()
