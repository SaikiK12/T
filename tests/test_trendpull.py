import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("run_trendpull", ROOT / "scripts" / "run_trendpull.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TrendPullTest(unittest.TestCase):
    def setUp(self):
        self.m = module()

    def test_reset_inside_rising_trend(self):
        # 400 rows of steady growth, a hot run, then a flat stretch: ROC63 resets near zero above a rising SMA200
        n = 600
        c = np.empty(n)
        c[:400] = 100 * 1.001 ** np.arange(400)
        c[400:470] = c[399] * 1.006 ** np.arange(1, 71)            # hot run
        c[470:] = c[469]                                           # flat: ROC63 falls to 0 after 63 rows
        sig, elig, trend = self.m.signals(c, 0.25)
        on = np.flatnonzero(sig)
        self.assertTrue(len(on) > 0)
        first = on[0]
        self.assertGreater(first, 470)
        roc = c[first] / c[first - 63] - 1
        peak = max(c[j] / c[j - 63] - 1 for j in range(first - 63, first))
        self.assertLessEqual(abs(roc), 0.25 * peak)
        self.assertTrue(trend[first])
        self.assertFalse(sig[:315].any())                          # no q80 before 315 rows

    def test_no_signal_in_falling_trend(self):
        c = 100 * 0.999 ** np.arange(600)
        sig, _, _ = self.m.signals(c, 0.5)
        self.assertFalse(sig.any())

    def test_trades_do_not_overlap(self):
        sig = np.zeros(100, bool)
        sig[[10, 11, 20, 31, 32]] = True
        self.assertEqual(list(self.m.trades(sig, 20)), [10, 31])

    def test_hold_returns_and_funding(self):
        idx = pd.date_range("2022-01-01", periods=10, freq="D")
        d = pd.DataFrame({"open": np.arange(10.0) + 10, "close": np.arange(10.0) + 10.5}, index=idx)
        r = self.m.hold_returns(d, 3, None)
        self.assertAlmostEqual(r[2], (15 + 0.5) / 13 - 1)           # open of row 3, close of row 5
        self.assertTrue(np.isnan(r[7]))
        day = 86_400_000
        t0 = int(pd.Timestamp("2022-01-01").value // 10**6)
        ft = np.array([t0 + 3 * day, t0 + 3 * day + 1, t0 + 5 * day + day, t0 + 6 * day + 1])  # 4 settlements
        cum = np.concatenate([[0.0], np.cumsum([0.01, 0.02, 0.04, 0.08])])
        rf = self.m.hold_returns(d, 3, (ft, cum))
        # row 2: hold from 00:00 of day 3 (exclusive) to 24:00 of day 5 (inclusive): 0.02 and 0.04
        self.assertAlmostEqual(rf[2], r[2] - 0.06)

    def test_cluster_t(self):
        x = np.array([1.0, 1.2, 0.8, 1.1, 0.9, 1.0])
        t, G = self.m.cluster_t(x, ["a", "a", "b", "b", "c", "c"])
        self.assertEqual(G, 3)
        self.assertGreater(t, 10)
        t2, _ = self.m.cluster_t(np.array([1.0, 0.0, -1.0, 0.0]), ["a", "a", "b", "b"])   # mean 0, sums +1 and -1
        self.assertAlmostEqual(t2, 0.0)


if __name__ == "__main__":
    unittest.main()
