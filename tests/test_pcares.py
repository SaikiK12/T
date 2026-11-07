import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


def module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("run_pcares", ROOT / "scripts" / "run_pcares.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def market(n_days=72, coins=16, b=0.7, seed=0):
    """Hourly returns: a market factor plus each coin's residual, whose running sum is an AR(1) with coefficient b
    (b = 1 is a random walk, no reversion)."""
    rng = np.random.default_rng(seed)
    n_h = n_days * 24
    m = rng.normal(0, 0.01, n_h)
    beta = rng.uniform(0.5, 1.5, coins)
    X = np.zeros((n_h, coins))
    for h in range(1, n_h):
        X[h] = b * X[h - 1] + rng.normal(0, 0.004, coins)
    R = m[:, None] * beta + np.diff(X, axis=0, prepend=0.0)
    R[0] = np.nan
    QV = np.tile(np.arange(coins, 0, -1, dtype=np.float32), (n_h, 1))   # coin 0 trades the most
    return R, QV, np.zeros((n_h, coins), np.float32)


def run(pc, R, QV, FUND, e=1.25, hedge="dollar", K=1, L=72):
    days = np.arange(pc.W // 24, len(R) // 24)
    U_of, model, S, FAST, _ = pc.build(R, QV, days, np.ones(R.shape[1], bool))
    return pc.simulate(R, FUND, days, U_of, model[K], S[K, L], FAST[K, L], days[0] * 24, e, hedge, len(days))


class TestPcares(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pc = module()

    def test_planted_reversion_earns_gross(self):
        R, QV, FUND = market(b=0.7)
        for hedge in ("dollar", "factor"):
            o = run(self.pc, R, QV, FUND, hedge=hedge)
            self.assertGreater(o["opened"], 20)
            self.assertGreater(o["gross"].sum(), 0.0, hedge)

    def test_random_walk_residual_earns_less(self):
        R, QV, FUND = market(b=0.7, seed=1)
        planted = run(self.pc, R, QV, FUND)["gross"].sum()
        R, QV, FUND = market(b=1.0, seed=1)
        self.assertLess(run(self.pc, R, QV, FUND)["gross"].sum(), planted)

    def test_scores_do_not_read_later_hours(self):
        pc = self.pc
        R, QV, _ = market()
        d0 = pc.W + 24
        U, V, sd = pc.fit_day(R, QV, d0, np.ones(R.shape[1], bool))
        Q, beta = pc.betas(R, d0, U, V, sd, 3)
        s1, f1 = pc.day_scores(R, d0, U, Q, beta, 72)
        R2 = R.copy()
        R2[d0 + 6:] = np.random.default_rng(9).normal(0, 0.05, R2[d0 + 6:].shape)
        U2, V2, sd2 = pc.fit_day(R2, QV, d0, np.ones(R.shape[1], bool))
        Q2, beta2 = pc.betas(R2, d0, U2, V2, sd2, 3)
        s2, f2 = pc.day_scores(R2, d0, U2, Q2, beta2, 72)
        np.testing.assert_array_equal(U, U2)
        np.testing.assert_allclose(s1[:6], s2[:6])
        np.testing.assert_array_equal(f1[:6], f2[:6])

    def test_universe_needs_full_window_and_ranks_by_volume(self):
        pc = self.pc
        R, QV, _ = market(coins=60)
        d0 = pc.W + 24
        R[d0 - 100, 0] = np.nan                                   # the top-volume coin misses one hour
        U, _, _ = pc.fit_day(R, QV, d0, np.ones(60, bool))
        self.assertEqual(len(U), pc.N)
        self.assertNotIn(0, U)
        self.assertEqual(list(U[:3]), [1, 2, 3])

    def test_long_pays_positive_funding(self):
        pc = self.pc
        R, QV, FUND = market()
        FUND[:, :] = 1e-3
        o = run(pc, R, QV, FUND, hedge="factor")
        self.assertTrue(np.isfinite(o["funding"]).all())
        # a book of one long in coin 0 against nothing: funding equals the summed weight times the rate
        n_h = len(R)
        days = np.arange(pc.W // 24, n_h // 24)
        U_of = {d: np.array([0, 1]) for d in days}
        model = {d: (np.zeros((1, 2)), np.zeros((1, 2))) for d in days}
        S = np.full((n_h, pc.N), np.nan)
        S[:, 0], S[:, 1] = -3.0, 3.0                               # coin 0 long, coin 1 short, held throughout
        FAST = np.ones((n_h, pc.N), bool)
        FUND = np.zeros_like(FUND)
        FUND[:, 0] = 1e-3
        o = pc.simulate(R, FUND, days, U_of, model, S, FAST, days[0] * 24, 1.25, "dollar", len(days))
        self.assertAlmostEqual(o["funding"].sum(), 0.5 * 1e-3 * (n_h - 1 - days[0] * 24), places=6)   # FUND is float32
        self.assertEqual(o["opened"], 2)
        self.assertAlmostEqual(o["turnover"].sum(), 1.0)


if __name__ == "__main__":
    unittest.main()
