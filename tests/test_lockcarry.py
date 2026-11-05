import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import lockcarry_rule as rule  # noqa: E402
from scripts import forward_lockcarry2 as fwd  # noqa: E402

DAY = rule.DAY_MS
SPOT_BIDS, SPOT_ASKS = [(99.9, 1000.0)], [(100.0, 1000.0)]
FUT_BIDS = [(102.0, 1e6)]


class Rule(unittest.TestCase):
    def test_walks(self):
        self.assertEqual(rule.walk_buy([(100.0, 1.0), (200.0, 10.0)], 300.0), (2.0, 150.0))
        self.assertIsNone(rule.walk_buy([(100.0, 1.0)], 300.0))
        self.assertAlmostEqual(rule.walk_sell_usd([(100.0, 100.0), (50.0, 1e6)], 200.0), 200.0 / 3.0)
        self.assertIsNone(rule.walk_sell_usd([(100.0, 100.0)], 200.0))

    def test_locked_dollars_do_not_depend_on_the_delivery_price(self):
        o = rule.offer(SPOT_BIDS, SPOT_ASKS, FUT_BIDS, 10.0, 100 * DAY, 0, 0.0005, 0.00035)
        self.assertAlmostEqual(o["tau_days"], 100.0)
        outs = [rule.settle(o, p)["usd_out"] for p in (50.0, 102.0, 300.0)]
        rounding = abs(o["unhedged_coins"]) * 250.0          # the remainder is exposed to P - f_avg only
        for u in outs:
            self.assertLess(abs(u - o["locked_usd"]), rounding + 1e-6)
        self.assertLess(o["unhedged_coins"] * o["f_avg"], 10.0)  # less than one contract
        # gross basis 2% over 100 days, less 5 bp in, 3.5 + 2.5 bp futures, 5 bp + 5 bp half-spread out
        expect = 1.02 * (1 - 0.0005) * (1 - 0.0006) * (1 - 0.0005 - 0.0005) - 1
        self.assertAlmostEqual(o["locked_ret"], expect, places=3)

    def test_thin_books_give_no_offer(self):
        self.assertIsNone(rule.offer(SPOT_BIDS, [(100.0, 1.0)], FUT_BIDS, 10.0, 100 * DAY, 0, 0.0, 0.0))
        self.assertIsNone(rule.offer(SPOT_BIDS, SPOT_ASKS, [(102.0, 10.0)], 10.0, 100 * DAY, 0, 0.0, 0.0))
        self.assertIsNone(rule.offer(SPOT_BIDS, SPOT_ASKS, FUT_BIDS, 10.0, 0, 0, 0.0, 0.0))

    def test_choose_shortest_or_best_above_the_hurdle(self):
        offs = [{"contract": "A", "tau_days": 5.0, "locked_yield": 0.20},     # too close to delivery
                {"contract": "B", "tau_days": 30.0, "locked_yield": 0.045},
                {"contract": "C", "tau_days": 90.0, "locked_yield": 0.08},
                {"contract": "D", "tau_days": 200.0, "locked_yield": 0.06}]
        self.assertEqual(rule.choose(offs, 0.04, 0.0, "shortest")["contract"], "B")
        self.assertEqual(rule.choose(offs, 0.04, 0.03, "best")["contract"], "C")
        self.assertIsNone(rule.choose(offs, 0.06, 0.03, "best"))

    def test_tbill_lag(self):
        s = [(0, 4.0), (DAY, 5.0)]
        self.assertIsNone(rule.tbill_asof(s, DAY))
        self.assertEqual(rule.tbill_asof(s, 2 * DAY), 0.04)
        self.assertEqual(rule.tbill_asof(s, 3 * DAY), 0.05)


class FakeDeribit:
    """Answers the public endpoints the lane calls for one BTC future and the BTC_USDC spot book."""

    def __init__(self, expiry_ms, fut_bid=102.0, delivery=None):
        self.expiry_ms, self.fut_bid, self.delivery = expiry_ms, fut_bid, delivery

    def __call__(self, url):
        def ok(result):
            return json.dumps({"result": result}).encode()
        if url.startswith(fwd.FRED):
            return b"observation_date,DTB3\n1970-01-01,4.00\n"
        if "kind=spot" in url:
            return ok([{"instrument_name": "BTC_USDC", "taker_commission": 0.0005}] if "BTC" in url else [])
        if "kind=future" in url:
            return ok([{"instrument_name": "BTC-X", "contract_size": 10, "expiration_timestamp": self.expiry_ms,
                        "taker_commission": 0.00035, "settlement_period": "month"},
                       {"instrument_name": "BTC-PERPETUAL", "settlement_period": "perpetual"}] if "BTC" in url else [])
        if "BTC_USDC" in url:
            return ok({"bids": [[99.9, 1000]], "asks": [[100.0, 2000]]})
        if "BTC-X" in url:
            return ok({"bids": [[self.fut_bid, 1e6]], "asks": [[self.fut_bid + 1, 1e6]]})
        if "get_delivery_prices" in url:
            day = __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime(self.expiry_ms / 1000))
            return ok({"data": [{"date": day, "delivery_price": self.delivery}] if self.delivery else []})
        raise OSError(url)


class Forward(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_open_then_settle_one_lock_per_book(self):
        now = 10 * DAY
        exp = now + 100 * DAY
        get = FakeDeribit(exp)
        offs = fwd.offers("BTC", now, 0.04, get)
        self.assertEqual([o["contract"] for o in offs], ["BTC-X"])
        self.assertTrue(offs[0]["fills_capacity"])
        new = fwd.open_locks(now, offs, 0.04, self.j)
        self.assertEqual(sorted(n["book"] for n in new), ["H0"])          # about 7%/yr: above 4%, not above 7%
        self.assertEqual(fwd.open_locks(now + 1, offs, 0.04, self.j), [])  # one open lock per coin and book
        self.assertEqual(fwd.settle_due(exp, [(0, 4.0)], get, self.j), [])  # not yet an hour past delivery
        get.delivery = 80.0
        done = fwd.settle_due(exp + 3_600_000, [(0, 4.0)], get, self.j)
        self.assertEqual(len(done), 1)
        self.assertLess(abs(done[0]["diff_bp"]), 1.0)
        self.assertGreater(done[0]["excess_ann"], 0.0)
        self.assertEqual(fwd.settle_due(exp + 7_200_000, [(0, 4.0)], get, self.j), [])   # settled once
        s = fwd.status(self.j)
        self.assertEqual((s["locks"], s["settled"], s["open"]), (1, 1, []))

    def test_status_creates_its_journal_folder(self):
        s = fwd.status(self.j / "journal")
        self.assertEqual((s["ticks"], s["locks"]), (0, 0))
        self.assertTrue((self.j / "journal" / "status.json").exists())

    def test_tbill_series_reads_fred_once(self):
        got = fwd.tbill_series(5 * DAY, FakeDeribit(0), self.j)
        self.assertEqual(got, [(0, 4.0)])
        self.assertEqual(fwd.tbill_series(5 * DAY, FakeDeribit(0), self.j), [(0, 4.0)])   # no duplicate row


if __name__ == "__main__":
    unittest.main()
