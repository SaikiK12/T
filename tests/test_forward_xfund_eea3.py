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


if __name__ == "__main__":
    unittest.main()
