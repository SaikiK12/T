import csv
import gzip
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import record_digest  # noqa: E402
import record_mexc_ticker  # noqa: E402
import record_notices  # noqa: E402
import record_unlocks  # noqa: E402

FUNDING = [{"symbol": "BTC_USDT", "fundingRate": 2.6e-05, "maxFundingRate": 0.0018, "minFundingRate": -0.0018,
            "collectCycle": 8, "nextSettleTime": 1792512000000, "timestamp": 1792500230101}]
TICKER = [{"symbol": "BTC_USDT", "lastPrice": 81626.2, "bid1": 81618.6, "ask1": 81618.7, "indexPrice": 81657.4,
           "fairPrice": 81626.3, "volume24": 311947348, "amount24": 2.55e9, "holdVol": 456242850,
           "timestamp": 1792500226880},
          {"symbol": "NEW_USDT", "lastPrice": 1.0, "bid1": 0.99, "ask1": 1.01, "indexPrice": 1.0, "fairPrice": 1.0,
           "volume24": 1, "amount24": 1.0, "holdVol": 5, "timestamp": 1792500226880}]


def fake_mexc(path, params=None):
    return {"funding_rate": FUNDING, "ticker": TICKER}[path]


class TickerRecorderTests(unittest.TestCase):
    def test_one_file_per_hour_and_outer_join(self):
        with tempfile.TemporaryDirectory() as d:
            t = 1792500248570
            path, n = record_mexc_ticker.record(fake_mexc, t, d, clock_ms=lambda: t)
            self.assertEqual(n, 2)
            self.assertTrue(path.name == "12.parquet" and path.parent.name == "2026-10-20")
            again, n2 = record_mexc_ticker.record(fake_mexc, t + 600_000, d)   # same hour
            self.assertEqual((again, n2), (path, 0))
            df = pd.read_parquet(path)
            self.assertEqual(df.loc[df.symbol == "BTC_USDT", "t_holdVol"].item(), 456242850)
            self.assertTrue(pd.isna(df.loc[df.symbol == "NEW_USDT", "f_fundingRate"].item()))
            self.assertTrue((df.recv_ms == t).all())

    def test_response_bounds_use_completion_even_across_an_hour_boundary(self):
        with tempfile.TemporaryDirectory() as d:
            hour = (1792500248570 // 3_600_000) * 3_600_000
            start = hour + 3_599_500
            times = iter([start + 1_200, start + 4_200])
            path, _ = record_mexc_ticker.record(fake_mexc, start, d, clock_ms=lambda: next(times))
            df = pd.read_parquet(path)
            self.assertEqual(path.name, pd.Timestamp(start, unit="ms", tz="UTC").strftime("%H.parquet"))
            self.assertTrue((df.request_start_ms == start).all())
            self.assertTrue((df.funding_recv_ms == start + 1_200).all())
            self.assertTrue((df.ticker_recv_ms == start + 4_200).all())
            self.assertTrue((df.recv_ms == start + 4_200).all())
            self.assertGreater(df.funding_recv_ms.iloc[0], hour + 3_600_000)

    def test_clock_regression_rejects_snapshot_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            start = 1792500248570
            times = iter([start - 1, start + 1])
            with self.assertRaisesRegex(ValueError, "clock moved backwards"):
                record_mexc_ticker.record(fake_mexc, start, d, clock_ms=lambda: next(times))
            self.assertEqual(list(Path(d).rglob("*.parquet")), [])


class NoticeRecorderTests(unittest.TestCase):
    def test_append_only_and_idempotent(self):
        pages = {1: [{"id": 3, "code": "c", "title": "Binance Will Delist X", "releaseDate": 300},
                     {"id": 2, "code": "b", "title": "Binance Will Delist Y", "releaseDate": 200}],
                 2: [{"id": 1, "code": "a", "title": "old", "releaseDate": 100}], 3: []}

        def fake_get(url):
            page = int(url.split("pageNo=")[1].split("&")[0])
            arts = pages.get(page, [])
            return {"data": {"catalogs": [{"articles": arts}] if arts else []}}

        with tempfile.TemporaryDirectory() as d:
            old_out, old_get = record_notices.OUT, record_notices.get
            record_notices.OUT, record_notices.get = Path(d), fake_get
            try:
                self.assertEqual(record_notices.record(161, "delisting", now="T1"), (3, 3))
                self.assertEqual(record_notices.record(161, "delisting", now="T2"), (0, 3))
                pages[1].insert(0, {"id": 4, "code": "d", "title": "new", "releaseDate": 400})
                self.assertEqual(record_notices.record(161, "delisting", now="T3"), (1, 4))
                rows = list(csv.DictReader((Path(d) / "binance_delisting.csv").open()))
            finally:
                record_notices.OUT, record_notices.get = old_out, old_get
        self.assertEqual([r["id"] for r in rows], ["1", "2", "3", "4"])
        self.assertEqual([r["first_seen_utc"] for r in rows], ["T1", "T1", "T1", "T3"])


class UnlockAndDigestTests(unittest.TestCase):
    def test_daily_snapshot_and_digest_only_on_change(self):
        with tempfile.TemporaryDirectory() as d:
            src, journal = Path(d) / "rec", Path(d) / "digests.csv"
            path, n = record_unlocks.record(lambda url: b'{"data": []}', "2026-10-20", src / "unlocks")
            self.assertEqual(n, 12)
            self.assertEqual(gzip.decompress(path.read_bytes()), b'{"data": []}')
            self.assertEqual(record_unlocks.record(lambda url: b"x", "2026-10-20", src / "unlocks")[1], 0)
            self.assertEqual(record_digest.digest(src, journal, "T1"), 1)
            self.assertEqual(record_digest.digest(src, journal, "T2"), 0)
            (src / "notes.csv").write_text("a\n")
            self.assertEqual(record_digest.digest(src, journal, "T3"), 1)
            (src / "notes.csv").write_text("a\nb\n")
            self.assertEqual(record_digest.digest(src, journal, "T4"), 1)
            self.assertEqual(len(list(csv.DictReader(journal.open()))), 3)


if __name__ == "__main__":
    unittest.main()
