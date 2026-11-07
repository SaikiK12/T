import unittest

import numpy as np
import pandas as pd

from scripts import run_lotcap as lc

H, DAY, T0 = lc.H, lc.DAY, lc.T0
D = T0 + 400 * DAY - H                     # a decision: the bar opening at 23:00 the day before 2022-02-05


def bars(closes, start=D, vol=None, funding=()):
    """A coin whose hourly closes from the bar opening at `start` are `closes`; funding = [(t, rate)]."""
    t = start + H * np.arange(len(closes), dtype=np.int64)
    v = np.ones(len(closes)) if vol is None else np.asarray(vol, float)
    ft = np.array([x for x, _ in funding], np.int64)
    fr = np.array([r for _, r in funding], float)
    return lc.Bars(t, np.asarray(closes, float), v, ft, fr)


class ScoreTest(unittest.TestCase):
    def test_lottery_scores(self):
        fx = pd.DataFrame({"t": 0, "sym": list("abcd"), "age": [1.0, 2.0, 3.0, 4.0],
                           "size": [10.0, 9.0, np.nan, 7.0], "vol_mcap": [1.0, 2.0, 3.0, 0.0]})
        sc = lc.scores(fx).set_index("sym")
        self.assertEqual(list(sc.lot_age), [1.0, 0.75, 0.5, 0.25])                  # the youngest is most lottery-like
        self.assertTrue(np.isnan(sc.loc["c", "lot_cluster"]))                         # needs all three
        # a: young 1, small rank 1/3 (size 10 is largest -> -size smallest), vol_mcap 2/3
        self.assertAlmostEqual(sc.loc["a", "lot_cluster"], (1.0 + 1 / 3 + 2 / 3) / 3)
        self.assertAlmostEqual(sc.loc["b", "lot_cluster"], (2 / 3 + 2 / 3 + 1.0) / 3)

    def test_legs_and_rebalances(self):
        ts = np.arange(20, dtype=np.int64) * DAY
        self.assertEqual(list(lc.rebalance_times(ts, 168)), [0, 7 * DAY, 14 * DAY])
        self.assertEqual(len(lc.rebalance_times(ts, 24)), 20)
        sc = pd.DataFrame({"t": 0, "sym": [f"s{i:02d}" for i in range(33)], "lot_age": np.arange(33) / 33.0,
                           "lot_cluster": np.nan})
        lg = lc.legs(sc, "age", [0])
        longs, shorts = lg[0]
        self.assertEqual(len(longs), 6)                                               # floor(33 / 5)
        self.assertEqual(longs[0], "s00")
        self.assertEqual(shorts[-1], "s32")
        self.assertEqual(lc.legs(sc, "cluster", [0]), {})                             # no names
        self.assertEqual(lc.legs(sc.iloc[:29], "age", [0]), {})                       # under MIN_NAMES


class BarsTest(unittest.TestCase):
    def test_reserved_rows_are_dropped(self):
        t = np.array([T0 - H, T0, lc.T1 - H, lc.T1], np.int64)
        b = lc.Bars(t, np.array([1e9, 1.0, 2.0, 1e9]), np.ones(4), np.array([T0 - 1, T0 + H, lc.T1]),
                    np.array([5.0, 0.01, 5.0]))
        self.assertEqual(np.nanmax(b.close), 2.0)
        self.assertEqual(int(b.traded.sum()), 2)
        self.assertAlmostEqual(b.funding(T0 - 10 * H, lc.T1 + H), 0.01)

    def test_short_cover_and_funding(self):
        # entry 100 at the close of the bar opening at D; then 105, (no trade), 125, 90
        b = bars([100, 105, 130, 125, 90], vol=[1, 1, 0, 1, 1],
                 funding=[(D + H, 0.5), (D + 2 * H, 0.001), (D + 4 * H, 0.002), (D + 5 * H, 0.004)])
        r, f, cov = b.leg(D, 4, True, 0.20)
        self.assertTrue(cov)
        self.assertAlmostEqual(r, 0.25)                         # the untraded 130 does not trigger; 125 does
        self.assertAlmostEqual(f, 0.001 + 0.002)                # settlements in (entry close, exit close]
        r, f, cov = b.leg(D, 4, True, 0.0)
        self.assertFalse(cov)
        self.assertAlmostEqual(r, -0.10)
        self.assertAlmostEqual(f, 0.001 + 0.002 + 0.004)
        r, _, cov = b.leg(D, 4, False, 0.20)                    # longs are never covered
        self.assertFalse(cov)
        self.assertAlmostEqual(r, -0.10)

    def test_untradable_legs(self):
        self.assertIsNone(bars([100, 101], vol=[0, 1]).leg(D, 1, True, 0.0))      # entry bar not traded
        end = lc.T1 - 3 * H
        self.assertIsNone(bars([100, 101, 102], start=end).leg(end, 3, True, 0.0))  # would end at T1
        r, _, _ = bars([100, 101, 102, 103], vol=[1, 1, 0, 0]).leg(D, 3, True, 0.0)
        self.assertAlmostEqual(r, 0.01)                           # stops trading: the last traded close


