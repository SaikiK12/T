from fractions import Fraction as F
import unittest

from lab.inverse_cash import InverseContract, InverseCashAccount, InverseEvent
from lab.inverse_risk import FlatInverseMargin, margin_view, marked_view, portfolio_mark, basis_frontier
from lab.stream_quotes import FrameClock


ANCHOR = FrameClock(1790000000 * 10**9, 100)
EXPIRY = ANCHOR.utc_ns + 86400 * 10**9


def rule():
    return FlatInverseMargin('BTC', 'S:SM', '75000000', '.03', '25', F(2, 3),
                             ('1'*64, '2'*64, '3'*64))


def account(fee=0):
    a = InverseCashAccount(InverseContract('BTC-test', 'BTC', 10, 10, EXPIRY, 'invented'), 11, ANCHOR)
    c = FrameClock(ANCHOR.utc_ns + 1, ANCHOR.mono_ns + 1)
    e = InverseEvent('open', 'open', 'BTC-test', c.utc_ns, c, 'invented', 100, -1000, fee)
    assert a.post(e, c.mono_ns)['status'] == 'applied'
    return a


class InverseRiskTests(unittest.TestCase):
    def test_flat_boundary_is_exact_and_nonlinear_domain_stays_unknown(self):
        r = rule()
        self.assertEqual(r.fractions('2250000')['maintenance'], F(2, 75))
        self.assertEqual(r.fractions('2250000')['initial'], F(1, 25))
        self.assertEqual(r.fractions('2250000.01')['reason'], 'nonlinear_segment_not_implemented')
        self.assertEqual(r.fractions('75000001')['reason'], 'source_maximum_face_exceeded')

    def test_source_currency_and_mode_cannot_be_swapped(self):
        for coin, mode in [('ETH', 'X:PM'), ('BTC', 'X:SM'), ('SOL', 'S:SM')]:
            with self.assertRaises(ValueError):
                FlatInverseMargin(coin, mode, 75000000, '.03', 25, F(2, 3), ('1'*64, '2'*64, '3'*64))
        with self.assertRaises(ValueError):
            FlatInverseMargin('BTC', 'S:SM', 75000000, '.03', 25, F(2, 3), ('1'*64,)*3)

    def test_marked_value_is_total_collateral_once_and_does_not_post_pnl(self):
        a = account(F(1, 10)); before = a.snapshot()
        v = marked_view(a, 125, 100, 100, rule())
        self.assertEqual(v['unrealized_coin'], -2)
        self.assertEqual(v['coin_equity'], F('8.9'))
        self.assertEqual(v['marked_value_usdc'], 890)
        self.assertEqual(a.snapshot(), before)
        p = portfolio_mark(1000, [v], source_input_complete=True, initial_capital=2100)
        self.assertEqual(p['marked_nav_usdc'], 1890)
        self.assertIsNone(p['actual_marked_nav_usdc'])

    def test_daily_realization_preserves_equity_and_does_not_add_another_gain(self):
        a = account(); before = marked_view(a, 125, 100, 100, rule())
        c = FrameClock(ANCHOR.utc_ns+2, ANCHOR.mono_ns+2)
        e = InverseEvent('settlement', 'daily', 'BTC-test', c.utc_ns, c, 'invented', 125, fee_coin=0)
        self.assertEqual(a.post(e, c.mono_ns)['status'], 'applied')
        after = marked_view(a, 125, 100, 100, rule())
        self.assertEqual(before['coin_equity'], after['coin_equity'])
        self.assertEqual(after['unrealized_coin'], 0)
        self.assertEqual(marked_view(a, 200, 100, 100, rule())['coin_equity'], 6)

    def test_unknown_fee_mark_or_denominator_withholds_its_dependent_amount(self):
        self.assertIsNone(marked_view(account(None), 100, 100, 100, rule())['coin_equity'])
        self.assertIsNone(marked_view(account(), None, 100, 100, rule())['marked_value_usdc'])
        x = marked_view(account(), 100, 100, 100, rule(), denominator='unknown')
        self.assertEqual(x['marked_value_usdc'], 1100)
        self.assertIsNone(x['margin']['initial_coin'])
        self.assertFalse(x['actual_risk_ready'])

    def test_idle_usdc_cannot_rescue_a_btc_margin_shortfall(self):
        a = account()
        # Deliberately extreme invented basis; no assertion it is a market-reachable price.
        # E=1+1000/4000=1.25BTC, MM=1000/10*2/75=2.666..BTC.
        view = marked_view(a, 4000, 10, 10, rule(), denominator='index')
        total = portfolio_mark(10000, [view], source_input_complete=True, initial_capital=11100)
        self.assertGreater(total['marked_nav_usdc'], 10000)
        self.assertFalse(total['conditional_maintenance_covered'])
        other = marked_view(a, 4000, 10, 10, rule(), denominator='mark')
        self.assertTrue(other['margin']['maintenance_covered'])
        self.assertFalse(other['margin']['actual_venue_margin_certified'])

    def test_same_coin_additional_obligations_and_expiry_are_not_ignored(self):
        x = margin_view(1, 1000, 100, rule(), other_initial_coin=1, other_maintenance_coin=1)
        self.assertLess(x['maintenance_buffer_coin'], 0)
        for seconds in [1800, 0, -1]:
            self.assertIsNone(margin_view(1, 1000, 100, rule(), seconds_to_expiry=seconds)['initial_coin'])
        with self.assertRaises(ValueError):
            margin_view(1, 1000, 100, rule(), other_initial_coin=0, other_maintenance_coin=1)

    def test_incomplete_portfolio_and_duplicate_coin_are_never_full_nav(self):
        view = marked_view(account(), 100, 100, 100, rule())
        self.assertIsNone(portfolio_mark(1000, [view], source_input_complete=False, initial_capital=2100)['marked_nav_usdc'])
        with self.assertRaises(ValueError):
            portfolio_mark(1000, [view, view], source_input_complete=True, initial_capital=2100)

    def test_unknown_margin_remains_unknown_when_marked_nav_is_known(self):
        view = marked_view(account(), 100, 100, 100, rule(), denominator='unknown')
        total = portfolio_mark(1000, [view], source_input_complete=True, initial_capital=2100)
        self.assertEqual(total['marked_nav_usdc'], 2100)
        self.assertIsNone(total['conditional_initial_covered'])
        self.assertIsNone(total['conditional_maintenance_covered'])

    def test_loss_frontier_is_exact_on_both_sides_of_boundary(self):
        x = basis_frontier(100, 10, 900, 1000, '.02')
        beta = x['maximum_common_future_mark_factor']
        self.assertEqual(beta, F(30, 29))
        self.assertEqual(110 + 900/beta, 980)
        self.assertLess(110 + 900/(beta+F(1, 1000)), 980)
        self.assertGreater(110 + 900/(beta-F(1, 1000)), 980)
        self.assertTrue(basis_frontier(1000, 0, 0, 1000, '.02')['all_positive_factors_meet_floor'])
        self.assertEqual(basis_frontier(0, 0, 0, 1000, '.02')['reason'], 'no_inverse_exposure_and_floor_not_met')

    def test_exact_types_and_positive_price_domain(self):
        for bad in [True, 1.0, 'NaN', '-1', '0']:
            with self.assertRaises(ValueError):
                marked_view(account(), bad, 100, 100, rule())


if __name__ == '__main__':
    unittest.main()
