import tempfile
from pathlib import Path
from unittest import TestCase, mock

import numpy as np
import pandas as pd

from lab import panel
from scripts import run_unlocks as u


class UnlockRunnerTests(TestCase):
    def prices(self):
        t = np.arange(panel.ms('2021-01-01'), panel.ms('2021-04-01'), panel.HOUR)
        shape = (len(t), 2)
        f = {'close': np.full(shape, 100.), 'volume': np.ones(shape),
             'quote_volume': np.full(shape, 1000.), 'fund_event': np.full(shape, np.nan)}
        return panel.Panel(t, ['TESTUSDT', 'BTCUSDT'], f)

    def test_entry_exit_day_closes_and_short_sign(self):
        p = self.prices()
        d = panel.ms('2021-02-15')
        a = np.where(p.t == d-6*u.DAY-u.HOUR)[0][0]
        b = np.where(p.t == d+u.DAY-u.HOUR)[0][0]
        p.f['close'][a, 0] = 200
        p.f['close'][b, 0] = 240
        p.f['fund_event'][a, 0] = .9  # excluded: settlement on entry bar
        p.f['fund_event'][a+1, 0] = .01
        p.f['fund_event'][b, 0] = -.003
        r = u.Prices(p).trade('TESTUSDT', d)
        self.assertAlmostEqual(r['gross'], -.2)
        self.assertAlmostEqual(r['funding'], .007)
        self.assertEqual(r['entry_bar_ms'], p.t[a])
        self.assertEqual(r['exit_bar_ms'], p.t[b])

    def test_zero_volume_stale_entry_and_delisting_exit(self):
        p = self.prices(); d = panel.ms('2021-02-15')
        a = np.where(p.t == d-6*u.DAY-u.HOUR)[0][0]
        p.f['volume'][a-24:a+1, 0] = 0
        self.assertIsNone(u.Prices(p).trade('TESTUSDT', d))
        p = self.prices(); b = np.where(p.t == d-2*u.DAY)[0][0]
        p.f['volume'][b+1:, 0] = 0
        p.f['close'][b+1:, 0] = 999  # archived flat/nontrading values cannot enter PnL
        r = u.Prices(p).trade('TESTUSDT', d)
        self.assertEqual(r['exit'], 100)
        self.assertTrue(r['delisted_in_hold'])

    def test_unbounded_short_loss_is_retained_not_clipped(self):
        p = self.prices(); d = panel.ms('2021-02-15')
        b = np.where(p.t == d+u.DAY-u.HOUR)[0][0]
        p.f['close'][b, 0] = 232
        self.assertAlmostEqual(u.Prices(p).trade('TESTUSDT', d)['gross'], -1.32)

    def test_protected_samples_cannot_be_used(self):
        p = self.prices(); p.t = p.t-u.DAY*400
        with self.assertRaises(PermissionError):
            u.Prices(p)
        p = self.prices()
        self.assertIsNone(u.Prices(p).trade('TESTUSDT', panel.ms('2021-04-01')))

    def test_cluster_standard_error_uses_iso_year_and_week(self):
        days = [panel.ms(d) for d in ['2021-01-04', '2021-01-05', '2021-01-11', '2021-01-18']]
        x = np.array([.02, -.01, .04, -.02]); residual = x-x.mean()
        se = np.sqrt(3/2*((residual[:2].sum())**2+residual[2]**2+residual[3]**2))/4
        r = u.statistics(x, days)
        self.assertEqual(r['clusters'], 3)
        self.assertAlmostEqual(r['cluster_t'], x.mean()/se)
        self.assertIsNone(u.statistics([.1], days[:1])['cluster_t'])
        self.assertEqual(u.statistics([], [])['n'], 0)

    def test_volume_window_excludes_last_seven_days(self):
        p = self.prices(); d = panel.ms('2021-02-15')
        p.f['quote_volume'][p.t >= d-7*u.DAY, 0] = 1e12
        r = u.Prices(p).volume_ratio({'perp': 'TESTUSDT', 'day_ms': d, 'tokens': 240, 'mult': 1})
        self.assertAlmostEqual(r, 1.)  # 240*100/(24*1000)

    def test_null_is_seeded_and_uses_same_symbol_priceable_days(self):
        p = self.prices(); prices = u.Prices(p); d = panel.ms('2021-02-15')
        ev = pd.DataFrame([{'perp': 'TESTUSDT', 'day_ms': d}])
        scored = [{'perp': 'TESTUSDT', 'gross': 0}]
        a = u.random_null(prices, ev, scored, replications=10)
        self.assertEqual(a, u.random_null(prices, ev, scored, replications=10))
        self.assertEqual(a['p'], 1.)
        self.assertGreater(a['admissible_count']['TESTUSDT'], 0)

    def test_missing_inputs_fail_before_panel_or_output(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(u.panel, 'load_panel') as loader:
            out = Path(d)/'out'
            with self.assertRaises(FileNotFoundError):
                u.run(Path(d)/'missing', Path(d), out)
            loader.assert_not_called()
            self.assertFalse(out.exists())

    def test_full_synthetic_evaluation_reports_costs_variants_and_null(self):
        p = self.prices(); prices = u.Prices(p)
        rows = []
        for symbol, date in [('TESTUSDT', '2021-02-15'), ('BTCUSDT', '2021-03-01')]:
            rows.append({'day': date, 'day_ms': panel.ms(date), 'perp': symbol,
                         'venue': 'binance', 'window': 'archive', 'check': 'verified',
                         'tokens': 240., 'mult': 1., 'frac_max_supply': .03})
        ev = pd.DataFrame(rows)
        with mock.patch.object(u, 'random_null', return_value={'p': 1.}):
            scored, excluded, summaries, result = u.evaluate(prices, ev)
        self.assertEqual(len(scored), 2)
        self.assertEqual(excluded, [])
        self.assertEqual(result['verdict'], 'NULL')
        primary = [r for r in summaries if r['variant'] == 'primary']
        self.assertEqual([r['cost_multiple'] for r in primary], [1, 2, 3])
        np.testing.assert_allclose([r['mean'] for r in primary], [-.002, -.004, -.006])
        self.assertEqual(result['trials'], 10)
        names = {r['variant'] for r in summaries}
        self.assertTrue({'D30_D', 'D_D7', 'btc_hedged', 'including_funding',
                         'dose_1_2', 'dose_2_5', 'dose_ge5', 'volume_ge082', 'volume_lt082'} <= names)

    def test_infinite_funding_is_not_silently_filled(self):
        p = self.prices(); d = panel.ms('2021-02-15')
        a = np.where(p.t == d-6*u.DAY-u.HOUR)[0][0]
        p.f['fund_event'][a+1, 0] = np.inf
        with self.assertRaises(ValueError):
            u.Prices(p).trade('TESTUSDT', d)
