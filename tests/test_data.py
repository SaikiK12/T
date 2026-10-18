import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from lab import data

KLINE_ROW = "{t},1.0,2.0,0.5,1.5,10,{c},15,7,4,6,0"


def make_zip(path, text):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("x.csv", text)
    return path


class ParseTests(unittest.TestCase):
    def test_kline_with_and_without_header(self):
        rows = "\n".join(KLINE_ROW.format(t=1704067200000 + i * 3600000, c=0) for i in range(3))
        header = ",".join(data.KLINE_COLS[:6] + ("close_time",) + ("quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"))
        with tempfile.TemporaryDirectory() as d:
            plain = data.parse(make_zip(Path(d) / "a.zip", rows), "klines")
            headed = data.parse(make_zip(Path(d) / "b.zip", header + "\n" + rows), "klines")
        self.assertEqual(len(plain), 3)
        self.assertEqual(list(plain.columns), list(data.KLINE_KEEP))
        self.assertTrue(plain.equals(headed))

    def test_microsecond_timestamps_become_milliseconds(self):
        rows = KLINE_ROW.format(t=1704067200000 * 1000, c=0)
        with tempfile.TemporaryDirectory() as d:
            df = data.parse(make_zip(Path(d) / "a.zip", rows), "klines")
        self.assertEqual(int(df["t"].iloc[0]), 1704067200000)

    def test_metrics_timestamp_is_utc_milliseconds(self):
        text = ("create_time,symbol,sum_open_interest,sum_open_interest_value,count_toptrader_long_short_ratio,"
                "sum_toptrader_long_short_ratio,count_long_short_ratio,sum_taker_long_short_vol_ratio\n"
                "2024-01-15 00:05:00,BTCUSDT,77234.0,3232040965.3,2.4,1.39,2.67,1.03\n")
        with tempfile.TemporaryDirectory() as d:
            df = data.parse(make_zip(Path(d) / "m.zip", text), "metrics")
        self.assertEqual(int(df["t"].iloc[0]), 1705277100000)  # 2024-01-15T00:05:00Z
        self.assertEqual(list(df.columns), ["t", "oi", "oi_value", "top_ls_count", "top_ls_sum", "ls_count", "taker_ls_vol"])

    def test_funding_parses(self):
        text = "calc_time,funding_interval_hours,last_funding_rate\n1704067200000,8,0.00037409\n"
        with tempfile.TemporaryDirectory() as d:
            df = data.parse(make_zip(Path(d) / "f.zip", text), "fundingRate")
        self.assertEqual(float(df["rate"].iloc[0]), 0.00037409)


class PlanTests(unittest.TestCase):
    def fake_list(self, monthly, daily):
        def list_fn(prefix, marker=""):
            keys = monthly if "/monthly/" in prefix else daily
            return sorted(k for k in keys if k.startswith(prefix) and k > marker)
        return list_fn

    def keys(self, kind, sym, itv, kind_dir, dates):
        return [f"data/futures/um/{kind_dir}/{kind}/{sym}/{itv}/{sym}-{itv}-{d}.zip" for d in dates]

    def test_daily_files_only_after_last_monthly(self):
        monthly = self.keys("klines", "AAAUSDT", "1h", "monthly", ["2024-01", "2024-02"])
        daily = self.keys("klines", "AAAUSDT", "1h", "daily", ["2024-02-10", "2024-03-01", "2024-03-02"])
        got = data.plan_files("AAAUSDT", "klines", "1h", list_fn=self.fake_list(monthly, daily), end="2024-12-31")
        self.assertEqual([k.rsplit("-", 2)[-2:] for k in got if "daily" in k], [["03", "01.zip"], ["03", "02.zip"]])
        self.assertEqual(sum("monthly" in k for k in got), 2)

    def test_symbol_with_no_monthly_uses_all_daily(self):
        daily = self.keys("klines", "NEWUSDT", "1h", "daily", ["2024-05-01", "2024-05-02"])
        got = data.plan_files("NEWUSDT", "klines", "1h", list_fn=self.fake_list([], daily), end="2024-12-31")
        self.assertEqual(len(got), 2)

    def test_end_date_cuts_later_files(self):
        monthly = self.keys("klines", "AAAUSDT", "1h", "monthly", ["2026-08", "2026-09", "2026-10"])
        got = data.plan_files("AAAUSDT", "klines", "1h", list_fn=self.fake_list(monthly, []), end="2026-09-30")
        self.assertEqual(len(got), 2)

    def test_funding_never_looks_for_daily_files(self):
        calls = []

        def list_fn(prefix, marker=""):
            calls.append(prefix)
            return ["data/futures/um/monthly/fundingRate/AAAUSDT/AAAUSDT-fundingRate-2024-01.zip"]

        data.plan_files("AAAUSDT", "fundingRate", "", list_fn=list_fn, end="2024-12-31")
        self.assertEqual(len(calls), 1)
        self.assertIn("/monthly/", calls[0])


if __name__ == "__main__":
    unittest.main()
