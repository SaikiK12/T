"""scripts/run_flow_hl_mc.py (R458): measured main-dex costs on R448's books, offline, with R448's own forward()."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("run_flow_hl_mc", ROOT / "scripts" / "run_flow_hl_mc.py")
fm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fm)
fh, H = fm.fh, fm.H
T0 = fh.ms(fh.FWD_START)                     # 2026-11-12 00:00 UTC


class Costs(unittest.TestCase):
    def test_fee_plus_slippage_on_the_right_row_and_fallbacks(self):
        assumed = np.array([[6e-4, 12e-4, np.nan]] * 4)
        coins = ["A", None, "C"]
        empty = pd.DataFrame(columns=["coin", "ts", "buy_1000_bp", "sell_1000_bp"])
        c, meas = fm.measured_costs(assumed, coins, T0, empty)
        np.testing.assert_array_equal(np.nan_to_num(c, nan=-1), np.nan_to_num(assumed, nan=-1))
        self.assertFalse(meas.any())
        books = pd.DataFrame({"coin": ["A", "C", "A"], "ts": [T0 + 2 * H + 7 * 60_000] * 2 + [T0 + 4 * H],
                              "buy_1000_bp": [3.0, 1.0, np.nan], "sell_1000_bp": [1.0, 1.0, 2.0]})
        c, meas = fm.measured_costs(assumed, coins, T0, books, max_gap_min=30)
        # row 1 trades at the close of the bar opening at T0 + H, i.e. T0 + 2H: 7 minutes from the snapshot
        self.assertAlmostEqual(c[1, 0], 4.5e-4 + 2e-4)
        self.assertEqual(c[0, 0], 6e-4)              # 67 minutes away: R448's cost
        self.assertEqual(c[3, 0], 6e-4)              # thin buy side at T0 + 4H: missing, R448's cost
        self.assertEqual(c[1, 1], 12e-4)             # unmapped: untouched
        self.assertTrue(np.isnan(c[1, 2]))           # no R448 cost (no rank): stays out
        self.assertEqual(int(meas.sum()), 1)
        neg = books.assign(buy_1000_bp=-5.0, sell_1000_bp=-1.0)
        self.assertAlmostEqual(fm.measured_costs(assumed, coins, T0, neg, max_gap_min=30)[0][1, 0], 4.5e-4)

    def test_cost_summary(self):
        traded = np.array([[True, False], [True, True]])
        meas = np.array([[True, True], [False, True]])
        s = fm.cost_summary(traded, meas, np.full((2, 2), 8e-4), np.full((2, 2), 5e-4))
        self.assertEqual(s["traded_coin_hours"], 3)
        self.assertAlmostEqual(s["traded_share_measured"], 2 / 3)
        self.assertAlmostEqual(s["assumed_cost_bp"], 8.0)
        self.assertAlmostEqual(s["measured_cost_bp"], 5.0)


def journal(d, n_sym=12, days=3, seed=0):
    """A synthetic R200 journal and R448 price store from T0: every hour on time, ranks 1..n_sym."""
    rng = np.random.default_rng(seed)
    T = days * 24 + 2
    syms = [f"Q{i:02d}USDT" for i in range(n_sym)]
    rows = [{"t": T0 + i * H, "symbol": s, "rank": j * 10 + 1, "tvc": rng.integers(0, 8), "t24": rng.integers(0, 8),
             "t4": rng.integers(0, 8)} for i in range(T) for j, s in enumerate(syms)]
    r200 = Path(d) / "r200"
    r200.mkdir()
    pd.DataFrame(rows).to_csv(r200 / "signals.csv", index=False)
    run_at = [pd.Timestamp(T0 + (i + 1) * H + 5 * 60_000, unit="ms", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
              for i in range(T)]
    pd.DataFrame({"t": T0 + np.arange(T) * H, "run_at": run_at}).to_csv(r200 / "ticks.csv", index=False)
    px = np.exp(np.cumsum(rng.normal(0, 0.01, (T + 1, n_sym)), axis=0))
    store = [(int(T0 + i * H), s[:-4], float(px[i, j]), 1e-5) for i in range(T + 1) for j, s in enumerate(syms)]
    return r200, store, [s[:-4] for s in syms]


class Read(unittest.TestCase):
    def test_parity_with_r448_forward_and_measured_costs(self):
        with tempfile.TemporaryDirectory() as d:
            r200, store, coins = journal(d)
            j = Path(d) / "j"
            meta = {"universe": [{"name": c} for c in coins]}
            with mock.patch.object(fh, "R200", r200), mock.patch.object(fh, "J", j), \
                    mock.patch.object(fh, "post", return_value=meta):
                j.mkdir()
                fh.hl_store_add(store)
                fh.forward()                                     # R448 writes its tickets
                tk = pd.read_csv(j / "tickets.csv")
                self.assertEqual(sorted(set(tk.book)), ["A", "B"])
                snaps = Path(d) / "snaps"
                (snaps / "main" / "books").mkdir(parents=True)
                rep = fm.read(snaps, Path(d) / "out0")           # no snapshot: measured equals assumed
                df = pd.read_csv(Path(d) / "out0" / "daily.csv")
                np.testing.assert_allclose(df.meas_1000_1x, df.assumed_1x, rtol=0, atol=1e-12)
                self.assertEqual(rep["A"]["traded_share_measured"], 0.0)
                self.assertTrue(rep["A"]["decision"].startswith("pending (3 strict on-time days"))
                ts = T0 + np.arange(3 * 24 + 2) * H + 5 * 60_000
                pd.DataFrame([{"coin": c, "ts": t, "buy_1000_bp": 0.5, "sell_1000_bp": 0.5, "buy_5000_bp": 1.0,
                               "sell_5000_bp": 1.0} for t in ts for c in coins]).to_csv(
                    snaps / "main" / "books" / "2026-11-12.csv", index=False)
                rep = fm.read(snaps, Path(d) / "out1")
                df = pd.read_csv(Path(d) / "out1" / "daily.csv")
                self.assertAlmostEqual(rep["A"]["traded_share_measured"], 1.0)
                self.assertAlmostEqual(rep["A"]["measured_cost_bp"], 5.0)   # 4.5 bp fee + 0.5 bp
                self.assertGreater(rep["A"]["assumed_cost_bp"], 5.0)        # tier costs are 6 bp or more
                self.assertTrue((df.meas_1000_1x >= df.assumed_1x - 1e-12).all())
                self.assertTrue((df.meas_5000_1x <= df.meas_1000_1x + 1e-12).all())
                self.assertTrue((df.meas_10000_1x == df.assumed_1x).all())  # no $10k column: R448's cost
                bad = tk.copy()
                bad.loc[0, "net"] += 1e-6
                bad.to_csv(j / "tickets.csv", index=False)
                with self.assertRaises(SystemExit):
                    fm.read(snaps, Path(d) / "out2")


class Decide(unittest.TestCase):
    def frame(self, n, meas, assumed):
        days = [fh.day_label(T0 + i * fh.DAY) for i in range(n)]
        df = pd.DataFrame({"day": days, "book": "A", "assumed_1x": assumed, "kind": "ontime"})
        for s in fm.SIZES:
            for k in (1, 2, 3):
                df[f"meas_{s}_{k}x"] = meas
        return df

    def test_screen_and_final(self):
        null = np.random.default_rng(1).normal(0, 1e-3, 183)
        tk = pd.DataFrame(columns=["day", "book", "net", "net_2x", "net_3x", "kind"])
        self.assertTrue(fm.decide(self.frame(89, 1e-4, 0.0), tk, "A", null)["decision"].startswith("pending (89"))
        self.assertTrue(fm.decide(self.frame(90, -1e-4, 0.0), tk, "A", null)["decision"]
                        .startswith("COSTLIER THAN ASSUMED at 90 days (-1.00"))
        self.assertTrue(fm.decide(self.frame(90, 1e-4, 1e-4), tk, "A", null)["decision"]
                        .startswith("NO WORSE THAN ASSUMED"))
        df = self.frame(365, 5e-3, 4e-3)
        tk = df.assign(net=-1e-4, net_2x=-2e-4, net_3x=-3e-4)[["day", "book", "net", "net_2x", "net_3x", "kind"]]
        self.assertTrue(fm.decide(df, tk, "A", null)["decision"].startswith("n/a: R448 did not pass"))
        tk = df.assign(net=4e-3, net_2x=3e-3, net_3x=2e-3)[["day", "book", "net", "net_2x", "net_3x", "kind"]]
        self.assertTrue(fm.decide(df, tk, "A", null)["decision"].startswith("EXECUTABLE AT MEASURED COSTS"))
        self.assertTrue(fm.decide(self.frame(365, -1e-4, 4e-3), tk, "A", null)["decision"]
                        .startswith("NOT EXECUTABLE AT MEASURED COSTS"))


class PreregAgreement(unittest.TestCase):
    def test_constants_match_the_frozen_text(self):
        p = ROOT / "experiments" / "flow_hl_mc_v1" / "PREREG.md"
        if not p.exists():
            self.skipTest("PREREG not in the tree yet")
        flat = " ".join(p.read_text().split())
        for phrase in ("taker fee of 4.5 bp", "cost of a $1k market order", "within 90 minutes",
                       "$1k (primary), $5k and $10k", "`main/books/`", "Zero new trials"):
            self.assertIn(phrase, flat, phrase)
        self.assertEqual((fm.TAKER, fm.SIZE_USD, fm.MAX_GAP_MIN, fm.SIZES),
                         (4.5e-4, 1_000, 90, (1_000, 5_000, 10_000)))


if __name__ == "__main__":
    unittest.main()
