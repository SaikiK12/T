import itertools
import unittest

import numpy as np

from lab.equations import (DAY, HOUR, LABELS, Panel, Forecasts, pooled_ar1, build_forecasts,
                           choose_states, hedge_quantity, simulate, vix_put_cash_pnl)


def toy_panel(days=3, coins=1):
    t0 = 1735689600000  # 2025-01-01
    times = t0 + np.arange(days*24+1)*HOUR
    shape = (len(times), coins, 2)
    return Panel(times, tuple(f"TOY{i}" for i in range(coins)), np.full(shape, 100.),
                 np.ones(shape, bool), np.zeros(shape), np.ones(shape, bool),
                 np.full((coins, 2), .01), np.zeros((coins, 2)), np.zeros((coins, 2)),
                 np.ones(coins, bool), np.zeros(shape, bool))


def dummy_forecasts(p):
    nd, n = (len(p.times)-1)//24+1, len(p.keys)
    return Forecasts(LABELS, np.zeros((2, 3, nd, n, 2)), np.zeros((3, nd, n)),
                     np.ones((nd, n), bool), np.zeros((nd, 2)), np.zeros((3, nd)),
                     np.zeros((3, nd), int), np.zeros((nd, n)))


class EquationTests(unittest.TestCase):
    def test_inventory_optimum_matches_independent_exhaustive_search(self):
        rng = np.random.default_rng(54)
        for _ in range(40):
            score = rng.normal(size=(4, 3))
            held = rng.choice([-1, 0, 1], size=4)
            chosen = choose_states(score, held, slots=2)
            actual = sum(score[i, {0: 0, 1: 1, -1: 2}[int(s)]] for i, s in enumerate(chosen))
            best = max(sum(score[i, {0: 0, 1: 1, -1: 2}[s]] for i, s in enumerate(st))
                       for st in itertools.product((0, 1, -1), repeat=4) if np.count_nonzero(st) <= 2)
            self.assertAlmostEqual(actual, best, places=13)
        self.assertEqual(choose_states(np.zeros((1, 3)), [1]).tolist(), [1])
        self.assertEqual(choose_states(np.zeros((1, 3)), [0]).tolist(), [0])

    def test_rounding_hedges_units_and_checks_both_venue_minima(self):
        np.testing.assert_allclose(hedge_quantity([100, 101], [.1, .01], [0, 0], [0, 0], 250), [2.4, 2.4])
        np.testing.assert_array_equal(hedge_quantity([100, 100], [.03, .2], [0, 0], [0, 0], 100), [0, 0])
        np.testing.assert_array_equal(hedge_quantity([100, 100], [.1, .1], [0, 0], [0, 251], 250), [0, 0])

    def test_funding_before_or_at_entry_is_excluded_and_actual_payments_not_doubled(self):
        p = toy_panel(days=2)
        p.rates[0, 0, 0], p.rates[1, 0, 0] = .5, .7
        p.rates[2, 0, 0], p.rates[24, 0, 0], p.rates[25, 0, 0] = .001, .002, .004
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((3, 1), int))
        np.testing.assert_allclose(r["funding"].sum(axis=0), [-1.75]*3)
        np.testing.assert_allclose(r["cost"].sum(axis=0), [.7, 1.4, 2.1])
        np.testing.assert_allclose(r["net"].sum(axis=0), [-2.45, -3.15, -3.85])
        self.assertTrue(r["scored"].all())
        self.assertEqual(r["entries"], 1)
        self.assertEqual(float(r["final_quantity"].sum()), 0)

    def test_constant_units_follow_price_moves_and_do_not_rebalance_each_day(self):
        p = toy_panel(days=2)
        p.prices[12:] = 110
        p.rates[13, 0, 0] = .001
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((3, 1), int))
        np.testing.assert_allclose(r["funding"].sum(axis=0), [-.275]*3)
        np.testing.assert_allclose(r["cost"].sum(axis=0), [.735, 1.47, 2.205])
        np.testing.assert_allclose(r["price"].sum(axis=0), 0, atol=1e-14)
        self.assertEqual(r["entries"], 1)

    def test_flip_covers_and_reopens_both_legs_with_all_fees(self):
        p = toy_panel(days=2)
        states = np.array([[1], [-1], [0]])
        p.rates[25, 0, 0], p.rates[26, 0, 0] = .001, .002
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=states)
        np.testing.assert_allclose(r["funding"].sum(axis=0), [.25]*3)
        np.testing.assert_allclose(r["cost"].sum(axis=0), [1.4, 2.8, 4.2])

    def test_missing_price_is_unscored_and_bridge_is_realized_before_paired_exit(self):
        p = toy_panel(days=1)
        p.prices[2, 0, 0] = np.nan
        p.fresh[2, 0, 0] = False
        p.prices[3:, 0, 0] = 110
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((2, 1), int))
        self.assertFalse(r["scored"].any())
        np.testing.assert_allclose(r["price"].sum(axis=0), [25]*3)
        self.assertEqual(r["forced"].sum(), 1)
        self.assertFalse(np.any(r["final_quantity"]))

    def test_unknown_funding_is_not_a_scored_zero_payment(self):
        p = toy_panel(days=1)
        p.funding_ok[6, 0, 0] = False
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((2, 1), int))
        self.assertFalse(r["scored"].any())
        self.assertEqual(r["forced"].sum(), 1)

    def test_known_zero_trade_bar_is_not_a_missing_price_or_a_fill(self):
        p = toy_panel(days=1)
        p.fresh[7, 0] = False
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((2, 1), int))
        self.assertTrue(r["scored"].all())
        self.assertEqual(r["forced"].sum(), 0)
        self.assertFalse(any(z["time_ms"] == p.times[7] for z in r["tickets"]))

    def test_unknown_current_funding_blocks_new_inventory_even_with_valid_forecast(self):
        p = toy_panel(days=1)
        p.funding_ok[1, 0, 0] = False
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((2, 1), int))
        self.assertEqual(r["entries"], 0)
        self.assertEqual(r["tickets"], [])

    def test_forced_exit_at_decision_clock_cannot_reenter_on_that_clock(self):
        p = toy_panel(days=3)
        p.funding_ok[24, 0, 0] = False
        p.fresh[24, 0] = False
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((4, 1), int))
        tickets = [z for z in r["tickets"] if z["time_ms"] == p.times[25]]
        self.assertEqual(len(tickets), 1)
        self.assertEqual(tickets[0]["reason"], "data_exit")
        self.assertEqual(tickets[0]["new_mexc"], 0)
        self.assertEqual(r["entries"], 2)  # first day and the following day

    def test_gross_breach_exit_persists_until_tradable_even_if_proxy_price_recovers(self):
        p = toy_panel(days=1)
        p.prices[2, 0] = 3000.
        p.fresh[2, 0] = False
        r = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                     baseline_states=np.ones((2, 1), int))
        self.assertTrue(r["gross_breach"].any())
        self.assertFalse(r["scored"].all())
        self.assertEqual(r["tickets"][-1]["time_ms"], p.times[3])
        self.assertEqual(r["tickets"][-1]["new_mexc"], 0.)

    def test_every_candidate_forecast_ignores_future_prices_and_rates(self):
        p = toy_panel(days=130, coins=2)
        rng = np.random.default_rng(14)
        common = np.cumsum(rng.normal(0, .001, (len(p.times), 2)), axis=0)
        p.prices[:, :, 0] *= np.exp(common)
        p.prices[:, :, 1] = p.prices[:, :, 0] * np.exp(rng.normal(0, .00002, common.shape))
        p.rates[:, :, 1] = .00002
        p.settlement[:] = True
        a = build_forecasts(p)
        d = 105
        p.prices[d*24+1:] *= 1.2
        p.rates[d*24+1:] = .1
        b = build_forecasts(p)
        np.testing.assert_allclose(a.funding[:, :, d], b.funding[:, :, d], equal_nan=True)
        np.testing.assert_allclose(a.basis[:, d], b.basis[:, d], equal_nan=True)
        np.testing.assert_allclose(a.beta[:, d], b.beta[:, d], equal_nan=True)
        self.assertTrue(np.isfinite(a.beta[:, d]).all())
        self.assertTrue((a.basis_training_dates[:, d] >= 20).all())

    def test_ar_centering_and_stability_contract(self):
        x = np.tile(np.arange(30)[:, None], (1, 2)).astype(float)
        self.assertEqual(pooled_ar1(x), .99)
        self.assertEqual(pooled_ar1(np.ones((30, 2))), 0)
        self.assertTrue(np.isnan(pooled_ar1(np.full((30, 2), np.nan))))

    def test_vix_quotes_are_points_with_100_dollar_multiplier_and_vro_payoff(self):
        self.assertEqual(563 * 91 * 100, 5123300)
        self.assertEqual(vix_put_cash_pnl(19, 110, 91, 563), 0)
        self.assertEqual(vix_put_cash_pnl(150, 110, 91, 563), -5123300)
        self.assertEqual(vix_put_cash_pnl(0, 110, 91, 563), 1069700)
        self.assertEqual(vix_put_cash_pnl(20, 130, 110), 0)

    def test_independent_terminal_trade_cashflow_reconstructs_marked_account(self):
        p = toy_panel(days=10, coins=2)
        rng = np.random.default_rng(222)
        p.prices = 100*np.exp(np.cumsum(rng.normal(0, .001, p.prices.shape), axis=0))
        p.rates = rng.normal(0, 1e-5, p.rates.shape)
        states = rng.choice([-1, 0, 1], (11, 2))
        result = simulate(p, dummy_forecasts(p), "reference", int(p.times[0]), int(p.times[-1]),
                          baseline_states=states)
        prices = {int(t): p.prices[j] for j, t in enumerate(p.times)}
        signed_trade_cash = funding_cash = fee = 0.
        for ticket in result["tickets"]:
            dq = np.array([ticket["new_mexc"]-ticket["old_mexc"],
                           ticket["new_lighter"]-ticket["old_lighter"]])
            px = np.array([ticket["mexc_price_proxy"], ticket["lighter_price_proxy"]])
            signed_trade_cash -= float(dq @ px)
            fee += ticket["mexc_cost_1x"]+ticket["lighter_cost_1x"]
        # Independent formula uses only strict-before event ticket inventory,
        # not the simulation's mark-to-market increments.
        for j, t in enumerate(p.times):
            for i, coin in enumerate(p.keys):
                before = [z for z in result["tickets"] if z["coin"] == coin and z["time_ms"] < t]
                q = np.array([before[-1]["new_mexc"], before[-1]["new_lighter"]]) if before else np.zeros(2)
                funding_cash -= float(np.sum(q*p.prices[j, i]*p.rates[j, i]))
        np.testing.assert_allclose(result["net"].sum(axis=0),
                                   [signed_trade_cash+funding_cash-m*fee for m in (1, 2, 3)], atol=1e-9)


if __name__ == "__main__":
    unittest.main()
