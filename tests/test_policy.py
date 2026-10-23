import unittest

import numpy as np
from scipy import stats as sps

from lab import policy


def noise(D=1000, N=80, seed=0, sd=0.01):
    return np.random.default_rng(seed).normal(0, sd, (D, N))


def plant_regimes(R, frac=0.3, edge=0.3, win=150, n_win=2, seed=1):
    """A share of strategies earn `edge` standard deviations per day, but only inside a few windows of `win` days."""
    rng = np.random.default_rng(seed)
    R = R.copy()
    D, N = R.shape
    who = rng.choice(N, int(frac * N), replace=False)
    for k in who:
        for _ in range(n_win):
            a = rng.integers(0, D - win)
            R[a:a + win, k] += edge * 0.01
    return R, who


def plant_fixed(R, frac=0.15, edge=0.12, seed=2):
    rng = np.random.default_rng(seed)
    R = R.copy()
    who = rng.choice(R.shape[1], int(frac * R.shape[1]), replace=False)
    R[:, who] += edge * 0.01
    return R, who


class BuildingBlocks(unittest.TestCase):
    def test_trailing_moments_match_numpy_and_exclude_today(self):
        R = noise(200, 5, seed=3)
        mean, se = policy.trailing_moments(R, 30)
        t = 100
        np.testing.assert_allclose(mean[t], R[t - 30:t].mean(axis=0), rtol=1e-10)
        np.testing.assert_allclose(se[t], R[t - 30:t].std(axis=0, ddof=1) / np.sqrt(30), rtol=1e-8)
        self.assertTrue(np.isnan(mean[29]).all() and np.isfinite(mean[30]).all())

    def test_episodes_find_a_planted_window(self):
        R = noise(600, 3, seed=4)
        R[200:320, 1] += 0.01                           # one standard deviation a day for 120 days
        eps = policy.episodes(policy.rolling_t(R, 40), thresh=3.0, min_days=30)
        self.assertEqual(len(eps[0]) + len(eps[2]), 0)
        self.assertEqual(len(eps[1]), 1)
        a, b = eps[1][0]
        self.assertTrue(190 < a < 260 and 300 < b < 380)

    def test_persistence_refuses_a_window_that_is_too_short(self):
        out = policy.persistence_test(noise(180, 30, seed=6), L=40, H=14, far_gap=100, n_perm=20)
        self.assertTrue(np.isnan(out["p"]))
        self.assertIn("insufficient", out)

    def test_policy_never_uses_the_future(self):
        R = noise(400, 30, seed=5)
        base = policy.run_policy(R, L=40, K=5, H=7)
        R2 = R.copy()
        R2[250:] = noise(150, 30, seed=99, sd=0.05)
        again = policy.run_policy(R2, L=40, K=5, H=7)
        np.testing.assert_array_equal(base[:250], again[:250])
        self.assertTrue(np.isnan(base[:40]).all() and np.isfinite(base[40:]).all())

    def test_switch_cost_is_charged_per_unit_moved(self):
        R = np.zeros((60, 4))
        R[:, 0] = 0.001                                  # strategy 0 is always best, so the policy never switches after day one
        free = policy.run_policy(R, L=10, K=1, H=5, switch_cost=0.0)
        paid = policy.run_policy(R, L=10, K=1, H=5, switch_cost=0.002)
        self.assertAlmostEqual(float(np.nansum(free) - np.nansum(paid)), 0.002, places=9)   # only the initial entry


class PowerAndSize(unittest.TestCase):
    def test_pure_noise_does_not_look_regime_bound_or_skilled(self):
        reject_persist = reject_policy = 0
        sims = 24
        for s in range(sims):
            R = noise(900, 60, seed=100 + s)
            rng = np.random.default_rng(s)
            reject_persist += policy.persistence_test(R, 40, 20, far_gap=200, n_perm=80, rng=rng)["p"] < 0.05
            reject_policy += policy.policy_vs_random(R, 40, 8, 7, n_rep=150, rng=rng)["p_random"] < 0.05
        self.assertLessEqual(reject_persist / sims, 0.17)
        self.assertLessEqual(reject_policy / sims, 0.17)

    def test_regime_bound_edges_are_found_and_exploited(self):
        R, _ = plant_regimes(noise(1500, 120, seed=7))
        rng = np.random.default_rng(0)
        pers = policy.persistence_test(R, 40, 20, far_gap=250, n_perm=150, rng=rng)
        self.assertLess(pers["p"], 0.05)
        self.assertGreater(pers["ic_recent"], pers["ic_far"] + 0.02)           # recent history predicts better than old
        res = policy.policy_vs_random(R, 40, 10, 7, n_rep=200, rng=rng)
        self.assertLess(res["p_random"], 0.05)
        self.assertGreater(res["t_vs_random"], 3.0)
        self.assertGreater(res["mean"], res["random_mean"] + 0.0003)

    def test_a_static_pick_misses_what_the_adaptive_policy_finds(self):
        R, _ = plant_regimes(noise(1500, 120, seed=8))
        half = len(R) // 2
        best = np.argsort(-R[:half].mean(axis=0))[:10]                          # choose on the first half, hold the second
        static = R[half:, best].mean(axis=1)
        adaptive = policy.run_policy(R, 40, 10, 7)[half:]
        pool = R[half:].mean(axis=1)
        self.assertLess(static.mean() - pool.mean(), 0.0003)                     # no real gain over the pool
        self.assertGreater(np.nanmean(adaptive) - pool.mean(), 0.0006)

    def test_fixed_skill_is_exploitable_but_not_mistaken_for_a_regime(self):
        rejects, ic_far, sims = 0, [], 12
        for s in range(sims):
            R, _ = plant_fixed(noise(1200, 100, seed=300 + s), seed=s)
            rng = np.random.default_rng(s)
            p = policy.persistence_test(R, 40, 20, far_gap=250, n_perm=80, rng=rng)
            rejects += p["p"] < 0.05
            ic_far.append(p["ic_far"])
        self.assertLessEqual(rejects / sims, 0.3)                                # recent is no better than distant
        self.assertGreater(float(np.mean(ic_far)), 0.025)                        # old history still predicts: a fixed edge
        res = policy.policy_vs_random(R, 150, 10, 7, n_rep=150, rng=np.random.default_rng(0))   # permanent skill wants a long lookback
        self.assertLess(res["p_random"], 0.05)

    def test_random_baseline_matches_the_policys_turnover(self):
        R = noise(500, 40, seed=11)
        days, chosen = policy._sets(R, 40, 6, 7, True, 0)
        swaps = [len(set(b.tolist()) - set(a.tolist())) for a, b in zip(chosen[:-1], chosen[1:])]
        rnd_cost = policy.random_policies(R, (days, chosen), 7, switch_cost=1.0, n_rep=3, L=40, rng=np.random.default_rng(0))
        zero = policy.random_policies(R, (days, chosen), 7, switch_cost=0.0, n_rep=3, L=40, rng=np.random.default_rng(0))
        total_cost = float(np.nansum(zero[0] - rnd_cost[0]))                     # cost units charged = (initial K + 2 * swaps) / K
        self.assertAlmostEqual(total_cost, (6 + 2 * sum(swaps)) / 6, places=6)


if __name__ == "__main__":
    unittest.main()
