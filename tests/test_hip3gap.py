import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import run_hip3gap as g
from scripts import run_hip3list as r


class Hip3Gap(unittest.TestCase):
    def test_design_gap_is_carried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "funding").mkdir()
            (root / "prices").mkdir()
            t0 = int(pd.Timestamp(r.START, tz="UTC").value // 10**6)
            rng = np.random.default_rng(0)
            px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 120 * 6)))     # one stock, two dexes, same price path
            rows = []
            for dex, rate in (("cash", 0.0), ("mkts", 0.0000125)):          # mkts longs pay about 11%/yr
                hours = np.arange(0, 120 * 24)
                pd.DataFrame({"t": (t0 + hours * 3_600_000).astype("int64"), "rate": rate}).to_parquet(
                    root / "funding" / f"{dex}_GOOGL.parquet", index=False)
                bars = np.arange(0, 120 * 6)
                pd.DataFrame({"t": (t0 + bars * 4 * 3_600_000).astype("int64"), "close": px, "volume": 1.0}
                             ).to_parquet(root / "prices" / f"{dex}_GOOGL.parquet", index=False)
                rows.append({"dex": dex, "coin": f"{dex}:GOOGL", "base": "GOOGL", "delisted": 0, "first_funding": ""})
            pd.DataFrame(rows).to_csv(root / "universe.csv", index=False)
            end = str((pd.Timestamp(r.START) + pd.Timedelta(days=119)).date())
            u = r.universe(end, root)
            _, tr = g.book(u, 14, 0.05, 20)
            self.assertEqual(len(tr), 1)
            self.assertEqual((tr.iloc[0].long, tr.iloc[0].short), ("cash", "mkts"))
            self.assertGreater(tr.iloc[0].funding_pnl, 0)


if __name__ == "__main__":
    unittest.main()
