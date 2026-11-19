import unittest
from unittest import mock

from lab import aster, carrylane

H = 3_600_000
DAY = 24 * H


class AsterClient(unittest.TestCase):
    def test_parse(self):
        t0 = 1_795_000_000_000 - 1_795_000_000_000 % DAY
        kl = [[t0 - DAY, "1", "2", "0.5", "1.5", "10", 0, "0", 1, "0", "0", "0"],
              [t0, "1", "2", "0.5", "1.7", "12", 0, "0", 1, "0", "0", "0"]]
        with mock.patch.object(aster, "_json", return_value=kl), mock.patch.object(aster, "PACE", 0):
            p = aster.prices("XUSDT", t0 - DAY, t0 + DAY)
        self.assertEqual(p.close.tolist(), [1.5, 1.7])
        self.assertEqual(list(p.columns), ["t", "close", "volume"])
        page = [{"fundingTime": t0 + i * H, "fundingRate": "0.0001"} for i in range(3)]
        with mock.patch.object(aster, "_json", return_value=page), mock.patch.object(aster, "PACE", 0):
            f = aster.funding("XUSDT", t0, t0 + DAY)
        self.assertEqual(len(f), 3)
        bt = [{"symbol": "XUSDT", "bidPrice": "99", "askPrice": "101"}, {"symbol": "YUSDT", "bidPrice": "0",
                                                                          "askPrice": "1"}]
        with mock.patch.object(aster, "_json", return_value=bt):
            self.assertEqual(aster.mids(), {"XUSDT": 100.0})
        info = {"symbols": [{"symbol": "XUSDT", "contractType": "PERPETUAL", "status": "TRADING"},
                            {"symbol": "OLDUSDT", "contractType": "PERPETUAL", "status": "SETTLING"}]}
        with mock.patch.object(aster, "_json", return_value=info):
            self.assertEqual(aster.listed(), {"XUSDT"})
        with mock.patch.object(aster, "_json", return_value={"bids": [["99", "5"]], "asks": [["101", "4"]]}):
            self.assertEqual(aster.book("XUSDT"), ([[99.0, 5.0]], [[101.0, 4.0]]))

    def test_register(self):
        v = aster.register()
        self.assertIs(carrylane.VENUES["aster"], v)
        self.assertEqual(v.bar_h, 24)


class Read(unittest.TestCase):
    def journal(self, lane, days, net):
        import pandas as pd
        j = lane / "journal"
        j.mkdir(parents=True)
        pd.DataFrame([{"run": "r", "day": d, "book": "A", "kind": "ontime", "exits": 0, "entries": int(i == 0),
                       "held": 1, "ready": "{}"} for i, d in enumerate(days)]).to_csv(j / "decisions.csv", index=False)
        pd.DataFrame([{"run": "r", "day": days[0], "book": "A", "action": "enter", "coin": "X", "long": "kraken",
                       "short": "aster", "spread_ann": "1", "forced": "false", "kind": "ontime", "close_long": "1",
                       "close_short": "1", "fill_long": "1", "fill_short": "1"}]).to_csv(j / "tickets.csv", index=False)
        pd.DataFrame([{"day": d, "book": "A", "kind": "ontime", "run": "r", "held": 1, "legs": 2.0 if i == 0 else 0.0,
                       "gross": v, "funding": v, "fill_adj": 0, "net": v - (0.0007 * 2 / 40 if i == 0 else 0),
                       "net_2x": 0, "net_3x": 0, "net_close": 0, "net_close_2x": 0, "net_close_3x": 0}
                      for i, (d, v) in enumerate(zip(days[1:], net))]).to_csv(j / "days.csv", index=False)
        pd.DataFrame([{"run": "r", "day": days[0], "book": "A", "action": "enter", "coin": "X", "venue": "aster",
                       "symbol": "XUSDT", "side": "sell", "utc": "", "mid": 1, "fill_1000": 1, "cost_bp_1000": 10.0,
                       "fill_2500": "", "cost_bp_2500": ""}]).to_csv(j / "book_fills.csv", index=False)

    def test_series_and_verdicts(self):
        import tempfile
        from pathlib import Path
        import numpy as np
        import pandas as pd
        from scripts import read_xfund_eea3_fwd as rd
        days = [str(d.date()) for d in pd.date_range("2026-11-20", periods=41)]
        rng = np.random.default_rng(1)
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp)
            self.journal(lane, days, list(5e-4 + rng.normal(0, 1e-4, 40)))
            s = rd.series(lane)
            self.assertEqual(len(s), 40)
            c = (10 + 4.0) / 1e4 + 0.0021                    # Aster measured + its fee; Kraken leg has no record
            self.assertAlmostEqual(s.net_book.iloc[0] - s.net.iloc[0], (0.0007 * 2 - c) / 40)
            self.assertTrue(rd.read(s)["verdict"].startswith("PASS (day 30"))
        with tempfile.TemporaryDirectory() as tmp:
            lane = Path(tmp)
            self.journal(lane, days, [-0.002] * 40)
            self.assertTrue(rd.read(rd.series(lane))["verdict"].startswith("FAIL (kill switch"))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rd.read(rd.series(Path(tmp)))["verdict"], "RUNNING")


if __name__ == "__main__":
    unittest.main()
