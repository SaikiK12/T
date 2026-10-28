"""Read-only, source-bounded inverse margin and marked-value diagnostics.

An owned spot coin is the SAME inverse collateral, never a second holding.
The current Deribit Tier4 flat segment supplies percentages, not the missing
inverse conversion denominator, owner mode, complete account or liquidation.
No order permission, cash posting or actual risk certification is provided.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import re

from lab.inverse_cash import InverseCashAccount, rational


@dataclass(frozen=True)
class FlatInverseMargin:
    coin: str
    mode: str
    maximum_face_usd: F
    flat_share: F
    start_leverage: F
    maintenance_share_of_initial: F
    source_sha256: tuple[str, ...]

    def __post_init__(self):
        if self.coin not in ('BTC', 'ETH') or self.mode != 'S:SM':
            raise ValueError('only the received segregated BTC/ETH inverse contract is implemented')
        for name in ('maximum_face_usd', 'flat_share', 'start_leverage', 'maintenance_share_of_initial'):
            object.__setattr__(self, name, rational(getattr(self, name), positive=True))
        if self.flat_share > 1 or self.maintenance_share_of_initial > 1 or self.start_leverage < 1:
            raise ValueError('invalid finite source margin fractions')
        if (type(self.source_sha256) is not tuple or len(self.source_sha256) != 3
                or len(set(self.source_sha256)) != 3
                or any(type(h) is not str or re.fullmatch('[0-9a-f]{64}', h) is None for h in self.source_sha256)):
            raise ValueError('three exact received primary-source identities required')

    def fractions(self, face):
        """No nonlinear interpolation or extrapolation beyond the flat segment."""
        face = rational(face, nonnegative=True)
        if face > self.maximum_face_usd:
            return {'initial': None, 'maintenance': None, 'reason': 'source_maximum_face_exceeded'}
        if face > self.maximum_face_usd * self.flat_share:
            return {'initial': None, 'maintenance': None, 'reason': 'nonlinear_segment_not_implemented'}
        initial = 1 / self.start_leverage
        return {'initial': initial, 'maintenance': initial * self.maintenance_share_of_initial, 'reason': None}


def margin_view(coin_equity, face_usd, denominator_usd_per_coin, rule, *,
                other_initial_coin=0, other_maintenance_coin=0, seconds_to_expiry=3600):
    """Conditional requirements in ONE settlement coin; no other-asset credit.

    The denominator is explicitly supplied, not inferred to be the venue's.
    Additional same-coin account requirements must not be silently omitted in
    an actual account assessment. This model's zero defaults are only fixtures.
    The last30min projected-margin convergence remains outside this contract.
    """
    if not isinstance(rule, FlatInverseMargin):
        raise ValueError('typed source margin contract required')
    face = rational(face_usd, nonnegative=True)
    extra_i = rational(other_initial_coin, nonnegative=True)
    extra_m = rational(other_maintenance_coin, nonnegative=True)
    if extra_m > extra_i:
        raise ValueError('same-coin additional maintenance cannot exceed initial margin')
    fractions = rule.fractions(face)
    reason = fractions['reason']
    if rational(seconds_to_expiry) <= 1800:
        reason = 'expiry_projection_or_delivery_not_implemented'
    if denominator_usd_per_coin is None:
        reason = reason or 'inverse_conversion_denominator_unknown'
    if coin_equity is None:
        reason = reason or 'coin_equity_unknown'
    if reason:
        return {'initial_coin': None, 'maintenance_coin': None, 'initial_buffer_coin': None,
                'maintenance_buffer_coin': None, 'initial_covered': None, 'maintenance_covered': None,
                'reason': reason, 'actual_venue_margin_certified': False}
    d = rational(denominator_usd_per_coin, positive=True)
    equity = rational(coin_equity)
    im = face / d * fractions['initial'] + extra_i
    mm = face / d * fractions['maintenance'] + extra_m
    return {'initial_coin': im, 'maintenance_coin': mm, 'initial_buffer_coin': equity - im,
            'maintenance_buffer_coin': equity - mm, 'initial_covered': equity >= im,
            'maintenance_covered': equity >= mm, 'reason': None, 'actual_venue_margin_certified': False}


def marked_view(account, future_mark, spot_quote, index, rule, *, denominator='index',
                other_initial_coin=0, other_maintenance_coin=0, seconds_to_expiry=3600):
    """Mark the existing inverse account without realizing or changing cash.

    spot_quote is USDC/coin; future_mark and index are USD/coin. The returned
    USDC component is a valuation of total inverse coin equity, not a second
    spot asset and not an executable close. Public mark publication time is
    separate from any source-effective/owner-account certification.
    """
    if (not isinstance(account, InverseCashAccount) or not isinstance(rule, FlatInverseMargin)
            or rule.coin != account.contract.coin or denominator not in ('index', 'mark', 'unknown')):
        raise ValueError('typed matching inverse account, margin rule and denominator control required')
    m = None if future_mark is None else rational(future_mark, positive=True)
    s = None if spot_quote is None else rational(spot_quote, positive=True)
    ix = None if index is None else rational(index, positive=True)
    known = not account.pending and not account.conflicts and m is not None
    unrealized = account.face * (account.entry_reciprocal - 1 / m) if known else None
    equity = account.coin + unrealized if known else None
    if denominator == 'unknown': d = None
    else: d = ix if denominator == 'index' else m
    margin = margin_view(equity, abs(account.face), d, rule,
        other_initial_coin=other_initial_coin, other_maintenance_coin=other_maintenance_coin,
        seconds_to_expiry=seconds_to_expiry)
    return {'coin': account.contract.coin, 'coin_cash': account.coin if known else None,
            'signed_face_usd': account.face, 'unrealized_coin': unrealized, 'coin_equity': equity,
            'marked_value_usdc': equity * s if equity is not None and s is not None else None,
            'future_mark_over_index': m / ix if m is not None and ix is not None else None,
            'outside_documented_default_ten_percent_band':
                abs(m / ix - 1) > F(1, 10) if m is not None and ix is not None else None,
            'denominator_control': denominator, 'margin': margin,
            'actual_executable_close_usdc': None, 'actual_risk_ready': False,
            'unknowns': ['owner_account_mode_and_complete_positions', 'actual_fees_and_eligible_collateral',
                         'inverse_margin_conversion_denominator', 'liquidation_trigger_and_engine',
                         'source_effective_mark_clock', 'future_exit_liquidity']}


def portfolio_mark(idle_quote, legs, *, source_input_complete, initial_capital):
    """Same quote capital once; legs are total coin-equity valuations only."""
    if type(source_input_complete) is not bool or type(legs) is not list:
        raise ValueError('explicit complete-input state and finite marked legs required')
    idle = rational(idle_quote, nonnegative=True)
    capital = rational(initial_capital, positive=True)
    coins = [x['coin'] for x in legs]
    if len(set(coins)) != len(coins):
        raise ValueError('duplicate collateral ownership requires account-level reconciliation')
    known = source_input_complete and all(x['marked_value_usdc'] is not None for x in legs)
    value = idle + sum((x['marked_value_usdc'] for x in legs), F(0)) if known else None
    def aggregate(field):
        if not known:
            return None
        states = [x['margin'][field] for x in legs]
        if any(x is False for x in states):
            return False
        return None if any(x is None for x in states) else True
    return {'marked_nav_usdc': value, 'pnl_from_initial_usdc': None if value is None else value - capital,
            'return_on_all_initial_capital': None if value is None else value / capital - 1,
            'conditional_initial_covered': aggregate('initial_covered'),
            'conditional_maintenance_covered': aggregate('maintenance_covered'),
            'actual_marked_nav_usdc': None, 'actual_risk_ready': False}


def basis_frontier(idle_quote, residual_quote, reciprocal_quote, initial_capital, loss_fraction):
    """Exact common-mark-factor boundary for NAV >= capital*(1-loss).

    Holding the supplied spot prices fixed, NAV(beta)=idle+residual+H/beta.
    H is SUM(face*spot_quote/current_future_mark). Neither the boundary nor
    fixed stress states estimate a probability or an actual risk limit.
    """
    idle = rational(idle_quote, nonnegative=True)
    residual = rational(residual_quote)
    h = rational(reciprocal_quote, nonnegative=True)
    capital = rational(initial_capital, positive=True)
    loss = rational(loss_fraction, nonnegative=True)
    if loss >= 1:
        raise ValueError('loss fraction must be below one')
    target = capital * (1 - loss)
    gap = target - idle - residual
    if gap <= 0:
        return {'maximum_common_future_mark_factor': None, 'all_positive_factors_meet_floor': True,
                'target_usdc': target, 'reason': 'constant_component_covers_floor'}
    return {'maximum_common_future_mark_factor': h / gap, 'all_positive_factors_meet_floor': False,
            'target_usdc': target, 'reason': None if h else 'no_inverse_exposure_and_floor_not_met'}
