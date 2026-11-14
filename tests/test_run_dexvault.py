"""scripts/run_dexvault.py (R446): HLP and LLP returns on a synthetic vaults/ layout, offline."""
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_dexvault", ROOT / "scripts" / "run_dexvault.py")
dv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dv)
D, H = dv.DAY, 3_600_000
T0 = dv.rx.ms("2025-03-01")


def write_csv(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def llp(root, days=10, step=0.0002, skip=()):
    """Share price 1 * (1 + step)^k stamped at 20:00 UTC on day k (plus an earlier 03:00 stamp that must be ignored)."""
    rows = []
    for k in range(days):
        if k in skip:
            continue
        rows.append({"ts": T0 + k * D + 3 * H, "share_price": 0.5})            # same day, overwritten by 20:00
        rows.append({"ts": T0 + k * D + 20 * H, "share_price": (1 + step) ** k})
    write_csv(root / "vaults" / "llp" / "share_prices" / "all.csv", ["ts", "share_price"], rows)


def hlp(root, fetches, per_hour=1.0, av=1000.0, week_from=None):
    """One snapshot per fetch time: week window (2-hour points from week_from or fetch - 7 d), month window (8-hour
    points over 30 d) and allTime (weekly points from T0 - 70 d). The vault earns `per_hour` of pnl an hour on `av`."""
    for f in fetches:
        rows = []
        for win, step, span in (("week", 2 * H, 7 * D), ("month", 8 * H, 30 * D), ("allTime", 7 * D, 200 * D)):
            first = (week_from if (win == "week" and week_from is not None) else f - span)
            first = max(first, T0 - 70 * D)
            t = first - (first - (T0 - 70 * D)) % step
            base = (t - (T0 - 70 * D)) / H * per_hour
            while t <= f:
                rows.append({"window": win, "ts": t, "account_value": av,
                             "pnl": (t - (T0 - 70 * D)) / H * per_hour - base})
                t += step
        write_csv(root / "vaults" / "hlp" / "snap" / f"{f}.csv", ["window", "ts", "account_value", "pnl"], rows)


class Periods(unittest.TestCase):
    def test_llp_daily_returns_use_the_days_last_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            llp(Path(d))
            per = dv.llp_periods(dv.llp_prices(d), "2025-03-02", "2025-03-05")
            self.assertEqual([p[0] for p in per], ["2025-03-02", "2025-03-03", "2025-03-04", "2025-03-05"])
            for _, span, r in per:
                self.assertAlmostEqual(span, 1.0)
                self.assertAlmostEqual(r, 0.0002)

    def test_llp_gap_books_the_whole_move_on_the_next_stamp(self):
        with tempfile.TemporaryDirectory() as d:
            llp(Path(d), skip=(3,))
            per = dict((p[0], p) for p in dv.llp_periods(dv.llp_prices(d), "2025-03-02", "2025-03-06"))
            self.assertNotIn("2025-03-04", per)
            self.assertAlmostEqual(per["2025-03-05"][1], 2.0)
            self.assertAlmostEqual(per["2025-03-05"][2], 1.0002 ** 2 - 1)

    def test_hlp_gate0_uses_alltime_pnl_over_account_value(self):
        with tempfile.TemporaryDirectory() as d:
            hlp(Path(d), [T0 + 100 * D])
            per = dv.hlp_gate0_periods(dv.hlp_snaps(d), "2025-03-01", "2025-05-01")
            self.assertTrue(len(per) >= 8)
            for _, span, r in per:
                self.assertAlmostEqual(span, 7.0)
                self.assertAlmostEqual(r, 7 * 24 * 1.0 / 1000)

    def test_hlp_day_uses_the_first_snapshot_after_the_day(self):
        with tempfile.TemporaryDirectory() as d:
            hlp(Path(d), [T0 + 10 * D + 2 * H + 37 * 60_000, T0 + 11 * D + 2 * H])
            self.assertAlmostEqual(dv.hlp_day(dv.hlp_snaps(d), T0 + 10 * D), 24 / 1000)
            self.assertIsNone(dv.hlp_day(dv.hlp_snaps(d), T0 + 12 * D))       # no snapshot fetched after it

    def test_hlp_day_falls_back_to_month_when_week_misses_the_start(self):
        with tempfile.TemporaryDirectory() as d:
            f = T0 + 20 * D + 3 * H
            hlp(Path(d), [f], week_from=T0 + 19 * D + 12 * H)     # week window starts after the day's first boundary
            self.assertAlmostEqual(dv.hlp_day(dv.hlp_snaps(d), T0 + 20 * D), 24 / 1000)

    def test_forward_daily_counts_a_missing_day(self):
        with tempfile.TemporaryDirectory() as d:
            llp(Path(d), skip=(4,))                                   # no stamp on 2025-03-05
            daily = dv.forward_daily(d, "llp", "2025-03-03", "2025-03-06")
            self.assertEqual(list(daily.missing), [0, 0, 1, 0])
            self.assertAlmostEqual(daily.net_1x.iloc[0], 0.0002 - 0.0010 / 365)
            self.assertEqual(daily.gross.iloc[2], 0.0)
            self.assertAlmostEqual(daily.gross.iloc[3], 1.0002 ** 2 - 1)     # the gap's move lands on the next stamp


class Reads(unittest.TestCase):
    def test_gate0_summary_on_a_steady_return(self):
        per = [(f"d{k}", 1.0, 0.10 / 365) for k in range(400)]               # 10%/yr, every day
        s = dv.gate0_summary(per, 10)
        self.assertAlmostEqual(s["1x"]["net_ann"], 0.10 - 0.0010)
        self.assertAlmostEqual(s["1x"]["excess_ann"], 0.10 - 0.0010 - 0.04)
        self.assertAlmostEqual(s["3x"]["excess_ann"], 0.10 - 0.0030 - 0.04)
        self.assertEqual(dv.decide_gate0(s), "CONTINUE to gate 1")
        self.assertEqual(dv.decide_gate0(dv.gate0_summary([], 10)), "NULL (stop)")

    def test_gate0_stops_only_below_zero(self):
        self.assertEqual(dv.decide_gate0({"1x": {"excess_ann": -0.001}}), "NULL (stop)")


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_prereg_text(self):
        text = (ROOT / "experiments" / "dexvault_v1" / "PREREG.md").read_text()
        self.assertEqual(dv.BOOKS, ("hlp", "llp"))
        self.assertEqual(dv.HURDLE_ANN, 0.04)
        self.assertIn("4.0%/yr on capital", text)
        self.assertEqual(dv.COST_ANN, 0.0010)
        self.assertIn("10 bp of capital a year", text)
        self.assertEqual(dv.GATE0_LAG, {"hlp": 4, "llp": 10})
        self.assertIn("lag 4 for HLP", text)
        self.assertIn("lag 10 for LLP", text)
        self.assertEqual(dv.FALLBACK, ("week", "month", "allTime"))
        self.assertIn("`week`, then `month`, then `allTime`", text)
        self.assertEqual(dv.WINDOWS["gate0"], ("2025-01-01", "2026-11-10"))
        self.assertIn("2025-01-01..2026-11-10", text)
        self.assertEqual(dv.LOOKS, dv.rx.LOOKS)
        self.assertIn("(2027-02-08)", text)
        self.assertIn("(2027-05-09)", text)


if __name__ == "__main__":
    unittest.main()
