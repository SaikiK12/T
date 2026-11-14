import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def module():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("run_vixpanic", ROOT / "scripts" / "run_vixpanic.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class VixPanicTest(unittest.TestCase):
    def setUp(self):
        self.m = module()

    def test_onsets_need_a_quiet_gap(self):
        idx = pd.bdate_range("2020-01-01", periods=60)
        f = pd.Series(False, index=idx)
        f.iloc[[25, 26, 30, 50, 52]] = True              # 26 and 30 follow 25; 52 follows 50
        on = self.m.onsets(f, gap=20)
        self.assertEqual(list(on), [idx[25]])              # 30 lies in 50's 20-row lookback
        self.assertEqual(list(self.m.onsets(f, gap=3)), [idx[25], idx[30], idx[50]])

    def test_triggers(self):
        idx = pd.bdate_range("2020-01-01", periods=300)
        vvix = pd.Series(np.arange(300, dtype=float), index=idx, name="VVIX")    # always a new high
        vix = pd.Series(20.0, index=idx, name="VIX")
        v3m = pd.Series(21.0, index=idx, name="VIX3M")
        v3m.iloc[280] = 19.0
        t = self.m.triggers(vix, v3m, vvix)
        self.assertFalse(t.VVIX95.iloc[250])              # fewer than 252 closes
        self.assertTrue(t.VVIX95.iloc[251:].all())
        self.assertEqual(list(t.index[t.BACKW]), [idx[280]])
        self.assertEqual(list(t.index[t.BOTH]), [idx[280]])

    def test_equity_return_from_next_open(self):
        idx = pd.bdate_range("2020-01-06", periods=10)
        px = pd.DataFrame({"o": np.arange(10, 20, dtype=float), "c": np.arange(10, 20, dtype=float) + 0.5}, index=idx)
        r = self.m.equity_returns(px, pd.DatetimeIndex([idx[2], idx[8]]), 3)
        self.assertEqual(list(r.index), [idx[2]])          # idx[8] has no 3-day hold left
        self.assertAlmostEqual(r.iloc[0], (15 + 0.5) / 13 - 1)   # open of idx[3], close of idx[5]

    def test_btc_return_net_of_funding(self):
        h = 3_600_000
        t0 = int(pd.Timestamp("2021-03-01", tz="UTC").value // 10**6)
        t = np.arange(t0, t0 + 40 * 24 * h, h)
        k = pd.DataFrame({"t": t.astype(float), "open": 100.0 + np.arange(len(t)) * 0.01})
        ft = np.arange(t0, t0 + 40 * 24 * h, 8 * h)
        fund = pd.DataFrame({"t": ft.astype(float) + 2, "rate": 0.0001})
        r = self.m.btc_returns(k, fund, [pd.Timestamp("2021-03-02")], 7)
        i0 = 24 + 22
        i1 = i0 + 7 * 24
        paid = 0.0001 * ((ft + 2 > t[i0]) & (ft + 2 <= t[i1])).sum()
        self.assertAlmostEqual(r.iloc[0], k.open[i1] / k.open[i0] - 1 - paid)
        self.assertEqual(len(self.m.btc_returns(k, fund, [pd.Timestamp("2021-04-08")], 7)), 0)   # past the data

    def test_null_p(self):
        rng = np.random.default_rng(0)
        pool = np.zeros(1000)
        pool[:10] = 1.0
        self.assertLess(self.m.null_p(1.0, pool, 10, rng), 0.001)
        self.assertEqual(self.m.null_p(1.0, pool, 4, rng), 1.0)


if __name__ == "__main__":
    unittest.main()
