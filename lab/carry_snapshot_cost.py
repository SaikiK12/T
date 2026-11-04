"""Conditional, lot-matched book costs from explicitly supplied linear contracts.

No fills, simultaneous markets, fees, future exits, capital return or account
eligibility are inferred. Provider contract lots become base quantity only
through explicit multipliers. Missing mechanics never become zero cost.
"""
from decimal import Decimal, InvalidOperation, localcontext
from fractions import Fraction
from math import gcd, lcm


def amount(value):
    if isinstance(value, bool):
        raise ValueError('explicit finite positive amount required')
    try:
        x = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError('invalid amount') from exc
    if not x.is_finite() or not 0 < x <= Decimal('1e30') or x.as_tuple().exponent < -18:
        raise ValueError('unsupported amount range or precision')
    return x


def contract(venue, key, symbol, payload):
    """Qualify a single request-bound contract; API trading flag is separate."""
    if venue not in ('mexc', 'kucoin') or not isinstance(payload, dict):
        raise ValueError('explicit supported source envelope required')
    if venue == 'mexc':
        if payload.get('success') is not True or type(payload.get('code')) is not int or payload['code'] != 0:
            raise ValueError('MEXC success envelope missing')
    elif payload.get('code') != '200000':
        raise ValueError('KuCoin success envelope missing')
    row = payload.get('data')
    if isinstance(row, list):
        if len(row) != 1:
            raise ValueError('single-contract request returned a nonexclusive inventory')
        row = row[0]
    if not isinstance(row, dict) or row.get('symbol') != symbol:
        raise ValueError('contract response identity mismatch')
    if venue == 'mexc':
        if (row.get('baseCoin') != key or row.get('quoteCoin') != 'USDT' or row.get('settleCoin') != 'USDT'
                or symbol != key + '_USDT' or type(row.get('state')) is not int or row['state'] != 0
                or type(row.get('type')) is not int or row['type'] != 1):
            raise ValueError('MEXC crypto/open/USDT convention unqualified')
        multiplier, lot = amount(row.get('contractSize')), amount(row.get('volUnit'))
        api = row.get('apiAllowed') if type(row.get('apiAllowed')) is bool else None
        minimum = amount(row['minVol']) if row.get('minVol') is not None else None
    else:
        if (row.get('baseCurrency') != key or row.get('quoteCurrency') != 'USDT'
                or row.get('settleCurrency') != 'USDT' or row.get('isInverse') is not False
                or row.get('type') != 'FFWCSX' or row.get('status') != 'Open' or row.get('expireDate')):
            raise ValueError('KuCoin linear/open/perpetual/USDT convention unqualified')
        multiplier, lot = amount(row.get('multiplier')), amount(row.get('lotSize'))
        api, minimum = None, lot
    if lot != lot.to_integral_value() or minimum is not None and (minimum < lot or minimum != minimum.to_integral_value()):
        raise ValueError('contract lot/minimum convention unqualified')
    with localcontext() as ctx:
        ctx.prec = 80
        quantum = multiplier * lot
        amount(quantum)
    return dict(venue=venue, key=key, symbol=symbol, multiplier_base=str(multiplier),
                lot_contracts=str(lot), base_quantum=str(quantum),
                minimum_contracts=None if minimum is None else str(minimum),
                reported_api_trading_flag=api, owner_trading_access_verified=False,
                owner_fees=None, convention='declared linear USDT contract units; no account authentication')


def book(venue, symbol, rules, payload):
    if rules.get('venue') != venue or rules.get('symbol') != symbol or not isinstance(payload, dict):
        raise ValueError('bound contract/book identity required')
    if venue == 'mexc':
        if 'success' in payload:
            if payload.get('success') is not True or type(payload.get('code')) is not int or payload['code'] != 0:
                raise ValueError('MEXC book envelope unsuccessful')
            data = payload.get('data')
        else:
            data = payload  # explicitly documented raw REST snapshot shape
        if not isinstance(data, dict) or data.get('symbol', symbol) != symbol:
            raise ValueError('MEXC request-bound book mismatch')
        sequence, stamp, width = data.get('version'), data.get('timestamp'), 3
        if type(stamp) is not int or not 10**12 <= stamp < 10**14:
            raise ValueError('MEXC reported milliseconds required')
        unit = 'provider_reported_milliseconds'
    else:
        if payload.get('code') != '200000' or not isinstance(payload.get('data'), dict):
            raise ValueError('KuCoin book envelope unsuccessful')
        data = payload['data']
        if data.get('symbol') != symbol:
            raise ValueError('KuCoin book symbol mismatch')
        sequence, stamp, width = data.get('sequence'), data.get('ts'), 2
        if type(stamp) is not int or not 10**12 <= stamp < 10**21:
            raise ValueError('explicit KuCoin raw source timestamp required')
        unit = 'provider_raw_unqualified'  # no unit/clock synchronization inferred from digit count
    if type(sequence) is not int or sequence < 0:
        raise ValueError('explicit nonnegative book sequence required')
    sides = {}
    with localcontext() as ctx:
        ctx.prec = 80
        for name in ('bids', 'asks'):
            raw = data.get(name)
            if not isinstance(raw, list) or not 1 <= len(raw) <= 20:
                raise ValueError('bounded nonempty depth required')
            levels = []
            for level in raw:
                if not isinstance(level, list) or len(level) != width:
                    raise ValueError('documented venue-specific depth tuple required')
                price, contracts = amount(level[0]), amount(level[1])
                if contracts % amount(rules['lot_contracts']):
                    raise ValueError('depth quantity is not a declared contract lot multiple')
                if venue == 'mexc':
                    count = amount(level[2])
                    if count != count.to_integral_value():
                        raise ValueError('explicit positive order count required')
                levels.append((price, contracts * amount(rules['multiplier_base'])))
            if any((a[0] <= b[0] if name == 'bids' else a[0] >= b[0]) for a, b in zip(levels, levels[1:])):
                raise ValueError('ordered unique book prices required')
            sides[name] = levels
        if sides['bids'][0][0] >= sides['asks'][0][0]:
            raise ValueError('crossed/locked book')
        mid = (sides['bids'][0][0] + sides['asks'][0][0]) / 2
    return dict(venue=venue, symbol=symbol, bids=sides['bids'], asks=sides['asks'], mid=mid,
                reported_sequence=sequence, reported_source_time=stamp, reported_time_unit=unit,
                sequence_continuity_verified=False, source_clock_authenticated=False)


