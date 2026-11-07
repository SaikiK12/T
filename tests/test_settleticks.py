import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from lab import prereg
from scripts import run_settleticks as st

S = st.S
T0 = 1_740_067_200_000                          # 2025-02-20 16:00 UTC, an invented settlement


def tape(rows):
    """rows: (seconds after T0, price, seller took liquidity)."""
    t = np.array([T0 + int(round(r[0] * S)) for r in rows], np.int64)
    return {"t": t, "price": np.array([r[1] for r in rows], float), "qty": np.ones(len(rows)),
            "bm": np.array([r[2] for r in rows], bool)}


class TestFills(unittest.TestCase):
    def setUp(self):
        self.tk = tape([(-5, 100.0, False), (-0.001, 101.0, True), (0, 100.5, True), (16, 99.0, False),
                        (17, 98.0, True), (61, 97.0, False), (62, 96.0, True), (70, 95.0, False)])

    def test_first_side(self):
        self.assertEqual(st.first_side(self.tk, T0 + 15 * S, T0 + 60 * S, True), 4)    # first seller-taken trade
        self.assertEqual(st.first_side(self.tk, T0 + 15 * S, T0 + 60 * S, False), 3)
        self.assertEqual(st.first_side(self.tk, T0 + 18 * S, T0 + 60 * S, True), -1)

    def test_taker_fill_flags(self):
        self.assertEqual(st.taker_fill(self.tk, T0 + 60 * S, False), (5, 0))         # a buy within 5 s
        self.assertEqual(st.taker_fill(self.tk, T0 + 63 * S, True, other=10 * S), (7, 1))  # no sell; either side
        self.assertEqual(st.taker_fill(self.tk, T0 + 80 * S, True), (7, 2))          # nothing after: last before
        empty = tape([])
        self.assertEqual(st.taker_fill(empty, T0, True), (-1, 3))

    def test_short_scalp(self):
        g, i, j, flag = st.scalp(self.tk, T0, -1, 15, 60)
        self.assertEqual((i, j, flag), (4, 5, 0))                                     # sell at 98, buy at 97
        self.assertAlmostEqual(g, -(97.0 / 98.0 - 1))

    def test_long_scalp_mirrors(self):
        g, i, j, _ = st.scalp(self.tk, T0, 1, 15, 60)
        self.assertEqual((i, j), (3, 6))                                              # buy at 99, sell at 96
        self.assertAlmostEqual(g, 96.0 / 99.0 - 1)

    def test_no_entry_trade_before_the_exit_is_no_trade(self):
        self.assertIsNone(st.scalp(self.tk, T0, -1, 18, 60))

    def test_nothing_after_the_exit_fill_is_read(self):
        a = st.scalp(self.tk, T0, -1, 15, 60)[0]
        tk = {k: v.copy() for k, v in self.tk.items()}
        tk["price"][6:] = [1.0, 500.0]
        self.assertEqual(a, st.scalp(tk, T0, -1, 15, 60)[0])


class TestPathFlow(unittest.TestCase):
    def test_path_starts_from_the_last_trade_before_T(self):
        tk = tape([(-5, 100.0, False), (-0.001, 101.0, True), (0, 100.5, True), (2, 99.99, True)])
        p = st.path(tk, T0, -1, (-10, -1, 0, 1, 2))
        self.assertTrue(np.isnan(p[-10]))
        self.assertAlmostEqual(p[-1], -(100.0 / 101.0 - 1))
        self.assertAlmostEqual(p[0], -(100.5 / 101.0 - 1))                            # a trade at T counts at T
        self.assertAlmostEqual(p[2], -(99.99 / 101.0 - 1))
        self.assertIsNone(st.path(tape([(0, 1.0, True)]), T0, -1))

    def test_flow_units(self):
        rows = [(-600 + k, 10.0, k % 2 == 0) for k in range(540)]                   # base: 10 quote a second
        rows += [(0.5, 20.0, True), (0.6, 10.0, False)]                              # in [0, 1): sold 20, bought 10
        f = st.flow(tape(rows), T0, -1)
        self.assertAlmostEqual(f[(0, 1)], (20.0 - 10.0) / 1 / 10.0)
        self.assertAlmostEqual(st.flow(tape(rows), T0, 1)[(0, 1)], -1.0)
        self.assertTrue(np.isnan(st.flow(tape([(0.5, 1.0, True)]), T0, -1)[(0, 1)]))


