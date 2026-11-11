"""R461 earnperp_v1 rule: session windows, trading days, instants, continuation sign, clustered test, verdict."""
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import earnperp_rule as rule  # noqa: E402

NY = ZoneInfo("America/New_York")
H = rule.HOUR_MS


def ny_ms(y, mo, d, h, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=NY).timestamp() * 1000)


class Instants(unittest.TestCase):
    def test_amc_thursday(self):
        i = rule.instants(ny_ms(2026, 7, 30, 16, 30))       # Thursday, summer time
        self.assertEqual(i["session"], "amc")
        self.assertEqual(i["R"], ny_ms(2026, 7, 30, 16))
        self.assertEqual(i["E"], ny_ms(2026, 7, 30, 18))      # 16:30 -> 17:00 -> +1 h
        self.assertEqual(i["X1"], ny_ms(2026, 7, 31, 10))
        self.assertEqual(i["X2"], ny_ms(2026, 7, 31, 16))

    def test_amc_friday_goes_to_monday_and_holiday_is_skipped(self):
        i = rule.instants(ny_ms(2026, 1, 16, 16, 5))        # Friday; Monday 2026-01-19 is MLK day
        self.assertEqual(i["X2"], ny_ms(2026, 1, 20, 16))

    def test_bmo_uses_previous_close_and_same_day(self):
        i = rule.instants(ny_ms(2026, 10, 27, 7, 0))        # Tuesday 07:00
        self.assertEqual(i["session"], "bmo")
        self.assertEqual(i["R"], ny_ms(2026, 10, 26, 16))
        self.assertEqual(i["E"], ny_ms(2026, 10, 27, 8))
        self.assertEqual(i["X1"], ny_ms(2026, 10, 27, 10))

    def test_early_close_and_out_of_window(self):
        self.assertEqual(rule.close_time(date(2025, 11, 28)).hour, 13)
        self.assertIsNone(rule.instants(ny_ms(2026, 7, 30, 12))["session"])      # intraday
        self.assertIsNone(rule.instants(ny_ms(2026, 7, 30, 22))["session"])      # late evening
        self.assertIsNone(rule.instants(ny_ms(2026, 8, 1, 17))["session"])       # Saturday


class Rows(unittest.TestCase):
    def test_continuation_sign_and_missing_exit(self):
        i = rule.instants(ny_ms(2026, 7, 30, 16, 30))
        t = np.array([i["R"], i["E"], i["X1"], i["X2"]], dtype="int64")
        o = np.array([100.0, 110.0, 111.0, 105.0])
        x = rule.event_row(t, o, i)
        self.assertEqual(x["s"], 1)
        self.assertGreater(x["x1"], 0)
        self.assertLess(x["x2"], 0)
        x = rule.event_row(t[:2], o[:2], i)
        self.assertTrue(np.isnan(x["x2"]))
        o2 = np.array([100.0, 90.0, 89.0, 95.0])
        x = rule.event_row(t, o2, i)
        self.assertEqual(x["s"], -1)
        self.assertGreater(x["x1"], 0)


class Test(unittest.TestCase):
    def test_cluster_flip_finds_a_planted_mean_and_not_a_null(self):
        rng = np.random.default_rng(0)
        cl = np.repeat(np.arange(120), 3)
        x = rng.normal(80, 300, len(cl))
        self.assertLess(rule.cluster_flip_p(x, cl, np.random.default_rng(1), draws=20_000), 0.01)
        ps = [rule.cluster_flip_p(rng.normal(0, 300, len(cl)), cl, np.random.default_rng(k), draws=5_000)
              for k in range(5)]
        self.assertGreater(min(ps), 0.005)

    def test_verdict(self):
        c = {"n_a": 200, "mean_a": -80.0, "p_holm": 0.01, "n_b": 60, "mean_b": -40.0}
        self.assertEqual(rule.verdict([c, dict(c, p_holm=0.4)])[0], "PASS")
        self.assertEqual(rule.verdict([dict(c, mean_b=10.0), dict(c, p_holm=0.4)])[0], "NULL")
        self.assertEqual(rule.verdict([dict(c, mean_a=-40.0), dict(c, p_holm=0.4)])[0], "PARTIAL")
        self.assertEqual(rule.verdict([dict(c, n_a=50), dict(c, n_a=50)])[0], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()


class EndToEnd(unittest.TestCase):
    def test_runner_on_a_synthetic_world_with_planted_continuation(self):
        import tempfile
        import pandas as pd
        import run_earnperp as runner
        tmp = Path(tempfile.mkdtemp())
        a_dir, b_dir, lane = tmp / "a" / "klines_1h", tmp / "b" / "klines_1h", tmp / "lane"
        for d in (a_dir, b_dir, lane):
            d.mkdir(parents=True)
        rng = np.random.default_rng(3)
        t = np.arange(ny_ms(2026, 1, 2, 0), ny_ms(2026, 11, 11, 0), H, dtype="int64")
        rows, k = [], 0
        days = [d for d in pd.bdate_range("2026-02-02", "2026-11-05") if rule.trading_day(d.date())]
        for i, day in enumerate(days[::2][:120]):
            tick = f"T{i % 40:02d}"
            acc = ny_ms(day.year, day.month, day.day, 16, 5)
            rows.append({"ticker": tick, "cik": 1, "form": "8-K", "items": "2.02",
                         "acceptance_utc": pd.Timestamp(acc, unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                         "filing_date": day.date().isoformat(), "accession": f"x{i}"})
        pd.DataFrame(rows).to_csv(lane / "events.csv", index=False)
        for i in range(40):
            o = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, len(t))))
            for r in rows:
                if r["ticker"] != f"T{i:02d}":
                    continue
                inst = rule.instants(int(pd.Timestamp(r["acceptance_utc"]).timestamp() * 1000))
                jump = rng.choice([-0.05, 0.05])
                e, x2 = np.searchsorted(t, inst["E"]), np.searchsorted(t, inst["X2"])
                o[e:] *= 1 + jump
                o[x2:] *= 1 + 0.5 * jump        # planted continuation, half the first reaction
            pd.DataFrame({"t": t, "open": o}).to_parquet(a_dir / f"T{i:02d}STOCK_USDT.parquet", index=False)
        pd.DataFrame({"t": t, "open": np.full(len(t), 5000.0)}).to_parquet(a_dir / "SPX500_USDT.parquet",
                                                                            index=False)
        old = runner.A_DIR, runner.B_DIR
        runner.A_DIR, runner.B_DIR = a_dir, b_dir
        try:
            state = runner.run(lane=lane, check=False)
        finally:
            runner.A_DIR, runner.B_DIR = old
        cells = pd.read_csv(lane / "results" / "cells.csv")
        d1 = cells[(cells.session == "amc") & (cells.h == "x2") & (cells.subset == "all") & ~cells.hedged].iloc[0]
        self.assertGreater(d1.mean_a, 150)
        self.assertLess(d1.p_a, 0.01)
        self.assertIn(state, ("PARTIAL", "PASS", "NULL", "INCONCLUSIVE"))
