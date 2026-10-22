import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from scripts import fetch_deribit_trades as fd


def tr(i, ts, name="BTC-8JAN21-24000-P", side="buy", amount=1.0, iv=50.0, block=False):
    x = {"trade_id": str(i), "timestamp": ts, "instrument_name": name, "direction": side, "amount": amount, "iv": iv,
         "price": 0.01, "index_price": 30000.0 + i}
    if block:
        x["block_trade_id"] = f"B{i}"
    return x


def pager(all_trades, size):
    """A fake history server: trades with start <= ts <= end, in order, `size` per page."""
    def get(url):
        q = parse_qs(urlparse(url).query)
        a, b = int(q["start_timestamp"][0]), int(q["end_timestamp"][0])
        hit = [x for x in all_trades if a <= x["timestamp"] <= b]
        return {"trades": hit[:size], "has_more": len(hit) > size}
    return get


class FetchDeribitTradesTest(unittest.TestCase):
    def test_paging_keeps_every_trade_once_across_a_shared_millisecond(self):
        rows = [tr(1, 10), tr(2, 20), tr(3, 20), tr(4, 30), tr(5, 30)]   # page 2 restarts inside ms 20
        got, n = fd.trades("BTC", 0, 100, get=pager(rows, 3))
        self.assertEqual([x["trade_id"] for x in got], ["1", "2", "3", "4", "5"])
        self.assertEqual(n, 3)
        with self.assertRaises(RuntimeError):                          # a full page inside one millisecond
            fd.trades("BTC", 0, 100, get=pager([tr(i, 20) for i in range(5)], 3))

    def test_instrument_names_parse_to_expiry_strike_and_side(self):
        self.assertEqual(fd.parse_instrument("BTC-8JAN21-24000-P"),
                         (int(pd.Timestamp("2021-01-08 08:00").value // 10**6), 24000.0, "P"))
        self.assertEqual(fd.parse_instrument("ETH-27DEC24-3500-C")[1:], (3500.0, "C"))

    def test_flow_sums_taker_sides_and_blocks_per_hour_and_instrument(self):
        h = 3_600_000
        rows = [tr(1, 5, side="buy", amount=2, iv=40), tr(2, 6, side="sell", amount=1, iv=70, block=True),
                tr(3, h + 1, side="sell", amount=3), tr(4, 7, name="BTC-8JAN21-30000-C", amount=0.5)]
        f = fd.flow(rows)
        r = f[(f.t == 0) & (f.cp == "P")].iloc[0]
        self.assertEqual((r.buy, r.sell, r.n_buy, r.n_sell, r.block_buy, r.block_sell), (2, 1, 1, 1, 0, 1))
        self.assertAlmostEqual(r.iv, 50.0)                     # (2 x 40 + 1 x 70) / 3
        self.assertEqual(r.index_price, 30002.0)               # the hour's last trade
        self.assertEqual(len(f), 3)

    def test_month_writes_flow_and_blocks_and_skips_a_written_month(self):
        t0 = int(pd.Timestamp("2021-01-01").value // 10**6)
        rows = [tr(1, t0 + 5), tr(2, t0 + 6, block=True), tr(3, t0 + 40 * 86_400_000)]   # the last is February
        with tempfile.TemporaryDirectory() as d:
            info = fd.month("BTC", "2021-01", out=Path(d), get=pager(rows, 1000))
            self.assertEqual((info["trades"], info["blocks"]), (2, 1))
            self.assertEqual(len(pd.read_parquet(Path(d) / "BTC" / "blocks" / "2021-01.parquet")), 1)
            self.assertIsNone(fd.month("BTC", "2021-01", out=Path(d), get=pager(rows, 1000)))


if __name__ == "__main__":
    unittest.main()
