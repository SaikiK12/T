from dataclasses import replace
from decimal import Decimal
import json
import unittest

from lab.stream_quotes import (FrameClock, NS, Replay, ReferencePrice, StreamBook, decode,
                               entry_cash_drift, freshness, source_ns)

UTC = 1_790_000_000*NS
ANCHOR = FrameClock(UTC, 10*NS)


def metadata():
    return {"BTC": {"mexc": {"symbol": "BTC_USDT", "contractSize": ".01", "marketOrderMaxLevel": 2,
                           "volUnit": 1, "minVol": 1, "maxVol": 100000, "type": 1, "settleCoin": "USDT",
                           "state": 0, "apiAllowed": True},
                    "lighter": {"symbol": "BTC", "supported_size_decimals": 2, "min_base_amount": ".01",
                                "min_quote_amount": "10", "status": "active", "is_frozen": False,
                                "market_config": {"force_reduce_only": False, "trading_hours": ""}}}}


def payload(venue, second=0, *, version=1, ask=101, size=10):
    if venue == "mexc":
        return {"channel": "push.depth.full", "symbol": "BTC_USDT", "ts": UTC//1_000_000,
                "data": {"cts": UTC//1_000_000+int(second*1000), "version": version,
                         "bids": [[99, size*100, 1]], "asks": [[ask, size*100, 1]]}}
    return {"type": "update/ticker", "channel": "ticker:1", "nonce": version,
            "timestamp": UTC//1_000_000+int(second*1000),
            "ticker": {"s": "BTC", "last_updated_at": UTC//1000+int(second*1e6),
                       "b": {"price": "99", "size": str(size)}, "a": {"price": str(ask), "size": str(size)}}}


def frame(venue, second=0, *, data=None, **kwargs):
    return {"venue": venue, "number": int(second*1000)+1, "utc_ns": UTC+int(second*NS),
            "mono_ns": ANCHOR.mono_ns+int(second*NS), "raw": json.dumps(data or payload(venue, second, **kwargs))}


def replay(frames):
    connections = {v: {"opened_mono_ns": 0, "closed_mono_ns": 100*NS} for v in ("mexc", "lighter")}
    return Replay(frames, metadata(), {1: "BTC"}, ANCHOR, connections)


