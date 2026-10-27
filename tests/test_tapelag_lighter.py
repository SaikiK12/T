"""R347 tapelag_lighter_v1 on invented numbers: stretches, quote grids, the deviation, trades, costs and the tests."""
import unittest

import numpy as np
import pandas as pd

from scripts import run_tapelag_lighter as tl


def flat(n, bid=100.0, ask=100.02, size=50.0):
    return (np.full(n, bid), np.full(n, ask), np.full(n, size), np.full(n, size))


class Stretches(unittest.TestCase):
    def test_gaps_and_recorded_breaks_cut(self):
        alive = [0, 1, 2, 3, 9, 10, 11, 20, 21]
        sid = tl.stretches(alive, breaks=[20], n=30, gap_max=5)
        self.assertTrue((sid[0:4] == 0).all())
        self.assertTrue((sid[4:9] == -1).all())          # gap of 6 s > 5 s
        self.assertTrue((sid[9:12] == 1).all())
        self.assertTrue((sid[12:20] == -1).all())        # gap of 9 s
        self.assertEqual(sid[20], 2)                     # the break at 20 cuts between 20 and 21
        self.assertEqual(sid[21], 3)
        self.assertTrue((sid[22:] == -1).all())

    def test_short_gap_without_break_is_one_stretch(self):
        sid = tl.stretches([0, 3, 7], n=10, gap_max=5)
        self.assertTrue((sid[0:8] == 0).all())
        self.assertTrue((sid[8:] == -1).all())

    def test_session_breaks_in_day_seconds(self):
        s = pd.DataFrame({"stream": ["lighter", "binance_book", "lighter"],
                          "end_utc": ["2026-10-22T00:00:10Z", "2026-10-22T00:00:20Z", "2026-10-23T00:00:05Z"]})
        d0 = tl.day_ms("2026-10-22")
        self.assertEqual(tl.session_breaks(s, "lighter", d0).tolist(), [10])
        self.assertEqual(tl.session_breaks(s, "binance_book", d0).tolist(), [20])


class Grid(unittest.TestCase):
    def test_forward_fill_stays_inside_a_stretch(self):
        d0 = 0
        rows = pd.DataFrame({"s": [1000, 4000, 9000], "bid": [1.0, 2.0, 3.0], "ask": [1.1, 2.1, 3.1],
                             "bid_sz": [5.0, 6.0, 7.0], "ask_sz": [5.0, 6.0, 7.0]})
        sid = np.array([0, 0, 0, 0, 0, 0, 1, 1, 1, 1, -1])   # a new stretch at second 6
        b, a, bs, as_ = tl.grid(rows, d0, sid)
        self.assertTrue(np.isnan(b[0]))                      # before the coin's first update
        self.assertEqual(b[1], 1.0)
        self.assertEqual(b[3], 1.0)
        self.assertEqual(b[4], 2.0)
        self.assertEqual(b[5], 2.0)
        self.assertTrue(np.isnan(b[6:9]).all())             # the new stretch has no update until second 9
        self.assertEqual(b[9], 3.0)
        self.assertTrue(np.isnan(b[10]))                    # not connected


class Deviation(unittest.TestCase):
    def test_reference_is_the_median_of_earlier_seconds(self):
        n = 10
        bb, ab = np.full(n, 100.0), np.full(n, 100.0) + 1e-9
        bl, al = np.full(n, 100.0), np.full(n, 100.0) + 1e-9
        bl[9], al[9] = 100.10, 100.10 + 1e-9                 # Lighter 10 bp rich at the last second only
        d, dev = tl.deviation(bl, al, bb, ab, win=5, win_min=3)
        self.assertTrue(np.isnan(dev[:3]).all())
        self.assertAlmostEqual(dev[9], 1e4 * np.log(1.001), places=3)   # the reference excludes second 9
        self.assertAlmostEqual(dev[8], 0.0, places=5)

    def test_crossed_or_missing_quotes_give_nan(self):
        d, _ = tl.deviation(np.array([1.0, 1.0, np.nan]), np.array([0.9, 1.1, 1.1]),
                            np.array([1.0, 1.0, 1.0]), np.array([1.1, 1.1, 1.1]), win=1, win_min=1)
        self.assertTrue(np.isnan(d[0]))
        self.assertTrue(np.isfinite(d[1]))
        self.assertTrue(np.isnan(d[2]))


