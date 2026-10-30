"""Synthetic checks for R332's helpers and the complete-metrics fetch plan: no panel return is read."""
import unittest

import numpy as np
import pandas as pd

from scripts import build_daily_v2 as bv
from scripts import fetch_metrics_full as fm
from scripts import run_mlrank3 as m3


class FetchPlanTest(unittest.TestCase):
    def test_needed_days_cover_ten_days_back_of_universe_rows(self):
        d = pd.DataFrame({"day": pd.to_datetime(["2023-03-20", "2023-03-20", "2023-03-25"]).date,
                          "perp": ["AUSDT", "BUSDT", "AUSDT"], "rank_qvol30": [10.0, 151.0, 150.0]})
        need = fm.needed(d, top=150, back=10)
        self.assertEqual(set(need), {"AUSDT"})                   # B is outside the top 150
        days = need["AUSDT"]
        self.assertEqual(days[0], "2023-03-10")                  # D-10 of the first row
        self.assertEqual(days[-1], "2023-03-24")                 # D-1 of the last row: row D holds day D-1
        self.assertEqual(len(days), 15)

    def test_needed_days_never_before_the_panel_start(self):
        d = pd.DataFrame({"day": pd.to_datetime(["2021-01-03"]).date, "perp": ["AUSDT"], "rank_qvol30": [1.0]})
        self.assertEqual(fm.needed(d)["AUSDT"], ["2021-01-01", "2021-01-02"])


class ShadowRootTest(unittest.TestCase):
    def test_links_everything_but_metrics(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "data"
            for name in ("klines_1h", "metrics_1h", "raw", "daily"):
                (base / name).mkdir(parents=True)
            full = Path(tmp) / "full"
            full.mkdir()
            src = bv.shadow(Path(tmp) / "src", base, full)
            self.assertEqual(sorted(p.name for p in src.iterdir()), ["klines_1h", "metrics_1h"])
            self.assertEqual((src / "metrics_1h").resolve(), full.resolve())
            bv.shadow(Path(tmp) / "src", base, full)            # a second run rebuilds the links
            self.assertEqual((src / "klines_1h").resolve(), (base / "klines_1h").resolve())


class PresenceTest(unittest.TestCase):
    def test_trials(self):
        self.assertEqual(m3.TRIALS, 7)

    def test_presence_reads_row_d_only(self):
        days = pd.date_range("2022-01-01", periods=3)
        oi = pd.DataFrame({"A": [1.0, np.nan, 1.0], "B": [np.nan, 2.0, np.nan], "C": [3.0, 3.0, 3.0]}, index=days)
        uni = pd.DataFrame(True, index=days, columns=oi.columns)
        uni.loc[days[2], "C"] = False
        p = m3.presence_pred({"oi_usd": oi}, uni)
        self.assertEqual(p.loc[(days[0], "A")], 1.0)
        self.assertEqual(p.loc[(days[1], "A")], 0.0)
        self.assertEqual(p.loc[(days[1], "B")], 1.0)
        self.assertNotIn((days[2], "C"), p.index)                 # outside the universe
        oi2 = oi.copy()
        oi2.iloc[2] = np.nan                                      # a later row never changes an earlier prediction
        q = m3.presence_pred({"oi_usd": oi2}, uni)
        pd.testing.assert_series_equal(p.loc[days[:2]], q.loc[days[:2]])

    def test_presence_starts_at_the_first_prediction_day(self):
        days = pd.date_range("2021-12-30", periods=4)
        oi = pd.DataFrame({"A": 1.0}, index=days)
        p = m3.presence_pred({"oi_usd": oi}, pd.DataFrame(True, index=days, columns=["A"]))
        self.assertEqual(p.index.get_level_values(0).min(), pd.Timestamp("2022-01-01"))

    def test_column_check_is_nan_aware(self):
        day = pd.to_datetime(["2023-01-01", "2023-01-01", "2023-01-02"]).date
        a = pd.DataFrame({"day": day, "perp": ["A", "B", "A"], "close": [1.0, 2.0, 3.0],
                          "oi_usd": [np.nan, 5.0, np.nan]})
        b = a.copy()
        b.loc[0, "oi_usd"] = 7.0
        b = b.iloc[:2]
        out = m3.column_check(a, b)
        self.assertEqual(out["differ"], {"close": 0, "oi_usd": 1})
        self.assertEqual((out["rows_v1"], out["rows_v2"], out["rows_both"]), (3, 2, 2))

    def test_coverage_bands(self):
        d = pd.DataFrame({"day": pd.to_datetime(["2023-01-01"] * 3).date, "rank_qvol30": [1.0, 60.0, 120.0],
                          "oi_usd": [1.0, np.nan, 1.0]})
        c = m3.coverage(d)
        self.assertEqual(c["2023 (0, 50]"], 1.0)
        self.assertEqual(c["2023 (50, 100]"], 0.0)
        self.assertEqual(c["2023 (100, 150]"], 1.0)


if __name__ == "__main__":
    unittest.main()
