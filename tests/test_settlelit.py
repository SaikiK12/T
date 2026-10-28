import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_settlelit as sl

MIN = sl.MIN
T0 = 1_740_067_200_000                          # 2025-02-20 16:00 UTC, an invented settlement


def bars(closes, vols=None, start=T0 - 10 * MIN):
    c = np.asarray(closes, float)
    v = np.ones(len(c)) if vols is None else np.asarray(vols, float)
    return {"t": start + MIN * np.arange(len(c), dtype=np.int64), "close": c, "traded": (c > 0) & (v > 0)}


class TestTrade(unittest.TestCase):
    def setUp(self):
        self.c = np.full(20, 100.0)              # bars opening T - 10 .. T + 9 min
        self.c[5:10] = 101.0                     # bars opening T - 5 .. T - 1 min close at 101
        self.c[10] = 99.0                        # the bar opening T closes at 99: the last trade before T + 1
        self.c[11:] = 98.0

    def test_short_from_before_T_to_T_plus_1(self):
        p, s_in, s_out = sl.trade(bars(self.c), T0, -1, 0, 1)
        self.assertAlmostEqual(p, -(99.0 / 101.0 - 1))
        self.assertFalse(s_in or s_out)

    def test_earlier_entry_and_later_exit(self):
        p = sl.trade(bars(self.c), T0, -1, 5, 5)[0]                 # entry: the bar opening T - 6 min (100)
        self.assertAlmostEqual(p, -(98.0 / 100.0 - 1))
        self.assertAlmostEqual(sl.trade(bars(self.c), T0, 1, 0, 2)[0], 98.0 / 101.0 - 1)

    def test_untraded_bars_take_the_last_trade_and_are_stale(self):
        v = np.ones(20)
        v[9] = 0                                                     # no trade in [T - 1, T)
        v[10] = 0                                                    # nor in [T, T + 1)
        p, s_in, s_out = sl.trade(bars(self.c, v), T0, -1, 0, 1)
        self.assertEqual(p, 0.0)                                     # both fall back to the bar opening T - 2
        self.assertTrue(s_in and s_out)
        v[:10] = 0
        self.assertIsNone(sl.trade(bars(self.c, v), T0, -1, 0, 1))

    def test_nothing_after_the_exit_is_read(self):
        a = sl.trade(bars(self.c), T0, -1, 0, 1)[0]
        c = self.c.copy()
        c[11:] = 1.0
        self.assertEqual(a, sl.trade(bars(c), T0, -1, 0, 1)[0])


class TestAccounting(unittest.TestCase):
    def test_net_and_funding_sign(self):
        self.assertAlmostEqual(sl.net(0.01, -0.0005, 2.0, 1), 0.01 - 0.0005 - 0.0004)
        self.assertAlmostEqual(sl.net(0.01, 0.0, 2.0, 3), 0.01 - 0.0012)

    def test_settlement_checks_the_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "data" / "lighter_hist" / "open" / "funding"
            folder.mkdir(parents=True)
            p = folder / "AAA.parquet"
            pd.DataFrame({"t": [T0 - 3_600_000, T0], "rate": [0.0001, -0.0005]}).to_parquet(p)
            man = {p.relative_to(root).as_posix(): prereg.sha256_file(p)}
            self.assertEqual(sl.settlement("AAA", T0, man, folder, root), -0.0005)
            with self.assertRaises(prereg.PreregError):
                sl.settlement("AAA", T0 + 1, man, folder, root)          # no settlement then
            with self.assertRaises(prereg.PreregError):
                sl.settlement("AAA", T0, {}, folder, root)                # not in the manifest

    def test_describe_and_decide(self):
        x = pd.DataFrame({"coin": ["A", "A", "B", "C"], "T": [T0, T0, T0 + 9 * sl.base.DAY, T0 + 9 * sl.base.DAY],
                          "price": [0.02, 0.004, 0.003, 0.005], "fund": [-0.001, 0.0, 0.0, -0.0002],
                          "cost_h_bp": [1.0, 4.0, 1.0, 0.5], "stale_in": [False, True, False, False],
                          "stale_out": [False, False, False, True]})
        d = sl.describe(x, "in0_out1")
        n1 = x.price + x.fund - 2 * x.cost_h_bp / 1e4
        self.assertAlmostEqual(d["net1_bp"], n1.mean() * 1e4)
        self.assertEqual(d["best_coin"], "A")
        self.assertAlmostEqual(d["wo_best_net1_bp"], n1[2:].mean() * 1e4)
        self.assertEqual((d["stale_entry"], d["stale_exit"]), (1, 1))
        self.assertAlmostEqual(d["day1_bp"], n1.sum() * 1e4 / 10)
        ok = {"t1": 2.0, "net2_bp": 0.1, "half1_net1_bp": 3.0, "half2_net1_bp": 1.0, "wo_best_net1_bp": 0.5,
              "trim10_net1_bp": 0.2}
        self.assertEqual(sl.decide(ok)["verdict"], "PASS")
        for k, v in (("t1", 1.99), ("net2_bp", -0.1), ("half1_net1_bp", 0.0), ("wo_best_net1_bp", -2.0),
                     ("trim10_net1_bp", float("nan")), ("trim10_net1_bp", -0.1)):
            self.assertEqual(sl.decide({**ok, k: v})["verdict"], "NULL", k)

    def test_constants(self):
        self.assertEqual(sl.TRIALS, 6)
        self.assertEqual(sl.BONF_T, 2.39)
        self.assertEqual(sl.PRIMARY, (0, 1))
        self.assertEqual(sl.name(*sl.PRIMARY), "in0_out1")


class TestHops(unittest.TestCase):
    def test_load_hops(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            (src / "results").mkdir()
            base = pd.DataFrame({"coin": ["BBBUSDT", "AAAUSDT"], "T": [T0 + 3_600_000, T0], "d": [-1, -1],
                                 "e": [0.004, 0.006], "cost_h_bp": [1.09, 4.17]})
            pd.concat([base.assign(book=sl.BOOK), base.iloc[[1]].assign(book=sl.SEEN)]).to_csv(
                src / "results" / "hops.csv.gz", index=False)
            (src / "symbols.csv").write_text("key,mexc,gate,dydx,lighter\nAAAUSDT,,,,AAA\nBBBUSDT,,,,1000BBB\n")
            h = sl.load_hops(src, src / "symbols.csv")
            self.assertEqual(h.coin.tolist(), ["AAAUSDT", "BBBUSDT"])
            self.assertEqual(h.lighter.tolist(), ["AAA", "1000BBB"])
            self.assertEqual(h.seen.tolist(), [True, False])


if __name__ == "__main__":
    unittest.main()