def pair_cost(left_rules, right_rules, left_book, right_book, notional='1000'):
    """Both directions at a common lot-multiple quantity; no basis profit term.

    Target is <= supplied MID notional per leg, not a cash-spending guarantee.
    Actual quote consideration includes spread/impact and can exceed the mid
    target. Fee and future-exit costs remain unknown under every multiplier.
    """
    unknown = dict(owner_fees=None, future_exit_cost=None, round_trip_cost=None, pair_pnl=None,
                   cost_tiers=[dict(multiple=k, net_pair_pnl=None, full_cost=None) for k in (1, 2, 3)],
                   actual_order_allowed=False, activation_allowed=False, observed_fills=False,
                   snapshots_simultaneous_verified=False, capital_return=None)
    for rules, snapshot in ((left_rules, left_book), (right_rules, right_book)):
        if (rules['venue'], rules['symbol']) != (snapshot['venue'], snapshot['symbol']):
            raise ValueError('rule/book identity mismatch')
    if left_rules['key'] != right_rules['key'] or left_rules['venue'] == right_rules['venue']:
        raise ValueError('same declared economic key on distinct venues required')
    with localcontext() as ctx:
        ctx.prec = 80
        a, b = (Fraction(amount(r['base_quantum'])) for r in (left_rules, right_rules))
        quantum = Fraction(lcm(a.numerator, b.numerator), gcd(a.denominator, b.denominator))
        step = Decimal(quantum.numerator) / Decimal(quantum.denominator)
        qty = (amount(notional) // (max(left_book['mid'], right_book['mid']) * step)) * step
        if qty <= 0:
            return dict(unknown, state='UNSCORED', reason='common_lot_exceeds_mid_notional_target')
        for rules in (left_rules, right_rules):
            if rules['minimum_contracts'] is None or qty / amount(rules['multiplier_base']) < amount(rules['minimum_contracts']):
                return dict(unknown, state='UNSCORED', reason='minimum_order_quantity_unknown_or_not_met')
        def walk(snapshot, side):
            remaining, paid = qty, Decimal(0)
            for price, available in snapshot[side]:
                used = min(remaining, available); paid += used * price; remaining -= used
                if not remaining: break
            if remaining: return None
            mid_value = qty * snapshot['mid']
            cost = paid - mid_value if side == 'asks' else mid_value - paid
            return dict(quote_consideration=str(paid), vwap=str(paid / qty), book_cost_quote=str(cost))
        directions = []
        denominator = qty * (left_book['mid'] + right_book['mid'])
        for buyer, seller in ((left_book, right_book), (right_book, left_book)):
            buy, sell = walk(buyer, 'asks'), walk(seller, 'bids')
            if buy is None or sell is None:
                directions.append(dict(buy_venue=buyer['venue'], sell_venue=seller['venue'], state='UNSCORED',
                                       reason='insufficient_shown_depth', book_cost_quote=None, book_cost_bp=None))
            else:
                cost = Decimal(buy['book_cost_quote']) + Decimal(sell['book_cost_quote'])
                directions.append(dict(buy_venue=buyer['venue'], sell_venue=seller['venue'],
                    state='CONDITIONAL_SNAPSHOT_ARITHMETIC', buy=buy, sell=sell,
                    book_cost_quote=str(cost), book_cost_bp=str(10000 * cost / denominator)))
        state = 'CONDITIONAL_ASYNCHRONOUS_SNAPSHOTS' if any(d['state'] != 'UNSCORED' for d in directions) else 'UNSCORED'
        return dict(unknown, state=state, quantity_base=str(qty),
                    common_base_lot=str(step), target_mid_notional_per_leg=str(amount(notional)),
                    sum_entry_mid_notionals=str(denominator), bp_denominator='sum of both entry mid notionals, not account capital',
                    directions=directions)
