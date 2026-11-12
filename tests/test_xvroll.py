"""xvroll_fwd (R482): the hourly pair book (funding, price, liquidation, re-splits), weekly stats, verdicts and the
read gate, on synthetic data (no network)."""
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_xvroll as xv  # noqa: E402

H = xv.H
S = xv.ms("2026-11-16", 20)


def bars(price, start=S, hours=24 * 35, high=None, low=None):
    """1-hour bars ending at start .. start + hours h; price(k) is the close of the bar ending k hours after start."""
    k = np.arange(-24, hours + 1)
    c = np.array([price(int(i)) for i in k], float)
    hi = c if high is None else np.array([high(int(i), x) for i, x in zip(k, c)], float)
    lo = c if low is None else np.array([low(int(i), x) for i, x in zip(k, c)], float)
    return pd.DataFrame({"open_ms": start + (k - 1) * H, "open": c, "high": hi, "low": lo, "close": c, "volume": 1.0})


def funding(rate, start=S, hours=24 * 35):
    t = start + np.arange(-24, hours + 1) * H
    return pd.DataFrame({"t": t, "rate": rate})


class Book(unittest.TestCase):
    def test_flat_prices_keep_the_funding_difference(self):
        flat = bars(lambda k: 3.0)
        d = xv.simulate("NATGAS", flat, funding(2e-4), flat, funding(5e-5), S, S + 28 * 24 * H)
        self.assertEqual(len(d), 29)
        self.assertEqual(d["liq"].sum(), 0)
        self.assertEqual(d["resplit"].sum(), 0)
        cost = xv.L * (xv.COST_X_BP + xv.COST_L_BP) / 1e4
        self.assertAlmostEqual(d["cost"].iloc[0], cost, places=12)
        gain = (1 - cost) * xv.L * (2e-4 - 5e-5) * 28 * 24          # funding on a fixed quantity at a flat price
        self.assertAlmostEqual(d["equity"].iloc[-1], 1 - cost + gain, places=9)
        self.assertAlmostEqual(d.attrs["funding_diff_ann_pct_notional"], (2e-4 - 5e-5) * 24 * 365 * 100, places=6)
        self.assertEqual(d.attrs["share_hours_xyz_pays_more"], 1.0)
        self.assertEqual(d.attrs["missing_share"], 0.0)

    def test_common_price_move_nets_out_until_a_resplit(self):
        up = bars(lambda k: 3.0 * (1 + 0.25 * min(max(k, 0), 240) / 240))   # +25% over 10 days, on both venues
        d = xv.simulate("NATGAS", up, funding(0.0), up, funding(0.0), S, S + 20 * 24 * H)
        self.assertEqual(d["liq"].sum(), 0)
        self.assertGreaterEqual(d["resplit"].sum(), 1)                       # the short's margin ran low
        self.assertAlmostEqual(d["pnl_x"].sum() + d["pnl_l"].sum(), 0.0, delta=0.02)
        self.assertGreater(d["equity"].iloc[-1], 0.99)

    def test_spike_liquidates_the_short_and_reenters(self):
        spike = 24 * 3 + 5
        xb = bars(lambda k: 3.0, high=lambda k, c: c * 1.6 if k == spike else c)
        lb = bars(lambda k: 3.0)
        d = xv.simulate("NATGAS", xb, funding(0.0), lb, funding(0.0), S, S + 10 * 24 * H)
        self.assertEqual(d["liq"].sum(), 1)
        after = d.iloc[4]                                                     # the mark after the spike
        self.assertLess(after["equity"], 0.51)
        self.assertGreater(after["equity"], 0.45)
        self.assertGreater(d.iloc[4]["cost"], 0)                              # re-entry and the transfer
        self.assertEqual(d["liq"].iloc[5:].sum(), 0)

    def test_weekly_stats_and_verdicts(self):
        flat = bars(lambda k: 3.0, hours=24 * 7 * 30)
        d = xv.simulate("NATGAS", flat, funding(3e-5, hours=24 * 7 * 30), flat, funding(0.0, hours=24 * 7 * 30),
                        S, S + 7 * 24 * 26 * H)
        irx = pd.DataFrame({"date": ["2026-11-01"], "close": [3.65]})
        d = xv.add_bill(d, irx)
        wk = xv.weekly(d)
        wk["excess"] += np.linspace(-1e-4, 1e-4, len(wk))
        st = xv.stats(wk, d)
        self.assertEqual(st["weeks"], len(wk))
        self.assertGreater(st["ann_excess_pct"], 2)
        self.assertEqual(xv.verdict("final", {**st, "weeks": 44})[0], "PASS")
        self.assertEqual(xv.verdict("final", {**st, "weeks": 44}, "NULL")[0], "NULL")
        self.assertEqual(xv.verdict("final", {**st, "weeks": 44, "nw_t": 1.0})[0], "PARTIAL")
        self.assertEqual(xv.verdict("futility", {**st, "weeks": 22})[0], "CONTINUE")
        self.assertEqual(xv.verdict("futility", {**st, "weeks": 22, "ann_excess_pct": -1})[0], "NULL")
        self.assertEqual(xv.verdict("futility", {**st, "weeks": 5})[0], "INCONCLUSIVE")
        self.assertEqual(xv.verdict("final", {**st, "weeks": 44, "missing_share": 0.2})[0], "INCONCLUSIVE")

    def test_missing_bars_are_counted_and_carried(self):
        xb = bars(lambda k: 3.0)
        xb = xb[(xb["open_ms"] < S + 10 * H) | (xb["open_ms"] > S + 40 * H)]
        d = xv.simulate("NATGAS", xb, funding(0.0), bars(lambda k: 3.0), funding(0.0), S, S + 10 * 24 * H)
        self.assertAlmostEqual(d.attrs["missing_share"], 31 / 240, places=9)    # bars opening at +10 h .. +40 h
        self.assertTrue(math.isfinite(d["equity"].iloc[-1]))


