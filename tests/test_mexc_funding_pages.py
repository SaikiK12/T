"""Public funding-page fixtures; no exchange endpoint or historical dataset is used."""
import unittest
from unittest.mock import patch

from lab import mexc


H = mexc.HOUR


def settlement(hour, rate=.001, **extra):
    return {"symbol": "TOY_USDT", "settleTime": hour * H, "fundingRate": rate, "collectCycle": 8, **extra}


def page(number, total, *rows):
    return {"currentPage": number, "totalPage": total, "resultList": list(rows)}


class FundingPages(unittest.TestCase):
    def fetch(self, pages, start=1 * H, end=8 * H, **kwargs):
        with patch.object(mexc, "get", side_effect=pages) as get:
            result = mexc.funding_history("TOY_USDT", start, end, **kwargs)
        return result, get

    def test_valid_multiple_pages_preserve_sorted_legacy_output(self):
        result, get = self.fetch([page(1, 2, settlement(8), settlement(7)),
                                  page(2, 2, settlement(6), settlement(1))])
        self.assertEqual(result.t.tolist(), [H, 6 * H, 7 * H])
        self.assertEqual(result.rate.tolist(), [.001] * 3)
        self.assertEqual(result.cycle_h.tolist(), [8] * 3)
        self.assertEqual([c.args[1]["page_num"] for c in get.call_args_list], [1, 2])
        self.assertTrue(all(c.args[1]["page_size"] == 1000 for c in get.call_args_list))

    def test_missing_page_metadata_does_not_silently_return_first_page(self):
        for field in ("totalPage", "currentPage", "resultList"):
            bad = page(1, 2, settlement(7))
            del bad[field]
            with self.subTest(field=field), self.assertRaises(mexc.MexcError):
                self.fetch([bad])

    def test_wrong_or_fractional_page_identity_fails(self):
        for bad in (page(2, 2, settlement(7)), page(1, 0, settlement(7)),
                    page(True, 1, settlement(7)), page(1, 1.5, settlement(7))):
            with self.subTest(bad=bad), self.assertRaises(mexc.MexcError):
                self.fetch([bad])

    def test_empty_response_is_allowed_only_for_single_empty_history(self):
        result, _ = self.fetch([page(1, 0)])
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ["t", "rate", "cycle_h"])
        for pages in ([page(1, 2)], [page(1, 2, settlement(7)), page(2, 2)]):
            with self.subTest(pages=pages), self.assertRaises(mexc.MexcError):
                self.fetch(pages)

    def test_repeated_page_cannot_exhaust_the_budget_as_success(self):
        with self.assertRaisesRegex(mexc.MexcError, "without progress"):
            self.fetch([page(1, 3, settlement(7)), page(2, 3, settlement(7))])

    def test_identical_boundary_overlap_is_deduplicated(self):
        result, _ = self.fetch([page(1, 2, settlement(7), settlement(6)),
                                page(2, 2, settlement(6), settlement(5))])
        self.assertEqual(result.t.tolist(), [5 * H, 6 * H, 7 * H])

    def test_conflicting_settlement_does_not_choose_one_rate(self):
        with self.assertRaisesRegex(mexc.MexcError, "conflicting"):
            self.fetch([page(1, 2, settlement(7)), page(2, 2, settlement(7, rate=.002), settlement(6))])

    def test_unsorted_or_forward_moving_pages_fail_before_early_stop(self):
        for pages in ([page(1, 2, settlement(0), settlement(7))],
                      [page(1, 2, settlement(6)), page(2, 2, settlement(7), settlement(5))]):
            with self.subTest(pages=pages), self.assertRaises(mexc.MexcError):
                self.fetch(pages)

    def test_malformed_rows_fail_instead_of_returning_unknown_funding(self):
        invalid = [settlement(7, rate="NaN"), settlement(7, rate="Infinity"), settlement(7, rate=True),
                   settlement(7, collectCycle=0), settlement(7, collectCycle=True),
                   settlement(7, symbol="OTHER_USDT"), settlement(7, settleTime=None),
                   settlement(7, settleTime=1.5), settlement(7, settleTime=True), None]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(mexc.MexcError):
                self.fetch([page(1, 1, row)])

    def test_distinct_raw_settlements_in_one_hour_are_not_silently_dropped(self):
        with self.assertRaisesRegex(mexc.MexcError, "same legacy hourly"):
            self.fetch([page(1, 1, settlement(7, settleTime=7 * H + 1000), settlement(7))])

    def test_older_boundary_stops_before_unneeded_page(self):
        result, get = self.fetch([page(1, 100, settlement(7), settlement(0))])
        self.assertEqual(result.t.tolist(), [7 * H])
        self.assertEqual(get.call_count, 1)

    def test_page_budget_exhaustion_raises_with_no_extra_request(self):
        with patch.object(mexc, "get", side_effect=[page(1, 3, settlement(7))]) as get:
            with self.assertRaisesRegex(mexc.MexcError, "max_pages=1"):
                mexc.funding_history("TOY_USDT", H, 8 * H, max_pages=1)
        self.assertEqual(get.call_count, 1)

    def test_zero_window_does_not_request_and_invalid_budget_is_rejected(self):
        with patch.object(mexc, "get") as get:
            self.assertTrue(mexc.funding_history("TOY_USDT", H, H).empty)
            for budget in (0, -1, True, 1.5):
                with self.subTest(budget=budget), self.assertRaises(ValueError):
                    mexc.funding_history("TOY_USDT", H, 8 * H, max_pages=budget)
            get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
