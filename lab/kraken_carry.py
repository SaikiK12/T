"""Fixed-quantity spot/perp carry screen with funded cash and unknown funding intervals."""
from decimal import Decimal, ROUND_FLOOR

from lab.carry_execution import number

D = Decimal
HOUR = 3600
DAY = 86400
ZERO = D(0)


def fixed_quantity(capital, spot, lot, spot_fee, slip):
    """Reserve half the account for spot INCLUDING the worst (3x) entry costs."""
    c, s, step = (number(x, positive=True) for x in (capital, spot, lot))
    f, b = (number(x, nonnegative=True) for x in (spot_fee, slip))
    units = c / 2 / (s * (1 + 3 * b) * (1 + 3 * f)) / step
    return units.to_integral_value(rounding=ROUND_FLOOR) * step


def funding_intervals(start, end, observed, envelopes, relative_cap):
    """A missing rate stays unknown; its explicit cap scenario is an interval.

    Envelopes are retrospective reference-index HIGH prices bracketing missing
    periods, never substituted funding observations. The current documented cap
    is a scenario assumption for past gaps, not a certification of historical caps.
    """
    cap = number(relative_cap, positive=True)
    rows = []
    for t in range(start, end, HOUR):
        if t in observed:
            rate = number(observed[t])
            rows.append((t, rate, rate, True))
        else:
            if t not in envelopes:
                raise ValueError("unbounded missing funding hour")
            bound = cap * number(envelopes[t], positive=True)
            rows.append((t, -bound, bound, False))
    return rows


def _dd(values):
    peak, worst = values[0], ZERO
    for equity in values:
        peak = max(peak, equity)
        if peak > 0:
            worst = max(worst, (peak - equity) / peak)
    return worst


