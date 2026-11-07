import unittest

import numpy as np
import pandas as pd

from scripts import run_qbasis as qb


def synth(n=8, start="2021-01-02", end="2024-06-30", plant=0.0, seed=0, drop=()):
    """A synthetic panel: each coin's basis wanders around its own level; with `plant`, the next day's return falls
    with today's basis rank (high basis, lower return). `drop` = coins with no quarterly (basis NaN)."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    rows = []
    for i in range(n):
        lvl = 0.02 + 0.02 * i
        b = lvl + rng.normal(0, 0.01, len(days))
        z = (i - (n - 1) / 2) / ((n - 1) / 2)                # -1 .. +1 by coin, matching the basis order
        r = rng.normal(0, 0.02, len(days))
        r[1:] += -plant * z
        close = 100 * np.cumprod(1 + r)
        for j, d in enumerate(days):
            rows.append({"day": d.date(), "perp": f"C{i}USDT", "close": close[j], "fund": 1e-4,
                         "qtr_basis_ann": np.nan if i in drop else b[j], "qtr_days": 30.0})
    return pd.DataFrame(rows)


class LegTest(unittest.TestCase):
    def test_legs_sides_and_holds(self):
        w = qb.wide(synth(n=6, end="2021-02-28"))
        sig = qb.signal(w, "level")
        lg = qb.legs(sig, w["close"], 1, 1, "high")
        d = pd.Timestamp("2021-01-10")
        L, S = lg[d]
        self.assertEqual(L, (sig.loc[d].idxmax(),))
        self.assertEqual(S, (sig.loc[d].idxmin(),))
        L2, S2 = qb.legs(sig, w["close"], 1, 2, "low")[d]
        self.assertEqual(set(S2), set(sig.loc[d].nlargest(2).index))
        self.assertEqual(set(L2), set(sig.loc[d].nsmallest(2).index))
        wk = qb.legs(sig, w["close"], 7, 1, "high")
        self.assertTrue(all((t - pd.Timestamp("2021-01-02")).days % 7 == 0 for t in wk))
        self.assertEqual(len(qb.legs(sig, w["close"], 1, 1, "high")), len(sig))

    def test_min_names_and_random_ties(self):
        w = qb.wide(synth(n=6, end="2021-02-28", drop=(0, 1)))      # 4 coins with a quarterly: no book
        self.assertEqual(qb.legs(qb.signal(w, "level"), w["close"], 1, 1, "high"), {})
        w = qb.wide(synth(n=8, end="2021-02-28"))
        flat = w["qtr_basis_ann"] * 0.0
        lg = qb.legs(flat, w["close"], 1, 1, "high")
        longs = {v[0] for v in lg.values()}
        self.assertGreater(len(longs), 2)                             # all tied: not the same coin every day

    def test_chg7(self):
        w = qb.wide(synth(n=5, end="2021-02-28"))
        c = qb.signal(w, "chg7")
        b = w["qtr_basis_ann"]
        d = pd.Timestamp("2021-02-01")
        self.assertAlmostEqual(c.loc[d, "C2USDT"], b.loc[d, "C2USDT"] - b.loc[d - pd.Timedelta(days=7), "C2USDT"])
        self.assertTrue(c.iloc[:7].isna().all().all())

    def test_window_mask(self):
        ts = np.array([pd.Timestamp("2023-12-30").value // 10**6, pd.Timestamp("2023-12-24").value // 10**6])
        self.assertEqual(list(qb.window_mask(ts, 1, "disc")), [True, True])
        self.assertEqual(list(qb.window_mask(ts, 7, "disc")), [False, True])
        self.assertEqual(list(qb.window_mask(ts, 1, "valid")), [False, False])


class EndToEndTest(unittest.TestCase):
    def test_planted_signal_is_found_and_null_is_not(self):
        w = qb.wide(synth(plant=0.004, seed=3))
        res, lgs = qb.build(w)
        out = qb.analyze(w, res, lgs)
        self.assertEqual(out["pick"].split()[:2], ["level", "low"])
        p = out["strategies"][out["pick"]]
        self.assertGreater(p["valid"]["gross"]["mean_bp"], 0)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertIn("C7USDT", out["membership"]["level high h1 k1"]["long"])
        self.assertGreater(out["basis_vs_funding"]["mean_basis_ann_by_year"][2022], 0)
        null = qb.analyze(*((lambda w: (w, *qb.build(w)))(qb.wide(synth(seed=4)))))
        g = null["strategies"]["level low h1 k1"]["valid"]["gross"]
        self.assertLess(abs(g["t"]), 3)

    def test_plumbing_reads_no_signal(self):
        out = qb.plumbing(synth(n=6, end="2021-03-31", drop=(5,)))
        self.assertEqual(out["coins"], [f"C{i}USDT" for i in range(5)])
        self.assertEqual(out["level"]["days"], 89)
        self.assertEqual(out["chg7"]["days"], 82)
        self.assertEqual(out["level"]["names_min"], 5)


if __name__ == "__main__":
    unittest.main()
