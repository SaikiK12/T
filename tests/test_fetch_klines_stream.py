import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_klines_stream", ROOT / "scripts" / "fetch_klines_stream.py")
fks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fks)

MIN = 60_000


def kline_zip(t0, n, header=True):
    """An invented archive file of n one-minute klines from t0 (ms), in Binance's twelve-column layout."""
    lines = ["open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,"
             "taker_buy_quote_volume,ignore"] if header else []
    for i in range(n):
        t = t0 + i * MIN
        lines.append(f"{t},{1 + i},{2 + i},{0.5 + i},{1.5 + i},10,{t + MIN - 1},15,3,4,6,0")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(lines) + "\n")
    return buf.getvalue()


def ms(day):
    return int(pd.Timestamp(day, tz="UTC").timestamp() * 1000)


class TestKeys(unittest.TestCase):
    def test_keys_between_keeps_overlapping_months_and_days(self):
        keys = ["p/X-1m-2020-12.zip", "p/X-1m-2021-01.zip", "p/X-1m-2026-09.zip", "p/X-1m-2026-10.zip",
                "p/X-1m-2026-09-30.zip", "p/X-1m-2026-10-01.zip"]
        self.assertEqual(fks.keys_between(keys, "2021-01-01", "2026-09-30"),
                         ["p/X-1m-2021-01.zip", "p/X-1m-2026-09.zip", "p/X-1m-2026-09-30.zip"])


class TestFetch(unittest.TestCase):
    def test_fetch_checks_the_published_digest(self):
        blob = b"abc"
        good = hashlib.sha256(blob).hexdigest()
        self.assertEqual(fks.fetch_verified("k", get=lambda url: blob, published=lambda k: good), (blob, good))
        with self.assertRaises(fks.data.FetchError):
            fks.fetch_verified("k", get=lambda url: blob, published=lambda k: "0" * 64)

    def test_missing_archive_file_is_none(self):
        def get(url):
            raise urllib.error.HTTPError(url, 404, "nf", {}, None)
        self.assertIsNone(fks.fetch_verified("k", get=get, published=lambda k: ""))


class TestFrame(unittest.TestCase):
    def test_rows_outside_the_window_never_survive_and_duplicates_keep_the_last(self):
        a = kline_zip(ms("2020-12-31 23:58"), 4)             # two bars in 2020, two in 2021
        b = kline_zip(ms("2021-01-01 00:01"), 2, header=False)  # repeats 00:01 with new prices
        df = fks.frame([a, b], "2021-01-01", "2021-01-01")
        self.assertEqual(list(df.columns), list(fks.COLUMNS))
        self.assertEqual(df.t.tolist(), [ms("2021-01-01 00:00"), ms("2021-01-01 00:01"), ms("2021-01-01 00:02")])
        self.assertEqual(df.open.tolist(), [3.0, 1.0, 2.0])   # 00:01 comes from the later file
        self.assertTrue((df.t < ms("2021-01-02")).all())

    def test_build_symbol_writes_zstd_parquet_and_lists_every_archive(self):
        blobs = {"p/X-1m-2021-01.zip": kline_zip(ms("2021-01-01"), 3),
                 "p/X-1m-2021-02.zip": kline_zip(ms("2021-02-01"), 2)}

        def plan(symbol, kind, interval, end):
            return list(blobs) + ["p/X-1m-2021-03.zip"]       # March is listed but absent (404)

        def fetch(key):
            b = blobs.get(key)
            return None if b is None else (b, hashlib.sha256(b).hexdigest())

        with tempfile.TemporaryDirectory() as d:
            entry = fks.build_symbol("XUSDT", "1m", "2021-01-01", "2021-03-31", d, workers=2, plan=plan, fetch=fetch,
                                     log=lambda *_: None)
            path = Path(d) / "XUSDT.parquet"
            out = pd.read_parquet(path)
            import pyarrow.parquet as pq
            codec = pq.ParquetFile(path).metadata.row_group(0).column(0).compression
        self.assertEqual(len(out), 5)
        self.assertEqual(codec, "ZSTD")
        self.assertEqual([a["key"] for a in entry["archives"]], list(blobs))
        self.assertEqual(entry["rows"], 5)
        self.assertEqual(entry["first"], ms("2021-01-01"))
        json.dumps(entry)


if __name__ == "__main__":
    unittest.main()
