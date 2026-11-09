import unittest

import numpy as np

from scripts import run_rawlead as rl

BASE = 10_000_000          # 100,000.00 USD in hundredths
JUMP = 3_000               # +3 bp
T_JUMP, CATCH = 70_000, 70_050


def tape(times, mid_fn, lag_fn, half=5, extra_us=lambda T: 0):
    """A bookTicker stream in arrival order: Binance T in ms, receive time = T + lag (ms) + extra_us, off = 0."""
    T = np.asarray(times, np.int64)
    lag = np.array([lag_fn(x) for x in T], np.int64)
    t = (T + lag) * 1000 + np.array([extra_us(x) for x in T], np.int64)
    mid = np.array([mid_fn(x) for x in T], np.int64)
    n = len(T)
    return rl.make_book(t, np.zeros(n), T, np.zeros(n), mid - half, np.full(n, 2 * half), np.full(n, 1000),
                        np.full(n, 1000))


def pair(usdc_lag=lambda T: 80):
    S = tape(np.arange(0, 100_000, 10), lambda T: BASE + (JUMP if T >= T_JUMP else 0), lambda T: 80)
    ct = np.unique(np.r_[np.arange(0, 100_000, 100), CATCH])
    D = tape(ct, lambda T: BASE + (JUMP if T >= CATCH else 0), usdc_lag)
    return S, D


