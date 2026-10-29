import json
import unittest

from scripts import m090_history_rule as rule


def page(rows, **meta):
    data = {"currentPage": 1, "totalPage": 2, "resultList": rows, **meta}
    return json.dumps({"success": True, "code": 0, "data": data}).encode()


class HistoryRuleTests(unittest.TestCase):
    def row(self, ts, rate=.001):
        return {"symbol": "BTC_USDT", "settleTime": ts, "fundingRate": rate}

    def test_exact_milliseconds_survive_without_hour_flooring(self):
        parsed = rule.parse_page_one(page([self.row(7_201_234), self.row(7_200_000)]), "BTC_USDT")
        self.assertEqual(parsed.total_pages, 2)
        self.assertEqual(rule.find_exact(parsed, 7_201_234).settlement_ms, 7_201_234)
        self.assertIsNone(rule.find_exact(parsed, 7_201_235))
        self.assertEqual(len(parsed.raw_sha256), 64)

    def test_duplicate_or_unsorted_events_fail(self):
        for rows in ([self.row(1), self.row(1)], [self.row(1), self.row(2)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                rule.parse_page_one(page(rows), "BTC_USDT")

    def test_malformed_and_cross_symbol_responses_fail(self):
        for raw in (b'{"success":true,"success":true}',
                    page([{"symbol": "ETH_USDT", "settleTime": 1, "fundingRate": .001}]),
                    page([self.row(True)]), page([self.row(1, float("nan"))]),
                    page([], currentPage=2)):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                rule.parse_page_one(raw, "BTC_USDT")

    def test_absent_event_remains_missing_even_with_more_pages(self):
        parsed = rule.parse_page_one(page([self.row(2)], totalPage=3), "BTC_USDT")
        self.assertIsNone(rule.find_exact(parsed, 1))


if __name__ == "__main__":
    unittest.main()
