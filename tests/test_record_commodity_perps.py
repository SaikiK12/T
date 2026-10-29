"""scripts/record_commodity_perps.py: Hyperliquid xyz and Kraken Futures message shapes into rows (offline)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_commodity_perps as cp  # noqa: E402

T_US = 1_793_227_549_000_000


def hl_bbo(bid="102.01", bq="3549.726", bn=1, ask="102.02", aq="3143.56", an=13, coin="xyz:CL", t=1793227549039):
    side = lambda p, s, n: {"px": p, "sz": s, "n": n} if p else None
    return {"channel": "bbo", "data": {"coin": coin, "time": t, "bbo": [side(bid, bq, bn), side(ask, aq, an)]}}


def hl_trade(tid=321057999416165, px="102.0", sz="43.244", side="B", coin="xyz:CL"):
    return {"channel": "trades", "data": [{"coin": coin, "side": side, "px": px, "sz": sz, "time": 1793227546408,
                                           "hash": "0x1", "tid": tid, "users": ["0xaaa", "0xbbb"]}]}


def hl_ctx(oracle="102.0", mark="102.0", oi="2548066.162", funding="0.00000625", coin="xyz:CL"):
    return {"channel": "activeAssetCtx", "data": {"coin": coin, "ctx": {
        "funding": funding, "openInterest": oi, "prevDayPx": "99.858", "dayNtlVlm": "291909773.49", "premium": "0.0001",
        "oraclePx": oracle, "markPx": mark, "midPx": "102.015", "impactPxs": ["102.01", "102.02"],
        "dayBaseVlm": "2860009.636"}}}


def kr_tick(bid=101.818, ask=102.021, index=101.97491, product="PF_WTIOILUSD", pred=-0.00891):
    return {"time": 1793227549087, "product_id": product, "funding_rate": -0.00647, "funding_rate_prediction": pred,
            "relative_funding_rate": -6.3e-05, "relative_funding_rate_prediction": -8.7e-05,
            "next_funding_rate_time": 1793228400000, "leverage": "25x", "premium": -0.1, "feed": "ticker", "bid": bid,
            "ask": ask, "bid_size": 2.5, "ask_size": 1.3, "volume": 35194.1, "index": index, "last": 101.976,
            "markPrice": 101.99, "openInterest": 15806.0, "suspended": False, "tag": "perpetual"}


def kr_trade(uid="u1", price=101.976, qty=0.4, product="PF_WTIOILUSD"):
    return {"feed": "trade", "product_id": product, "uid": uid, "side": "buy", "type": "fill", "seq": 11,
            "time": 1793227549100, "qty": qty, "price": price}


class HyperliquidTests(unittest.TestCase):
    def test_bbo_rows_only_on_change_with_both_sides(self):
        t = cp.Tape()
        t.hl(hl_bbo(), T_US)
        t.hl(hl_bbo(), T_US + 1)
        t.hl(hl_bbo(aq="3000"), T_US + 2)
        rows = t.rows[("hlbbo", "CL")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (T_US, 1793227549039, 102.01, 3549.726, 1, 102.02, 3143.56, 13))

    def test_an_empty_side_is_nan_not_zero(self):
        t = cp.Tape()
        t.hl(hl_bbo(bid=None), T_US)
        row = t.rows[("hlbbo", "CL")][0]
        self.assertTrue(row[2] != row[2])
        self.assertEqual(row[4], 0)

    def test_trades_are_deduplicated_by_trade_id_and_keep_both_addresses(self):
        t = cp.Tape()
        t.hl(hl_trade(), T_US)
        t.hl(hl_trade(), T_US + 1)
        t.hl(hl_trade(tid=2, side="A"), T_US + 2)
        rows = t.rows[("hltrade", "CL")]
        self.assertEqual([r[2] for r in rows], [321057999416165, 2])
        self.assertEqual(rows[0][3:], ("B", 102.0, 43.244, "0xaaa", "0xbbb"))
        self.assertEqual(t.stat["dup"], 1)

    def test_context_rows_on_change_and_other_coins_keep_their_names(self):
        t = cp.Tape()
        t.hl(hl_ctx(), T_US)
        t.hl(hl_ctx(), T_US + 1)
        t.hl(hl_ctx(oracle="102.5"), T_US + 2)
        t.hl(hl_ctx(coin="xyz:NATGAS"), T_US + 3)
        self.assertEqual(len(t.rows[("hlctx", "CL")]), 2)
        self.assertEqual(t.rows[("hlctx", "CL")][0][1:5], (6.25e-06, 2548066.162, 102.0, 102.0))
        self.assertIn(("hlctx", "NATGAS"), t.rows)

    def test_acks_are_ignored_and_other_channels_counted(self):
        t = cp.Tape()
        t.hl({"channel": "subscriptionResponse", "data": {}}, T_US)
        t.hl({"channel": "pong"}, T_US)
        t.hl({"channel": "l2Book", "data": {}}, T_US)
        self.assertEqual(t.rows, {})
        self.assertEqual(t.stat["unknown"], 1)


class KrakenTests(unittest.TestCase):
    def test_ticker_keeps_index_and_funding_and_writes_only_on_change(self):
        t = cp.Tape()
        t.kraken(kr_tick(), T_US)
        t.kraken(kr_tick(), T_US + 1)
        t.kraken(kr_tick(index=102.1), T_US + 2)
        t.kraken(kr_tick(product="PF_NATGASUSD"), T_US + 3)
        rows = t.rows[("krtick", "PF_WTIOILUSD")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][2:9], (101.818, 2.5, 102.021, 1.3, 101.976, 101.97491, 101.99))
        self.assertIn(("krtick", "PF_NATGASUSD"), t.rows)

    def test_a_message_without_a_symbol_is_counted_and_never_stored(self):
        t = cp.Tape()
        t.kraken({"feed": "ticker", "bid": 1.0}, T_US)
        t.hl({"channel": "bbo", "data": {"coin": "", "time": 1, "bbo": [None, None]}}, T_US)
        self.assertEqual(t.rows, {})
        self.assertEqual(t.stat["unknown"], 2)

    def test_trades_dedupe_by_uid_and_the_snapshot_is_not_stored(self):
        t = cp.Tape()
        t.kraken(kr_trade(), T_US)
        t.kraken(kr_trade(), T_US + 1)
        t.kraken({"feed": "trade_snapshot", "product_id": "PF_WTIOILUSD", "trades": [{"uid": "old"}]}, T_US)
        t.kraken({"feed": "heartbeat"}, T_US)
        t.kraken({"event": "subscribed", "feed": "ticker", "product_ids": ["PF_WTIOILUSD"]}, T_US)
        t.kraken({"event": "subscribed", "feed": "trade", "product_ids": ["PF_WTIOILUSD"]}, T_US)
        t.kraken({"event": "info", "version": 1}, T_US)
        self.assertEqual(sorted(k for k in t.rows), [("krtrade", "PF_WTIOILUSD")])
        rows = t.rows[("krtrade", "PF_WTIOILUSD")]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][2:], ("u1", "buy", "fill", 11, 0.4, 101.976))
        self.assertEqual(t.stat["dup"], 1)


def bn_book(bid="102.12", ask="102.13", sym="CLUSDT", u=11951436712974, t=1793227827197):
    return {"stream": f"{sym.lower()}@bookTicker", "data": {"e": "bookTicker", "u": u, "s": sym, "ps": sym, "b": bid,
                                                           "B": "688.73", "a": ask, "A": "1483.99", "T": t, "E": t}}


def bn_agg(aid=24939955, sym="CLUSDT", price="102.13", q="3.48", nq="3.48", maker=False):
    return {"stream": f"{sym.lower()}@aggTrade", "data": {"e": "aggTrade", "E": 1793227827347, "a": aid, "s": sym,
                                                          "p": price, "q": q, "nq": nq, "f": 1, "l": 1,
                                                          "T": 1793227827197, "m": maker}}


def bn_mark(mark="102.13", index="102.19840676", sym="CLUSDT"):
    return {"stream": f"{sym.lower()}@markPrice@1s", "data": {
        "e": "markPriceUpdate", "E": 1793227827844, "s": sym, "p": mark + "000000", "ap": mark, "P": "102.09098791",
        "i": index, "r": "0.00000000", "T": 1793232000000}}


class BinanceTests(unittest.TestCase):
    def test_quotes_keep_the_first_update_in_each_100_ms_bucket_and_only_changes(self):
        t = cp.Tape()
        t.binance(bn_book(), T_US)
        t.binance(bn_book(bid="102.11", u=2), T_US + 50_000)           # same bucket: dropped
        t.binance(bn_book(bid="102.11", u=3), T_US + 120_000)          # next bucket: kept
        t.binance(bn_book(bid="102.11", u=4), T_US + 250_000)          # next bucket, unchanged: dropped
        rows = t.rows[("bnbook", "CLUSDT")]
        self.assertEqual([r[2] for r in rows], [11951436712974, 3])
        self.assertEqual(rows[0][3:], (102.12, 688.73, 102.13, 1483.99))

    def test_aggtrades_keep_nq_and_the_maker_flag_and_drop_repeats(self):
        t = cp.Tape()
        t.binance(bn_agg(), T_US)
        t.binance(bn_agg(), T_US + 1)
        t.binance(bn_agg(aid=2, nq="0.00", maker=True), T_US + 2)
        rows = t.rows[("bnagg", "CLUSDT")]
        self.assertEqual([r[2] for r in rows], [24939955, 2])
        self.assertEqual(rows[1][3:], (102.13, 3.48, 0.0, 1))
        self.assertEqual(t.stat["dup"], 1)

    def test_mark_price_rows_carry_the_index_and_next_funding_time(self):
        t = cp.Tape()
        t.binance(bn_mark(), T_US)
        t.binance(bn_mark(), T_US + 1)
        t.binance(bn_mark(index="102.3"), T_US + 2)
        t.binance(bn_mark(sym="XAUUSDT"), T_US + 3)
        rows = t.rows[("bnmark", "CLUSDT")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][2:], (102.13, 102.19840676, 102.09098791, 0.0, 1793232000000))
        self.assertIn(("bnmark", "XAUUSDT"), t.rows)

    def test_urls_cover_every_symbol_and_stream(self):
        u = cp.bn_url(cp.BN_MARKET, ("aggTrade", "markPrice@1s"))
        self.assertEqual(u.count("@aggTrade"), len(cp.BN_SYMBOLS))
        self.assertEqual(u.count("@markPrice@1s"), len(cp.BN_SYMBOLS))
        self.assertTrue(u.startswith(cp.BN_MARKET + "clusdt@aggTrade"))


class FileTests(unittest.TestCase):
    def test_parts_round_trip_and_split_by_day(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            t = cp.Tape()
            t.hl(hl_trade(tid=1), T_US)
            t.hl(hl_trade(tid=2), T_US + 1)
            t.hl(hl_trade(tid=3), T_US + 86_400_000_000)
            t.kraken(kr_tick(), T_US)
            with mock.patch.object(cp.os, "getpid", return_value=7):
                self.assertEqual(cp.write_parts(t.drain(), T_US / 1e6, out), 4)
            self.assertEqual(list(cp.load("hltrade", "CL", cp.utc_day(T_US), out).tid), [1, 2])
            self.assertEqual(list(cp.load("hltrade", "CL", cp.utc_day(T_US + 86_400_000_000), out).tid), [3])
            self.assertEqual(len(cp.load("krtick", "PF_WTIOILUSD", cp.utc_day(T_US), out)), 1)
            self.assertIsNone(cp.load("hltrade", "GOLD", cp.utc_day(T_US), out))

    def test_caps(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(cp.full(out, free_gb=9.0), "")
            self.assertIn("free", cp.full(out, free_gb=cp.MIN_FREE_GB - 0.1))
            (out / "x").mkdir()
            # The recorder checks st_size, so allocating MAX_MB bytes in RAM
            # and writing them to disk is unnecessary. A sparse file exercises
            # the same cap without exhausting the test runner.
            with (out / "x" / "big.parquet").open("wb") as f:
                f.truncate(int(cp.MAX_MB * 1e6))
            self.assertIn("MB", cp.full(out, free_gb=9.0))

    def test_subscriptions_cover_every_coin_and_product(self):
        hl = list(cp.hl_subscriptions())
        self.assertEqual(len(hl), 3 * len(cp.HL_COINS))
        self.assertTrue(all(s["subscription"]["coin"].startswith("xyz:") for s in hl))
        kr = list(cp.kr_subscriptions())
        self.assertEqual([s["feed"] for s in kr], ["ticker", "trade"])
        self.assertEqual(kr[0]["product_ids"], list(cp.KR_PRODUCTS))


if __name__ == "__main__":
    unittest.main()
