"""scripts/record_lighter_trades.py: trade and quote rows from the public stream's message shapes (offline)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import record_lighter_trades as lt  # noqa: E402

T_US = 1_793_226_264_700_000


def trade(i=36963312382, price="101.914", size="0.078", ask=718715, bid=1483, maker_ask=True, **extra):
    d = {"trade_id": i, "type": "trade", "market_id": 145, "size": size, "price": price, "ask_account_id": ask,
         "bid_account_id": bid, "is_maker_ask": maker_ask, "block_height": 368199848, "timestamp": 1793226264654,
         "taker_fee": 266, "taker_position_size_before": "38.298", "taker_entry_quote_before": "3913.559208",
         "taker_initial_margin_fraction_before": 500, "maker_fee": 38, "maker_position_size_before": "-18.472",
         "maker_entry_quote_before": "1882.587996", "maker_initial_margin_fraction_before": 500,
         "transaction_time": 1793226264654509}
    d.update(extra)
    return d


def update(trades=(), liq=(), market=145, kind="update/trade"):
    return {"channel": f"trade:{market}", "type": kind, "trades": list(trades), "liquidation_trades": list(liq)}


def ticker(bid="101.910", bq="156.686", ask="101.914", aq="2.944", market=145, upd=1793226254820121):
    return {"channel": f"ticker:{market}", "type": "update/ticker", "nonce": 25989459126,
            "ticker": {"s": "WTI", "a": {"price": ask, "size": aq}, "b": {"price": bid, "size": bq},
                       "last_updated_at": upd}}


class ParseTests(unittest.TestCase):
    def test_a_trade_keeps_both_accounts_the_maker_side_and_the_positions_before(self):
        t = lt.Tape()
        t.feed(update([trade()]), T_US)
        row = t.rows[("trade", "WTI")][0]
        self.assertEqual(row[:2], (T_US, 36963312382))
        self.assertEqual(row[6:14], (101.914, 0.078, 718715, 1483, 1, 266, 38, 38.298))
        self.assertEqual(row[14:], (3913.559208, 500, 0, -18.472, 1882.587996, 500))
        self.assertEqual(row[5], 0)

    def test_liquidation_trades_are_flagged_and_repeats_are_dropped(self):
        t = lt.Tape()
        t.feed(update([trade(i=1)], liq=[trade(i=2, taker_fee=10000, type="liquidation")]), T_US)
        t.feed(update([trade(i=1), trade(i=3)], kind="subscribed/trade"), T_US + 5)
        rows = t.rows[("trade", "WTI")]
        self.assertEqual([r[1] for r in rows], [1, 2, 3])
        self.assertEqual([r[5] for r in rows], [0, 1, 0])
        self.assertEqual(rows[1][11], 10000)
        self.assertEqual(t.stat["dup"], 1)

    def test_a_missing_field_is_marked_not_guessed(self):
        t = lt.Tape()
        d = trade()
        for k in ("taker_fee", "taker_position_size_before", "ask_account_id"):
            d.pop(k)
        t.feed(update([d]), T_US)
        row = t.rows[("trade", "WTI")][0]
        self.assertEqual((row[8], row[11]), (-1, -1))
        self.assertTrue(row[13] != row[13])                    # NaN

    def test_quotes_are_rows_only_when_they_change(self):
        t = lt.Tape()
        t.feed(ticker(), T_US)
        t.feed(ticker(), T_US + 1)
        t.feed(ticker(aq="3.0"), T_US + 2)
        rows = t.rows[("quote", "WTI")]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][3:], (101.910, 156.686, 101.914, 2.944))

    def test_other_markets_map_to_their_symbols_and_unknown_ones_are_counted(self):
        t = lt.Tape()
        t.feed(update([trade(i=5)], market=158), T_US)
        t.feed(update([trade(i=6)], market=999), T_US)
        t.feed({"session_id": "x", "type": "connected"}, T_US)
        self.assertIn(("trade", "NATGAS"), t.rows)
        self.assertEqual(t.stat["unknown_market"], 1)


class FileTests(unittest.TestCase):
    def test_parts_round_trip_in_arrival_order_and_split_by_day(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            t = lt.Tape()
            t.feed(update([trade(i=1), trade(i=2)]), T_US)
            t.feed(update([trade(i=3)]), T_US + 86_400_000_000)
            with mock.patch.object(lt.os, "getpid", return_value=7):
                self.assertEqual(lt.write_parts(t.drain(), T_US / 1e6, out), 3)
            df = lt.load("trade", "WTI", lt.utc_day(T_US), out)
            self.assertEqual(list(df.trade_id), [1, 2])
            self.assertEqual(list(lt.load("trade", "WTI", lt.utc_day(T_US + 86_400_000_000), out).trade_id), [3])
            self.assertIsNone(lt.load("trade", "WTI", "2020-01-01", out))

    def test_caps(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(lt.full(out, free_gb=9.0), "")
            self.assertIn("free", lt.full(out, free_gb=lt.MIN_FREE_GB - 0.1))
            (out / "x").mkdir()
            (out / "x" / "big.parquet").write_bytes(b"0" * int(lt.MAX_MB * 1e6))
            self.assertIn("MB", lt.full(out, free_gb=9.0))


if __name__ == "__main__":
    unittest.main()
