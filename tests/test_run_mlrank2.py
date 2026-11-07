import unittest

import numpy as np
import pandas as pd

from scripts import run_mlrank as ml
from scripts import run_mlrank2 as m2
from tests.test_run_mlrank import synth


def dying(n_perps=40, end="2024-06-30", seed=5, die_every=6):
    """synth() with a survivorship leak: every `die_every`-th perp trades like the rest, then falls 10% a day over its
    last 5 days and stops trading (at a staggered day). Only the survivors are 'listed on other venues' (n_venues 3
    against 1), so n_venues knows who dies and the prices do not, until the fall."""
    df = synth(n_perps=n_perps, end=end, seed=seed)
    days = pd.date_range("2021-01-02", end, freq="D")
    keep = []
    for i in range(n_perps):
        p = f"P{i:02d}USDT"
        g = df[df.perp == p].copy()
        if i % die_every == 0:
            stop = days[150 + 28 * i]
            g = g[pd.to_datetime(g.day) < stop].copy()
            r = np.random.default_rng(i).normal(0.0, 0.02, len(g))
            r[0], r[-5:] = 0.0, -0.10
            g["close"] = 100 * np.cumprod(1 + r)
            g["ret"] = np.r_[np.nan, r[1:]]
            g["n_venues"] = 1
        keep.append(g)
    return pd.concat(keep, ignore_index=True)


class SetupTest(unittest.TestCase):
    def test_features_and_trials(self):
        self.assertEqual(m2.LEAKY, ["n_venues", "fund_gap7", "kimchi7"])
        self.assertTrue(set(m2.LEAKY) <= set(ml.PIT))
        self.assertEqual(m2.CLEAN, [f for f in ml.PIT if f not in m2.LEAKY])
        self.assertEqual(len(m2.CLEAN), 24)
        self.assertEqual(len(m2.STRATS), 6)
        self.assertEqual(m2.TRIALS, 7)
        self.assertTrue(all(k[2] == "clean" for k in m2.STRATS))

    def test_dead_perps_and_leg_share(self):
        df = dying(n_perps=12, end="2022-06-30")
        w, f, uni = ml.prepare(df)
        dead = m2.dead_perps(w)
        self.assertEqual(dead, {"P00USDT", "P06USDT"})
        t = pd.Timestamp("2022-01-03").value // 10**6
        rows = [{"t": t, "w": {"P00USDT": -0.5, "P01USDT": -0.5, "P02USDT": 1.0}}]
        sh = m2.dead_share(rows, dead, 1, "disc")
        self.assertEqual(sh, {"long": 0.0, "short": 0.5})


class EndToEndTest(unittest.TestCase):
    def test_leak_is_found_only_by_the_leaky_features(self):
        df = dying()
        keys = [("ridge", 1, "clean"), ("ridge", 1, "leak")]
        w, res, ics = m2.build(df, keys=keys)
        out = m2.analyze(w, res, ics)
        s = out["strategies"]
        self.assertGreater(s["ridge h1 leak"]["disc"]["short_bp"], s["ridge h1 clean"]["disc"]["short_bp"])
        leak, clean = (out["dead_share"][f"ridge h1 {s}"]["disc"]["short"] for s in ("leak", "clean"))
        self.assertGreater(leak, 0.3)                       # dying names are about 10% of the universe
        self.assertLess(clean, leak / 2)
        self.assertEqual(out["pick"] is None or out["pick"].endswith("clean"), True)
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertLess(out["universe_dead_share"]["disc"], 0.2)

    def test_plumbing_reads_no_return(self):
        out = m2.plumbing(dying(n_perps=12, end="2022-06-30"))
        self.assertEqual(out["dead_perps"], 2)
        self.assertEqual(out["coverage"]["n_venues"]["2021"], [1.0, 1.0])
        self.assertEqual(set(out["coverage"]), set(m2.CLEAN + m2.LEAKY))


if __name__ == "__main__":
    unittest.main()
