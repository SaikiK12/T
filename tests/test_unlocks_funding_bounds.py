from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from scripts import unlocks_funding_bounds as b


class FundingBoundsTests(unittest.TestCase):
    def series(self, rates=None):
        times = np.array([b.prices.START + i * b.HOUR for i in range(6)], dtype=np.int64)
        rates = rates if rates is not None else [.01] * len(times)
        return times, [(int(t), 1., r) for t, r in zip(times, rates)]

    def mark(self, low=200., high=200.):
        day = b.prices.START
        return {day: (day, low, high, low, low)}

    def test_funding_uses_changed_mark_not_entry_notional(self):
        start = b.prices.START + b.HOUR + 30000
        f = b.funding_bound(self.series(), self.mark(), start, start + b.HOUR, 100., 1)
        self.assertTrue(f['complete'])
        self.assertAlmostEqual(f['lower'], .02)
        self.assertAlmostEqual(f['upper'], .02)
        self.assertEqual(f['optional_settlements'], 0)

    def test_negative_funding_and_long_sign_reverse_bounds(self):
        start = b.prices.START + b.HOUR + 30000
        f = b.funding_bound(self.series([-.01] * 6), self.mark(100, 200), start, start + b.HOUR, 100., 1)
        long = b.funding_bound(self.series([-.01] * 6), self.mark(100, 200), start, start + b.HOUR, 100., -1)
        self.assertAlmostEqual(f['lower'], -.02)
        self.assertAlmostEqual(f['upper'], -.01)
        self.assertAlmostEqual(long['lower'], .01)
        self.assertAlmostEqual(long['upper'], .02)

    def test_boundary_settlements_are_optional_in_both_directions(self):
        start = b.prices.START + b.HOUR
        for sign in (-1, 1):
            f = b.funding_bound(self.series(), self.mark(), start, start + b.HOUR, 100., sign)
            self.assertEqual(f['optional_settlements'], 2)
            self.assertAlmostEqual(f['lower'], -.04 if sign == -1 else 0.)
            self.assertAlmostEqual(f['upper'], .04 if sign == 1 else 0.)

    def test_internal_missing_settlement_is_unknown_not_zero(self):
        t, rows = self.series()
        series = np.delete(t, 2), rows[:2] + rows[3:]
        start = b.prices.START + b.HOUR + 30000
        f = b.funding_bound(series, self.mark(), start, start + 2 * b.HOUR, 100., 1)
        self.assertFalse(f['complete'])
        self.assertIn('gap', f['reason'])
        self.assertNotIn('lower', f)

    def test_recorded_variable_interval_is_respected(self):
        start = b.prices.START
        times = np.array([start, start + b.HOUR, start + 3 * b.HOUR, start + 4 * b.HOUR], dtype=np.int64)
        rows = [(int(t), interval, .01) for t, interval in zip(times, (1, 1, 2, 1))]
        f = b.funding_bound((times, rows), self.mark(), start + b.HOUR + 30000, start + 3 * b.HOUR + 30000, 100., 1)
        self.assertTrue(f['complete'])
        self.assertAlmostEqual(f['lower'], .02)

    def test_missing_anchor_or_mark_stays_unknown(self):
        start = b.prices.START + b.HOUR + 30000
        self.assertFalse(b.funding_bound(self.series(), {}, start, start + b.HOUR, 100., 1)['complete'])
        self.assertFalse(b.funding_bound(self.series(), self.mark(), b.prices.START, start, 100., 1)['complete'])
        self.assertFalse(b.funding_bound(None, self.mark(), start, start + b.HOUR, 100., 1)['complete'])

    def test_exit_notional_and_both_hedge_legs_pay_fees(self):
        f = {'complete': True, 'lower': .01, 'upper': .03}
        n = b.net_bounds(-1., [2.], [f], 1)
        self.assertAlmostEqual(n['price_only'], -1.003)
        pair = b.net_bounds(0., [2., .5], [f, f], 3)
        self.assertAlmostEqual(pair['price_only'], -.0135)
        self.assertAlmostEqual(pair['lower'], .0065)
        unknown = b.net_bounds(0., [1.], [{'complete': False}], 1)
        self.assertIsNone(unknown['lower'])

    def test_collateral_is_optimistic_necessary_floor_not_liquidation(self):
        f = {'complete': True, 'positive_credit_upper': .2}
        self.assertAlmostEqual(b.collateral_floor(300., 100., f, 1), 1.801)
        self.assertIsNone(b.collateral_floor(None, 100., f, 1))
        self.assertIsNone(b.collateral_floor(300., 100., {'complete': False}, 1))

    def test_mark_peak_includes_entry_mark_and_rejects_gaps(self):
        day = b.prices.START + 10 * b.DAY
        marks = {day - k * b.DAY: (day - k * b.DAY, 100, 120, 80, 100) for k in range(8)}
        marks[day - 7 * b.DAY] = (day - 7 * b.DAY, 100, 180, 80, 170)
        self.assertEqual(b.mark_peak(marks, day), 170)
        del marks[day - 2 * b.DAY]
        self.assertIsNone(b.mark_peak(marks, day))

    def test_existing_results_are_never_overwritten_or_loaded(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(b, 'verify') as check:
            with self.assertRaises(FileExistsError):
                b.run(Path(tmp), Path(tmp), Path(tmp))
            check.assert_not_called()

    def test_negative_observed_sample_is_null_and_small_sample_is_explicit(self):
        rows = []
        for i in range(40):
            rows.append({'variant': 'short', 'funding_complete': True, 'perp': str(i % 5),
                         'day_ms': b.prices.START + i * 7 * b.DAY,
                         **{f'net_lower_{k}x': -.01 - (i % 3) * .01 for k in (1, 2, 3)}})
        self.assertEqual(b.conditional_screen(rows)['registry_verdict'], 'NULL')
        self.assertEqual(b.conditional_screen(rows[:5])['status'], 'INSUFFICIENT')

    def test_full_synthetic_event_hedge_and_missing_funding_are_retained(self):
        day = b.prices.START + 10 * b.DAY
        bars, marks, funding = {}, {}, {}
        for symbol, level in [('TESTUSDT', 100.), ('BTCUSDT', 200.)]:
            dates = [day - k * b.DAY for k in range(-1, 8)]
            bars[symbol] = {t: (t, level, level, level, 1., level) for t in dates}
            marks[symbol] = {t: (t, level, level, level, level) for t in dates}
            times = np.arange(day - 8 * b.DAY, day + 2 * b.DAY, 8 * b.HOUR, dtype=np.int64)
            funding[symbol] = times, [(int(t), 8., .0001) for t in times]
        events = pd.DataFrame([{'perp': 'TESTUSDT', 'day_ms': day, 'day': '2021-01-11',
                                'venue': 'binance', 'window': 'archive', 'check': 'verified'}])
        rows, excluded, stats, verdict = b.evaluate(bars, marks, funding, events)
        self.assertFalse(excluded)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r['funding_complete'] for r in rows))
        self.assertAlmostEqual(rows[0]['price_only_1x'], -.002)
        self.assertAlmostEqual(rows[1]['price_only_3x'], -.012)
        self.assertEqual(verdict['full_r258_cohort_funding_status'], 'OBSERVED')
        funding.pop('TESTUSDT')
        rows, excluded, stats, verdict = b.evaluate(bars, marks, funding, events)
        self.assertEqual(len(rows), 2)
        self.assertIsNone(rows[0]['net_lower_1x'])
        self.assertEqual(verdict['full_r258_cohort_funding_status'], 'INCONCLUSIVE_MISSING_WINDOWS')
        self.assertEqual(verdict['isolated_collateral_necessary_floor']['1']['unknown'], 1)


if __name__ == '__main__':
    unittest.main()
