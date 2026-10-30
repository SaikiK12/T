import unittest

import numpy as np
import pandas as pd

from scripts import run_fundxs as fx
from scripts import run_qbasis as qb


def synth(n=60, start="2021-01-02", end="2024-06-30", plant=0.0, seed=0, base=0.0003, late=()):
    """A synthetic panel: each coin's daily funding wanders around its own level (some at the base rate exactly);
    with `plant`, the next day's price return falls with the coin's funding rank. Volume rank = coin order. `late`
    = coins that start trading 40 days in."""
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    rows = []
    for i in range(n):
        lvl = base + 0.0002 * (i - n / 2) / n
        f = np.full(len(days), base) if i % 3 == 0 else lvl + rng.normal(0, 0.0002, len(days))
        z = (i - (n - 1) / 2) / ((n - 1) / 2)
        r = rng.normal(0, 0.02, len(days))
        r[1:] += -plant * z
        close = 100 * np.cumprod(1 + r)
        for j, d in enumerate(days):
            if i in late and j < 40:
                continue
            rows.append({"day": d.date(), "perp": f"C{i:02d}USDT", "close": close[j], "fund": f[j],
                         "rank_qvol30": float(i + 1)})
    return pd.DataFrame(rows)


class SignalTest(unittest.TestCase):
    def test_signal_sums_inside_history(self):
        w = fx.wide(synth(n=6, end="2021-03-31", late=(2,)))
        s3 = fx.signal(w, "fund3")
        d = pd.Timestamp("2021-02-01")
        f = w["fund"]
        self.assertAlmostEqual(s3.loc[d, "C01USDT"], f.loc[d - pd.Timedelta(days=2):d, "C01USDT"].sum())
        self.assertTrue(s3.iloc[:2].isna().all().all())
        first = w["close"]["C02USDT"].first_valid_index()
        self.assertTrue(np.isnan(s3.loc[first + pd.Timedelta(days=1), "C02USDT"]))     # window starts before listing
        self.assertFalse(np.isnan(s3.loc[first + pd.Timedelta(days=2), "C02USDT"]))
        self.assertTrue(fx.signal(w, "fund30").iloc[:29].isna().all().all())

    def test_windows_match_r301(self):
        self.assertEqual(fx.WINDOWS, qb.WINDOWS)
        self.assertEqual(fx.COST, qb.COST)
        self.assertEqual(fx.TRIALS, 8)


class LegTest(unittest.TestCase):
    def test_legs_quintiles_and_holds(self):
        w = fx.wide(synth(n=60, end="2021-03-31"))
        sig = fx.signal(w, "fund3")
        uni = fx.universe(w, 50)
        lg = fx.legs(sig, uni, 1)
        d = pd.Timestamp("2021-02-10")
        L, S = lg[d]
        self.assertEqual((len(L), len(S)), (10, 10))
        row = sig.loc[d][uni.loc[d]]
        self.assertLessEqual(row[list(L)].max(), row[list(S)].min())                   # long the lowest funding
        self.assertTrue(all(int(s[1:3]) < 50 for s in L + S))                          # inside the top 50
        wk = fx.legs(sig, uni, 7)
        self.assertTrue(all((t - pd.Timestamp("2021-01-02")).days % 7 == 0 for t in wk))
        self.assertEqual(len(fx.legs(sig, fx.universe(w, 150), 1)[d][0]), 12)          # 60 names: 12 a leg

    def test_min_names_and_random_ties(self):
        w = fx.wide(synth(n=25, end="2021-02-28"))
        self.assertEqual(fx.legs(fx.signal(w, "fund3"), fx.universe(w, 150), 1), {})
        w = fx.wide(synth(n=60, end="2021-03-31"))
        flat = fx.signal(w, "fund3") * 0.0
        lg = fx.legs(flat, fx.universe(w, 150), 1)
        self.assertGreater(len({v[0] for v in lg.values()}), 5)                        # all tied: not one fixed leg


class EndToEndTest(unittest.TestCase):
    def test_planted_signal_is_found_and_null_is_not(self):
        w = fx.wide(synth(plant=0.002, seed=3))
        res, price, lgs = fx.build(w)
        out = fx.analyze(w, res, price, lgs)
        p = out["strategies"][out["pick"]]
        self.assertGreater(p["valid"]["gross"]["t"], 2)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        pt = out["parts"]["fund3 h1 top150"]["disc"]
        self.assertAlmostEqual(pt["gross"], pt["price"] + pt["funding"], places=6)
        self.assertGreater(pt["fund_short"], 0)                                        # shorts collect high funding
        self.assertGreater(out["ties"]["fund3 top150"]["disc"]["median_modal_share"], 0.3)
        self.assertLess(out["leg_ranks"]["fund3 h1 top50"]["disc"]["long"], 51)
        self.assertEqual(out["r276_parity"]["periods"], len(res[("fund3", 1, 150)]))
        null = fx.analyze(*((lambda w: (w, *fx.build(w)))(fx.wide(synth(seed=4)))))
        g = null["strategies"]["fund3 h1 top150"]["valid"]
        self.assertLess(abs(g["gross"]["t"]), 3)

    def test_plumbing_reads_no_signal(self):
        out = fx.plumbing(synth(n=40, end="2021-03-31", late=(39,)))
        self.assertEqual(out["perps"], 40)
        self.assertEqual(out["fund3 top150"]["days"], 87)
        self.assertEqual(out["fund30 top150"]["days"], 60)
        self.assertEqual(out["fund3 top50"]["names_min"], 39)


if __name__ == "__main__":
    unittest.main()
