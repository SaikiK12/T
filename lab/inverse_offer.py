"""Exact collateral and terminal-sale hurdles over the existing inverse model.

No Binance/Deribit unit substitution, actual margin attestation, forecast,
price prediction, order, source authentication or strategy activation.
"""
from fractions import Fraction as F

from lab.inverse_cash import rational, terminal_conversion


def coverage(initial_coin, hedge_coin, entry_fee_coin, *, other_coin_debits=0):
    """Short face Q has equity E(M)=Q/M+D, D=B-fees-sum(face/entry).

    D>=0 proves the MODEL's >=1x coin coverage at every positive mark, not
    exchange liquidation immunity. Missing fee/debit is unknown, never zero.
    """
    b = rational(initial_coin, nonnegative=True); a = rational(hedge_coin, positive=True)
    known = entry_fee_coin is not None and other_coin_debits is not None
    delta = None if not known else b-a-rational(entry_fee_coin, nonnegative=True)-rational(other_coin_debits, nonnegative=True)
    return {'known_initial_coin': b, 'known_hedge_coin': a, 'residual_coin_delta': delta,
        'all_positive_marks_1x_model_coverage': None if delta is None else delta >= 0,
        'minimum_required_initial_coin': None if delta is None else b-delta,
        'actual_margin_rules_verified': False, 'actual_liquidation_immunity': None,
        'actual_order_allowed': False}


def equity_coin(face_usd, hedge_coin, initial_coin, entry_fee_coin, mark, *, other_coin_debits=0):
    c = coverage(initial_coin, hedge_coin, entry_fee_coin, other_coin_debits=other_coin_debits)
    q = rational(face_usd, positive=True); m = rational(mark, positive=True)
    return None if c['residual_coin_delta'] is None else q/m+c['residual_coin_delta']


def prefund(hedge_coin, entry_fee_coin, spot_entry_rate, *, fee_asset, base_step=None):
    """Supply the SAME required net collateral after explicit spot fee debits.

    Quote-debit pays a quote fee on principal; base-debit buys extra base so
    gross*(1-rate) supplies collateral. A supplied step is conditional only;
    source-certified lot/fee-asset evidence is still required for actual orders.
    No fee currency is guessed when missing. None step is ideal arithmetic.
    """
    a = rational(hedge_coin, positive=True)
    if entry_fee_coin is None or spot_entry_rate is None or fee_asset is None:
        return {'gross_spot_base': None, 'net_collateral_coin': None,
            'quote_cost_multiplier': None, 'coverage': None, 'actual_order_allowed': False}
    fee = rational(entry_fee_coin, nonnegative=True); rate = rational(spot_entry_rate, nonnegative=True)
    if rate >= 1 or fee_asset not in ('base', 'quote'):
        raise ValueError('explicit base/quote fee debit and rate below one required')
    required = a+fee; gross = required/(1-rate) if fee_asset == 'base' else required
    if base_step is not None:
        step = rational(base_step, positive=True)
        gross = -((-gross)//step)*step
    net = gross*(1-rate) if fee_asset == 'base' else gross
    return {'gross_spot_base': gross, 'net_collateral_coin': net,
        'quote_cost_multiplier': F(1) if fee_asset == 'base' else 1+rate,
        'coverage': coverage(net, a, fee), 'actual_order_allowed': False}


def terminal_hurdle(face_usd, hedge_coin, initial_coin, entry_fee_coin,
                   delivery_fee_rate, spot_exit_rate, *, delivery_price=None,
                   exit_ratio=None, initial_spend_quote, total_capital_quote,
                   cash_benchmark_factor=1, idle_cash_factor=1, other_exit_cost_quote=None):
    """Minimum sale/TWAP/FX ratio to match the SAME entire initial capital.

    Total terminal cash = idle*(idle factor)+[Q*(1-deliveryfee)+D*X]*ratio
    *(1-sale_fee)-other_exit_cost. Ratio includes source settlement-vs-sale
    timing/price and USD-vs-quote effects. Missing terms do not grant net cash.
    With D=0 only, the algebraic unit proceeds need no settlement-price guess.
    """
    q = rational(face_usd, positive=True); a = rational(hedge_coin, positive=True)
    b = rational(initial_coin, nonnegative=True)
    spent = rational(initial_spend_quote, nonnegative=True); capital = rational(total_capital_quote, positive=True)
    if spent > capital:
        raise ValueError('initial outlay exceeds same segregated capital')
    result = {'same_initial_capital_quote': capital, 'initial_spend_quote': spent,
        'idle_cash_quote': capital-spent, 'unit_terminal_quote_before_ratio': None,
        'minimum_exit_ratio': None, 'conditional_total_terminal_quote': None,
        'conditional_net_vs_cash_benchmark_quote': None, 'residual_coin_delta': None,
        'actual_expected_net_quote': None, 'actual_order_allowed': False, 'activation_allowed': False}
    c = coverage(b, a, entry_fee_coin); delta = c['residual_coin_delta']; result['residual_coin_delta'] = delta
    if any(x is None for x in (delta, delivery_fee_rate, spot_exit_rate,
            cash_benchmark_factor, idle_cash_factor, other_exit_cost_quote)):
        return result
    df = rational(delivery_fee_rate, nonnegative=True); sf = rational(spot_exit_rate, nonnegative=True)
    if df >= 1 or sf >= 1:
        raise ValueError('fee rates below one required')
    benchmark = capital*rational(cash_benchmark_factor, positive=True)
    idle = (capital-spent)*rational(idle_cash_factor, positive=True)
    other = rational(other_exit_cost_quote, nonnegative=True)
    if delivery_price is None:
        unit = q*(1-df)*(1-sf) if delta == 0 else None
    else:
        # Reuse the frozen inverse conversion and its source-role convention.
        unit = terminal_conversion(q, a, b, entry_fee_coin, df,
            delivery_price, F(1), sf)['usdt_proceeds']
    result['unit_terminal_quote_before_ratio'] = unit
    if unit is None or unit <= 0:
        return result
    result['minimum_exit_ratio'] = max(F(0), (benchmark-idle+other)/unit)
    if exit_ratio is not None:
        end = idle+unit*rational(exit_ratio, positive=True)-other
        result['conditional_total_terminal_quote'] = end
        result['conditional_net_vs_cash_benchmark_quote'] = end-benchmark
    return result