class TestDecision(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(st.ENTRY, 15)
        self.assertEqual(st.EXITS, (30, 60, 120, 300))
        self.assertIn(st.PRIMARY, st.EXITS)
        self.assertEqual(st.TRIALS, 7)
        self.assertEqual(st.BONF_T, 2.24)
        self.assertEqual(list(st.scalp_set())[:4], ["in15_out30", "in15_out60", "in15_out120", "in15_out300"])
        self.assertIn(0, st.PATH)

    def test_halves_and_calendar(self):
        T = np.array([T0, T0 + 3 * st.base.DAY, T0 + 9 * st.base.DAY])
        self.assertEqual(st.calendar_days(T), 10)
        self.assertEqual(st.halves(T).tolist(), [True, True, False])

    def test_describe_and_decide(self):
        x = pd.DataFrame({"coin": ["A", "A", "B", "C"], "T": [T0, T0, T0 + 9 * st.base.DAY, T0 + 9 * st.base.DAY],
                          "seen": [True, False, False, True], "gross": [0.01, 0.003, 0.002, 0.004],
                          "flag": [0, 1, 2, 0]})
        d = st.describe(x, "in15_out60", 10)
        n1 = x.gross - 2 * st.COST_BP / 1e4
        self.assertAlmostEqual(d["net1_bp"], n1.mean() * 1e4)
        self.assertAlmostEqual(d["unseen_net1_bp"], n1[~x.seen].mean() * 1e4)
        self.assertEqual(d["best_coin"], "A")
        self.assertAlmostEqual(d["wo_best_net1_bp"], n1[2:].mean() * 1e4)
        self.assertAlmostEqual(d["day1_bp"], n1.sum() * 1e4 / 10)
        self.assertEqual((d["exit_other_side"], d["exit_stale"]), (1, 1))
        ok = {"t1": 2.1, "net2_bp": 0.5, "half1_net1_bp": 1.0, "half2_net1_bp": 0.1, "wo_best_net1_bp": 0.3,
              "unseen_net1_bp": 0.2}
        self.assertEqual(st.decide(ok)["verdict"], "PASS")
        for k, v in (("t1", 1.99), ("t1", float("nan")), ("net2_bp", 0.0), ("half2_net1_bp", -0.1),
                     ("wo_best_net1_bp", -1.0), ("unseen_net1_bp", 0.0)):
            self.assertEqual(st.decide({**ok, k: v})["verdict"], "NULL", k)


class TestFiles(unittest.TestCase):
    def test_check_data(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            folder = root / "data" / "settle_ticks"
            p = folder / "binance" / "AAAUSDT" / f"{T0}.parquet"
            p.parent.mkdir(parents=True)
            pd.DataFrame({"t": [T0], "price": [1.0], "qty": [1.0], "buyer_maker": [True], "agg_id": [1]}).to_parquet(p)
            prov = root / "prov.json"
            prov.write_text(json.dumps({"file_hashes": [{"path": p.relative_to(root).as_posix(),
                                                         "sha256": prereg.sha256_file(p)}]}))
            self.assertEqual(st.check_data(prov, folder, root), 1)
            tk = st.ticks("AAAUSDT", T0, folder)
            self.assertEqual(tk["t"].tolist(), [T0])
            self.assertTrue(tk["bm"][0])
            p.write_bytes(p.read_bytes() + b"x")
            with self.assertRaises(prereg.PreregError):
                st.check_data(prov, folder, root)

    def test_load_hops(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d)
            base = pd.DataFrame({"coin": ["BBBUSDT", "AAAUSDT"], "T": [T0 + 3600_000, T0], "d": [-1, 1],
                                 "e": [0.004, 0.006], "f_hat": [-0.004, 0.006], "interval_h": [8, 4]})
            pd.concat([base.assign(book=st.BOOK), base.iloc[[1]].assign(book=st.SEEN),
                       base.assign(book="mexc+lighter th0.3%")]).to_csv(src / "hops.csv.gz", index=False)
            h = st.load_hops(src)
            self.assertEqual(h.coin.tolist(), ["AAAUSDT", "BBBUSDT"])                 # in T order
            self.assertEqual(h.seen.tolist(), [True, False])


if __name__ == "__main__":
    unittest.main()