class Reads(unittest.TestCase):
    def fake_fetch(self, read, arch, out, start_ms, end_ms):
        out.mkdir(parents=True, exist_ok=True)
        hours = int((end_ms - start_ms) // H)
        for name in xv.PAIRS:
            b = bars(lambda k: 3.0, start_ms, hours)
            b.to_csv(out / f"xyz_{name}_1h.csv", index=False)
            b.to_csv(out / f"lighter_{name}_1h.csv", index=False)
            f = funding(3e-5, start_ms, hours)
            f.rename(columns={"t": "time", "rate": "fundingRate"}).assign(premium=0).to_csv(
                out / f"xyz_{name}_funding.csv", index=False)
            funding(0.0, start_ms, hours).to_csv(out / f"lighter_{name}_funding.csv", index=False)
        pd.DataFrame({"date": ["2026-11-01"], "close": [3.65]}).to_csv(out / "IRX.csv", index=False)
        return {"files": {}, "recorded": {}}

    def test_gate_refusal_once_only_and_futility_carry(self):
        with tempfile.TemporaryDirectory() as d:
            lane, data = Path(d) / "lane", Path(d) / "data"
            early = datetime(2027, 5, 14, 23, tzinfo=timezone.utc)
            self.assertIsNone(xv.run("futility", lane, None, data, check=False, now=early, fetcher=self.fake_fetch))
            later = datetime(2027, 5, 15, 1, tzinfo=timezone.utc)
            out = xv.run("futility", lane, None, data, check=False, now=later, fetcher=self.fake_fetch)
            self.assertEqual(out["verdict"], "CONTINUE")
            self.assertTrue((lane / "results" / "futility" / "weekly_NATGAS.csv").exists())
            self.assertIsNone(xv.run("futility", lane, None, data, check=False, now=later, fetcher=self.fake_fetch))
            s = json.loads((lane / "results" / "futility" / "summary.json").read_text())
            self.assertEqual(s["window"], [xv.START, "2027-05-14"])
            self.assertIsNone(xv.run("final", lane, None, data, check=False, now=later, fetcher=self.fake_fetch))


if __name__ == "__main__":
    unittest.main()
