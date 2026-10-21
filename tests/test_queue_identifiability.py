import json
from pathlib import Path
import unittest

from research.queue_identifiability import Order, cancel, consume, demonstrate, world


class IdentifiabilityTests(unittest.TestCase):
    def test_same_public_observations_have_different_exact_fills(self):
        a, first = world("A")
        b, second = world("B")
        self.assertEqual(a, b)
        self.assertEqual([r["quantity"] for r in a if r["event"]=="sell_trade"], [10]*7+[5])
        self.assertEqual([r["quantity"] for r in a if r["event"]=="bid_depth"],
                         [110,120,130,140,150,160,150,140,130,120,110,100,90,80,70,60,50,40,35])
        self.assertEqual((first["our_filled"], second["our_filled"]), (10,0))

    def test_fifo_and_quantity_conservation_in_both_worlds(self):
        for identity in ("A", "B"):
            with self.subTest(identity=identity):
                trace, result = world(identity)
                self.assertEqual(sum(r["quantity"] for r in result["fills"]),75)
                self.assertEqual(sum(r["quantity"] for r in result["remaining"]),35)
                self.assertEqual(110+50-50-75,trace[-1]["quantity"])
        self.assertEqual(world("A")[1]["fills"][5],dict(order="ours",quantity=10))
        self.assertFalse(any(r["order"]=="ours" for r in world("B")[1]["fills"]))

    def test_order_boundaries_and_rejected_overconsumption(self):
        queue=(Order("A",100),Order("ours",10))
        after,fills=consume(queue,100)
        self.assertEqual(after,(Order("ours",10),))
        self.assertEqual(fills,(Order("A",100),))
        self.assertEqual(queue,(Order("A",100),Order("ours",10)))
        with self.assertRaises(ValueError): consume(queue,111)
        with self.assertRaises(ValueError): cancel(queue,"A",101)
        with self.assertRaises(ValueError): cancel(queue,"unknown",1)

    def test_zero_negative_bool_and_fractional_events_are_rejected(self):
        for quantity in (0,-1,True,1.5):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError): consume((Order("A",10),),quantity)
                with self.assertRaises(ValueError): cancel((Order("A",10),),"A",quantity)

    def test_receipt_explicitly_limits_scope(self):
        receipt=demonstrate()
        stored = Path(__file__).resolve().parents[1] / "research/fixtures/queue_identifiability.json"
        self.assertEqual(json.loads(stored.read_text()), receipt)
        self.assertEqual(receipt["market_trials"],0)
        self.assertEqual(len(receipt["hidden_histories"]),2)
        self.assertIn("Not a test of an installed HftBacktest",receipt["limits"][0])


if __name__ == "__main__":
    unittest.main()
