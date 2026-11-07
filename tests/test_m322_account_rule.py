import unittest
from dataclasses import replace

from scripts import m322_account_rule as account
from scripts import m322_signal_rule as signal


class AccountRuleTests(unittest.TestCase):
    def setUp(self):
        self.day = 1000 * signal.DAY
        self.sha = "a" * 64
        closes = tuple(signal.Close(self.day - i * signal.DAY, 100.0 if i else 50.0)
                       for i in reversed(range(25)))
        coins = [signal.Contract(f"C{i:02d}USDT", i + 1, closes, self.day + signal.MINUTE,
                                 100, self.sha, None if i == 0 else f"C{i:02d}_USDT")
                 for i in range(30)]
        prior = [signal.PriorBreadth(self.day - i * signal.DAY, .2,
                                     self.day - i * signal.DAY + signal.MINUTE, 100, self.sha)
                 for i in range(1, 181)]
        self.ticket = signal.ticket(self.day, coins, prior)

    def quote(self, contract, scheduled, size=1000):
        return account.Quote(contract, scheduled + 1000, scheduled + 1100, 100,
                             99.0, 101.0, size, size, self.sha)

    def terms(self, contract, at_ms=None):
        return account.ContractTerms(contract, .001, 1, 1, 100000, True, True,
                                     self.ticket.decision_ms - 1000 if at_ms is None else at_ms, 100, self.sha)

    def test_cash_allocation_missing_mapping_partial_depth_and_slot(self):
        book = account.Account(10_000, 1)
        quotes = {leg.mexc_contract: self.quote(leg.mexc_contract, self.ticket.entry_ms,
                                                 size=100 if leg.symbol == "C01USDT" else 1000)
                  for leg in self.ticket.legs if leg.mexc_contract}
        positions, skipped = book.open(self.ticket, quotes, {c: self.terms(c) for c in quotes}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        self.assertEqual(len(positions), 29)
        self.assertEqual(skipped, (account.Skipped("C00USDT", "unmapped"),))
        self.assertAlmostEqual(positions[0].quantity_base, .1)
        self.assertGreater(positions[0].requested_quantity_base, positions[0].quantity_base)
        self.assertAlmostEqual(positions[0].entry_fee_cash, .1 * 101 * account.API_FEE)
        self.assertGreater(book.cash, 8000)
        self.assertEqual(positions[0].exit_ms, positions[0].entry_ms + signal.HOLD)
        with self.assertRaisesRegex(ValueError, "already processed"):
            book.open(self.ticket, quotes, {c: self.terms(c) for c in quotes}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)

    def test_no_fill_day_cannot_be_replayed_with_later_quotes(self):
        book = account.Account(10_000, 1)
        positions, skipped = book.open(self.ticket, {}, {}, processed_ms=self.ticket.entry_ms + 100, processed_clock_error_ms=100)
        self.assertEqual(positions, ())
        self.assertEqual(len(skipped), 30)
        one = self.ticket.legs[1].mexc_contract
        with self.assertRaisesRegex(ValueError, "already processed"):
            book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)

    def test_minimum_and_step_use_contract_units_without_borrowing(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        terms = replace(self.terms(one), min_contracts=1000, max_contracts=2000)
        positions, skipped = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: terms}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        self.assertEqual(positions, ())
        self.assertIn(account.Skipped("C01USDT", "below_minimum_volume"), skipped)
        self.assertEqual(book.cash, 10_000)

    def test_missing_exit_or_funding_does_not_change_book(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        positions, _ = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        p = positions[0]
        exit_quote = self.quote(one, p.exit_ms)
        settled = p.entry_ms + signal.DAY
        asof = p.exit_ms + account.WINDOW
        before = book.cash
        with self.assertRaisesRegex(ValueError, "settlement"):
            book.close(self.ticket.slot, {one: exit_quote}, {one: self.terms(one, p.exit_ms - 1000)},
                       {one: [settled]}, [], self.sha, asof)
        self.assertEqual(book.cash, before)
        self.assertIn(self.ticket.slot, book.slots)
        funding = account.Funding(one, settled, .001, 100, settled + 500, settled + 600, 100, self.sha)
        with self.assertRaisesRegex(ValueError, "depth"):
            book.close(self.ticket.slot, {one: replace(exit_quote, bid_size_contracts=.00001)},
                       {one: self.terms(one, p.exit_ms - 1000)}, {one: [settled]}, [funding], self.sha, asof)
        self.assertEqual(book.cash, before)
        delta = book.close(self.ticket.slot, {one: exit_quote}, {one: self.terms(one, p.exit_ms - 1000)},
                           {one: [settled]}, [funding], self.sha, asof)
        self.assertAlmostEqual(delta, p.quantity_base * (99 * (1 - account.API_FEE) - .1))
        self.assertNotIn(self.ticket.slot, book.slots)

    def test_late_quote_and_clock_uncertainty_fail_before_spending(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        q = self.quote(one, self.ticket.entry_ms)
        with self.assertRaisesRegex(ValueError, "on-time"):
            book.open(self.ticket, {one: replace(q, available_ms=self.ticket.entry_ms + account.WINDOW)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        self.assertEqual(book.cash, 10_000)
        self.assertEqual(book.slots, {})

    def test_delayed_processing_cannot_backdate_a_fill(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        q = self.quote(one, self.ticket.entry_ms)
        with self.assertRaisesRegex(ValueError, "promptly"):
            book.open(self.ticket, {one: q}, {one: self.terms(one)},
                      processed_ms=self.ticket.entry_ms + 2300, processed_clock_error_ms=100)
        self.assertEqual(book.cash, 10_000)

    def test_funding_deficit_is_not_financed_by_silent_borrowing(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        positions, _ = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)},
                                 {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        p = positions[0]
        settled = p.entry_ms + signal.DAY
        funding = account.Funding(one, settled, 1.0, 1_000_000, settled + 500, settled + 600, 100, self.sha)
        before = book.cash
        with self.assertRaisesRegex(ValueError, "exceeds available cash"):
            book.reconcile_funding(settled + 1000, {one: [settled]}, [funding], self.sha)
        self.assertEqual(book.cash, before)
        self.assertIn(self.ticket.slot, book.slots)

    def test_cost_tiers_charge_spread_and_fee_once_at_each_side(self):
        balances = []
        one = self.ticket.legs[1].mexc_contract
        for tier in (1, 2, 3):
            book = account.Account(10_000, tier)
            positions, _ = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
            p = positions[0]
            book.close(self.ticket.slot, {one: self.quote(one, p.exit_ms)},
                       {one: self.terms(one, p.exit_ms - 1000)}, {one: []}, [], self.sha,
                       p.exit_ms + account.WINDOW)
            balances.append(book.cash)
        self.assertGreater(balances[0], balances[1])
        self.assertGreater(balances[1], balances[2])

    def test_funding_must_be_current_before_overlap_and_is_booked_once(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        positions, _ = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        p = positions[0]
        second = replace(self.ticket, day_ms=self.day + signal.DAY,
                         decision_ms=self.ticket.decision_ms + signal.DAY,
                         entry_ms=self.ticket.entry_ms + signal.DAY,
                         exit_ms=self.ticket.exit_ms + signal.DAY,
                         slot=((self.day + signal.DAY) // signal.DAY) % 5)
        quote = self.quote(one, second.entry_ms)
        with self.assertRaisesRegex(ValueError, "complete funding"):
            book.open(second, {one: quote}, {one: self.terms(one, second.decision_ms - 1000)}, processed_ms=second.entry_ms + 1400, processed_clock_error_ms=100)
        settled = p.entry_ms + signal.DAY // 2
        funding = account.Funding(one, settled, .001, 100, settled + 500, settled + 600, 100, self.sha)
        asof = second.entry_ms + 1300
        delta = book.reconcile_funding(asof, {one: [settled]}, [funding], self.sha)
        self.assertAlmostEqual(delta, -p.quantity_base * .1)
        self.assertEqual(book.reconcile_funding(asof, {one: [settled]}, [funding], self.sha), 0)
        with self.assertRaisesRegex(ValueError, "schedule"):
            book.open(second, {one: quote}, {one: self.terms(one, second.decision_ms - 1000)},
                      processed_ms=second.entry_ms + 1400, processed_clock_error_ms=100)
        book.open(second, {one: quote}, {one: self.terms(one, second.decision_ms - 1000)},
                  processed_ms=second.entry_ms + 1400, processed_clock_error_ms=100,
                  schedule_through_ms=second.entry_ms + 1500, next_events={one: None}, schedule_sha256=self.sha)
        with self.assertRaisesRegex(ValueError, "changed"):
            book.reconcile_funding(second.entry_ms + 1600, {one: [settled]}, [replace(funding, rate=.002)], self.sha)

    def test_marks_require_complete_funding_and_timely_prices(self):
        book = account.Account(10_000, 1)
        one = self.ticket.legs[1].mexc_contract
        positions, _ = book.open(self.ticket, {one: self.quote(one, self.ticket.entry_ms)}, {one: self.terms(one)}, processed_ms=self.ticket.entry_ms + 1400, processed_clock_error_ms=100)
        p = positions[0]
        asof = p.entry_ms + 3_600_000
        quote = account.Quote(one, asof - 1000, asof - 500, 100, 99, 101, 1000, 1000, self.sha)
        with self.assertRaisesRegex(ValueError, "funding"):
            book.mark(asof, {one: quote})
        book.reconcile_funding(asof, {one: []}, [], self.sha)
        self.assertAlmostEqual(book.mark(asof, {one: quote}), book.cash + p.quantity_base * 100)
        with self.assertRaisesRegex(ValueError, "stale"):
            book.mark(asof, {one: replace(quote, observed_ms=asof - account.WINDOW - 1)})


if __name__ == "__main__":
    unittest.main()
