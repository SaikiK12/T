import json
import unittest

from scripts.fetch_macro import parse, parse_cot

DAY = 86_400_000
T0 = 1_609_459_200_000  # 2021-01-01


class FetchMacroTest(unittest.TestCase):
    def test_fng(self):
        raw = json.dumps({"data": [{"value": "55", "timestamp": str(T0 // 1000 + DAY // 1000)},
                                   {"value": "20", "timestamp": str(T0 // 1000)}]}).encode()
        df = parse("fng", raw)
        self.assertEqual(df.t.tolist(), [T0, T0 + DAY])            # sorted by day
        self.assertEqual(df.value.tolist(), [20.0, 55.0])

    def test_fred_drops_missing(self):
        raw = b"observation_date,DGS3MO\n2021-01-01,0.09\n2021-01-02,\n2021-01-03,.\n2021-01-04,0.08\n"
        df = parse("fred", raw)
        self.assertEqual(df.t.tolist(), [T0, T0 + 3 * DAY])
        self.assertEqual(df.value.tolist(), [0.09, 0.08])

    def test_llama_shapes(self):
        st = json.dumps([{"date": str(T0 // 1000 + 3600), "totalCirculatingUSD": {"peggedUSD": 5.0}}]).encode()
        self.assertEqual(parse("stable", st).t.tolist(), [T0])      # floored to the day
        ch = json.dumps({"totalDataChart": [[T0 // 1000, 1], [T0 // 1000, 2]]}).encode()
        self.assertEqual(parse("chart", ch).value.tolist(), [2.0])  # a repeated day keeps the last value
        tv = json.dumps([{"date": T0 // 1000, "tvl": 7}]).encode()
        self.assertEqual(parse("tvl", tv).value.tolist(), [7.0])

    def test_blockchain_and_cot(self):
        bc = json.dumps({"values": [{"x": T0 // 1000 + DAY // 1000, "y": 3}, {"x": T0 // 1000, "y": 2}]}).encode()
        self.assertEqual(parse("bc", bc).value.tolist(), [2.0, 3.0])
        cot = json.dumps([{"market_and_exchange_names": "BITCOIN - CME", "cftc_contract_market_code": "133741",
                           "report_date_as_yyyy_mm_dd": "2021-01-05T00:00:00.000", "open_interest_all": "10",
                           "lev_money_positions_long": "4", "lev_money_positions_short": "6",
                           "yyyy_report_week_ww": "2021 Report Week 1"}]).encode()
        df = parse_cot(cot)
        self.assertEqual(df.t.tolist(), [T0 + 4 * DAY])
        self.assertEqual(df.available_t.tolist(), [T0 + 8 * DAY])   # the Friday release, a Tuesday report
        self.assertEqual(df.lev_money_positions_short.tolist(), [6.0])
        self.assertNotIn("yyyy_report_week_ww", df.columns)


if __name__ == "__main__":
    unittest.main()
