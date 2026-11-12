"""R480 futroll_fwd: recorder plumbing, the roll schedule, the rolled-futures index and an end-to-end gated read on
synthetic data (no network)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import record_futroll as rec  # noqa: E402
import run_futroll as rf  # noqa: E402
import run_rollcarry as rc  # noqa: E402

H = 3_600_000
UTC = timezone.utc
PRICES = {"NGF27.NYM": 4.0, "NGG27.NYM": 4.4, "NGH27.NYM": 4.84}   # 10% contango a month
READS = {"futility": {"last": "2027-01-15", "after": "2027-01-16", "cycles": 2, "min_weeks": 5},
         "final": {"last": "2027-02-12", "after": "2027-02-13", "cycles": 3, "min_weeks": 8}}


def hours(a, b):
    t0 = int(pd.Timestamp(a, tz="UTC").value // 1_000_000)
    t1 = int(pd.Timestamp(b, tz="UTC").value // 1_000_000)
    return list(range(t0, t1, H))


def oracle(t, days):
    """The perp's price at time t: xyz's blend, switching at 18:00 New York (two hours after the 16:00 mark).
    Contracts before the window (NGX26, NGZ26) are priced like NGF27, so November's roll does not move it."""
    d = [x for x in days if rc.mark_ms(x) + 2 * H <= t][-1]
    return sum(w * PRICES.get(s, 4.0) for s, w in rf.held("NG", d).items())


