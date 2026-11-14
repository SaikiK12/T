import importlib.util
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_jlphedge", ROOT / "scripts" / "run_jlphedge.py")
jh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jh)
DAY, H = jh.DAY, jh.H


def synthetic(n_days, betas, alpha, seed=0, coins=("SOL", "ETH", "BTC")):
    """Pool stamps whose daily return is alpha + betas . coin returns, and the coins' closes, on days 0..n_days."""
    rng = np.random.default_rng(seed)
    rc = rng.normal(0, 0.03, (n_days, len(coins)))
    rp = alpha + rc @ np.asarray(betas)
    stamp = {0: 1.0}
    closes = {c: {0: 100.0} for c in coins}
    for d in range(1, n_days + 1):
        stamp[d] = stamp[d - 1] * (1 + rp[d - 1])
        for i, c in enumerate(coins):
            closes[c][d] = closes[c][d - 1] * (1 + rc[d - 1, i])
    return stamp, closes


class JLPHedge(unittest.TestCase):
    def test_stamps_take_the_closest_point_within_an_hour(self):
        pts = [(10 * DAY - 5 * 60_000, 2.0), (10 * DAY + 2 * 60_000, 3.0), (11 * DAY + 61 * 60_000, 4.0)]
        st = jh.stamps(pts, 9, 12)
        self.assertEqual(st, {10: 3.0})                  # day 11's only point is 61 minutes late

    def test_spans_skip_a_missing_stamp(self):
        stamp = {0: 1.0, 1: 1.1, 3: 1.21}
        closes = {"ETH": {0: 10.0, 1: 11.0, 2: 12.0, 3: 12.1}}
        sp = jh.spans(stamp, closes, ("ETH",))
        self.assertEqual([(s["a"], s["b"]) for s in sp], [(0, 1), (1, 3)])
        self.assertAlmostEqual(sp[1]["rp"], 0.1)
        self.assertAlmostEqual(sp[1]["rc"][0], 0.1)

    def test_hedge_ratios_recover_the_basket_and_use_only_old_spans(self):
        stamp, closes = synthetic(200, [0.45, 0.1, 0.12], 0.0005)
        sp = jh.spans(stamp, closes, ("SOL", "ETH", "BTC"))
        h = jh.hedge_ratios(sp, 150)
        np.testing.assert_allclose(h, [0.45, 0.1, 0.12], atol=1e-9)
        # only spans ending by day 149 count: corrupting later spans changes nothing
        sp2 = [dict(s, rp=s["rp"] + (5.0 if s["b"] >= 150 else 0.0)) for s in sp]
        np.testing.assert_allclose(jh.hedge_ratios(sp2, 150), h)
        self.assertIsNone(jh.hedge_ratios(sp, 30))       # fewer than 40 spans

    def test_hedged_book_keeps_the_pool_yield(self):
        alpha = 0.001
        stamp, closes = synthetic(300, [0.5], alpha, coins=("ETH",))
        sp = jh.spans(stamp, closes, ("ETH",))
        fday = {"ETH": {}}
        rows = jh.book(sp, fday, ("ETH",), 100, 290, 0.0)
        live = [r for r in rows if not r["idle"]]
        self.assertEqual(len(live), len(rows))
        for r in live:
            self.assertAlmostEqual(r["net"], alpha / 1.5, places=9)   # capital = pool + margin of the 0.5 short

    def test_funding_is_received_by_the_shorts(self):
        stamp, closes = synthetic(200, [0.5], 0.0, coins=("ETH",))
        sp = jh.spans(stamp, closes, ("ETH",))
        fday = {"ETH": {d: (0.0002 * 24, 24) for d in range(201)}}
        r = jh.book(sp, fday, ("ETH",), 150, 150, 0.0)[0]
        self.assertAlmostEqual(r["funding"], 0.5 * 0.0048 / 1.5)

    def test_costs_charge_turnover_against_the_drifted_hedge(self):
        stamp, closes = synthetic(200, [0.5], 0.0, coins=("ETH",))
        sp = jh.spans(stamp, closes, ("ETH",))
        fday = {"ETH": {}}
        ratios = {s["a"]: np.array([0.5]) for s in sp}
        rows = jh.book(sp, fday, ("ETH",), 100, 102, 1.0, ratios)
        self.assertAlmostEqual(rows[0]["cost"] * 1.5, jh.HEDGE_COST * 0.5 + jh.POOL_RT / 365)   # entry
        s0 = next(s for s in sp if s["a"] == 100)
        drift = 0.5 * (1 + s0["rc"][0]) / (1 + s0["rp"])
        self.assertAlmostEqual(rows[1]["cost"] * 1.5, jh.HEDGE_COST * abs(0.5 - drift) + jh.POOL_RT / 365)

    def test_funding_day_is_the_hour_before_settlement(self):
        f = jh.fday_from({10 * DAY: 0.001, 10 * DAY + H: 0.002, 11 * DAY: 0.004})
        self.assertEqual(f[9], (0.001, 1))               # the midnight settlement pays for 23:00-24:00 of day 9
        self.assertEqual(f[10], (0.006, 2))

    def test_summary_and_gate1(self):
        rows = [{"day": d, "days": 1, "idle": 0, "net": 0.0005, "excess": 0.0005 - 0.04 / 365, "hurdle": 0}
                for d in range(100)]
        s = jh.summary(rows, 0, 99)
        self.assertAlmostEqual(s["net_pct_yr"], 0.0005 * 365 * 100)
        self.assertEqual(s["scored_days"], 100)
        good = {"excess_pts_yr": 5.0, "nw_t": 2.6, "max_dd_pct": -1.0}
        self.assertEqual(jh.gate1(good, good, good, 90), "EARNED")
        self.assertEqual(jh.gate1(dict(good, nw_t=2.2), good, good, 180), "NULL")
        self.assertEqual(jh.gate1(dict(good, excess_pts_yr=-1), good, good, 90), "NULL")
        self.assertEqual(jh.gate1(dict(good, nw_t=1.0), good, good, 90), "CONTINUE")

    def test_forward_gap_reenters_the_hedge(self):
        stamp, closes = synthetic(200, [0.5], 0.0, coins=("ETH",))
        sp = [s for s in jh.spans(stamp, closes, ("ETH",)) if s["a"] != 101]      # day 101 unscored
        ratios = {s["a"]: np.array([0.5]) for s in sp}
        rows = jh.book(sp, {"ETH": {}}, ("ETH",), 100, 103, 1.0, ratios)
        self.assertEqual([r["a"] for r in rows], [100, 102, 103])
        self.assertAlmostEqual(rows[1]["cost"] * 1.5, jh.HEDGE_COST * 0.5 + jh.POOL_RT / 365)

    def test_gate0_report_runs_on_synthetic_inputs(self):
        stamp, closes = synthetic(400, [0.45, 0.1, 0.12], 0.0004)
        _, c_eth = synthetic(400, [0.5], 0.0003, seed=1, coins=("ETH",))
        pts = {"J": [(d * DAY - 60_000, v) for d, v in stamp.items()],
               "G": [(d * DAY + 120_000, v * 2) for d, v in stamp.items()]}
        fday = {c: {d: (0.0001 * 24, 24) for d in range(401)} for c in ("SOL", "ETH", "BTC")}
        rep, daily = jh.gate0_report(pts, closes, fday, 0, 100, 390, 400)
        self.assertEqual(set(rep["books"]), {"J", "G"})
        j = rep["books"]["J"]
        self.assertEqual(j["verdict_gate0"], "CONTINUE")
        self.assertGreater(j["summary"]["1x"]["net_pct_yr"], j["summary"]["3x"]["net_pct_yr"])
        self.assertEqual(len([r for r in daily if r[0] == "J"]), 291)
        self.assertIn("window_30_1x", j["diagnostics"])
        self.assertEqual(daily[-1][-2:], ["", ""])                 # book G has one hedge coin

    def test_looks_read_only_the_first_days(self):
        rows = {k: [{"day": d, "days": 1, "idle": 0, "net": 0.002 - 0.0001 * k, "excess": 0.002 - 0.0001 * k
                     - 0.04 / 365, "hurdle": 0.04 / 365} for d in range(200)] for k in (1, 2, 3)}
        for d in range(90, 200):                                     # losses after the first 90 days
            for k in rows:
                rows[k][d]["net"] = rows[k][d]["excess"] = -0.01
        out = jh.looks(rows, 0)
        self.assertEqual(out[90]["through"], jh.label(89))
        self.assertGreater(out[90]["1x"]["excess_pts_yr"], 3.0)
        self.assertEqual(out[180]["decision"], "NULL")


if __name__ == "__main__":
    unittest.main()
