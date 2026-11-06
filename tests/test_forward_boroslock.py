import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts import boroslock_fwd_rule as rule
from scripts import forward_boroslock as fb

DAY = 86400
T = 1_800_000_000 - (1_800_000_000 % DAY)          # a maturity at 00:00 UTC
NOW = T - 49 * DAY + 2 * 3600 + 300                 # 49 days before, at 02:05 UTC


def zbytes(lines):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("x", "\n".join(lines))
    return b.getvalue()


def market(mid=229, venue="HYPERLIQUID", coin="BTC", token=1, period=3600):
    sym = f"{venue}-{coin}{'USDT' if venue == 'BINANCE' else ''}-XX"
    return {"marketId": mid, "tokenId": token, "imData": {"symbol": sym, "maturity": T},
            "metadata": {"underlyingSymbol": coin, "isSpreadMarket": False},
            "config": {"takerFee": str(int(5e14))}, "extConfig": {"settleFeeRate": str(int(1e15)), "paymentPeriod": period},
            "data": {"bestBid": 0.0835, "bestAsk": 0.084, "notionalOI": 17.5, "floatingApr": 0.1095}}


class Fake:
    """A fetch that serves the Boros list, assets, books, settlement months and Hyperliquid funding."""

    def __init__(self, hl_rate=1.25e-5, boros_apr=0.1095, miss=()):
        self.hl_rate, self.boros_apr, self.miss = hl_rate, boros_apr, set(miss)

    def __call__(self, url, data=None, timeout=30):
        if "/markets?" in url:
            return json.dumps({"results": [market(), market(241, token=3),
                                           {**market(9, coin="SOL")}]}).encode()
        if url.endswith("/assets"):
            return json.dumps({"results": [{"tokenId": 1, "usdPrice": 100000.0},
                                           {"tokenId": 3, "usdPrice": 1.0}]}).encode()
        if "order-book" in url:
            yu = "100000000000000000"                  # 0.1 BTC per level
            return json.dumps({"long": {"ia": [835, 830, 820], "sz": [yu, yu, yu]},
                               "short": {"ia": [840], "sz": [yu]}, "syncStatus": {"timestamp": NOW - 5}}).encode()
        if "historical-data" in url:
            hrs = range(T - 50 * DAY, T + 3600, 3600)
            return zbytes([json.dumps({"timestamp": h + 10, "settlementApr": self.boros_apr})
                           for h in hrs if h not in self.miss])
        if url == fb.HL:
            start = json.loads(data)["startTime"] // 1000
            return json.dumps([{"time": h * 1000 + 40, "fundingRate": str(self.hl_rate)}
                               for h in range(start - start % 3600 + 3600, T + 3601, 3600)][:500]).encode()
        raise OSError(url)


class Rule(unittest.TestCase):
    def test_levels_read_ticks_and_decimals(self):
        a = rule.levels({"ia": [835, 830], "sz": ["1000000000000000000", "0"]})
        self.assertAlmostEqual(a[0][0], 0.0835)
        self.assertEqual(len(a), 1)
        self.assertAlmostEqual(rule.levels({"ia": [0.0835], "sz": ["1"]})[0][0], 0.0835)

    def test_walk_and_thin_book(self):
        bids = [(0.09, 1.0), (0.08, 1.0)]
        self.assertAlmostEqual(rule.walk(bids, 1.5), (0.09 + 0.5 * 0.08) / 1.5)
        self.assertIsNone(rule.walk(bids, 2.5))

    def test_settle_exact_oracle_and_a_miss(self):
        lk = {"t0": NOW, "maturity": T, "period": 3600, "locked": 0.08}
        hrs = list(range(NOW - NOW % 3600 + 3600, T + 1, 3600))
        venue = [(h, 1.25e-5) for h in hrs]
        boros = [(h + 10, 0.1095) for h in hrs]
        s = rule.settle(lk, boros, venue)
        self.assertAlmostEqual(s["diff_bp"], 0.0, places=9)
        self.assertEqual(s["misses"], 0)
        s = rule.settle(lk, boros[:10] + boros[11:], venue)
        self.assertEqual(s["misses"], 1)
        self.assertAlmostEqual(s["diff_bp"], 1.25e-5 * 1e4, places=9)

    def test_excess_scales_costs(self):
        self.assertAlmostEqual(rule.excess_ann(0.08, 0.0015, 0.04, 73, m=2),
                               0.08 - 0.0015 - 2 * rule.HEDGE_RT * 5 - 0.04)


class Runner(unittest.TestCase):
    def test_offers_scope_and_fill(self):
        offs = fb.offers(NOW, 0.04, Fake())
        # SOL is out of scope; market 241 is USD-collateral: $10k = 10,000 YU > 0.3 YU of bids, too thin
        self.assertEqual({o["market"] for o in offs}, {"229-HYPERLIQUID-BTC-XX"})
        o = offs[0]                                            # $10k at $100k = 0.1 BTC: the best level
        self.assertAlmostEqual(o["fill_apr"], 0.0835)
        self.assertAlmostEqual(o["locked"], 0.0835 - 0.0015)
        self.assertFalse(o["fills_capacity"])                  # $100k = 1 BTC > 0.3 BTC of bids

    def test_open_settle_status_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d)
            offs = fb.offers(NOW, 0.04, Fake())
            new = fb.open_locks(offs, j)
            self.assertEqual({(n["book"], n["coin"]) for n in new}, {("K0", "BTC"), ("K1", "BTC")})
            self.assertEqual(fb.open_locks(offs, j), [])      # one open lock per book and coin
            series = [((T - 60 * DAY) * 1000, 4.0)]
            self.assertEqual(fb.settle_due(T + 3600, series, Fake(), j), [])   # too early
            out = fb.settle_due(T + 3 * 3600, series, Fake(miss={T - 10 * DAY}), j)
            self.assertEqual(len(out), 2)
            self.assertEqual(out[0]["misses"], 1)
            self.assertAlmostEqual(out[0]["diff_bp"], 0.125, places=6)
            self.assertEqual(fb.settle_due(T + 4 * 3600, series, Fake(), j), [])  # settled once
            s = fb.status(j)
            self.assertEqual((s["locks"], s["settled"], s["open"]), (2, 2, []))


if __name__ == "__main__":
    unittest.main()