class RawLeadTest(unittest.TestCase):
    def test_refuses_backwards_clock(self):
        with self.assertRaises(SystemExit):
            rl.make_book([2000, 1000], [0, 0], [1, 2], [0, 0], [10, 10], [1, 1], [1, 1], [1, 1])
        with self.assertRaises(SystemExit):
            rl.make_book([1000, 2000], [0, 0], [2, 1], [0, 0], [10, 10], [1, 1], [1, 1], [1, 1])

    def test_lead_event_label_and_frontier(self):
        S, D = pair()
        floor = rl.floor_by_minute([S, D])
        sig = rl.signals(S, D)
        idx, d, q, cnt = rl.events(S, D, 2.0, sig, floor)
        self.assertEqual(cnt["kept"], 1)
        self.assertEqual(S["T"][idx[0]], T_JUMP)
        self.assertEqual(d[0], 1)
        self.assertAlmostEqual(q[0], 0.0)
        times = rl.label(S, D, sig, idx, d)
        self.assertEqual(times[0, 0], CATCH - T_JUMP)
        self.assertTrue(np.isinf(times[0, 1]) and np.isinf(times[0, 2]))
        self.assertEqual(rl.first_outcome(times)[0], 0)
        g1, thin = rl.fills(D, d, rl.arrival(S, idx, q, 1, 250.0), 1000)
        self.assertAlmostEqual(g1[0], np.log((BASE + JUMP - 5) / (BASE + 5)) * 1e4, places=6)
        self.assertFalse(thin[0])              # 1 coin at 100k covers 5k notional
        g250, _ = rl.fills(D, d, rl.arrival(S, idx, q, 250, 250.0), 1000)
        self.assertLess(g250[0], 0)            # the order arrives after the catch-up: only the spread is left
        gm, _ = rl.fills(D, d, rl.arrival(S, idx, q, rl.MACHINE, 250.0), 1000)
        self.assertAlmostEqual(gm[0], g250[0])

    def test_unread_rows_are_drained_and_waited_for(self):
        # the USDC stream queues from T = 69,900: Binance had published 69,900 and 70,000 (still the old price) before
        # the trigger, this container had not read them; the drained machine waits for them and pays the wait
        S, D = pair(usdc_lag=lambda T: 150 if T >= 69_900 else 80)
        floor = rl.floor_by_minute([S, D])
        sig = rl.signals(S, D)
        idx, d, q, cnt = rl.events(S, D, 2.0, sig, floor)
        self.assertEqual((cnt["kept"], cnt["unread_at_trigger"], cnt["kept_unread"]), (1, 1, 1))
        self.assertAlmostEqual(q[0], 70.0)
        _, _, qn, cn = rl.events(S, D, 2.0, sig, floor, naive=True)
        self.assertEqual(cn["kept"], 1)
        self.assertAlmostEqual(qn[0], 0.0)
        # a 220 ms wait is over the 100 ms cap: the drained machine skips the event, the naive one does not
        S, D = pair(usdc_lag=lambda T: 300 if T >= 69_900 else 80)
        floor = rl.floor_by_minute([S, D])
        sig = rl.signals(S, D)
        _, _, _, cnt = rl.events(S, D, 2.0, sig, floor)
        self.assertEqual((cnt["kept"], cnt["queued"]), (0, 1))
        self.assertEqual(rl.events(S, D, 2.0, sig, floor, naive=True)[3]["kept"], 1)

    def test_same_millisecond_move_is_not_a_lead(self):
        # both books move in the same Binance millisecond; the USDC row is read 0.1 ms after the USDT row.
        # The naive machine sees a 3 bp stale quote and buys it after the catch-up; the drained machine sees none.
        S = tape(np.arange(0, 100_000, 10), lambda T: BASE + (JUMP if T >= T_JUMP else 0), lambda T: 80)
        D = tape(np.arange(0, 100_000, 100), lambda T: BASE + (JUMP if T >= T_JUMP else 0), lambda T: 80,
                 extra_us=lambda T: 100 if T == T_JUMP else 0)
        floor = rl.floor_by_minute([S, D])
        sig = rl.signals(S, D)
        _, _, _, cnt = rl.events(S, D, 2.0, sig, floor)
        self.assertEqual(cnt["kept"], 0)
        idx, d, q, cn = rl.events(S, D, 2.0, sig, floor, naive=True)
        self.assertEqual((cn["kept"], cn["unread_at_trigger"]), (1, 1))
        g, _ = rl.fills(D, d, rl.arrival(S, idx, q, rl.MACHINE, 250.0), 1000)
        self.assertLess(g[0], 0)

    def test_queued_trigger_is_excluded(self):
        S = tape(np.arange(0, 100_000, 10), lambda T: BASE + (JUMP if T >= T_JUMP else 0),
                 lambda T: 400 if 69_000 <= T <= 71_000 else (max(80, 400 - (T - 71_000)) if T > 71_000 else 80))
        ct = np.unique(np.r_[np.arange(0, 100_000, 100), CATCH])
        D = tape(ct, lambda T: BASE + (JUMP if T >= CATCH else 0), lambda T: 80)
        floor = rl.floor_by_minute([S, D])
        idx, d, q, cnt = rl.events(S, D, 2.0, rl.signals(S, D), floor)
        self.assertEqual(cnt["queued"], 1)
        self.assertEqual(cnt["kept"], 0)

    def test_first_outcome_ties_go_against_catch(self):
        inf = np.inf
        t = np.array([[50, inf, inf], [100, 100, inf], [inf, inf, 30], [inf, inf, inf], [40, 60, 20]])
        self.assertEqual(rl.first_outcome(t).tolist(), [0, 1, 2, 3, 2])

    def test_classify_windows(self):
        tr = dict(T=np.array([500, 1200, 1500, 2100, 5500, 5600]), side=np.array([1, 1, -1, 1, -1, 1]))
        cls = rl.classify(tr, np.array([1000, 5000]), np.array([1, -1]))
        self.assertEqual(cls.tolist(), [0, 1, -1, 0, 1, -1])

    def test_markout_sign(self):
        D = tape(np.arange(0, 20_000, 100), lambda T: BASE + (JUMP if T >= 5_000 else 0), lambda T: 80)
        tr = dict(T=np.array([4_000, 4_000]), p=np.array([100_000.05, 99_999.95]), side=np.array([1, -1]))
        m = rl.markouts(D, tr, 1000)
        self.assertAlmostEqual(m[0], (np.log(BASE + JUMP) - np.log(BASE + 5)) * 1e4, places=6)
        self.assertLess(m[1], 0)

    def test_block_bootstrap_and_verdict(self):
        rng = np.random.default_rng(0)
        ci = rl.block_boot(np.ones(200), np.repeat(np.arange(20), 10), rng)
        self.assertEqual((ci["mean"], ci["lo"], ci["hi"], ci["p_le0"]), (1.0, 1.0, 1.0, 0.0))
        asset = np.array(["BTC", "ETH"] * 100)
        self.assertEqual(rl.verdict(np.ones(200), asset, ci=ci), "PASS")
        self.assertEqual(rl.verdict(-np.ones(200), asset, ci=dict(ci, lo=-1.0)), "NULL")
        self.assertEqual(rl.verdict(np.ones(50), asset[:50], ci=ci), "INCONCLUSIVE")
        self.assertEqual(rl.verdict(np.ones(200), np.array(["BTC"] * 200), ci=ci), "NULL")
        d = rl.block_boot_diff(np.r_[np.full(50, 2.0), np.zeros(150)], np.r_[np.ones(50), np.zeros(150)],
                               np.repeat(np.arange(20), 10), rng)
        self.assertAlmostEqual(d["diff"], 2.0)

    def test_crossing_delay(self):
        self.assertEqual(rl.crossing_delay([1, 25, 50, 100], [4, 3, 2, 0], 2), 50.0)
        self.assertEqual(rl.crossing_delay([1, 25, 50, 100], [4, 3, 2, 0], 5), 0.0)
        self.assertIsNone(rl.crossing_delay([1, 25, 50, 100], [4, 3, 2, 0], -1))
        self.assertAlmostEqual(rl.crossing_delay([1, 25, 50, 100], [4, 3, 2, 0], 2.5), 37.5)

    def test_trial_count(self):
        self.assertEqual(rl.TRIALS, 4 * 10 * 3 + 4 * 6 + 4)


if __name__ == "__main__":
    unittest.main()
