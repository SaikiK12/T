"""R336 levels_mexc0_v1 on invented numbers: the zero-fee core, the spread costs, the policy and the books."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_levels_mexc0 as lm

H, DAY = lm.H, lm.DAY


def row(sym, base, taker, maker, state=0):
    return {"symbol": sym, "baseCoin": base, "takerFeeRate": taker, "makerFeeRate": maker, "state": state}


def events(rows):
    """rows: (symbol, decision row on R333's grid, exit row, g, sig, E_sigma, c)."""
    f = pd.DataFrame(rows, columns=["symbol", "row", "exit", "g", "sig", "E_sigma", "c"])
    f["t"] = lm.GRID0 + f.pop("row") * H
    return f


class Core(unittest.TestCase):
    def test_zero_fee_on_every_snapshot_and_trading(self):
        snaps = [[row("A_USDT", "A", 0, 0), row("B_USDT", "B", 0, 0), row("C_USDT", "C", 0, 0, state=1)],
                 [row("A_USDT", "A", 0, 0), row("B_USDT", "B", 0.0004, 0), row("C_USDT", "C", 0, 0)]]
        core, base = lm.zero_fee_core(snaps)
        self.assertEqual(core, {"A_USDT"})
        self.assertEqual(base, {"A_USDT": "A"})

    def test_median_half_spread_drops_bad_quotes(self):
        t = pd.DataFrame({"symbol": ["A"] * 4, "t_bid1": [99.0, 99.0, 0.0, 101.0], "t_ask1": [101.0, 101.0, 1.0, 100.0]})
        self.assertAlmostEqual(lm.half_spreads(t)["A"], 100.0)   # 2 / 200 x 1e4; the zero bid and crossed quote drop

    def test_cheapest_contract_per_coin_with_a_floor(self):
        med = pd.Series({"A_USDT": 0.4, "A_USDC": 0.2, "B_USD1": 7.0})
        out = lm.coin_costs({"A_USDT": "A", "A_USDC": "A", "B_USD1": "B"}, med)
        self.assertEqual(out["AUSDT"][0], "A_USDC")
        self.assertAlmostEqual(out["AUSDT"][2], 1e-4)            # 0.2 bp floored to 1 bp
        self.assertAlmostEqual(out["BUSDT"][2], 7e-4)


class Rules(unittest.TestCase):
    def test_policy_needs_four_times_the_one_way_cost(self):
        ev = events([("X", 0, 1, 0.0, 0.02, 0.21, 1e-3), ("X", 2, 3, 0.0, 0.02, -0.21, 1e-3),
                     ("X", 4, 5, 0.0, 0.02, 0.19, 1e-3), ("X", 6, 7, 0.0, 0.02, np.nan, 1e-3)])
        np.testing.assert_array_equal(lm.policy(ev), [1, -1, 0, 0])   # 0.0042 and 0.0038 against 0.004

    def test_manual_cap_keeps_the_first_trades_of_each_day(self):
        rows = [("X%d" % k, k, k + 1, 0.0, 0.02, 1.0, 1e-4) for k in range(10)]
        rows.append(("Y", 0, 1, 0.0, 0.02, 3.0, 1e-4))          # same hour as X0, larger |expected|
        rows.append(("Z", 30, 31, 0.0, 0.02, 1.0, 1e-4))        # the next day
        ev = events(rows)
        kept = lm.manual_cap(ev, np.ones(len(ev), int), cap=3)
        self.assertEqual(ev.symbol[kept != 0].tolist(), ["X0", "X1", "Y", "Z"])

    def test_manual_cap_breaks_ties_by_larger_expected(self):
        ev = events([("X", 0, 1, 0.0, 0.02, 1.0, 1e-4), ("Y", 0, 1, 0.0, 0.02, 3.0, 1e-4)])
        kept = lm.manual_cap(ev, np.ones(2, int), cap=1)
        self.assertEqual(ev.symbol[kept != 0].tolist(), ["Y"])

    def test_net_and_day_sums_with_empty_days(self):
        d = lm.GRID0 // DAY
        ev = events([("X", 0, 1, 0.01, 0.02, 1.0, 1e-3), ("Y", 1, 2, -0.004, 0.02, -1.0, 1e-3),
                     ("X", 50, 51, 0.002, 0.02, 1.0, 1e-3)])
        net, day, sym = lm.trades(ev, np.array([1, -1, 1]), 2)
        np.testing.assert_allclose(net, [0.01 - 0.004, 0.004 - 0.004, 0.002 - 0.004])
        s = lm.day_sums(net, day, d, d + 4)
        np.testing.assert_allclose(s.values, [0.006, 0.0, -0.002, 0.0])

    def test_decision_needs_all_five(self):
        p = {"1x": {"t": 2.1, "bp_per_day_wo_best10": 1, "bp_per_day_first_half": 1, "bp_per_day_second_half": 1,
                    "bp_per_day_wo_best_coin": 1}, "2x": {"bp_per_day": 0.5}}
        self.assertEqual(lm.decide(p)[0], "PARTIAL")
        p["1x"]["bp_per_day_wo_best_coin"] = -0.1
        self.assertEqual(lm.decide(p)[0], "NULL")


class Grid(unittest.TestCase):
    def test_exit_row_closes_on_r333s_grid(self):
        # R333's first saved event: decision bar 2022-01-01 00:00 (row 8760), timeout exit row 8772
        self.assertEqual(lm.exit_close_ms(8772), int(pd.Timestamp("2022-01-01 13:00", tz="UTC").timestamp() * 1000))

    def test_grid_check_rejects_bad_exits_and_overlaps(self):
        lm.check_grid(events([("X", 10, 22, 0, 1, 1, 1), ("X", 23, 24, 0, 1, 1, 1)]))
        with self.assertRaises(ValueError):
            lm.check_grid(events([("X", 10, 23, 0, 1, 1, 1)]))      # 13 h
        with self.assertRaises(ValueError):
            lm.check_grid(events([("X", 10, 10, 0, 1, 1, 1)]))      # no hour held
        with self.assertRaises(ValueError):
            lm.check_grid(events([("X", 10, 15, 0, 1, 1, 1), ("X", 15, 16, 0, 1, 1, 1)]))

    def test_concurrency_counts_overlapping_trades(self):
        ev = events([("X", 0, 5, 0, 1, 1, 1), ("Y", 2, 4, 0, 1, 1, 1), ("Z", 10, 11, 0, 1, 1, 1)])
        self.assertEqual(lm.concurrency(ev, np.array([1, 1, 1]))["max"], 2)
        self.assertEqual(lm.concurrency(ev, np.array([1, 0, 1]))["max"], 1)

    def test_stats_drop_best_days_and_best_coin(self):
        d = lm.GRID0 // DAY
        net = np.array([0.05, 0.01, -0.01, 0.01])
        day = np.array([d, d + 1, d + 2, d + 3])
        sym = np.array(["A", "B", "B", "B"])
        s = lm.sum_stats(net, day, sym, d, d + 4, best=1)
        self.assertEqual(s["best_coin"], "A")
        self.assertAlmostEqual(s["bp_per_day_wo_best_coin"], 1e4 * 0.01 / 4, places=1)
        self.assertAlmostEqual(s["bp_per_day_wo_best10"], 1e4 * 0.01 / 3, places=1)

    def test_only_frozen_ticker_files_are_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "PREREG.md"
            p.write_text("x\n```inputs\n" + "a" * 64 + "  data/recorders/mexc_ticker/2026-10-20/12.parquet\n"
                         + "b" * 64 + "  scripts/run_levels_mexc0.py\n```\n")
            self.assertEqual(lm.frozen_ticker_files(p), ["data/recorders/mexc_ticker/2026-10-20/12.parquet"])


if __name__ == "__main__":
    unittest.main()
