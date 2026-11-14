import importlib.util
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("run_flow_hl", ROOT / "scripts" / "run_flow_hl.py")
fh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fh)
H = fh.H


class FlowHL(unittest.TestCase):
    def test_coin_map(self):
        coins = {"BTC", "kPEPE", "kBONK", "SOL"}
        self.assertEqual(fh.hl_coin("BTCUSDT", coins), "BTC")
        self.assertEqual(fh.hl_coin("1000PEPEUSDT", coins), "kPEPE")
        self.assertEqual(fh.hl_coin("1000000BONKUSDT", coins), "kBONK")
        self.assertIsNone(fh.hl_coin("ETHUSDT", coins))
        self.assertIsNone(fh.hl_coin("BTCUSDC", coins))

    def test_entry_lag(self):
        t = 100 * H
        self.assertEqual(fh.entry_lag(t, t + H + 17 * 60_000), 1)      # written 17 min after the bar closed
        self.assertEqual(fh.entry_lag(t, t + 2 * H), 1)                 # exactly at the next close
        self.assertEqual(fh.entry_lag(t, t + 2 * H + 1), 2)             # just after it: the close after
        self.assertEqual(fh.entry_lag(t, t + 3 * H + 41 * 60_000), 3)
        self.assertEqual(fh.entry_lag(t, t), 1)                         # never less than one bar

    def test_shift_rows_needs_tradable_entry(self):
        ind = np.zeros((4, 2), bool)
        ind[0, 0] = ind[0, 1] = True
        elig = np.ones((4, 2), bool)
        elig[1, 1] = False
        out = fh.shift_rows(ind, elig, np.ones(4, int))
        self.assertEqual(out[1].tolist(), [1, 0])

    def test_returns_charge_longs_the_next_settlement(self):
        close = np.array([[100.0], [110.0], [99.0]])
        rate = np.array([[np.nan], [0.001], [np.nan]])
        r = fh.hl_returns(close, rate)
        self.assertAlmostEqual(r[0, 0], 0.10 - 0.001)
        self.assertAlmostEqual(r[1, 0], 99 / 110 - 1)

    def test_short_book_earns_when_signalled_coin_falls(self):
        T, S = 24 * 6, 3
        ret = np.zeros((T, S))
        ret[:, 0] = -0.001                      # the signalled coin falls every hour
        ind = np.zeros((T, S), np.int64)
        ind[:, 0] = 1
        trad = np.ones((T, S), bool)
        cmat = np.zeros((T, S))
        r = fh.book_days({"tvc": ind}, ("tvc",), ret, trad, cmat, 72, T, 1.0)
        self.assertTrue((r["net"] > 0).all())
        self.assertEqual(len(r["net"]), 3)
        self.assertEqual(r["by_coin"].shape, (3, S))

    def test_describe_and_leave_two_out(self):
        x = np.r_[np.full(30, 0.001), [0.5]]
        d = fh.describe(x)
        self.assertEqual(d["days"], 31)
        self.assertLess(d["trimmed_mean_bp_day"], d["mean_bp_day"])
        g = np.zeros((5, 4))
        g[:, 0], g[:, 1], g[:, 2] = 0.01, 0.005, 0.001
        self.assertAlmostEqual(fh.leave_two_out(g), 10.0)

    def test_boot_threshold_is_centred_null(self):
        rng = np.random.default_rng(0)
        x = rng.normal(0.01, 0.02, 200)
        thr = fh.boot_threshold(x, 365, n_boot=4000)
        self.assertGreater(thr, 0)
        self.assertLess(thr, 0.005)              # the mean is removed: the threshold sits near zero, not near 1%


if __name__ == "__main__":
    unittest.main()
