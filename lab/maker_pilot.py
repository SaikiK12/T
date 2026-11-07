"""Conditional two-sided quoting on recorded BBO/trades; never actual fill/queue proof."""
from bisect import bisect_right
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction as F


def num(x, *, positive=False):
    if isinstance(x, (bool, float)):
        raise ValueError("explicit decimal strings required")
    try:
        d = Decimal(str(x))
    except InvalidOperation as exc:
        raise ValueError("invalid decimal") from exc
    if not d.is_finite() or (positive and d <= 0):
        raise ValueError("invalid finite positive decimal")
    return F(d)


def fmt(x):
    with localcontext() as ctx:
        ctx.prec = 50
        return format(Decimal(x.numerator) / Decimal(x.denominator), ".12f")


def eligible(order, trade):
    """Strict price-through, ordinary contra flow and explicit matching-time interval.

    Local/transaction clocks are assumed aligned, not calibrated by this data.
    Receive-after-cancel can still report an execution inside the old live interval.
    """
    if trade["liq"] or not order["accepted"] or order["remaining"] <= 0:
        return False
    if not order["arrival"] <= trade["tx_us"] < order["cancel"] or trade["t"] < order["arrival"]:
        return False
    return ((order["side"] == 1 and not trade["maker_ask"] and trade["px"] < order["price"])
            or (order["side"] == -1 and trade["maker_ask"] and trade["px"] > order["price"]))


