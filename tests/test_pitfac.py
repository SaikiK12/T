import unittest

import numpy as np
import pandas as pd

from scripts import pitfac_factors as pf


def panel(days=40, perps=("AUSDT", "BUSDT")):
    rows = []
    for k, p in enumerate(perps):
        for d in range(days):
            if p == "BUSDT" and d == 5:
                continue                                        # a day without a trade: no row
            r = {c: np.nan for c in pf.NEED[2:]}
            r.update(day=pd.Timestamp("2021-01-02") + pd.Timedelta(days=d), perp=p, rank_qvol30=1.0 + k,
                     mcap_est=1e9 * (k + 1), qvol=1e7, fees=1e4, oi_usd=1e8, n_venues=2.0,
                     fund=0.0003, gate_fund=0.0001, kucoin_fund=0.0002, upbit_rel=0.01 * (k + 1),
                     bithumb_rel=np.nan, wick_up=0.03 if d % 2 else 0.0, wick_dn=0.0)
            rows.append(r)
    return pd.DataFrame(rows)


class PitfacTest(unittest.TestCase):
    def test_rows_times_and_values(self):
        f = pf.factors(panel())
        self.assertEqual(set(f.sym), {"AUSDT", "BUSDT"})
        day = pd.Timestamp("2021-01-20")
        a = f[(f.sym == "AUSDT") & (f.t == day.value // 10**6 - pf.H)].iloc[0]   # the bar ending at 00:00
        self.assertAlmostEqual(a.kr_rel_7d, 0.01)
        self.assertAlmostEqual(a["size"], np.log(1e9))
        self.assertAlmostEqual(a.vol_mcap, np.log(1e7 / 1e9))
        self.assertAlmostEqual(a.fund_gap_all_7d, 7 * (0.0003 - 0.00015))
        self.assertAlmostEqual(a.age, np.log1p(18))
        self.assertAlmostEqual(a.n_venues_7d, 2.0)
        self.assertTrue(np.isnan(a.fee_yield))                                     # 19 days of fees < 20
        b = f[(f.sym == "BUSDT") & (f.t == pd.Timestamp("2021-01-07").value // 10**6 - pf.H)]
        self.assertEqual(len(b), 0)                                                # no row on a day without a trade

    def test_universe_and_no_future(self):
        p = panel(perps=("AUSDT", "BUSDT", "CUSDT"))
        p.loc[p.perp == "CUSDT", "rank_qvol30"] = 151.0
        f = pf.factors(p)
        self.assertNotIn("CUSDT", set(f.sym))
        later = p.copy()
        cut = pd.Timestamp("2021-01-25")
        num = later.columns.drop(["day", "perp", "rank_qvol30"])
        later.loc[later.day > cut, num] = later.loc[later.day > cut, num] * 3.0
        g = pf.factors(later)
        known = f.t <= cut.value // 10**6 - pf.H
        pd.testing.assert_frame_equal(f[known].reset_index(drop=True), g[g.t <= cut.value // 10**6 - pf.H]
                                      .reset_index(drop=True))


if __name__ == "__main__":
    unittest.main()
