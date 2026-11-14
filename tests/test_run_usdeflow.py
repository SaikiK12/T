"""scripts/run_usdeflow.py (R488): DefiLlama supply parsing, the ISO-week supply change and its end-of-week stamp,
weekly mean funding with the hour minimum, the carry proxy's 7-day rule, the sample window (first week above $100m,
last target week ending 2026-11-08), the circular-shift null with +/-4 week exclusion, halves, gates and verdict.
Synthetic series only."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_usdeflow as ru  # noqa: E402

DAY = ru.DAY


def daily(first, vals):
    idx = [ru.add_days(first, i) for i in range(len(vals))]
    return pd.Series(list(vals), index=idx, dtype=float)


def hourly(first_day, rates_per_week, hours=168):
    t0 = ru.ms(first_day)
    rows = []
    for k, r in enumerate(rates_per_week):
        for h in range(hours):
            rows.append({"time": t0 + k * ru.WEEK + h * 3_600_000 + 151, "rate": r})
    return pd.DataFrame(rows)


class TestSupply(unittest.TestCase):
    def test_parse_tokens_and_cut(self):
        body = {"tokens": [{"date": ru.ms("2026-11-07") // 1000, "circulating": {"peggedUSD": 5.0}},
                           {"date": ru.ms("2026-11-08") // 1000, "circulating": {"peggedUSD": 6.0}},
                           {"date": ru.ms("2026-11-09") // 1000, "circulating": {"peggedUSD": 7.0}},
                           {"date": ru.ms("2026-11-06") // 1000, "circulating": {}}]}
        s, field = ru.parse_supply(body)
        self.assertEqual(field, "tokens[].circulating.peggedUSD")
        self.assertEqual(list(s.index), ["2026-11-07", "2026-11-08"])     # cut at 2026-11-09, missing dropped
        s2, f2 = ru.parse_supply({"totalCirculating": [{"date": ru.ms("2024-03-04") // 1000,
                                                         "totalCirculating": 2.0}]})
        self.assertEqual(f2, "totalCirculating[].totalCirculating")
        self.assertEqual(float(s2["2024-03-04"]), 2.0)

    def test_weekly_change_uses_next_monday_stamp(self):
        # 2024-03-04 is a Monday. Supply doubles on the stamp of 2024-03-18 (end of the week of 03-11).
        vals = [100.0] * 14 + [200.0] * 14
        s = daily("2024-03-04", vals)
        w = ru.weekly_supply(s, "monday")
        self.assertAlmostEqual(w.w["2024-03-11"], np.log(2))
        self.assertAlmostEqual(w.w["2024-03-18"], 0.0)
        self.assertAlmostEqual(w.s_prev["2024-03-11"], 100.0)
        ws = ru.weekly_supply(s, "sunday")                                 # Sunday 03-17 still 100: change a week later
        self.assertAlmostEqual(ws.w["2024-03-11"], 0.0)
        self.assertAlmostEqual(ws.w["2024-03-18"], np.log(2))

    def test_monday(self):
        self.assertEqual(ru.monday("2026-11-08"), "2026-11-02")
        self.assertEqual(ru.monday("2026-11-09"), "2026-11-09")


class TestFundingAndProxy(unittest.TestCase):
    def test_weekly_mean_and_hour_minimum(self):
        f = hourly("2024-03-04", [1e-5, 2e-5])
        f = pd.concat([f, hourly("2024-03-18", [3e-5], hours=100)], ignore_index=True)
        m, n = ru.weekly_funding(f)
        self.assertAlmostEqual(m["2024-03-04"], 1e-5)
        self.assertAlmostEqual(m["2024-03-11"], 2e-5)
        self.assertTrue(np.isnan(m["2024-03-18"]))                        # 100 < 150 hours
        self.assertEqual(int(n["2024-03-18"]), 100)

    def test_parse_funding(self):
        bodies = [[{"coin": "BTC", "fundingRate": "0.0000125", "premium": "0", "time": ru.ms("2026-11-08")}],
                  [{"coin": "BTC", "fundingRate": "0.0000125", "premium": "0", "time": ru.ms("2026-11-08")},
                   {"coin": "BTC", "fundingRate": "0.00002", "premium": "0", "time": ru.ms("2026-11-09")}]]
        f = ru.parse_funding(bodies, "BTC")
        self.assertEqual(len(f), 1)                                        # duplicate dropped, cut applied
        with self.assertRaises(ValueError):
            ru.parse_funding(bodies, "ETH")

    def test_proxy_needs_seven_days_and_v2_books(self):
        days = [ru.add_days("2025-06-02", i) for i in range(13)]
        rows = []
        for d in days:
            for b, v in ((ru.BOOKS["R278 A"], 0.001), (ru.BOOKS["R279 B"], 0.003)):
                rows.append({"book": b, "engine": "v2", "date": d, "net_1x": v, "net_2x": v / 2, "net_3x": v / 3})
        rows.append({"book": ru.BOOKS["R278 A"], "engine": "v1", "date": days[0], "net_1x": 9, "net_2x": 9,
                     "net_3x": 9})
        d = pd.DataFrame(rows)
        d = d[(d.engine == "v2") & d.book.isin(ru.BOOKS.values())]
        p = ru.weekly_proxy(d)
        self.assertAlmostEqual(p.net_1x["2025-06-02"], 0.002)
        self.assertAlmostEqual(p.net_2x["2025-06-02"], 0.001)
        self.assertTrue(np.isnan(p.net_1x["2025-06-09"]))                 # 6 days only
        self.assertEqual(int(p.books_min["2025-06-02"]), 2)


class TestPanelAndNull(unittest.TestCase):
    def make(self, n_weeks=120, beta=1.0, seed=0):
        rng = np.random.default_rng(seed)
        first = "2024-01-01"
        weeks = [ru.add_days(first, 7 * k) for k in range(n_weeks)]
        logs = np.cumsum(rng.normal(0, 0.05, n_weeks))
        supply_end = pd.Series(np.exp(logs) * 1e9, index=weeks)
        w = pd.DataFrame({"s_end": supply_end, "s_prev": supply_end.shift(1)})
        w["w"] = np.log(w.s_end) - np.log(w.s_prev)
        w.loc[weeks[:3], "s_prev"] = 5e7                                   # below $100m: excluded
        w.loc[weeks[:3], "w"] = np.nan
        f = pd.Series(0.0, index=weeks)
        for k in range(1, n_weeks):
            f.iloc[k] = f.iloc[k - 1] + beta * 1e-5 * w.w.fillna(0).iloc[k - 1] / 0.05 + 1e-6 * rng.normal()
        return w, f

    def test_window(self):
        w, f = self.make(n_weeks=160)
        p = ru.panel(w, {"BTC": f}, last_target_end="2026-11-08")
        self.assertEqual(p.index[0], "2024-01-22")
        self.assertEqual(p.index[-1], "2026-10-26")                       # target week 11-02..11-08
        self.assertAlmostEqual(p.d_BTC.iloc[0], f["2024-01-29"] - f["2024-01-22"])

    def test_signal_found_and_gates(self):
        w, f = self.make(n_weeks=150, beta=1.0, seed=3)
        p = ru.panel(w, {"BTC": f, "ETH": f * 1.1}, last_target_end="2026-11-08")
        res = {c: ru.test_coin(p, c) for c in ru.COINS}
        self.assertGreater(res["BTC"]["rho"], 0.5)
        self.assertLess(res["BTC"]["p_one"], 0.05)
        self.assertEqual(res["BTC"]["shifts"], res["BTC"]["n"] - 2 * ru.MIN_SHIFT + 1)
        g = ru.gates(res)
        self.assertTrue(all(g.values()))
        self.assertEqual(ru.verdict(g), "SIGNAL")

    def test_negative_effect_is_null(self):
        w, f = self.make(n_weeks=150, beta=-1.0, seed=4)
        p = ru.panel(w, {"BTC": f, "ETH": f}, last_target_end="2026-11-08")
        res = {c: ru.test_coin(p, c) for c in ru.COINS}
        self.assertLess(res["BTC"]["rho"], -0.5)
        self.assertLess(res["BTC"]["p_neg"], 0.05)
        self.assertEqual(ru.verdict(ru.gates(res)), "NULL")

    def test_noise_not_found(self):
        rng = np.random.default_rng(5)
        ps = [ru.circular_null(rng.normal(size=140), rng.normal(size=140))["p_two"] for _ in range(20)]
        self.assertGreater(np.median(ps), 0.2)

    def test_one_coin_failing_is_null(self):
        res = {"BTC": {"rho": 0.3, "p_one": 0.01, "first_rho": 0.2, "second_rho": 0.3},
               "ETH": {"rho": 0.3, "p_one": 0.2, "first_rho": 0.2, "second_rho": 0.3}}
        self.assertEqual(ru.verdict(ru.gates(res)), "NULL")
        res["ETH"]["p_one"] = 0.01
        res["ETH"]["second_rho"] = -0.1
        g = ru.gates(res)
        self.assertTrue(g["G1_rho_gt_0_and_p_one_lt_0.05_BTC_and_ETH"])
        self.assertFalse(g["G2_both_halves_positive_BTC_and_ETH"])
        self.assertEqual(ru.verdict(g), "NULL")

    def test_halves(self):
        x = np.arange(10.0)
        y = np.r_[np.arange(5.0), -np.arange(5.0)]
        h = ru.halves(x, y)
        self.assertEqual((h["first_n"], h["second_n"]), (5, 5))
        self.assertAlmostEqual(h["first_rho"], 1.0)
        self.assertAlmostEqual(h["second_rho"], -1.0)


if __name__ == "__main__":
    unittest.main()
