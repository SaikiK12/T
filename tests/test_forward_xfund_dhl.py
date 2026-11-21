import unittest
from unittest import mock

from lab import carrylane, deribit
from scripts import forward_xfund_dhl as f
from scripts import read_xfund_dhl_fwd as r


class DeribitClient(unittest.TestCase):
    def test_instrument_and_parsers(self):
        self.assertEqual(deribit.instrument("1000PEPE"), "1000PEPE_USDC-PERPETUAL")
        chart = {"ticks": [0, 3_600_000, 3_600_000], "close": [1.0, 2.0, 2.0], "volume": [5.0, 6.0, 6.0]}
        with mock.patch.object(deribit, "_get", return_value=chart), mock.patch.object(deribit, "PACE", 0):
            p = deribit.prices("BTC", 0, 2 * deribit.H)
        self.assertEqual(p.t.tolist(), [0, 3_600_000])
        rows = [{"timestamp": 3_600_000, "interest_1h": 1e-5}, {"timestamp": 0, "interest_1h": 2e-5}]
        with mock.patch.object(deribit, "_get", return_value=rows), mock.patch.object(deribit, "PACE", 0):
            g = deribit.funding("BTC", 0, 3_600_000)
        self.assertEqual(g.t.tolist(), [0, 3_600_000])
        summary = [{"instrument_name": "BTC_USDC-PERPETUAL", "bid_price": 99.0, "ask_price": 101.0},
                   {"instrument_name": "BTC-PERPETUAL", "bid_price": 1.0, "ask_price": 2.0}]
        with mock.patch.object(deribit, "_get", return_value=summary):
            self.assertEqual(deribit.mids(), {"BTC": 100.0})

    def test_lane_wiring(self):
        self.assertIn("deribit", carrylane.VENUES)
        self.assertEqual(carrylane.VENUES["deribit"].bar_h, 1)           # closes at 00:00 UTC from hourly bars
        self.assertEqual(f.LANE.rid, "R520")
        self.assertEqual(set(f.BOOKS), {"deribit", "hyperliquid"})

    def test_read_on_an_empty_journal(self):
        self.assertEqual(r.r512.FEE_BP["deribit"], 3.5)
        s = r.r512.series(r.LANE, "A")
        self.assertEqual(r.r512.read(s)["scored_days"], 0)


if __name__ == "__main__":
    unittest.main()


class Looks(unittest.TestCase):
    def test_decide(self):
        import numpy as np
        rng = np.random.default_rng(0)
        self.assertEqual(r.decide([]), "RUNNING")
        self.assertEqual(r.decide([0.001] * 10), "RUNNING")
        self.assertTrue(r.decide([-0.01] * 4).startswith("FAIL (kill switch"))
        strong = 0.002 + rng.normal(0, 0.001, 90)
        self.assertEqual(r.decide(strong), "PASS (look 1)")
        self.assertEqual(r.decide(-0.0001 + rng.normal(0, 0.0001, 90)), "FAIL (look 1: mean <= 0)")
        weak = 0.00012 + rng.normal(0, 0.001, 180)
        self.assertIn(r.decide(weak), ("PASS (look 2)", "FAIL (look 2)", "PASS (look 1)", "FAIL (look 1: mean <= 0)"))

    def test_look1_pass_is_final(self):
        import numpy as np
        rng = np.random.default_rng(1)
        x = list(0.002 + rng.normal(0, 0.001, 90)) + [-0.05] * 5       # passes at 90, then a crash
        self.assertEqual(r.decide(x), "PASS (look 1)")
        self.assertTrue(r.decide([0.0001] * 90 + [0.0] * 5 + [-0.05]).startswith(("FAIL (kill", "PASS", "CONTINUE")))
