import unittest

import numpy as np
from scipy import stats as sps

from lab import inference as inf


class SharpeTests(unittest.TestCase):
    def test_psr_matches_the_formula(self):
        got = inf.psr(0.1, 0.0, 100)
        want = sps.norm.cdf(0.1 * np.sqrt(99) / np.sqrt(1 + 0.25 * 2 * 0.01))
        self.assertAlmostEqual(float(got), float(want), places=12)
        self.assertGreater(inf.psr(0.2, 0.0, 100), inf.psr(0.1, 0.0, 100))
        self.assertLess(inf.psr(0.1, 0.05, 100, skew=-1.0, kurt=8.0), inf.psr(0.1, 0.05, 100))   # fat left tail hurts

    def test_expected_max_sr_tracks_the_simulated_maximum(self):
        rng = np.random.default_rng(0)
        sim = rng.standard_normal((20000, 100)).max(axis=1).mean()
        self.assertAlmostEqual(inf.expected_max_sr(100, 1.0), sim, delta=0.1)
        self.assertEqual(inf.expected_max_sr(1, 1.0, 0.3), 0.3)
        self.assertGreater(inf.expected_max_sr(1000, 1.0), inf.expected_max_sr(10, 1.0))

    def test_dsr_has_the_right_size_and_some_power(self):
        rng = np.random.default_rng(1)
        N, T, sims = 50, 400, 300
        naive = deflated = 0
        for _ in range(sims):
            r = rng.normal(0, 0.01, (T, N))
            srs = inf.sharpe(r)
            b = int(srs.argmax())
            naive += inf.psr(srs[b], 0.0, T, sps.skew(r[:, b]), sps.kurtosis(r[:, b], fisher=False)) > 0.95
            deflated += inf.dsr(r[:, b], srs) > 0.95
        self.assertGreater(naive / sims, 0.7)          # the best of 50 noise strategies almost always "looks significant"
        self.assertLess(deflated / sims, 0.12)         # deflating by the number of trials restores roughly 5%
        hits = 0
        T = 1000
        for _ in range(sims // 3):
            r = rng.normal(0, 0.01, (T, N))
            r[:, 7] += 0.0016                          # per-period Sharpe 0.16, t about 5
            srs = inf.sharpe(r)
            b = int(srs.argmax())
            hits += inf.dsr(r[:, b], srs) > 0.95
        self.assertGreater(hits / (sims // 3), 0.5)


class PboTests(unittest.TestCase):
    def test_noise_averages_one_half_and_a_persistent_edge_gives_near_zero(self):
        rng = np.random.default_rng(2)
        # one noise dataset is a single draw (PBO ranges 0.15 to 0.91 across datasets); the mean is what theory fixes
        vals = [inf.cscv_pbo(rng.normal(0, 0.01, (800, 30)), 16, max_combos=400, rng=rng)["pbo"] for _ in range(60)]
        self.assertTrue(0.4 < float(np.mean(vals)) < 0.6)
        edge = rng.normal(0, 0.01, (1600, 30))
        edge[:, 4] += 0.0015
        self.assertLess(inf.cscv_pbo(edge, 16, max_combos=1000, rng=rng)["pbo"], 0.1)


class SpaTests(unittest.TestCase):
    def test_incomplete_data_cannot_generate_a_small_bootstrap_pvalue(self):
        for bad in (np.nan, np.inf, -np.inf):
            x = np.zeros((30, 2))
            x[5, 1] = bad
            for function in (inf.spa, inf.model_confidence_set):
                with self.subTest(function=function.__name__, bad=bad):
                    with self.assertRaises(ValueError):
                        function(x, n_boot=10)

    def test_bootstrap_resolution_and_parameters_are_explicit(self):
        rng = np.random.default_rng(45)
        x = rng.normal(0.2, 0.01, (100, 2))
        out = inf.spa(x, n_boot=10)
        self.assertGreaterEqual(out["consistent"], 1.0 / 11)
        for kwargs in ({"n_boot": 1}, {"block": 0}, {"block": np.nan}):
            with self.assertRaises(ValueError):
                inf.spa(x, **kwargs)

    def test_size_and_power_under_a_noise_universe(self):
        rng = np.random.default_rng(3)
        n, K, sims = 300, 20, 60
        rej = 0
        for _ in range(sims):
            rej += inf.spa(rng.normal(0, 1, (n, K)), n_boot=300, block=5, rng=rng)["consistent"] < 0.05
        self.assertLessEqual(rej / sims, 0.12)
        hit = 0
        for _ in range(sims):
            d = rng.normal(0, 1, (n, K))
            d[:, 3] += 0.25                            # t about 4.3
            hit += inf.spa(d, n_boot=300, block=5, rng=rng)["consistent"] < 0.05
        self.assertGreater(hit / sims, 0.85)

    def test_poor_strategies_inflate_the_reality_check_but_not_spa(self):
        rng = np.random.default_rng(4)
        n = 400
        d = np.hstack([rng.normal(0, 1, (n, 5)), rng.normal(-0.6, 1, (n, 400))])
        d[:, 0] += 0.14                                # a modest real edge
        out = inf.spa(d, n_boot=400, block=5, rng=rng)
        self.assertLess(out["consistent"], out["upper"])
        self.assertLessEqual(out["lower"], out["consistent"])


class McsTests(unittest.TestCase):
    def test_bad_models_are_eliminated_and_equal_models_survive_together(self):
        rng = np.random.default_rng(5)
        n = 500
        loss = rng.normal(1.0, 1.0, (n, 7))
        loss[:, 4:] += 0.5                             # three clearly worse models
        alive, p = inf.model_confidence_set(loss, alpha=0.10, n_boot=400, block=5, rng=rng)
        self.assertEqual(sorted(alive), [0, 1, 2, 3])
        self.assertTrue((p[[4, 5, 6]] < 0.10).all())
        kept = 0
        sims = 150                                     # nominal coverage is 0.90; 150 draws leave a standard error of 0.025
        for _ in range(sims):
            a, _ = inf.model_confidence_set(rng.normal(0, 1, (300, 6)), 0.10, n_boot=300, block=5, rng=rng)
            kept += len(a) == 6
        self.assertGreater(kept / sims, 0.80)


class OnlineFdrTests(unittest.TestCase):
    def test_gamma_is_a_sub_probability_sequence(self):
        g = inf._gamma(np.arange(1, 2_000_001))
        self.assertLessEqual(float(g.sum()), 1.0)
        self.assertTrue((g >= 0).all())

    def test_no_discoveries_means_no_wealth_spent_beyond_w0(self):
        rej, lev = inf.lord_plus(np.ones(500), alpha=0.05)
        self.assertFalse(rej.any())
        self.assertLessEqual(float(lev.sum()), 0.025 + 1e-9)

    def test_controls_false_discoveries_on_mixed_streams_and_keeps_power(self):
        rng = np.random.default_rng(6)
        fdp, power, any_null = [], [], 0
        for _ in range(300):
            is_signal = rng.random(150) < 0.10
            p = np.where(is_signal, rng.beta(0.05, 20, 150), rng.random(150))
            rej, _ = inf.lord_plus(p, 0.05)
            fdp.append(((rej & ~is_signal).sum() / max(rej.sum(), 1)))
            power.append((rej & is_signal).sum() / max(is_signal.sum(), 1))
        self.assertLess(float(np.mean(fdp)), 0.08)
        self.assertGreater(float(np.mean(power)), 0.3)
        for _ in range(400):
            any_null += inf.lord_plus(rng.random(100), 0.05)[0].any()
        self.assertLess(any_null / 400, 0.08)

    def test_ledger_matches_batch_and_rejections_earn_wealth_back(self):
        p = [0.9, 1e-9, 0.5, 1e-6, 0.8]
        led = inf.OnlineFDR(0.05)
        decisions = [led.test(x)[0] for x in p]
        self.assertEqual(decisions, list(inf.lord_plus(p, 0.05)[0]))
        _, lev = inf.lord_plus(p, 0.05)
        self.assertGreater(lev[2], inf.lord_plus([0.9, 0.9, 0.5], 0.05)[1][2])   # level after a rejection beats one without

    def test_bh(self):
        p = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
        self.assertEqual(int(inf.bh(p, 0.05).sum()), 2)
        self.assertEqual(int(inf.bh(np.ones(10), 0.05).sum()), 0)


class ShrinkageTests(unittest.TestCase):
    def test_winners_curse_is_removed_when_there_is_no_real_spread(self):
        rng = np.random.default_rng(7)
        m = rng.normal(0, 1, 300)
        se = np.ones(300)
        post, _, mu0, tau2 = inf.eb_shrink(m, se)
        top = np.argsort(m)[-5:]
        self.assertGreater(float(m[top].mean()), 1.5)                  # naive top-5 looks great: pure selection bias
        self.assertLess(tau2, 0.25)                                    # the spread is estimated as (almost) nothing
        self.assertLess(abs(float(post[top].mean()) - mu0), 0.3)       # so the shrunk top-5 sits at the grand mean

    def test_shrinkage_cuts_error_when_effects_do_vary(self):
        rng = np.random.default_rng(8)
        true = rng.normal(0.2, 1.0, 400)
        se = rng.uniform(0.5, 2.0, 400)
        m = true + rng.normal(0, 1, 400) * se
        post, _, _, tau2 = inf.eb_shrink(m, se)
        self.assertLess(float(((post - true) ** 2).mean()), float(((m - true) ** 2).mean()))
        self.assertTrue(0.5 < tau2 < 1.6)


if __name__ == "__main__":
    unittest.main()
