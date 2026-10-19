import unittest

import numpy as np

from lab import propfirm as pf


def gambler(mu, sigma, a, b):
    """P(Brownian motion with drift reaches +a before -b)."""
    if mu == 0:
        return b / (a + b)
    k = 2 * mu / sigma ** 2
    return (1 - np.exp(k * b)) / (np.exp(-k * a) - np.exp(k * b))


class PropFirmTests(unittest.TestCase):
    def rules(self, **kw):
        base = dict(name="t", account=100_000, fee=500, targets=(0.10,), daily_loss=0.0, max_dd=0.10)
        base.update(kw)
        return pf.Rules(**base)

    def test_pass_probability_matches_the_analytic_barrier(self):
        rng = np.random.default_rng(1)
        for mu in (0.0, 0.0005):
            r = rng.normal(mu, 0.01, 200_000)
            out = pf.evaluate(r, self.rules(), 1.0, n=4000, horizon=3000, funded_days=0, block=1, seed=2)
            a = 0.10 + 0.583 * 0.01                     # discrete steps overshoot a barrier by about 0.583 sigma
            self.assertAlmostEqual(out["p_pass"], gambler(mu, 0.01, a, a), delta=0.03)
            self.assertEqual(out["fail_time"], 0)

    def test_daily_loss_breaks_on_one_bad_day(self):
        paths = np.array([[0.01, -0.06, 0.2]])
        o = pf.run_phase(paths, self.rules(daily_loss=0.05), 0.10)
        self.assertFalse(o.passed[0])
        self.assertEqual(o.reason[0], 1)
        self.assertEqual(o.days[0], 2)

    def test_intraday_steps_count_for_the_daily_limit(self):
        day = np.array([-0.03, -0.03, 0.05, 0.02])      # closes -1% but touches -6% intraday
        o = pf.run_phase(day[None, :], self.rules(daily_loss=0.05), 0.10, steps_per_day=4)
        self.assertEqual(o.reason[0], 1)

    def test_trailing_lock_floor_stops_at_the_start(self):
        up = np.r_[np.full(10, 0.02), np.full(10, -0.03)]      # +20%, then down 3% a day
        trail = pf.run_phase(up[None, :], self.rules(dd_mode="trailing", max_dd=0.05), 1.0)
        lock = pf.run_phase(up[None, :], self.rules(dd_mode="trailing_lock", max_dd=0.05), 1.0)
        self.assertEqual(trail.reason[0], 2)
        self.assertEqual(trail.days[0], 12)                    # floor 1.15 broken at 1.14
        self.assertEqual(lock.reason[0], 2)
        self.assertEqual(lock.days[0], 17)                     # floor locked at 1.00, broken at 0.99

    def test_consistency_delays_the_pass(self):
        path = np.array([[0.08, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01]])
        free = pf.run_phase(path, self.rules(), 0.10)
        cons = pf.run_phase(path, self.rules(consistency=0.5), 0.10)
        self.assertEqual(free.days[0], 3)
        self.assertEqual(cons.days[0], 9)                      # best day 8% <= 0.5 x 16%

    def test_too_small_to_pass_loses_the_fee(self):
        r = np.random.default_rng(3).normal(0, 0.01, 50_000)
        out = pf.evaluate(r, self.rules(), 0.05, n=500, horizon=60, funded_days=90, block=1)
        self.assertEqual(out["p_pass"], 0.0)
        self.assertAlmostEqual(out["ev"], -500.0)

    def test_drift_raises_the_pass_rate(self):
        rng = np.random.default_rng(4)
        p = [pf.evaluate(rng.normal(mu, 0.01, 50_000), self.rules(), 1.0, n=2000, horizon=400, funded_days=0,
                         block=1, seed=5)["p_pass"] for mu in (-0.0005, 0.0, 0.0005)]
        self.assertLess(p[0], p[1])
        self.assertLess(p[1], p[2])

if __name__ == "__main__":
    unittest.main()
