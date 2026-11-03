import tempfile
import unittest
from pathlib import Path

from scripts import record_lighter_index as rec

MSG = {"channel": "market_stats:159", "type": "update/market_stats", "timestamp": 1793701515138,
       "market_stats": {"symbol": "BRENTOIL", "market_id": 159, "index_price": "105.76", "mark_price": "105.77",
                        "mid_price": "105.79", "best_ask_price": "105.80", "best_bid_price": "105.78",
                        "last_trade_price": "105.76", "funding_rate": "0.0004", "current_funding_rate": "0.0004",
                        "funding_timestamp": 1793700000001, "open_interest": "2621521.24"}}


class LighterIndexTest(unittest.TestCase):
    def test_feed_keeps_known_markets_only(self):
        b = rec.Book()
        b.feed(MSG, 1_793_701_515_200_000)
        other = {**MSG, "market_stats": {**MSG["market_stats"], "market_id": 1}}
        b.feed(other, 1_793_701_515_300_000)
        b.feed({"type": "update/trade", "trades": []}, 1_793_701_515_400_000)
        rows = b.drain()
        self.assertEqual(list(rows), ["BRENTOIL"])
        row = dict(zip(rec.COLS, rows["BRENTOIL"][0]))
        self.assertEqual(row["index"], 105.76)
        self.assertEqual(row["bid"], 105.78)
        self.assertEqual(row["funding_ts"], 1793700000001)
        self.assertEqual(b.stat["unknown_market"], 1)

    def test_sample_repeats_latest_state(self):
        b = rec.Book()
        b.feed(MSG, 1_000_000)
        b.sample(2_000_000)
        r = b.drain()["BRENTOIL"]
        self.assertEqual([x[-1] for x in r], [0, 1])
        self.assertEqual(r[1][0], 2_000_000)
        self.assertEqual(r[1][2:-1], r[0][2:-1])
        b.latest.clear()
        b.sample(3_000_000)
        self.assertEqual(b.drain(), {})

    def test_all_channel_shape(self):
        b = rec.Book()
        b.feed({**MSG, "market_stats": {"159": MSG["market_stats"]}}, 1)
        self.assertEqual(len(b.drain()["BRENTOIL"]), 1)

    def test_write_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            b = rec.Book()
            b.feed(MSG, 1_793_701_515_200_000)
            self.assertEqual(rec.write_parts(b.drain(), 1_793_701_515.0, out), 1)
            day = rec.utc_day(1_793_701_515_200_000)
            df = rec.load("BRENTOIL", day, out)
            self.assertEqual(list(df.columns), rec.COLS)
            self.assertAlmostEqual(df["mark"].iloc[0], 105.77)
            self.assertIsNone(rec.load("WTI", day, out))

    def test_full_stops_on_low_disk(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("disk below", rec.full(Path(d), free_gb=1.0))
            self.assertEqual(rec.full(Path(d), free_gb=50.0), "")


if __name__ == "__main__":
    unittest.main()
