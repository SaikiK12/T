import math
import unittest

import numpy as np

from lab import anytime


class Mixture(unittest.TestCase):
    def test_closed_form_matches_integral(self):
        rho, s, n = 0.3, 4.0, 50.0
        lam = np.linspace(0, 20, 200_001)
        dens = 2 * np.exp(-lam ** 2 / (2 * rho ** 2)) / (rho * math.sqrt(2 * math.pi))
        y = np.exp(lam * s - lam ** 2 * n / 2) * dens
        numeric = float(np.sum((y[1:] + y[:-1]) / 2 * np.diff(lam)))
        self.assertAlmostEqual(float(anytime.halfnormal_log_e([s], n, rho)[0]), math.log(numeric), places=5)

    def test_tuned_rho_crosses_at_tstar(self):
        rho, s = anytime.tune_rho(90.0, 0.025)
        self.assertAlmostEqual(float(anytime.halfnormal_log_e([s], 90.0, rho)[0]), math.log(40.0), places=4)
        self.assertGreater(s / math.sqrt(90), 1.96)      # a sequential bar sits above the fixed-n one


class LongRunSd(unittest.TestCase):
    def test_bartlett(self):
        rng = np.random.default_rng(0)
        x = rng.normal(0, 1, 200)
        d = x - x.mean()
        b = int(200 ** (1 / 3))
        v = d @ d / 200 + sum(2 * (1 - k / (b + 1)) * (d[k:] @ d[:-k]) / 200 for k in range(1, b + 1))
        self.assertAlmostEqual(anytime.long_run_sd(x), math.sqrt(v))


class Monitor(unittest.TestCase):
    def test_drift_crosses_and_noise_rarely_does(self):
        rng = np.random.default_rng(7)
        bp = 1e-4
        hits = sum(anytime.monitor(rng.normal(0, 18 * bp, 200))["first_cross"] is not None for _ in range(150))
        self.assertLessEqual(hits, 12)                    # about 2-3% expected; a loose bound for 150 paths
        firsts = [anytime.monitor(rng.normal(12 * bp, 18 * bp, 200))["first_cross"] for _ in range(30)]
        self.assertTrue(all(f is not None for f in firsts))
        self.assertLess(np.median(firsts), 60)
        m = anytime.monitor(np.full(40, 1e-4) + rng.normal(0, 1e-6, 40))
        self.assertIsNone(m["log_e"][0])                  # burn-in
        self.assertEqual(m["first_cross"], 30)            # crosses on the first allowed day


if __name__ == "__main__":
    unittest.main()
