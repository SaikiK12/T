import unittest
from unittest import mock

from lab import bitfinex, carrylane
from scripts import forward_xfund_bfx as f
from scripts import read_xfund_bfx_fwd as r


class Bfx(unittest.TestCase):
    def test_client_parsers(self):
        self.assertEqual(bitfinex.key("DOGE"), "tDOGEF0:USTF0")
        self.assertEqual(bitfinex._base("tDOGEF0:USTF0"), "DOGE")
        self.assertIsNone(bitfinex._base("tBTCUSD"))
        rows = [[100.0, 2, 1.5], [99.0, 1, 2.0], [101.0, 3, -1.0], [102.0, 1, -0.5]]
        with mock.patch.object(bitfinex.fb, "get", return_value=rows):
            bids, asks = bitfinex.book("BTC")
        self.assertEqual(bids, [[100.0, 1.5], [99.0, 2.0]])
        self.assertEqual(asks, [[101.0, 1.0], [102.0, 0.5]])

    def test_lane_wiring(self):
        self.assertIn("bitfinex", carrylane.VENUES)
        self.assertEqual(carrylane.VENUES["bitfinex"].bar_h, 1)
        self.assertEqual(f.LANE.rid, "R524")
        self.assertEqual(set(f.BOOKS), {"binance", "bitfinex"})
        self.assertEqual(r.r520.r512.FEE_BP["bitfinex"], 6.5)

    def test_read_on_an_empty_journal(self):
        s = r.r520.r512.series(r.LANE, "A")
        self.assertEqual(len(s), 0)


if __name__ == "__main__":
    unittest.main()


class Looks(unittest.TestCase):
    def test_decide(self):
        import numpy as np
        rng = np.random.default_rng(0)
        good = 0.0002 + rng.normal(0, 0.0002, 180)
        self.assertEqual(r.decide(good[:50], good[:50]), "RUNNING")
        self.assertEqual(r.decide(good[:90], good[:90]), "PASS (look at 90)")
        self.assertEqual(r.decide(-np.abs(good[:90]), good[:90]), "FAIL (look at 90: mean <= 0)")
        self.assertTrue(r.decide(good[:90], np.full(90, -0.001)).startswith("FAIL (kill switch"))
        weak = 0.00001 + rng.normal(0, 0.0005, 180)
        self.assertIn(r.decide(weak, np.abs(weak)), ("PASS (look at 90)", "PASS (look at 180)", "FAIL (look at 180)",
                                                       "FAIL (look at 90: mean <= 0)"))
