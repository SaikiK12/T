import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import fetch_hip3list as f
from scripts import run_hip3list as r
from scripts import run_xfund_listing as lst

DAY = 86_400_000


class Hip3List(unittest.TestCase):
    def setUp(self):
        self._gap = lst.LAUNCH_GAP
        self.addCleanup(setattr, lst, "LAUNCH_GAP", self._gap)   # setup() changes R516's module constant

    def test_shared(self):
        m = [{"dex": "xyz", "coin": "xyz:TSLA"}, {"dex": "km", "coin": "km:TSLA"}, {"dex": "km", "coin": "km:ONLY"}]
        self.assertEqual([x["coin"] for x in f.shared(m)], ["xyz:TSLA", "km:TSLA"])
        self.assertEqual({x["base"] for x in f.shared(m)}, {"TSLA"})

    def _market(self, root, dex, base, first_day, rate, t0, days=120):
        hours = np.arange(first_day * 24, days * 24)
        pd.DataFrame({"t": (t0 + hours * 3_600_000).astype("int64"), "rate": rate}).to_parquet(
            root / "funding" / f"{dex}_{base}.parquet", index=False)
        bars = np.arange(first_day * 6, days * 6)
        pd.DataFrame({"t": (t0 + bars * 4 * 3_600_000).astype("int64"), "close": 100.0, "volume": 1.0}).to_parquet(
            root / "prices" / f"{dex}_{base}.parquet", index=False)
        return {"dex": dex, "coin": f"{dex}:{base}", "base": base, "delisted": 0, "first_funding": ""}

    def test_listing_on_a_new_dex_is_traded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "funding").mkdir()
            (root / "prices").mkdir()
            t0 = int(pd.Timestamp(r.START, tz="UTC").value // 10**6)
            rows = [self._market(root, "xyz", "TSLA", 0, 0.0, t0),
                    self._market(root, "km", "TSLA", 60, 0.0001, t0)]     # km lists 60 days later; longs pay 87.6%/yr
            pd.DataFrame(rows).to_csv(root / "universe.csv", index=False)
            end = str((pd.Timestamp(r.START) + pd.Timedelta(days=119)).date())
            u, vset, launch = r.setup(end, root)
            self.assertEqual(lst.LAUNCH_GAP, 0)
            ev = r.pairs_events(u, launch)
            self.assertEqual(ev[["coin", "young"]].values.tolist(), [["TSLA", "km"]])
            rows_, tr = lst.run_book(u, vset, launch, 0.20, 10, 30)
            self.assertEqual(len(tr), 1)
            self.assertEqual((tr.iloc[0].long, tr.iloc[0].short), ("xyz", "km"))
            self.assertGreater(tr.iloc[0].funding_pnl, 0)


if __name__ == "__main__":
    unittest.main()