class StreamContractTests(unittest.TestCase):
    def test_clock_units_and_epoch_are_explicit_not_guessed(self):
        self.assertEqual(source_ns(UTC//1000, "us"), UTC)
        self.assertEqual(source_ns(UTC//1_000_000, "ms"), UTC)
        for value in (True, 1., "1790000000000", -1, 1):
            with self.assertRaises(ValueError):
                source_ns(value, "ms")
        with self.assertRaises(ValueError):
            source_ns(UTC//1_000_000, "us")

    def test_mexc_full_depth_uses_contract_size_not_order_count(self):
        _, _, b = decode("mexc", payload("mexc"), ANCHOR, metadata(), {1:"BTC"})
        self.assertIsInstance(b, StreamBook)
        self.assertEqual(b.asks[0].size, 10.)
        self.assertEqual(b.source_time_ns, UTC)
        self.assertEqual(b.depth.receive_time_ns, ANCHOR.mono_ns)

    def test_missing_source_clock_never_uses_envelope_or_local_fallback(self):
        mx, lt = payload("mexc"), payload("lighter")
        del mx["data"]["cts"]
        del lt["ticker"]["last_updated_at"]
        for venue, data in (("mexc",mx),("lighter",lt)):
            self.assertIsInstance(decode(venue,data,ANCHOR,metadata(),{1:"BTC"})[2],str)

    def test_fair_and_index_keep_their_documented_publication_clocks(self):
        mx = {"channel":"push.fair.price","symbol":"BTC_USDT","ts":UTC//1_000_000,
              "data":{"symbol":"BTC_USDT","price":"102"}}
        lt = {"type":"update/market_stats","channel":"market_stats:1","timestamp":UTC//1_000_000,
              "market_stats":{"market_id":1,"symbol":"BTC","index_price":"103"}}
        for venue,data,expected in (("mexc",mx,102),("lighter",lt,103)):
            kind,symbol,price=decode(venue,data,ANCHOR,metadata(),{1:"BTC"})
            self.assertEqual((kind,symbol),("reference","BTC"))
            self.assertIsInstance(price,ReferencePrice)
            self.assertEqual(price.price,expected)
            self.assertEqual(price.source_time_ns,UTC)
        lt["market_stats"]["symbol"]="OTHER"
        self.assertIsInstance(decode("lighter",lt,ANCHOR,metadata(),{1:"BTC"})[2],str)

    def test_time_skew_clock_steps_future_and_stale_are_separate_failures(self):
        _,_,b=decode("mexc",payload("mexc"),ANCHOR,metadata(),{1:"BTC"})
        self.assertEqual(freshness(b,ANCHOR.mono_ns+NS,ANCHOR),[])
        self.assertIn("receive_age_outside_0_1s",freshness(b,ANCHOR.mono_ns+NS+1,ANCHOR))
        future=replace(b,depth=replace(b.depth,exchange_time_ns=UTC+NS))
        self.assertIn("reported_source_age_outside_minus100ms_2s",freshness(future,ANCHOR.mono_ns,ANCHOR))
        step=replace(b,clock=FrameClock(UTC+100_000_000,ANCHOR.mono_ns))
        self.assertIn("local_UTC_step_over_50ms",freshness(step,ANCHOR.mono_ns,ANCHOR))

    def test_duplicate_or_production_heartbeat_does_not_refresh_first_seen(self):
        r=replay([frame("mexc"),frame("mexc",.8)])
        r.advance(ANCHOR.mono_ns+2*NS)
        self.assertEqual(r.latest["mexc","book","BTC"].clock,ANCHOR)
        self.assertIn("receive_age_outside_0_1s",freshness(r.latest["mexc","book","BTC"],r.target,ANCHOR))

    def test_conflicting_and_bad_updates_poison_until_strict_new_full_quote(self):
        bad=payload("mexc",.1);del bad["data"]["cts"]
        r=replay([frame("mexc"),frame("mexc",.1,data=bad),frame("mexc",.2),
                  frame("mexc",.3,version=2),frame("mexc",.4,version=2,ask=102)])
        r.advance(ANCHOR.mono_ns+250_000_000)
        self.assertIsInstance(r.latest["mexc","book","BTC"],str)
        r.advance(ANCHOR.mono_ns+350_000_000)
        self.assertIsInstance(r.latest["mexc","book","BTC"],StreamBook)
        r.advance(ANCHOR.mono_ns+450_000_000)
        self.assertEqual(r.latest["mexc","book","BTC"],"conflicting_duplicate")

    def test_version_regression_and_unidentified_corruption_are_not_silent(self):
        r=replay([frame("mexc",version=2),frame("mexc",.1,version=1)])
        r.advance(ANCHOR.mono_ns+200_000_000)
        self.assertEqual(r.latest["mexc","book","BTC"],"source_clock_or_version_regression")
        f=frame("lighter",.2);f["raw"]="[]"
        r=replay([frame("lighter"),f]);r.advance(ANCHOR.mono_ns+300_000_000)
        self.assertEqual(r.latest["lighter","book","BTC"],"unattributed_invalid_frame")

    def test_causal_grid_excludes_future_quotes_and_never_creates_delayed_quantity(self):
        r=replay([frame("mexc",.2),frame("lighter",.2)])
        before,_=r.observe("BTC",ANCHOR.mono_ns)
        after,_=r.observe("BTC",ANCHOR.mono_ns+300_000_000,allow_new_quantity=False)
        self.assertIsNone(before["quantity_base"])
        self.assertIsNone(after["cost"])
        self.assertIn("no_causal_decision_quantity",after["book_flags"])
        with self.assertRaises(ValueError):r.advance(ANCHOR.mono_ns)

    def test_fixed_decision_quantity_and_capital_survive_the_access_delay(self):
        r=replay([frame("mexc"),frame("lighter"),frame("mexc",.3,version=2,ask=103),
                  frame("lighter",.3,version=2,ask=103)])
        before,b0=r.observe("BTC",ANCHOR.mono_ns)
        after,b1=r.observe("BTC",ANCHOR.mono_ns+300_000_000,before["quantity_base"],allow_new_quantity=False)
        self.assertEqual(before["quantity_base"],after["quantity_base"])
        self.assertEqual(after["book_flags"],[])
        self.assertFalse(after["execution_ready"])
        self.assertEqual(after["cost"]["capital_usd"],10000.)
        self.assertEqual([s["multiple"] for s in after["cost"]["scenarios"]],[1,2,3])
        drift=entry_cash_drift(b0,b1,Decimal(before["quantity_base"]))
        self.assertEqual(drift,{"long_mexc_usd":5.,"long_lighter_usd":5.})

    def test_lighter_bbo_cannot_claim_hidden_deeper_capacity(self):
        r=replay([frame("mexc"),frame("lighter",size=.1)])
        row,_=r.observe("BTC",ANCHOR.mono_ns)
        self.assertFalse(row["cost"]["displayed_fillable"])
        self.assertIn("insufficient_displayed_depth",row["book_flags"])

    def test_disconnect_invalidates_even_a_recent_quote(self):
        r=replay([frame("mexc"),frame("lighter")])
        r.connections["lighter"]["closed_mono_ns"]=ANCHOR.mono_ns+100_000_000
        row,_=r.observe("BTC",ANCHOR.mono_ns+200_000_000)
        self.assertIn("lighter:disconnected",row["book_flags"])


if __name__ == "__main__":
    unittest.main()
