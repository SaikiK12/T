import unittest

from scripts import run_carrycost_hist as c


class WalkTest(unittest.TestCase):
    def test_walk_and_cost(self):
        bids = [(99.0, 10.0), (98.0, 100.0)]
        asks = [(101.0, 5.0), (102.0, 100.0)]
        # $505 fills exactly the first ask level: VWAP 101, mid 100 -> 100 bp.
        self.assertAlmostEqual(c.cost_bp(bids, asks, "buy", 505), 100.0, places=6)
        # $990 sells exactly the first bid level: VWAP 99 -> 100 bp.
        self.assertAlmostEqual(c.cost_bp(bids, asks, "sell", 990), 100.0, places=6)
        # Too thin: None.
        self.assertIsNone(c.cost_bp(bids, asks, "buy", 1e9))
        # Crossed or empty books are unmeasured.
        self.assertIsNone(c.cost_bp([(101.0, 1)], [(100.0, 1)], "buy", 10))
        self.assertIsNone(c.cost_bp([], asks, "buy", 10))


class GateReplayTest(unittest.TestCase):
    def test_set_make_take_and_minute_samples(self):
        h = 1_700_000_000
        lines = [
            f"{h},set,99,10,1,0", f"{h},set,101,-10,1,0",   # bid 99 x10, ask 101 x10 (contracts)
            f"{h + 30},make,100,5,2,1",                    # bid 100 x5 added at 00:00:30
            f"{h + 90},take,101,-10,3,1",                  # ask 101 removed at 00:01:30
            f"{h + 91},make,102,-4,4,1",
        ]
        s = c.gate_samples(lines, h, mult=0.1, minutes=3)
        self.assertEqual(len(s), 3)
        self.assertEqual(s[0], ([(99.0, 1.0)], [(101.0, 1.0)]))           # minute 0: the snapshot
        self.assertEqual(s[1][0][0], (100.0, 0.5))                         # minute 1: new best bid
        self.assertEqual(s[2][1], [(102.0, 0.4)])                          # minute 2: ask 101 gone

    def test_event_cost_needs_enough_samples(self):
        book = ([(99.0, 100.0)], [(101.0, 100.0)])
        self.assertAlmostEqual(c.event_cost([book] * 40, "buy", 100), 100.0)
        self.assertIsNone(c.event_cost([book] * 10, "buy", 100))
        self.assertAlmostEqual(c.event_cost([book] * 10, "buy", 100, "snap0"), 100.0)


class TardisTest(unittest.TestCase):
    def test_first_hour_minute_samples(self):
        d0 = 1_700_000_000
        cols = ["exchange", "symbol", "timestamp", "local_timestamp"]
        for k in range(2):
            cols += [f"asks[{k}].price", f"asks[{k}].amount", f"bids[{k}].price", f"bids[{k}].amount"]
        def row(t, ask):
            return ",".join(["binance-futures", "X", str(int(t * 1e6)), str(int(t * 1e6)),
                             str(ask), "1", "99", "2", str(ask + 1), "3", "98", "4"])
        lines = [",".join(cols), row(d0 + 0.2, 101), row(d0 + 61, 102), row(d0 + 3601, 150)]
        s = c.tardis_samples(lines, d0, minutes=3)
        self.assertEqual(s[0][1][0], (101.0, 1.0))     # minute 0: first snapshot after the start
        self.assertEqual(s[1][1][0], (101.0, 1.0))     # minute 1 (00:01:00): still the 00:00:00.2 book
        self.assertEqual(s[2][1][0], (102.0, 1.0))     # minute 2: the 00:01:01 book
        self.assertEqual(s[0][0], [(99.0, 2.0), (98.0, 4.0)])


class EventsTest(unittest.TestCase):
    def test_sides(self):
        ev = c.load_events()
        self.assertTrue(ev)
        for e in ev[:50]:
            self.assertNotEqual(e["gate_side"], e["binance_side"])
        mults = c.multipliers()
        self.assertTrue(all(e["gate_sym"] in mults for e in ev if c.WINDOW[0] <= e["day"] <= c.WINDOW[1]))


if __name__ == "__main__":
    unittest.main()
