import unittest

import numpy as np
import pandas as pd

from scripts import run_famswitch as F


def frame(n=300, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    S = pd.DataFrame({"a": rng.normal(0, 0.01, n), "b": rng.normal(0, 0.01, n)}, index=idx)
    S.loc[idx[150:], "a"] += 0.01                     # a becomes the winner from day 150
    return S


class Switch(unittest.TestCase):
    def test_weights_sum_to_one_once_available(self):
        S = frame()
        A = F.available(S)
        for W in (F.w_eq(S, A), F.w_hedge(S, A), F.w_ftl(S, A)):
            s = W.sum(axis=1)[A.any(axis=1)]
            self.assertTrue(np.allclose(s, 1.0))
            self.assertTrue((W.sum(axis=1)[~A.any(axis=1)] == 0).all())

    def test_no_look_ahead(self):
        S = frame()
        A = F.available(S)
        d = S.index[200]
        S2 = S.copy()
        S2.loc[d - pd.Timedelta(days=F.LAG - 1):, "b"] += 1.0     # change only returns on/after d - LAG + 1
        for f in (F.w_hedge, F.w_ftl):
            self.assertTrue(np.allclose(f(S, A).loc[:d].values, f(S2, A).loc[:d].values))

    def test_hedge_and_ftl_follow_the_winner(self):
        S = frame()
        A = F.available(S)
        self.assertGreater(F.w_hedge(S, A)["a"].iloc[-30:].mean(), 0.9)
        self.assertEqual(F.w_ftl(S, A)["a"].iloc[-30:].min(), 1.0)

    def test_switch_cost(self):
        S = frame()
        W = pd.DataFrame({"a": [1.0, 0.0, 0.0], "b": [0.0, 1.0, 1.0]}, index=S.index[:3])
        x, turn = F.run(S.iloc[:3], W, 2)
        self.assertEqual(list(turn), [1.0, 2.0, 0.0])
        self.assertAlmostEqual(x.iloc[1], S["b"].iloc[1] - 2 * F.SWITCH_COST * 2.0)


if __name__ == "__main__":
    unittest.main()
