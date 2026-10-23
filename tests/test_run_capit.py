import unittest

import numpy as np
import pandas as pd

from scripts import run_capit as cp
from scripts import run_qbasis as qb


def synth(n=60, start="2021-01-02", end="2024-09-30", plant=0.0, seed=0, crash_every=40, dip_p=0.004):
    """A synthetic panel. Each coin random-walks; with probability dip_p a coin drops 25% in one day (no follow-through).
    Every `crash_every` days all coins fall 7% and open interest falls 12%. With `plant`, a coin at least 20% below
    its 25-day average gains `plant` the next day."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    T = len(days)
    close = np.full((T, n), np.nan)
    ret = np.zeros((T, n))
    oi = np.zeros((T, n))
    p = np.full(n, 100.0)
    o = np.full(n, 1e6)
    for t in range(T):
        r = rng.normal(0, 0.02, n)
        r[rng.random(n) < dip_p] -= 0.25
        crash = t > 0 and t % crash_every == 0
        if crash:
            r -= 0.07
        if t >= cp.MA and plant:
            ma = np.nanmean(close[t - cp.MA:t], axis=0)
            r[(close[t - 1] / ma - 1) <= -0.2] += plant
        p = p * (1 + r) if t else p
        o = o * (0.88 if crash else 1.0) * np.exp(rng.normal(0, 0.01, n))
        close[t], ret[t], oi[t] = p, r if t else 0.0, o
    rows = []
    for j in range(n):
        for t, d in enumerate(days):
            rows.append({"day": d.date(), "perp": f"C{j:02d}USDT", "close": close[t, j], "ret": ret[t, j],
                         "fund": 1e-4, "oi_usd": oi[t, j], "rank_qvol30": float(j + 1)})
    return pd.DataFrame(rows)


class SignalTest(unittest.TestCase):
    def test_gap_dips_and_no_exit(self):
        days = pd.date_range("2021-01-02", periods=40, freq="D")
        c = pd.DataFrame({"A": 100.0, "B": 100.0}, index=days)
        c.iloc[30:, 0] = 65.0                                       # A falls 35% on day 30
        c.iloc[33:, 1] = np.nan                                     # B stops trading after day 32
        w = {"close": c, "rank_qvol30": c * 0 + 1}
        g = cp.ma_gap(w)
        self.assertTrue(g.iloc[:24].isna().all().all())
        self.assertAlmostEqual(g.iloc[30, 0], 65 / ((24 * 100 + 65) / 25) - 1)
        self.assertTrue(cp.dips(w, 0.30).iloc[30, 0])
        self.assertFalse(cp.dips(w, 0.40).iloc[30, 0])
        nx = cp.no_exit(w, 1)
        self.assertTrue(nx.iloc[32, 1])
        self.assertFalse(nx.iloc[31, 1])
        self.assertFalse(cp.no_exit(w, 5).iloc[29, 1])

    def test_triggers(self):
        w = cp.wide(synth(n=40, end="2022-12-31", dip_p=0.0))
        share, bt = cp.breadth(w)
        chg, med, ct = cp.cascade(w)
        crash_days = [d for i, d in enumerate(w["close"].index) if i and i % 40 == 0]
        self.assertTrue(all(ct.loc[d] for d in crash_days))
        self.assertLess(chg.loc[crash_days[3]], -0.08)
        self.assertEqual(int(ct.sum()), len(crash_days))
        self.assertTrue(bt.iloc[:180].eq(False).all())             # needs 180 prior days
        self.assertTrue(((share >= cp.BREADTH_FLOOR) | ~bt).all())

    def test_basket_and_decision(self):
        w = cp.wide(synth(n=40, end="2021-06-30"))
        bk = cp.basket(w, 1)
        ret, fund = cp.targets(w, 1)
        d = pd.Timestamp("2021-03-01")
        self.assertAlmostEqual(bk.loc[d], float((ret.loc[d] - fund.loc[d]).mean()))
        w2 = cp.wide(synth(n=25, end="2021-03-31"))
        self.assertTrue(cp.basket(w2, 1).isna().all())             # fewer than 30 names
        rows = [{"gross": 0.01}, {"gross": -0.02}]
        np.testing.assert_allclose(cp.decision(rows, "dip", 1, 2, 0.5), [0.01 - 8 * cp.COST, -0.02 - 8 * cp.COST])
        np.testing.assert_allclose(cp.decision(rows, "cascade", 2, 1, 0.003),
                                   [0.01 - 2 * cp.COST - 0.003, -0.02 - 2 * cp.COST - 0.003])

    def test_constants(self):
        self.assertEqual(cp.WINDOWS, qb.WINDOWS)
        self.assertEqual(cp.TRIALS, 10)


class EndToEndTest(unittest.TestCase):
    def test_planted_rebound_is_found_and_null_is_not(self):
        w = cp.wide(synth(plant=0.05, seed=3))
        res, trig = cp.build(w)
        out = cp.analyze(w, res, trig)
        self.assertTrue(out["pick"].startswith("dip"))
        p = out["strategies"][out["pick"]]
        self.assertGreater(p["valid"]["1x"]["t"], 2)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertGreater(len(out["trigger_days"]["cascade"]), 20)
        null = cp.analyze(*((lambda w: (w, *cp.build(w)))(cp.wide(synth(seed=4)))))
        g = null["strategies"]["dip20 h1"]["valid"]["gross"]
        self.assertLess(abs(g["t"]), 3)

    def test_plumbing_reads_no_return(self):
        out = cp.plumbing(synth(n=40, end="2021-12-31"))
        self.assertEqual(out["panel_days"], 364)
        self.assertGreater(out["dip20"]["perp_events"], out["dip40"]["perp_events"])
        self.assertEqual(out["cascade"]["days"], 9)
        self.assertEqual(out["oi_coverage_first_day"], "2021-01-03")


if __name__ == "__main__":
    unittest.main()