def replay(quotes, trades, *, start, end, quote_usd, lot, tick, min_base, min_quote,
           maker_fee, taker_fee, multiple, capital="10000", assets=3,
           refresh_us=15_000_000, arrival_us=1_000_000, cancel_us=1_000_000,
           max_quote_age_us=1_000_000, max_report_delay_us=5_000_000):
    if trades is None:
        return dict(state="NO_TRADE_FILE", pnl=None, actual_fills=False,
                    meaning="Missing trade file is not zero trades or zero profit")
    if multiple not in (1, 2, 3) or start >= end or arrival_us <= 0 or cancel_us <= 0:
        raise ValueError("invalid frozen timing/cost case")
    lot, tick = num(lot, positive=True), num(tick, positive=True)
    mf, tf = num(maker_fee), num(taker_fee)
    cash0 = num(capital, positive=True) / assets
    if min(mf, tf) < 0:
        raise ValueError("negative fees unsupported")
    qs = sorted(quotes, key=lambda r: r["t"])
    if not qs or len({q["t"] for q in qs}) != len(qs):
        raise ValueError("missing/duplicate quote timestamp")
    for q in qs:
        if not 0 < q["bid"] < q["ask"] or min(q["bq"], q["aq"]) < 0:
            raise ValueError("invalid BBO")
        if q["bid"] % tick or q["ask"] % tick:
            raise ValueError("current tick does not fit historical quote")
    tx = sorted(trades, key=lambda r: (r["t"], r["trade_id"]))
    if len({t["trade_id"] for t in tx}) != len(tx):
        raise ValueError("duplicate trade identity")
    if any(t["sz"] <= 0 or t["px"] <= 0 or t["tx_us"] <= 0 or t["maker_ask"] not in (0, 1) or t["liq"] not in (0, 1) for t in tx):
        raise ValueError("invalid trade quantity/clock/side")
    times = [q["t"] for q in qs]

    def at(t):
        i = bisect_right(times, t) - 1
        return qs[i] if i >= 0 and t - times[i] <= max_quote_age_us and min(qs[i]["bq"], qs[i]["aq"]) > 0 else None

    first = at(start)
    if first is None:
        return dict(state="NO_START_BBO", pnl=None, actual_fills=False)
    mid0 = (first["bid"] + first["ask"]) / 2
    quantity = (num(quote_usd, positive=True) / mid0 // lot) * lot
    if quantity < num(min_base, positive=True) or quantity * first["bid"] < num(min_quote, positive=True):
        return dict(state="BELOW_CURRENT_MINIMUM", pnl=None, actual_fills=False)
    if 2 * quantity * mid0 > cash0:
        raise ValueError("fully funded per-market inventory cap exceeds allocation")
    orders, fills, decisions = [], [], []
    pos, cashflow, fees, min_equity = F(0), F(0), F(0), cash0
    stop = None
    # Decision events use only already-received BBO/fill reports; quote acknowledgements
    # and engine-clock equality remain explicitly hypothetical.
    events = [(t, 0, None) for t in range(start, end, refresh_us)]
    events += [(t["t"], 1, t) for t in tx if start <= t["t"] <= end + max_report_delay_us]
    events.sort(key=lambda e: (e[0], e[1]))
    for now, kind, tr in events:
        if kind == 0:
            q = at(now)
            d = dict(time=now, fresh=q is not None, pos_known=fmt(pos))
            decisions.append(d)
            if q is None:
                continue
            for side, price in ((1, q["bid"]), (-1, q["ask"])):
                if side * pos >= quantity:
                    continue
                arrival = now + arrival_us
                cancel = min(now + refresh_us + cancel_us, end)
                if arrival >= cancel:
                    continue
                aq = at(arrival)
                accepted = aq is not None and ((price < aq["ask"]) if side == 1 else (price > aq["bid"]))
                orders.append(dict(id=len(orders), decision=now, side=side, price=price,
                                   quantity=quantity, remaining=quantity, arrival=arrival,
                                   cancel=cancel, accepted=accepted))
            continue
        candidates = [o for o in orders if eligible(o, tr)]
        if len(candidates) > 1:
            raise ValueError("overlapping own orders at matching time")
        if not candidates:
            continue
        o = candidates[0]
        amount = min(o["remaining"], tr["sz"])
        amount = (amount // lot) * lot  # no fill above executed volume; never round up.
        if amount <= 0:
            continue
        price, side = o["price"], o["side"]
        o["remaining"] -= amount
        pos += side * amount
        cashflow -= side * amount * price
        fee = multiple * amount * price * mf
        fees += fee
        fill = dict(order=o["id"], receive_us=now, match_us=tr["tx_us"], source_trade_id=tr["trade_id"],
                    side=side, quantity=fmt(amount), price=fmt(price), maker_fee=fmt(fee),
                    receive_after_effective_cancel=now >= o["cancel"], inventory=fmt(pos))
        fills.append(fill)
        quote = at(now)
        marked = cash0 + cashflow + pos * (sum((quote["bid"], quote["ask"])) / 2) - fees if quote else None
        if marked is not None:
            min_equity = min(min_equity, marked)
        funded_notional = abs(pos) * (quote["bid"] + quote["ask"]) / 2 if quote else None
        if abs(pos) > 2 * quantity or (marked is not None and marked <= 0) or (funded_notional is not None and funded_notional > cash0):
            stop = dict(time=now, state="INVENTORY_OR_CAPITAL_GUARD_BREACH", inventory=fmt(pos),
                        equity=fmt(marked) if marked is not None else None)
            break
    base = dict(quantity=fmt(quantity), quote_usd=str(quote_usd), multiple=multiple,
                capital_allocation=fmt(cash0), minimum_fill_time_marked_equity=fmt(min_equity),
                hypothetical_orders=len(orders), accepted_in_model=sum(o["accepted"] for o in orders),
                fills=fills, decisions=decisions, terminal_inventory=fmt(pos),
                quote_currency_cashflow=fmt(cashflow), maker_fees=fmt(fees),
                actual_fills=False, engine_clock_and_ack_certified=False,
                funding_and_owner_fee_entitlement_certified=False,
                meaning="Conditional strict-through candidates; no queue/ack/inclusion or income-rate proof")
    if stop is not None:
        return dict(**base, state=stop["state"], stop=stop, pnl=None, recovery_counted=False)
    last = at(end)
    if last is None and pos:
        return dict(**base, state="NO_FRESH_EXIT_BBO", pnl=None)
    mid = (last["bid"] + last["ask"]) / 2 if last else F(0)
    marked = cashflow + pos * mid - fees
    side_price, shown = ((last["bid"], last["bq"]) if pos > 0 else (last["ask"], last["aq"])) if last else (F(0), F(0))
    if abs(pos) > shown:
        return dict(**base, state="EXIT_DEPTH_UNQUALIFIED", pnl=None, mid_mark_before_funding=fmt(marked))
    exit_drag = abs(pos) * abs(side_price - mid)
    exit_fee = abs(pos) * side_price * tf * multiple
    # Actual spread crossing is present once; additional copies are a stress only.
    net = cashflow + pos * side_price - fees - (multiple - 1) * exit_drag - exit_fee
    return dict(**base, state="CONDITIONAL_BEFORE_FUNDING", pnl=fmt(net),
                mid_mark_before_funding=fmt(marked), terminal_exit_drag=fmt(exit_drag * multiple),
                terminal_taker_fee=fmt(exit_fee), net_is_settled_broker_profit=False,
                costs="maker fee, terminal taker fee and terminal crossing stressed1x/2x/3x; no maker touch fills")