class Simulate(unittest.TestCase):
    def test_buy_when_cheap_by_more_than_a_round_trip(self):
        n = 40
        bl, al, bs, as_ = flat(n)                            # half-spread 1.0 bp
        dev = np.zeros(n)
        dev[9] = -2.9                                         # below 1 + 2 x 1.0: no trade
        dev[10] = -3.1
        bl[16], al[16] = 100.05, 100.07                      # exit second 10 + 1 + 5
        t, sk = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=0.5)
        self.assertEqual(len(t), 1)
        r = t.iloc[0]
        self.assertEqual((r.s, r.e, r.x, r.side), (10, 11, 16, 1))
        c_e, c_x = 1e4 * 0.01 / 100.01, 1e4 * 0.01 / 100.06
        self.assertAlmostEqual(r.gross, 1e4 * (100.06 / 100.01 - 1))
        self.assertAlmostEqual(r.net1, r.gross - c_e - c_x)
        self.assertAlmostEqual(r.c_e, c_e)

    def test_the_book_cost_is_the_floor_of_a_tight_quote(self):
        n = 40
        bl, al, bs, as_ = flat(n, bid=100.0, ask=100.0002)   # half-spread 0.01 bp
        dev = np.zeros(n)
        dev[10] = 1.9                                         # below 1 + 2 x 0.5
        dev[20] = 2.1
        t, _ = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=0.5)
        self.assertEqual(t.s.tolist(), [20])
        self.assertEqual(t.side.tolist(), [-1])
        self.assertAlmostEqual(t.net1.iloc[0], -1.0)          # flat mid, 0.5 bp a side
        t, _ = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=float("nan"))
        self.assertEqual(len(t), 0)                           # no book cost measured: no trade

    def test_one_position_per_coin(self):
        n = 40
        bl, al, bs, as_ = flat(n)
        dev = np.zeros(n)
        dev[5:9] = 4.0                                        # signals at 5..8; the first trade holds 6..11
        dev[12] = 4.0
        t, _ = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=0.5)
        self.assertEqual(t.s.tolist(), [5, 12])

    def test_funding_hour_and_missing_exit(self):
        n = 7300
        bl, al, bs, as_ = flat(n)
        dev = np.zeros(n)
        dev[3595] = 4.0                                       # hold 3596..3601 spans 01:00
        dev[5000] = -4.0
        al[5006] = np.nan                                     # no quote at the exit
        dev[6000] = -4.0
        t, sk = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=0.5)
        self.assertEqual(sk["funding_hour"], 1)
        self.assertEqual(sk["exit_quote"], 1)
        self.assertEqual(t.s.tolist(), [6000])

    def test_delay_moves_entry_and_exit(self):
        n = 40
        bl, al, bs, as_ = flat(n)
        dev = np.zeros(n)
        dev[10] = -4.0
        t, _ = tl.simulate(dev, bl, al, bs, as_, theta=1.0, hold=5, walk=0.5, delay=3)
        self.assertEqual((t.e.iloc[0], t.x.iloc[0]), (13, 18))


class Costs(unittest.TestCase):
    def test_stress_charges_k_times_the_cost(self):
        t = pd.DataFrame({"gross": [2.0, 2.0], "c_e": [0.5, 1.0], "c_x": [0.5, 2.0]})
        self.assertEqual(tl.stress(t, 1).tolist(), [1.0, -1.0])
        self.assertEqual(tl.stress(t, 3).tolist(), [-1.0, -7.0])

    def test_walk_costs_median_of_both_sides_with_a_floor(self):
        rows = pd.DataFrame({"symbol": ["BTC", "BTC", "BTC", "ETH", "XYZ"], "buy_1k_bp": [0.0, 0.2, 1.0, 0.0, 1.0],
                             "sell_1k_bp": [0.2, 0.4, 3.0, 0.1, 1.0]})
        w = tl.walk_costs(rows, coins=("BTC", "ETH", "SOL"))
        self.assertAlmostEqual(w["BTC"], 0.3)                # sides 0.1, 0.3, 2.0: median 0.3
        self.assertAlmostEqual(w["ETH"], 0.1)                # 0.05 floored to 0.1
        self.assertTrue(np.isnan(w["SOL"]))
        self.assertNotIn("XYZ", w)