def replay(*, start, end, capital, lot, spot, trade, marks, funding,
           spot_fee, perp_fee, slip, initial_margin, maintenance_margin,
           tier_ceiling, multiple):
    """One continuous long spot/short linear perp; no churn, transfers or resize.

    Prices are historical bar-open benchmarks plus declared friction, not fills.
    All fees are paid in USD. No borrowing, non-USD conversions or collateral
    offsets. The short wallet has its own half of total funded capital.
    A possible maintenance breach invalidates an executable terminal result;
    the otherwise continuing ledger is explicitly a counterfactual diagnostic.
    """
    if end <= start or start % DAY or end % DAY:
        raise ValueError("whole UTC days required")
    if multiple not in (1, 2, 3):
        raise ValueError("1x/2x/3x costs required")
    c, step = number(capital, positive=True), number(lot, positive=True)
    sf, pf, b = (number(x, nonnegative=True) for x in (spot_fee, perp_fee, slip))
    im, mm = (number(x, positive=True) for x in (initial_margin, maintenance_margin))
    ceiling = number(tier_ceiling, positive=True)
    if not 0 < mm <= im <= 1:
        raise ValueError("invalid supplied margin rates")
    days = list(range(start, end + DAY, DAY))
    if any(t not in spot or t not in trade for t in days):
        raise ValueError("missing daily execution benchmark")
    if any(t not in marks for t in range(start, end, HOUR)):
        raise ValueError("missing hourly mark")
    if [r[0] for r in funding] != list(range(start, end, HOUR)):
        raise ValueError("funding clock mismatch")
    s0, s1 = (number(spot[t], positive=True) for t in (start, end))
    f0, f1 = (number(trade[t], positive=True) for t in (start, end))
    q = fixed_quantity(c, s0, step, sf, b)
    if not q:
        raise ValueError("quantity rounds to zero")
    k = D(multiple)
    sb, ss, fs, fb = s0 * (1 + k * b), s1 * (1 - k * b), f0 * (1 - k * b), f1 * (1 + k * b)
    if min(sb, ss, fs, fb) <= 0:
        raise ValueError("nonpositive stressed execution")
    spot_entry_fee, perp_entry_fee = q * sb * sf * k, q * fs * pf * k
    spot_cash = c / 2 - q * sb - spot_entry_fee
    perp_cash = c / 2 - perp_entry_fee
    if spot_cash < 0 or perp_cash < q * f0 * im:
        raise ValueError("entry is not fully funded")
    fl, fu = ZERO, ZERO
    min_buffer, breach = None, None
    min_usd_cash, cash_breach = perp_cash, None
    navs = [dict(t=start, lower=c, upper=c, label="before entry")]
    monthly = []
    month_start = start
    ml, mu = ZERO, ZERO
    for t, low_rate, high_rate, known in funding:
        low_rate, high_rate = number(low_rate), number(high_rate)
        if low_rate > high_rate or (known and low_rate != high_rate):
            raise ValueError("invalid funding interval")
        mark = marks[t]
        high = number(mark["high"], positive=True)
        opened = number(mark["open"], positive=True)
        low = number(mark["low"], positive=True)
        if not low <= opened <= high:
            raise ValueError("mark OHLC bounds")
        notional = q * high
        if notional >= ceiling:
            raise ValueError("position leaves the qualified first EEA margin tier")
        # At the hourly high, negative funding might already have accrued;
        # positive funding is not lent to this stress check before it settles.
        wallet_floor = perp_cash + fl + min(ZERO, q * low_rate) + q * (fs - high)
        usd_floor = perp_cash + fl + min(ZERO, q * low_rate)
        min_usd_cash = min(min_usd_cash, usd_floor)
        if usd_floor < 0 and cash_breach is None:
            cash_breach = dict(t=t, usd_cash_floor=usd_floor, financing_charge=None)
        buffer = wallet_floor - notional * mm
        if min_buffer is None or buffer < min_buffer:
            min_buffer = buffer
        if buffer <= 0 and breach is None:
            breach = dict(t=t, wallet_floor=wallet_floor, maintenance=notional * mm,
                          state="POSSIBLE_MAINTENANCE_BREACH", liquidation_fill=None)
        if t > start and t % DAY == 0:
            base = spot_cash + q * number(spot[t], positive=True) + perp_cash + q * (fs - opened)
            navs.append(dict(t=t, lower=base + fl, upper=base + fu, label="daily open mark"))
        fl += q * low_rate
        fu += q * high_rate
        ml += q * low_rate
        mu += q * high_rate
        # First of month at 00 UTC: cash attribution only, no trade or resize.
        from datetime import datetime, timezone
        after = t + HOUR
        dt = datetime.fromtimestamp(after, timezone.utc)
        if (dt.day == 1 and dt.hour == 0) or after == end:
            monthly.append(dict(start=month_start, end=after, funding_lower=ml, funding_upper=mu))
            month_start, ml, mu = after, ZERO, ZERO
    spot_exit_fee, perp_exit_fee = q * ss * sf * k, q * fb * pf * k
    terminal_base = spot_cash + q * ss - spot_exit_fee + perp_cash + q * (fs - fb) - perp_exit_fee
    net_low, net_high = terminal_base + fl - c, terminal_base + fu - c
    fees = spot_entry_fee + perp_entry_fee + spot_exit_fee + perp_exit_fee
    slippage = q * k * b * (s0 + s1 + f0 + f1)
    basis = q * ((s1 - s0) + (f0 - f1))
    # Independent cash-vs-attribution invariant inside the run, tolerance in USD.
    if max(abs(net_low - (fl + basis - fees - slippage)),
           abs(net_high - (fu + basis - fees - slippage))) > D("1e-18"):
        raise ValueError("cash attribution does not reconcile")
    navs.append(dict(t=end, lower=c + net_low, upper=c + net_high, label="after both exits"))
    annual = D(365 * DAY) / D(end - start)
    return dict(capital=c, quantity=q, initial_spot_notional=q*s0, cost_multiple=multiple,
                observed_funding_hours=sum(r[3] for r in funding),
                unknown_funding_hours=sum(not r[3] for r in funding),
                funding_lower=fl, funding_upper=fu, basis_pnl=basis, fees=fees,
                slippage_assumption=slippage, total_execution_cost=fees+slippage,
                counterfactual_net_lower=net_low, counterfactual_net_upper=net_high,
                annual_return_on_total_capital_lower=net_low/c*annual,
                annual_return_on_total_capital_upper=net_high/c*annual,
                annual_funding_on_initial_notional_lower=fl/(q*s0)*annual,
                annual_funding_on_total_capital_lower=fl/c*annual,
                daily_mark_drawdown_lower_path=_dd([n["lower"] for n in navs]),
                min_short_wallet_maintenance_buffer=min_buffer,
                possible_maintenance_breach=breach,
                min_short_usd_cash_lower=min_usd_cash,
                possible_usd_cash_deficit=cash_breach,
                executable_net=None, actual_fills=False,
                margin_screen_clear=breach is None and cash_breach is None,
                terminal_scope="counterfactual if a possible margin breach; otherwise cost-model interval, never a fill",
                monthly_funding_attribution=monthly, daily_nav_interval=navs)
