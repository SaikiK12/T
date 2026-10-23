import unittest
from dataclasses import replace
from unittest import mock

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

    def test_firm_costs_are_charged_only_on_a_gross_stream(self):
        rules = self.rules(cost_side=0.0004, swap_day=0.00033)
        net = pf.net_of_costs([0.01, -0.01], rules, turnover=[2.0, 0.0], exposure=1.0)
        np.testing.assert_allclose(net, [0.01 - 0.0008 - 0.00033, -0.01 - 0.00033])
        hourly = pf.net_of_costs(np.zeros(24), rules, exposure=1.0, steps_per_day=24)
        self.assertAlmostEqual(hourly.sum(), -0.00033)
        rng = np.random.default_rng(3)
        r = rng.normal(0.002, 0.01, 2000)
        turn = rng.uniform(0, 2, 2000)
        kw = dict(n=2000, horizon=300, funded_days=0, block=1, seed=4)
        plain = pf.evaluate(r, rules, 1.0, **kw)
        self.assertEqual(plain, pf.evaluate(r, self.rules(), 1.0, **kw))          # no turnover: r is already net
        charged = pf.evaluate(r, rules, 1.0, turnover=turn, exposure=1.0, **kw)
        self.assertEqual(charged, pf.evaluate(pf.net_of_costs(r, rules, turn, 1.0), self.rules(), 1.0, **kw))
        self.assertLess(charged["p_pass"], plain["p_pass"])

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

    def funded(self, r, n=400, **kw):
        rules = self.rules(payout_days=10, split=1.0, **kw)
        return pf.funded_payouts(r, rules, 1.0, n, 60, 1, 1, np.random.default_rng(6))

    def test_payout_cap_limits_each_payment(self):
        r = np.full(1000, 0.01)                                # +1% a day: 10% profit per 10-day cycle
        free = self.funded(r)
        capped = self.funded(r, payout_cap=2_000)
        self.assertAlmostEqual(free.mean(), 6 * 10_000, delta=1e-6)   # 6 cycles x (10% of 100k), split 1
        self.assertTrue(np.all(capped <= 6 * 2_000 + 1e-6))

    def test_payout_cap_applies_before_the_split(self):
        r = np.full(1000, 0.01)
        rules = self.rules(payout_days=10, split=0.9, payout_cap=2_000)
        paid = pf.funded_payouts(r, rules, 1.0, 50, 60, 1, 1, np.random.default_rng(6))
        self.assertAlmostEqual(paid.mean(), 6 * 0.9 * 2_000, delta=1e-6)   # each request 2,000, trader keeps 90%

    def test_partial_payout_leaves_a_cushion(self):
        r = np.full(1000, 0.01)
        half = self.funded(r, payout_share=0.5)
        # cycle k withdraws half of 10% plus the cushion left before it: 0.1 x (1 - 0.5^k)
        self.assertAlmostEqual(half[0], 100_000 * sum(0.1 * (1 - 0.5 ** k) for k in range(1, 7)), delta=1.0)

    def test_denied_payouts_pay_nothing(self):
        r = np.full(1000, 0.01)
        self.assertEqual(self.funded(r, payout_deny=1.0).sum(), 0.0)

    def test_floor_after_payout_ends_accounts_sooner(self):
        r = np.random.default_rng(7).normal(0.0, 0.01, 50_000)
        free = self.funded(r, n=2000)
        locked = self.funded(r, n=2000, floor_after_payout=1.0)
        self.assertLess(locked.mean(), free.mean())


    def topstep_cycle_payout(self, cycles, **changes):
        rules = replace(pf.PRESETS["topstep_50k"], **changes)
        paths = [np.asarray(cycle, float)[None, :] / rules.account for cycle in cycles]
        self.assertTrue(all(len(cycle) == rules.payout_days for cycle in cycles))
        with mock.patch.object(pf, "bootstrap", side_effect=paths):
            return pf.funded_payouts(np.zeros(sum(map(len, cycles))), rules, 1.0, 1,
                                     sum(map(len, cycles)), 1, 1, np.random.default_rng(6))[0]

    def test_topstep_retained_cushion_does_not_qualify_after_a_losing_cycle(self):
        first = [4000 / 14] * 14
        losing = [150] * 5 + [-1250] + [0] * 8  # five winning days, but net -500
        # First gross request 2000, trader 1800, cushion 2000. The next balance
        # is 1500: no new profit since that payout, so no additional 675 is due.
        self.assertAlmostEqual(self.topstep_cycle_payout([first, losing]), 1800, places=6)

    def test_topstep_profit_reference_survives_loss_and_partial_recovery(self):
        first = [4000 / 14] * 14
        losing = [150] * 5 + [-1250] + [0] * 8
        partial_recovery = [150] * 5 + [-350] + [0] * 8
        # Cushion path: 2000 -> 1500 -> 1900. The positive third cycle still
        # has not recovered the balance left after the last successful payout.
        self.assertAlmostEqual(self.topstep_cycle_payout([first, losing, partial_recovery]),
                               1800, places=6)
        recovered = [150] * 5 + [-649.99] + [0] * 8
        # Final cushion 2000.01: first newly eligible request is 1000.005.
        self.assertAlmostEqual(self.topstep_cycle_payout([first, losing, partial_recovery, recovered]),
                               1800 + 0.9 * 1000.005, places=6)

    def test_first_payout_is_exempt_from_the_new_profit_threshold(self):
        # A deliberately high threshold isolates the first-request exemption.
        first = [4000 / 14] * 14
        later = [1000 / 14] * 14
        self.assertAlmostEqual(self.topstep_cycle_payout([first, later], payout_profit_required=10000),
                               1800, places=6)

    def test_topstep_minimum_is_gross_and_includes_125(self):
        for profit, expected in ((250, 112.50), (249.98, 0.0)):
            with self.subTest(profit=profit):
                # Five winning days; subsequent losses leave a gross request of 125 or 124.99.
                cycle = [150] * 5 + [profit - 750] + [0] * 8
                self.assertAlmostEqual(self.topstep_cycle_payout([cycle]), expected, places=6)

    def test_under_minimum_request_neither_withdraws_balance_nor_arms_floor(self):
        below = [150] * 5 + [-500.02] + [0] * 8  # +249.98, request 124.99 rejected
        two_cents = [0.02] + [0] * 13
        self.assertAlmostEqual(self.topstep_cycle_payout([below, two_cents]), 112.50, places=6)
        # An invalid first request must not activate the post-payout zero-loss floor.
        # +200 -> -100 -> +900 remains above the original trailing floor throughout.
        small = [150] * 5 + [-550] + [0] * 8
        loss = [-300] + [0] * 13
        recovery = [200] * 5 + [0] * 9
        self.assertAlmostEqual(self.topstep_cycle_payout([small, loss, recovery]), 405, places=6)

    def test_under_minimum_request_preserves_last_successful_profit_reference(self):
        first = [150] * 5 + [-500] + [0] * 8  # request 125, retain 125
        below = [150] * 5 + [-625.02] + [0] * 8  # +124.98: balance 249.98, request 124.99
        final = [150] * 5 + [-749.98] + [0] * 8  # +0.02: balance 250, valid request 125
        # Artificial USD 100 new-profit threshold isolates reference retention: the
        # final gain is 125 since the successful payout, but only .02 since the rejected request.
        self.assertAlmostEqual(self.topstep_cycle_payout([first, below, final], payout_profit_required=100),
                               225, places=6)

if __name__ == "__main__":
    unittest.main()