def synth(arch, src, rate_h=0.0):
    (arch / "yahoo").mkdir(parents=True)
    (arch / "xyz").mkdir(parents=True)
    (src / "xyz").mkdir(parents=True)
    (src / "yahoo").mkdir(parents=True)
    ts = hours("2026-11-01", "2027-02-20")
    for s, p in PRICES.items():
        pd.DataFrame({"open_ms": ts, "open": p, "high": p, "low": p, "close": p, "volume": 1}).to_csv(
            arch / "yahoo" / f"{s}.csv", index=False)
    with rf.lane_settings():
        days = rf.business_days("2026-10-01", "2027-02-26")
        px = [oracle(t + H, days) for t in ts]
    c1 = pd.DataFrame({"open_ms": ts, "open": px, "high": px, "low": px, "close": px, "volume": 1})
    c1.to_csv(arch / "xyz" / "NATGAS_1h.csv", index=False)
    c1.iloc[::4].to_csv(src / "xyz" / "NATGAS_4h.csv", index=False)
    fund = pd.DataFrame({"time": [t + H for t in ts], "fundingRate": rate_h, "premium": 0.0})
    fund.iloc[: len(fund) // 2].to_csv(arch / "xyz" / "NATGAS_funding.csv", index=False)
    fund.iloc[len(fund) // 3:].to_csv(src / "xyz" / "NATGAS_funding.csv", index=False)
    for n in ("CL", "BRENTOIL"):
        pd.DataFrame(columns=["open_ms", "open", "high", "low", "close", "volume"]).to_csv(
            src / "xyz" / f"{n}_4h.csv", index=False)
    pd.DataFrame({"date": pd.date_range("2026-10-01", "2027-02-20").strftime("%Y-%m-%d"), "close": 0.0,
                  "adjclose": 0.0}).to_parquet(src / "yahoo" / "IRX.parquet", index=False)


class Recorder(unittest.TestCase):
    def test_contracts(self):
        c = rec.contracts(datetime(2026, 11, 12, tzinfo=UTC))
        self.assertEqual(c[:4], ["NGZ26.NYM", "NGF27.NYM", "NGG27.NYM", "NGH27.NYM"])
        self.assertEqual(c[4:8], ["CLZ26.NYM", "CLF27.NYM", "CLG27.NYM", "CLH27.NYM"])
        self.assertEqual(c[8:], ["BZF27.NYM", "BZG27.NYM", "BZH27.NYM", "BZJ27.NYM"])
        c = rec.contracts(datetime(2026, 12, 31, tzinfo=UTC))
        self.assertEqual((c[0], c[8]), ("NGF27.NYM", "BZG27.NYM"))
        # the runner's names agree with the recorder's
        self.assertEqual(rf.symbol("NG", 2026, 11, 1), "NGZ26.NYM")
        self.assertEqual(rf.symbol("BZ", 2026, 12, 2), "BZG27.NYM")
        self.assertEqual(rf.symbol("CL", 2027, 12, 1), "CLF28.NYM")
        self.assertEqual(rf.symbol("CL", 2027, 12, 2), "CLG28.NYM")

    def test_merge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x" / "A.csv"
            rows = [{"open_ms": 2 * H, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0},
                    {"open_ms": H, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 0}]
            self.assertEqual(rec.merge(p, rows, "open_ms", rec.BAR_COLS), 2)
            rows = [{"open_ms": 2 * H, "open": 1, "high": 1, "low": 1, "close": 2, "volume": 0},
                    {"open_ms": 3 * H, "open": 1, "high": 1, "low": 1, "close": 3, "volume": 0}]
            self.assertEqual(rec.merge(p, rows, "open_ms", rec.BAR_COLS), 1)
            df = pd.read_csv(p)
            self.assertEqual(df["open_ms"].tolist(), [H, 2 * H, 3 * H])
            self.assertEqual(df["close"].tolist(), [1, 2, 3])


class Schedule(unittest.TestCase):
    def test_weights(self):
        with rf.lane_settings():
            b = rc.bdays(2026, 12)
            self.assertEqual(rf.held("NG", b[3]), {"NGF27.NYM": 1.0})
            w = rf.held("NG", b[4])
            self.assertAlmostEqual(w["NGF27.NYM"], 0.8)
            self.assertAlmostEqual(w["NGG27.NYM"], 0.2)
            self.assertAlmostEqual(rf.held("NG", b[7])["NGG27.NYM"], 0.8)
            self.assertEqual(rf.held("NG", b[8]), {"NGG27.NYM": 1.0})
            self.assertEqual(rf.held("NG", "2027-01-04"), {"NGG27.NYM": 1.0})
            self.assertEqual(rf.held("BZ", b[0]), {"BZG27.NYM": 1.0})
            self.assertIn("2027-01-18", rc.HOLIDAYS)
            self.assertEqual(rc.FUND_BP, rf.HEDGE_BP)
        self.assertNotIn("2027-01-18", rc.HOLIDAYS)
        self.assertEqual(rc.FUND_BP, 5.0)

    def test_index_does_not_jump_at_the_roll(self):
        with tempfile.TemporaryDirectory() as d:
            arch, src = Path(d) / "a", Path(d) / "s"
            synth(arch, src)
            bars = {s: rf.read_bars(arch / "yahoo" / f"{s}.csv") for s in PRICES}
            irx = pd.read_parquet(src / "yahoo" / "IRX.parquet")
            with rf.lane_settings():
                idx = rf.hedge_index("NG", bars, irx, "2026-11-13", "2027-01-15")
            self.assertEqual(idx.attrs["missing_marks"], 0)
            self.assertAlmostEqual(float(idx["ret"].abs().sum()), 0.0)
            # the oracle's roll-up: five 20% steps of a 10% spread, each against the blend before it
            dec = idx[(idx["date"] > "2026-12-01") & (idx["date"] < "2026-12-31")]
            self.assertAlmostEqual(float((1 + dec["roll_spread"]).prod()), 1.1, places=6)
            self.assertAlmostEqual(float(dec["roll_cost"].sum()), 2 * rf.ROLL_LEG_BP / 1e4, places=9)
            self.assertAlmostEqual(float(idx["close"].iloc[-1]), (1 - 0.2 * 2 * rf.ROLL_LEG_BP / 1e4) ** 10, places=9)


class EndToEnd(unittest.TestCase):
    def read(self, rate_h):
        with tempfile.TemporaryDirectory() as d:
            arch, src, lane = Path(d) / "a", Path(d) / "s", Path(d) / "lane"
            synth(arch, src / "futility", rate_h)
            old = rf.READS
            rf.READS = READS
            try:
                early = rf.run("futility", lane, arch, Path(d) / "s", check=False,
                               now=datetime(2027, 1, 15, tzinfo=UTC), fetcher=None)
                self.assertIsNone(early)
                self.assertFalse((lane / "results" / "futility").exists())
                state = rf.run("futility", lane, arch, Path(d) / "s", check=False,
                               now=datetime(2027, 1, 16, tzinfo=UTC), fetcher=None)
                again = rf.run("futility", lane, arch, Path(d) / "s", check=False,
                               now=datetime(2027, 1, 17, tzinfo=UTC), fetcher=None)
            finally:
                rf.READS = old
            self.assertIsNone(again)
            out = json.loads((lane / "results" / "futility" / "summary.json").read_text())
            cyc = pd.read_csv(lane / "results" / "futility" / "cycles_NATGAS.csv")
            return state, out, cyc

    def test_no_funding_pays_the_roll(self):
        state, out, cyc = self.read(0.0)
        n = out["pairs"]["NATGAS"]
        self.assertEqual(n["missing_share"], 0.0)
        self.assertEqual(out["pairs"]["CL"]["state"], "no data")
        self.assertEqual(len(cyc), 2)
        # each cycle: the short loses the roll (about 10% of notional, notional 3/4 of capital); the hedge is flat
        for _, c in cyc.iterrows():
            self.assertAlmostEqual(c["roll_spread"], 0.1, delta=0.005)
            self.assertAlmostEqual(c["gap"], -0.75 * 0.1, delta=0.01)
        self.assertEqual(state, "NULL")
        self.assertLess(n["all"]["ann_excess_pct"], 0)

    def test_funding_above_the_roll_earns(self):
        state, out, cyc = self.read(0.0002)     # about 14% of notional a month
        self.assertEqual(state, "CONTINUE")
        self.assertGreater(out["pairs"]["NATGAS"]["all"]["ann_excess_pct"], 0)
        self.assertTrue((cyc["fund"] + cyc["gap"] > 0).all())
        st = out["pairs"]["NATGAS"]["all"]
        # roll costs reach the cost column: 2 rolls x 2 legs x 4 bp on 3/4 of capital, over 10 weeks
        roll_ann = 2 * 2 * rf.ROLL_LEG_BP / 1e4 * 0.75 / 10 * 52 * 100
        self.assertGreater(st["ann_excess_pct"] - st["ann_excess_2x_pct"], roll_ann)
        self.assertAlmostEqual(st["ann_excess_pct"] - st["ann_excess_2x_pct"], st["cost_ann_pct"], places=6)


if __name__ == "__main__":
    unittest.main()