class Summary(unittest.TestCase):
    def test_summary_counts_the_top_three_coins(self):
        t = pd.DataFrame({"coin": ["A"] * 4 + ["B"] * 3 + ["C"] * 2 + ["D"],
                          "day": ["d"] * 10, "bucket": list(range(10)), "side": [1, -1] * 5,
                          "gross": [3.0, 3.0, 3.0, 3.0, -2.0, -2.0, -2.0, 4.0, 4.0, 9.0],
                          "c_e": [0.5] * 10, "c_x": [0.5] * 10, "touch_usd": [2000.0] * 10})
        t["net1"] = tl.stress(t, 1)
        out = tl.summarize(t, [("d", b) for b in range(10)], coins=("A", "B", "C", "D"))
        self.assertEqual(out["top3_coins_by_trades"], ["A", "B", "C"])
        self.assertEqual(out["top3_positive_1x"], 2)
        self.assertEqual(out["two_coins_left_out"], ["A", "D"])
        self.assertAlmostEqual(out["1x"]["per_trade_bp"], float(t.net1.mean()), places=3)


class Tests(unittest.TestCase):
    def test_bucket_series_fills_zero(self):
        t = pd.DataFrame({"day": ["a", "a", "b"], "bucket": [1, 1, 3], "net1": [1.0, 2.0, -1.0]})
        x = tl.bucket_series(t, "net1", [("a", 0), ("a", 1), ("b", 3)])
        self.assertEqual(x.tolist(), [0.0, 3.0, -1.0])

    def test_bootstrap_separates_a_real_mean_from_noise(self):
        rng = np.random.default_rng(0)
        X = np.column_stack([rng.normal(0.5, 1.0, 400), rng.normal(0.0, 1.0, 400)])
        t, p, pfw = tl.block_bootstrap(X, block=4, draws=500, seed=1)
        self.assertLess(p[0], 0.01)
        self.assertGreater(p[1], 0.05)
        self.assertTrue((pfw >= p).all())
        t, p, pfw = tl.block_bootstrap(np.column_stack([np.zeros(50), rng.normal(0, 1, 50)]), block=4, draws=50)
        self.assertEqual((p[0], pfw[0]), (1.0, 1.0))          # no trades: undefined t, never a pass

    def test_trimmed_mean(self):
        x = np.r_[np.full(20, 1.0), 100.0, -100.0]
        self.assertEqual(tl.trimmed_mean(x, trim=1), 1.0)

    def test_decide(self):
        base = {"2x": {"per_trade_bp": 0.5}, "trimmed_bucket_mean_1x": 1.0, "top3_positive_1x": 2}
        trials = {(6.0, 5): dict(base), (3.0, 5): dict(base)}
        fam = {"p": {(6.0, 5): 0.01, (3.0, 5): 0.5}, "p_family": {(6.0, 5): 0.03, (3.0, 5): 0.9}}
        self.assertEqual(tl.decide((6.0, 5), fam, trials), "PASS")
        trials[(6.0, 5)]["top3_positive_1x"] = 1                 # fails rule 4, but its family-wise p holds
        self.assertEqual(tl.decide((6.0, 5), fam, trials), "PARTIAL")
        self.assertEqual(tl.decide((6.0, 5), {"p": fam["p"], "p_family": {(6.0, 5): 0.2, (3.0, 5): 0.9}},
                                   trials), "NULL")
        trials[(6.0, 5)]["top3_positive_1x"] = 2
        fam["p"][(6.0, 5)] = 0.2
        self.assertEqual(tl.decide((6.0, 5), fam, trials), "PARTIAL")
        fam["p_family"][(6.0, 5)] = 0.2
        self.assertEqual(tl.decide((6.0, 5), fam, trials), "NULL")


if __name__ == "__main__":
    unittest.main()