class BookTest(unittest.TestCase):
    def setUp(self):
        self.bars = {"L": bars([100] + [110] * 48), "S": bars([100, 130] + [130] * 47),
                     "S2": bars([100] + [95] * 48)}

    def test_gross_turnover_and_cover_costs(self):
        lg = {D: (("L",), ("S", "S2")), D + DAY: (("L",), ("S", "S2"))}
        rows = lc.book(lg, self.bars, 24, 0.20)
        self.assertEqual(rows[0]["covered"], ["S"])
        self.assertAlmostEqual(rows[0]["gross"], 0.10 + (-0.30 + 0.05) / 2)
        self.assertAlmostEqual(rows[0]["price"], 0.10 - (0.30 - 0.05) / 2)            # no funding here
        net = lc.costed(rows, 1e-3)
        self.assertAlmostEqual(net[0], rows[0]["gross"] - 1e-3 * (2.0 + 0.5))      # enter 2 units, cover S (0.5)
        # day 2: L and S2 held (no trade); S re-entered at 130 (0.5) and flat after, so not covered
        self.assertEqual(rows[1]["covered"], [])
        self.assertAlmostEqual(net[1], rows[1]["gross"] - 1e-3 * 0.5)
        self.assertEqual(list(lc.turnover(rows)), [2.0, 0.5])
        uncovered = lc.book(lg, self.bars, 24, 0.0)
        self.assertEqual(uncovered[0]["covered"], [])
        self.assertAlmostEqual(lc.costed(uncovered, 1e-3)[1], uncovered[1]["gross"])   # nothing changes

    def test_missing_coin_is_left_out(self):
        rows = lc.book({D: (("L", "X"), ("S2",))}, self.bars, 24, 0.0)
        self.assertEqual((rows[0]["n_long"], rows[0]["n_short"]), (1, 1))


class StatsTest(unittest.TestCase):
    def test_windows(self):
        lo = pd.Timestamp("2024-01-01", tz="UTC").value // 10**6
        ts = np.array([lo - H, lo - H + DAY, lo + 30 * DAY], np.int64)
        np.testing.assert_array_equal(lc.window_mask(ts, 24, "valid"), [False, True, True])
        np.testing.assert_array_equal(lc.window_mask(ts, 24, "disc"), [False, False, False])
        end = pd.Timestamp("2023-12-31", tz="UTC").value // 10**6 - H
        # a weekly hold decided at 23:00 on Dec 24 ends at 00:00 Jan 1, the last time a discovery target may read
        np.testing.assert_array_equal(lc.window_mask(np.array([end, end - 5 * DAY]), 168, "disc"), [False, False])
        np.testing.assert_array_equal(lc.window_mask(np.array([end - 6 * DAY, end - 7 * DAY]), 168, "disc"),
                                      [True, True])

    def test_series_stats_and_decision(self):
        ts = np.arange(400, dtype=np.int64) * DAY
        x = np.full(400, 0.001)
        x[:10] = 0.05
        s = lc.series_stats(x, ts, 24)
        self.assertAlmostEqual(s["mean_wo_best_bp"], 10.0)
        self.assertAlmostEqual(s["bp_day"], x.mean() * 1e4)
        good = {"t": 3.0, "mean_bp": 5.0, "mean_wo_best_bp": 2.0}
        rep = {("age", 24, 0.1): {"disc": {"1x": {"t": 2.5, "mean_bp": 4.0}},
                                  "valid": {"1x": good, "2x": {"mean_bp": 1.0}}},
               ("age", 24, 0.0): {"disc": {"1x": {"t": 3.0, "mean_bp": -1.0}},
                                  "valid": {"1x": good, "2x": {"mean_bp": 1.0}}}}
        pick, ok, checks = lc.decide(rep)
        self.assertEqual(pick, ("age", 24, 0.1))                # the higher t has a negative mean: not eligible
        self.assertTrue(ok)
        rep[pick]["valid"]["2x"]["mean_bp"] = -0.5
        self.assertFalse(lc.decide(rep)[1])


class EndToEndTest(unittest.TestCase):
    def test_analyze_on_synthetic_coins(self):
        rng = np.random.default_rng(7)
        syms = [f"C{i:02d}USDT" for i in range(40)]
        days = np.concatenate([np.arange(1000, 1060), np.arange(1100, 1160)])     # 2023-09.. and 2024-01..
        ts = T0 + days * DAY - H
        fx = pd.DataFrame({"t": np.repeat(ts, len(syms)), "sym": np.tile(syms, len(ts)),
                           "age": rng.normal(5, 1, len(ts) * len(syms)), "size": rng.normal(20, 1, len(ts) * 40),
                           "vol_mcap": rng.normal(0, 1, len(ts) * 40)})
        n = (lc.T1 - T0) // H
        bs = {}
        for s in syms:
            c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
            bs[s] = lc.Bars(T0 + H * np.arange(n, dtype=np.int64), c, np.ones(n), np.array([], np.int64),
                            np.array([]))
        _, res = lc.build(fx, bs)
        out = lc.analyze(res)
        self.assertEqual(len(out["strategies"]), lc.TRIALS)
        self.assertIn(out["verdict"], ("NULL", "PARTIAL"))
        self.assertEqual(set(out["spa"]), {"disc", "valid"})
        self.assertEqual(len(out["covered_minus_uncovered"]), 12)
        a = out["strategies"]["age h24 cover0"]
        self.assertGreater(a["valid"]["1x"]["periods"], 40)
        self.assertEqual(a["valid"]["covers_per_period"], 0.0)
        self.assertTrue(np.isfinite(out["parity"]["age_h24_cover0_price_bp_day"]))
        self.assertEqual(len(lc.bars_digest(bs)), 64)


if __name__ == "__main__":
    unittest.main()
